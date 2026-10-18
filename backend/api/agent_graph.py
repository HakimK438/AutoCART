"""
Saathi's brain: a small LangGraph agent. Fast by design: almost every answer is built from the database in milliseconds.

    classify ─► buy / ack / greet / bye ─────────────────────────► END
        ├─► ask (a question about one product) ──────────────────► END   (or on to search when no product is meant)
        ├─► compare / contact / detail ──────────────────────────► END
        └─► retrieve ─► answer ──────────────────────────────────► END

Understanding is layered, cheapest first:
  1. nlu.py: budgets ("under 2k"), sorting ("cheapest"), question types ("warranty?"), "it / the second one", Hinglish.
  2. Spelling repair against the catalogue's own words ("airpodes" -> "airdopes").
  3. Search: brand and name matching, plus (when ready) a free local embedding model for meaning ("something for a run").
  4. product_qa.py answers questions about a product from its own data, and gives a phone number when a detail is not there.
  5. A language model (Gemini/Groq) is only a last resort for questions nothing above could place. It never slows a normal answer.

The embedding index loads in the background and caches its vectors on disk, so a request never waits for it:
until it is ready, search uses keywords. Prices, stock and ratings are always re-read from the database.
"""

import hashlib
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from . import nlu, product_qa
from .agents.llm_provider import UnifiedLLMProvider
from .models import Product
from .product_qa import POLICY, product_dict

log = logging.getLogger(__name__)
_llm = UnifiedLLMProvider()
CACHE_FILE = Path(__file__).resolve().parents[1] / '.cache' / 'saathi_vectors.npz'

STOP = set('a an the i me my to for of in on and or is are with want need looking find show give get please some any good best can you do does it this that under below within upto budget rs'.split())
NUMBERS = {'first': 0, '1st': 0, 'one': 0, 'second': 1, '2nd': 1, 'two': 1, 'third': 2, '3rd': 2, 'three': 2, 'fourth': 3, '4th': 3}
# Words that carry a question or a request but never name a product.
FILLER = set('''was were am be been its shall have has had what which who how when where why long much many tell details detail review reviews rating ratings rated bad worth
buying buy warranty guarantee battery life backup stock available availability price cost delivery deliver return returns refund seller sold by near there also too really very just
only quality better compare vs versus difference storage ram display screen camera colour color size weight material processor payment cod upi emi store shop brand yes no ok hi hello
number phone call contact if so about them these those would could will should did im ive ill like let know whether tell
work works working take takes time soon fast quick quickly does'''.split())
GENERIC = set('product products item items something anything stuff thing things gift gifts option options idea ideas popular suggest recommend recommendation us'.split())
POINTER = re.compile(r'\b(it|this|that|these|those|first|second|third|1st|2nd|3rd|last|cheaper|cheapest|same one|this one|that one)\b')


class State(TypedDict, total=False):
    message: str
    name: str
    memory: str
    last_cards: List[Dict[str, Any]]
    loc: Optional[Dict[str, Any]]
    intent: str
    budget: Optional[int]
    budget_min: Optional[int]
    sort: str
    products: List[Dict[str, Any]]
    passages: List[str]
    reply: str
    provider: str
    actions: List[str]
    buy_id: str
    over_budget: bool
    contact: Optional[Dict[str, Any]]
    fallback: str
    kind: str   # the kind of product asked for ('phone', 'laptop'...)
    alt: str    # 'none': we have none of what was named, these are the same kind from other brands. 'topup': a few of them were added


# ---------------------------------------------------------------- retrieval --

class Index:
    """Products and policy passages, searchable by keyword at once and by meaning once the embedding vectors are ready."""

    def __init__(self):
        self.lock = threading.Lock()
        self.docs: List[Dict[str, Any]] = []
        self.vecs = None
        self.key = None
        self.checked = 0.0
        self.embedding = False
        self.model = None
        self.model_failed = os.getenv('AUTOCART_DISABLE_EMBEDDINGS') == '1'

    @staticmethod
    def _product_text(p: Product) -> str:
        specs = ' '.join(f'{k} {v}' for k, v in (p.specifications or {}).items()) if isinstance(p.specifications, dict) else ''
        return f'{p.name}. {p.brand}. {p.category}. {(p.description or "")[:300]} {specs}'[:700]

    def _load_docs(self):
        key = (Product.objects.count(), Product.objects.order_by('-id').values_list('id', flat=True).first() or '')
        if key == self.key:
            return
        products = list(Product.objects.all())
        docs = [{'kind': 'product', 'id': p.id, 'text': self._product_text(p)} for p in products]
        docs += [{'kind': 'policy', 'id': k, 'text': t} for k, t in POLICY]
        with self.lock:
            self.docs, self.vecs, self.key = docs, None, key
        self._start_embedding(docs)

    def refresh(self):
        """Reload the documents when the catalogue changed (two cheap queries to find out)."""
        self._load_docs()

    def _embedder(self):
        if self.model is None and not self.model_failed:
            try:
                from fastembed import TextEmbedding
                self.model = TextEmbedding('BAAI/bge-small-en-v1.5')
            except Exception as e:  # no network, no model: keywords only
                log.warning('Embedding model unavailable, using keyword search: %s', e)
                self.model_failed = True
        return self.model

    def _start_embedding(self, docs):
        if self.model_failed or self.embedding:
            return
        self.embedding = True
        threading.Thread(target=self._embed, args=(docs,), daemon=True).start()

    def _embed(self, docs):
        """Background: embed every document, reusing vectors cached on disk so a restart takes seconds, not a minute."""
        try:
            import numpy as np
            model = self._embedder()
            if model is None:
                return
            hashes = [hashlib.sha1(d['text'].encode()).hexdigest() for d in docs]
            cache: Dict[str, Any] = {}
            try:
                if CACHE_FILE.exists():
                    with np.load(CACHE_FILE, allow_pickle=False) as z:
                        cache = dict(zip(z['hashes'].tolist(), z['vecs']))
            except Exception:
                cache = {}
            missing = [i for i, h in enumerate(hashes) if h not in cache]
            if missing:
                fresh = list(model.embed([docs[i]['text'] for i in missing]))
                for i, v in zip(missing, fresh):
                    vec = np.array(v, dtype='float32')
                    cache[hashes[i]] = vec / (np.linalg.norm(vec) + 1e-9)
                try:
                    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                    keep = list(dict.fromkeys(hashes))
                    np.savez(CACHE_FILE, hashes=np.array(keep), vecs=np.stack([cache[h] for h in keep]))
                except Exception as e:
                    log.warning('Could not save the embedding cache: %s', e)
            vecs = np.stack([cache[h] for h in hashes])
            with self.lock:
                if self.docs is docs:  # the catalogue did not change meanwhile
                    self.vecs = vecs
        except Exception as e:
            log.warning('Embedding failed, keeping keyword search: %s', e)
        finally:
            self.embedding = False

    def search(self, query: str, kind: str, k: int = 12):
        self.refresh()
        with self.lock:
            docs, vecs = self.docs, self.vecs
        rows = [(i, d) for i, d in enumerate(docs) if d['kind'] == kind]
        if vecs is not None and self.model is not None:
            import numpy as np
            q = np.array(list(self.model.query_embed([query]))[0], dtype='float32')
            q /= np.linalg.norm(q) + 1e-9
            scored = [(float(vecs[i] @ q), d) for i, d in rows]
        else:
            words = {w for w in re.findall(r'[a-z0-9]+', query.lower()) if w not in STOP and len(w) > 2}
            scored = [(len(words & set(re.findall(r'[a-z0-9]+', d['text'].lower()))) / (len(words) or 1), d) for _, d in rows]
        scored.sort(key=lambda x: -x[0])
        return scored[:k]

    @property
    def semantic(self) -> bool:
        return self.vecs is not None and self.model is not None


INDEX = Index()


def warm_up():
    """Load the index in the background when the server starts, so even the first chat is quick."""
    threading.Thread(target=INDEX.refresh, daemon=True).start()


# ------------------------------------------------------- brand-aware matching --

BRAND_ALIAS = {'iphone': 'apple', 'ipad': 'apple', 'macbook': 'apple', 'galaxy': 'samsung', 'redmi': 'xiaomi', 'pixel': 'google', 'airpods': 'apple'}
VERBS = set('buy order purchase place now cart add me mera mujhe karo kar de dena chahiye want get pls plz the'.split())
# Everyday words shoppers use, mapped to the words our catalogue uses.
SYNONYMS = {
    'earphones': 'earbuds', 'earphone': 'earbuds', 'tws': 'earbuds', 'buds': 'earbuds', 'headset': 'headphones', 'headphone': 'headphones',
    'mobile': 'smartphone', 'mobiles': 'smartphone', 'phones': 'smartphone', 'cellphone': 'smartphone', 'tv': 'television', 'telly': 'television',
    'notebook': 'laptop', 'laptops': 'laptop', 'sneakers': 'shoes', 'trainers': 'shoes', 'specs': 'sunglasses', 'shades': 'sunglasses',
    'fridge': 'refrigerator', 'mixie': 'mixer', 'kurti': 'kurta', 'tee': 't-shirt', 'tshirt': 't-shirt', 'perfume': 'fragrance', 'scent': 'fragrance',
    'watches': 'watch', 'smartwatches': 'smartwatch', 'bottle': 'bottle', 'flask': 'flask', 'book': 'book', 'novel': 'book',
}


class Vocab:
    """Every word in the catalogue (product names, brands, categories). Used to fix typos like 'airpodes' -> 'airdopes'."""

    def __init__(self):
        self.key, self.words, self.checked = None, set(), 0.0

    def get(self):
        key = (Product.objects.count(), Product.objects.order_by('-id').values_list('id', flat=True).first())
        if key != self.key:
            words = set()
            for name, brand, cat in Product.objects.values_list('name', 'brand', 'category'):
                words.update(re.findall(r'[a-z0-9]+', f'{name} {brand} {cat}'.lower()))
            self.key, self.words = key, {w for w in words if len(w) > 2}
        return self.words


VOCAB = Vocab()


COMMON = set('''first second third fourth fifth last next one two three four five show cheap cheaper cheapest best top price prices more less other
another something anything gift gifts for what where when which how please thanks thank need needs looking track return returns cancel delivery deliver
much many very really also just like love nice good great new old same different color colour size small large big medium black white blue red green
pink grey gray brown women woman men man kids girl boy family home work office daily today tomorrow week month year offer offers deal deals sale discount
rating rated review reviews stock available quality cost costs worth recommend suggest help with without from than then them they their there here'''.split())


def correct(text: str) -> str:
    """Spell-corrects a shopper's message against the catalogue words, and swaps everyday words for catalogue ones.
    Short words, numbers and ordinary English words are left alone. If the shopper named a brand, that brand's
    product words are tried first, so 'boat airpodes' becomes 'boat airdopes', not Apple AirPods."""
    import difflib
    vocab = VOCAB.get()
    brand = detect_brand(text)
    brand_words = set()
    if brand:
        for name in Product.objects.filter(brand__iexact=brand).values_list('name', flat=True):
            brand_words.update(w for w in re.findall(r'[a-z0-9]+', name.lower()) if len(w) > 2)
    out = []
    for w in re.findall(r'[a-z0-9]+', text.lower()):
        w = SYNONYMS.get(w, w)
        if (len(w) >= 4 and not w.isdigit() and w not in vocab and w not in STOP and w not in VERBS and w not in COMMON
                and w not in FILLER and w not in NUMBERS and w not in BRAND_ALIAS):
            near = (difflib.get_close_matches(w, brand_words, n=1, cutoff=0.7) if brand_words else []) or \
                difflib.get_close_matches(w, vocab, n=1, cutoff=0.8 if len(w) < 6 else 0.75)
            if near:
                w = near[0]
        out.append(w)
    return ' '.join(out)


def _tokens(text: str) -> List[str]:
    return [w for w in re.findall(r'[a-z0-9]+', text.lower()) if w not in STOP and w not in VERBS and w not in NUMBERS]


def _named_tokens(text: str) -> List[str]:
    """The words of a message that could name a product ("is the boat airdopes 141 good?" -> boat airdopes 141)."""
    q = nlu.clean_query(text)
    return [w for w in re.findall(r'[a-z0-9]+', q) if len(w) > 1 and w not in FILLER and w not in STOP and w not in VERBS and w not in NUMBERS and w not in GENERIC]


def detect_brand(text: str) -> str:
    """The catalogue brand the customer named, or '' when none. Matches whole words so 'one' never means OnePlus."""
    low = ' ' + ' '.join(re.findall(r'[a-z0-9&.]+', text.lower())) + ' '
    best = ''  # a brand named outright wins over a product word that hints at one ("boat airpods" is boAt)
    for b in Product.objects.exclude(brand='').values_list('brand', flat=True).distinct():
        key = ' '.join(re.findall(r'[a-z0-9&.]+', b.lower()))
        if key and f' {key} ' in low and len(key) > len(best):
            best = b
    if best:
        return best
    for alias, brand in BRAND_ALIAS.items():
        if f' {alias} ' in low and Product.objects.filter(brand__iexact=brand).exists():
            return Product.objects.filter(brand__iexact=brand).values_list('brand', flat=True).first()
    return ''


ACCESSORY = {'charger', 'case', 'cover', 'cable', 'adapter', 'protector', 'strap', 'stand', 'holder', 'pouch', 'skin', 'accessories'}

# The catalogue only has broad categories ("Electronics"), so the KIND of a product (phone, laptop, speaker...) is read from its name.
# Order matters: an "iPhone charger" is an accessory, not a phone, and a "Galaxy Tab" is a tablet, not a phone.
KIND_RULES = [
    ('accessory', r'\b(charger|case|cover|cable|adapter|protector|strap|stand|holder|pouch|skin|battery pack|power bank|airpower|screen guard|tempered)\b'),
    ('tablet', r'\b(ipad|tablet|tab)\b'),
    ('laptop', r'\b(laptop|macbook|notebook|chromebook|vivobook|zenbook|thinkpad|ideapad|inspiron|pavilion|aspire|xps)\b'),
    ('phone', r'\b(iphone|smartphone|phone|mobile|galaxy\s*(?:s|a|m|z|f|note)\s*\d+|redmi|poco|realme|oneplus|pixel\s*\d+|nokia)\b'),
    ('audio', r'\b(airpods|earbuds?|earphones?|headphones?|neckband|airdopes|buds)\b'),
    ('speaker', r'\b(speaker|homepod|soundbar|boombox|bullhorn|megaphone)\b'),
    ('watch', r'\b(smartwatch|watch|smart band|fitness band)\b'),
    ('tv', r'\b(television|tv)\b'),
    ('shoes', r'\b(shoes?|sneakers?|sandals?|slippers?|boots?|loafers?)\b'),
    ('camera', r'\b(camera|dslr|gopro)\b'),
]
KIND_LABEL = {'phone': 'phones', 'laptop': 'laptops', 'audio': 'earphones and headphones', 'tablet': 'tablets', 'speaker': 'speakers', 'watch': 'watches',
              'tv': 'TVs', 'shoes': 'shoes', 'camera': 'cameras'}


def _kind(text: str) -> str:
    low = text.lower()
    return next((kind for kind, rx in KIND_RULES if re.search(rx, low)), '')


def product_kind(p: Product) -> str:
    """'phone', 'laptop', 'speaker'... or '' when the name does not say."""
    return _kind(p.name)


def query_kind(text: str) -> str:
    """The kind of product a shopper asked for ("iphone", "phones" and "mobile" are all 'phone'), or '' when they named no kind (a brand alone, say)."""
    return _kind(' '.join(SYNONYMS.get(w, w) for w in re.findall(r'[a-z0-9]+', text.lower())))


KIND_WORDS = set('''phone phones smartphone smartphones mobile mobiles laptop laptops notebook tablet tablets headphones headphone earbuds earphones earphone speaker speakers
watch watches smartwatch tv television shoes camera cameras'''.split())  # a request for the kind itself, with no brand or model


def by_kind(found: List[Product], kind: str, brand: str = '') -> List[Product]:
    """Keeps only products of the kind asked for ("iphone" must not bring a HomePod, "iphone charger" must not bring a phone).
    A product whose name does not say its kind is kept only when it is from the brand the shopper named ("boat headphones" -> boAt Rockerz)."""
    if not kind:
        return found
    return [p for p in found if product_kind(p) == kind or (not product_kind(p) and brand and (p.brand or '').lower() == brand.lower())]


def _alt_queries(query: str) -> List[str]:
    """When a misspelt word could mean two catalogue words ("airpodes" is AirPods or Airdopes), the query rewritten with the other reading."""
    import difflib
    vocab, alts = VOCAB.get(), []
    for w in re.findall(r'[a-z0-9]+', query.lower()):
        if len(w) >= 5 and not w.isdigit() and w not in vocab and w not in STOP and w not in VERBS and w not in COMMON and w not in BRAND_ALIAS:
            for other in difflib.get_close_matches(w, vocab, n=3, cutoff=0.75)[1:]:
                alts.append(query.lower().replace(w, other))
    return alts[:2]


def match_products(query: str, limit: int = 5):
    """Same as _match, but a word that could be read two ways also surfaces the best product for the other reading, right after the first result."""
    brand, exact, found = _match(query, limit)
    for alt in _alt_queries(query):
        _, _, more = _match(alt, 2)
        extra = next((p for p in more if p.id not in {f.id for f in found}), None)
        if extra:
            found = found[:1] + [extra] + found[1:limit - 1]
            exact = False
    return brand, exact, found


def _match(query: str, limit: int = 5):
    """Returns (brand, exact, products). Only products of the named brand: if the exact model is missing, the closest models of that same brand."""
    query = correct(query)
    brand = detect_brand(query)
    toks = _tokens(query)
    if brand:  # drop the brand's own name; keep words like 'iphone' that also appear in product names
        bt = set(re.findall(r'[a-z0-9]+', brand.lower()))
        toks = [t for t in toks if t not in bt]
    qs = Product.objects.filter(brand__iexact=brand) if brand else Product.objects.all()
    scored = []
    for p in qs:
        name = set(re.findall(r'[a-z0-9]+', (p.name + ' ' + (p.category or '')).lower()))
        hit = [t for t in toks if t in name]
        if toks and not hit and not brand:
            continue
        weight = sum(2 if any(c.isdigit() for c in t) else 1 for t in hit)
        if name & ACCESSORY and not set(toks) & ACCESSORY:  # "iphone" means the phone, not its charger or case
            weight -= 0.5
        scored.append((weight, p.stock > 0, p.rating or 0, p, len(hit) == len(toks)))
    if toks and any(s[0] > 0 for s in scored):  # some products match the product word: the rest of the brand's range is not an answer ("iphone" -> a HomePod)
        scored = [s for s in scored if s[0] > 0]
    scored.sort(key=lambda x: (-x[0], not x[1], -x[2]))
    if not scored or (not brand and scored[0][0] == 0):
        return brand, False, []
    exact = bool(toks) and scored[0][4] and (len(scored) == 1 or scored[1][0] < scored[0][0])
    return brand, exact, [x[3] for x in scored[:limit]]


# -------------------------------------------------------------------- nodes --

ACK = r"\s*(done|ok(ay)?|k|yes|yeah|yep|sure|fine|cool|great|alright|signed in|logged in|i (have )?(signed|logged) in|haan|ha|theek hai|thik hai)\W*"
BYE = r"\s*(no|nope|nothing|nothing else|bye|goodbye|that'?s all|that is all|no thanks?|nahi)\W*"
MENU = r"\s*(menu|help|options|start|main menu|what can you do\??)\W*"
BUY_RE = r'\b(buy|order|purchase|get me|i want|want to buy)\b'
FAQ_RE = r'\b(deliver|delivery|return|refund|cancel|pay|payment|cod|cash on|pickup|pick up|track|policy|how (does|do|long)|warranty|seller|contact|coupon)\b'


def _is_greeting(t: str) -> bool:
    """A greeting with a typo ("heloo", "helo", "hii there" is handled above): one short word close to hello, hey or namaste that is not a catalogue word."""
    import difflib
    word = t.strip().strip('!.?,')
    if re.fullmatch(r'(hi+|hello|hey|hola|namaste|good day)( there| saathi| friend| team| everyone)', word):
        return True
    if not word or ' ' in word or len(word) > 9 or word in VOCAB.get():
        return False
    return bool(difflib.get_close_matches(word, ['hello', 'hey', 'namaste', 'thanks', 'hola', 'hiya'], n=1, cutoff=0.75))


def classify(state: State) -> State:
    msg = state['message']
    t = msg.lower()
    lo, hi = nlu.parse_budget(msg)
    sort = nlu.parse_sort(msg)
    out: State = {'budget': hi, 'budget_min': lo, 'sort': sort}
    has_filter = bool(hi or lo or sort)
    cards = [c for c in state.get('last_cards') or [] if c.get('type') == 'product']
    all_aspects = nlu.aspects(t)
    asks = all_aspects - {'compare'}
    pointer = bool(POINTER.search(t))
    intent = 'search'
    if re.fullmatch(r'\s*(?:press |option |no\.? |number |#)?([1-9])\W*', t) and cards:
        intent = 'buy'
    elif re.fullmatch(r"\s*(hi|hello|hey|hii+|namaste|good (morning|afternoon|evening)|thanks?( you)?|thank you)\W*", t) or re.fullmatch(MENU, t) or _is_greeting(t):
        intent = 'greet'
    elif re.fullmatch(ACK, t):
        intent = 'ack'
    elif re.fullmatch(BYE, t):
        intent = 'bye'
    elif nlu.wants_phone(t):
        intent = 'contact'
    elif nlu.needs_person(t):
        intent = 'detail'
    elif 'compare' in all_aspects:
        intent = 'compare'
    elif asks and not has_filter and (nlu.is_question(t) or pointer or re.search(r'\b(details? (of|about)|review of|tell me about|know about)\b', t)):
        named = bool(_named_tokens(msg))
        intent = 'faq' if (asks <= nlu.POLICY_ASPECTS and not named and not pointer) else 'ask'
    elif re.search(BUY_RE, t) and not re.search(r'\b(my order|track|status|cancel|return|refund)\b', t) and not (has_filter and re.search(r'\bi want\b', t) and not re.search(r'\bbuy\b', t)):
        intent = 'buy'
    elif re.search(FAQ_RE, t) and not re.search(r'\b(under|below|₹|rs)\b', t):
        intent = 'faq'
    out['intent'] = intent
    return out


MENU_ACTIONS = ['Find a gift under ₹1,500', 'Track my order', 'Return an item', 'How does delivery work?']


def greet(state: State) -> State:
    n = state.get('name')
    return {'reply': f"Hi{' ' + n if n else ''}! Tell me what you need in your own words, like \"boat earbuds under 2000\", \"cheapest laptop\" or \"is the iPhone 13 any good?\". "
                     "I can also track your orders, check stock near you and give you a number to call.",
            'actions': MENU_ACTIONS, 'provider': 'rules'}


def ack(state: State) -> State:
    prods = [c for c in state.get('last_cards') or [] if c.get('type') == 'product']
    if len(prods) == 1:  # "done" right after we showed one product: carry on with buying it
        return {'reply': 'Great, setting up that order now.', 'buy_id': prods[0]['id'], 'products': [], 'provider': 'rules', 'actions': []}
    if prods:
        return {'reply': f"Which one should I order? Type a number from **1** to **{len(prods)}**.", 'actions': [], 'provider': 'rules'}
    return {'reply': 'Great. What would you like next? Tell me what you need, or pick one below.', 'actions': MENU_ACTIONS, 'provider': 'rules'}


def bye(state: State) -> State:
    n = state.get('name')
    return {'reply': f"Happy shopping{', ' + n if n else ''}! I'm here whenever you need me.", 'actions': [], 'provider': 'rules'}


def _pick_from_last(text: str, cards: List[Dict[str, Any]]):
    """The product the customer points at from the last list ('2', 'the second one', 'buy it'). Never guesses:
    if the message names a product of its own ('buy boat airdopes'), the catalogue is searched instead."""
    prods = [c for c in cards if c.get('type') == 'product']
    if not prods:
        return None
    m = re.search(r'\b([1-9])\b', text)
    if m and int(m.group(1)) <= len(prods) and not re.search(r'[a-z]{3,}', re.sub(r'press|option|number|buy|order|the|one|no', '', text)):
        return prods[int(m.group(1)) - 1]
    names_something = bool([t for t in _tokens(text) if t not in ('it', 'this', 'that', 'one', 'ones')])
    if names_something:
        return None
    for word, idx in NUMBERS.items():
        if re.search(rf'\b{word}\b', text) and idx < len(prods):
            return prods[idx]
    if re.search(r'\b(it|this|that)\b', text) or len(prods) == 1:
        return prods[0]
    return None


def _numbered(prods) -> str:
    return '\n'.join(f"**{i}.** {p.name} · ₹{p.price:,.0f}" + ('' if p.stock > 0 else ' (out of stock)') for i, p in enumerate(prods, 1))


def buy(state: State) -> State:
    t = state['message'].lower()
    cards = state.get('last_cards') or []
    pick = _pick_from_last(t, cards)
    p = Product.objects.filter(id=pick['id']).first() if pick else None
    if not p:
        brand, exact, found = match_products(nlu.clean_query(state['message']) or state['message'])
        found = by_kind(found, query_kind(nlu.clean_query(state['message'])), brand)  # "buy iphone" lists phones, not the charger or the case
        if not found:
            what = f' from {brand}' if brand else ''
            return {'reply': f"I could not find anything{what} in our stores right now. Tell me the product or brand you want, like \"Nike running shoes\".", 'actions': ['Show me popular products'], 'provider': 'rules'}
        if exact and found[0].stock > 0:
            p = found[0]
        else:
            lead = f"I don't have that exact model, but here are the closest from **{brand}**:" if brand and not exact else 'Here is what matches:'
            return {'reply': f"{lead}\n{_numbered(found)}\n\n{'Tap **Buy now**' if len(found) == 1 else 'Tap **Buy now** on the one you want'}, and I will set up the order.", 'products': [product_dict(x) for x in found],
                    'actions': [str(i) for i in range(1, len(found) + 1)], 'provider': 'rules'}
    if p.stock <= 0:
        _, _, alts = match_products(f'{p.brand} {p.category}')
        alts = [a for a in alts if a.stock > 0 and a.id != p.id][:3]
        return {'reply': f"{p.name} is out of stock right now." + (f" Closest available from **{p.brand}**:\n{_numbered(alts)}\n\nTap **Buy now** on one." if alts else ''),
                'actions': [str(i) for i in range(1, len(alts) + 1)], 'provider': 'rules', 'products': [product_dict(x) for x in alts]}
    return {'reply': f'Found it: **{p.name}** by {p.brand or "the seller"}, ₹{p.price:,.0f}, in stock. Check the order below and tap **Confirm order**.', 'buy_id': p.id, 'products': [product_dict(p)], 'provider': 'rules', 'actions': []}


# ---- product questions, comparison, phone numbers -----------------------------------------------------------

def _cards_to_products(cards: List[Dict[str, Any]]) -> List[Product]:
    """The products on screen, in the order shown. Order cards point at the product they carry."""
    ids = [c.get('id') for c in cards if c.get('type') == 'product'] or [c.get('productId') for c in cards if c.get('type') == 'order' and c.get('productId')]
    by_id = {p.id: p for p in Product.objects.filter(id__in=[i for i in ids if i])}
    return [by_id[i] for i in ids if i in by_id]


def _focus(state: State) -> Optional[Product]:
    """The one product the conversation is about right now (the single card on screen, if any)."""
    prods = _cards_to_products(state.get('last_cards') or [])
    return prods[0] if prods else None


def _follow_ups(p: Product, asked: set) -> List[str]:
    acts = ['Buy it'] if p.stock > 0 else []
    for aspect, label in (('reviews', 'Is it any good?'), ('stock', 'Is it in stock near me?'), ('warranty', 'Does it have a warranty?'), ('delivery', 'How fast can I get it?')):
        if aspect not in asked and len(acts) < 3:
            acts.append(label)
    return acts


def ask(state: State) -> State:
    """A question about one product: the one named in the message, else the one the shopper points at on screen."""
    msg, loc = state['message'], state.get('loc')
    asked = nlu.aspects(msg) - {'compare'}
    cards = [c for c in state.get('last_cards') or [] if c.get('type') in ('product', 'order')]
    prods = _cards_to_products(cards)
    toks = _named_tokens(msg)
    p: Optional[Product] = None
    if toks:
        _, exact, found = match_products(' '.join(toks))
        if found and (exact or len(found) == 1):
            p = found[0]
        elif not found and asked <= nlu.POLICY_ASPECTS:  # "how long does delivery take": no product is meant
            return {'fallback': 'faq', 'intent': 'faq'}
        else:  # several products fit (or none): treat it as a search so the shopper sees the options
            return {'fallback': 'search', 'intent': 'search'}
    elif prods:
        ref = nlu.reference(msg, len(prods))
        if ref in ('cheapest', 'best'):
            p = min(prods, key=lambda x: x.price) if ref == 'cheapest' else max(prods, key=lambda x: x.rating or 0)
        elif ref is not None:
            p = prods[int(ref)]
        else:
            p = prods[0]
    if p is None:
        if asked <= nlu.POLICY_ASPECTS:
            return {'fallback': 'faq', 'intent': 'faq'}
        return {'reply': 'Which product do you mean? Tell me its name, or ask me to find something first and then ask about the one you like.',
                'actions': ['Find a gift under ₹1,500', 'Show me popular products'], 'provider': 'rules'}
    res = product_qa.answer_about(p, asked or {'reviews'}, loc)
    out: State = {'reply': res['reply'], 'products': [product_dict(p)], 'actions': _follow_ups(p, asked), 'provider': 'rules'}
    if res['missing'] or nlu.needs_person(msg):
        out['contact'] = product_qa.contact_card(p, loc, 'Ask the seller directly')
    return out


def compare(state: State) -> State:
    msg = state['message']
    prods: List[Product] = []
    named = [part for part in re.split(r'\b(?:vs\.?|versus|compared to|compare|and|with|or|,)\b', msg.lower()) if _named_tokens(part)]
    for part in named[:3]:
        _, exact, found = match_products(' '.join(_named_tokens(part)), 3)
        if found and (exact or len(found) == 1) and found[0].id not in {x.id for x in prods}:
            prods.append(found[0])
    if len(prods) < 2:
        shown = _cards_to_products(state.get('last_cards') or [])
        m = re.search(r'\b(?:first|top)\s+(two|2|three|3)\b', msg.lower())
        prods = shown[:(2 if m and m.group(1) in ('two', '2') else 3)]
    if len(prods) < 2:
        return {'reply': 'Tell me two products to compare, like "compare boat airdopes 141 and noise buds", or search first and I will compare what we find.',
                'actions': ['Find a gift under ₹1,500'], 'provider': 'rules'}
    return {'reply': product_qa.compare(prods), 'products': [product_dict(p) for p in prods], 'actions': [str(i) for i in range(1, len(prods) + 1)], 'provider': 'rules'}


def contact(state: State) -> State:
    """The shopper asked for a phone number: support, plus the store and seller of the product being discussed."""
    p = _focus(state)
    card = product_qa.contact_card(p, state.get('loc'))
    what = f' about **{p.name}**' if p else ''
    return {'reply': f'Here is who to call{what}. Support is open {product_qa.SUPPORT_HOURS}. Tap a number to call from your phone.', 'contact': card,
            'actions': [], 'provider': 'rules', 'products': [product_dict(p)] if p else []}


def detail(state: State) -> State:
    """A question too specific to answer reliably from a catalogue: bulk orders, invoices, compatibility, bargaining. A person should take it."""
    p = _focus(state)
    return {'reply': 'That is a detailed one (bulk orders, invoices, compatibility and negotiated prices need someone who can check with the seller), so I would rather not guess. '
                     'A quick call will get you a firm answer.', 'contact': product_qa.contact_card(p, state.get('loc'), 'Best answered by a person'),
            'actions': ['Talk to a person'], 'provider': 'rules', 'products': [product_dict(p)] if p else []}


# ---- search ---------------------------------------------------------------------------------------------------

def _within(p: Product, lo: Optional[int], hi: Optional[int]) -> bool:
    return (not hi or p.price <= hi) and (not lo or p.price >= lo)


def _order(prods: List[Product], sort: str, near: Dict[str, Any]) -> List[Product]:
    """Nearby and in stock first, then by what the shopper asked for (cheapest, best rated, biggest discount...)."""
    def discount(p):
        return (p.originalPrice - p.price) / p.originalPrice if p.originalPrice and p.originalPrice > p.price else 0

    keys = {
        'price_asc': lambda p: p.price, 'price_desc': lambda p: -p.price, 'discount': lambda p: -discount(p),
        'popular': lambda p: (not p.bestSeller, -(p.reviewCount or 0)), 'new': lambda p: (not p.newArrival, p.createdAt or ''),
    }
    rank = keys.get(sort, lambda p: -(p.rating or 0) * min(1, (p.reviewCount or 0) / 50 + 0.5))
    return sorted(prods, key=lambda p: (p.stock <= 0, bool(near) and p.id not in near, rank(p)))


def _diverse(prods: List[Product], n: int = 4) -> List[Product]:
    """One product per category first, so a vague request ("a gift under 1500") shows variety."""
    seen, first, rest = set(), [], []
    for p in prods:
        (rest if p.category in seen else first).append(p)
        seen.add(p.category)
    return (first + rest)[:n]


def retrieve(state: State) -> State:
    msg, loc = state['message'], state.get('loc')
    lo, hi, sort = state.get('budget_min'), state.get('budget'), state.get('sort') or ''
    q = correct(nlu.clean_query(msg))
    passages = [d['text'] for s, d in INDEX.search(q or msg, 'policy', 2) if s > (0.5 if INDEX.semantic else 0.2)]
    if state['intent'] == 'faq':
        return {'passages': passages or [t for _, t in POLICY[:2]], 'products': []}
    toks = [t for t in _tokens(q) if t not in GENERIC and t not in FILLER]
    kind = query_kind(q) or query_kind(nlu.clean_query(msg))  # "iphone", "phones", "mobile" -> 'phone'. Checked first: "phone" is a filler word, so toks can be empty
    if not toks and not kind:  # "show me popular products", "a gift under 1500": browse the shelves
        pool = [p for p in Product.objects.filter(stock__gt=0) if _within(p, lo, hi)]
        near = product_qa.near_map([p.id for p in pool], loc)
        ordered = _order(pool, sort or 'rating', near)
        return {'products': [product_dict(p) for p in _diverse(ordered)], 'passages': passages}
    if len(toks) == 1 and toks[0] not in VOCAB.get() and not toks[0].isdigit() and not detect_brand(q) and not query_kind(q):
        return {'products': [], 'passages': passages}  # one word we have never seen: say so, rather than showing look-alikes
    brand, _, found = match_products(q, 8)
    found = by_kind(found, kind, brand)
    if kind and kind != 'accessory' and not found and brand:  # "samsung phone": that brand's phones, even though no name says "phone"
        found = by_kind(list(Product.objects.filter(brand__iexact=brand)), kind, brand)
    if brand or found or kind:  # a company or a product word was named: those matches are the answer. Look-alikes by meaning must not
        prods = found   # join them, or the budget filter drops the real matches and keeps unrelated cheap items ("laptops under 50000" -> a pen)
    else:
        hits = INDEX.search(q, 'product', 14)
        ids = [d['id'] for s, d in hits if s > (0.5 if INDEX.semantic else 0.15)]
        by_id = {p.id: p for p in Product.objects.filter(id__in=ids)}
        prods = [by_id[i] for i in ids if i in by_id]
        for p in found:  # name matches are the most precise signal: keep them in the pool
            if p.id not in {x.id for x in prods}:
                prods.append(p)
    alt, extra_ids = '', set()
    if kind and kind != 'accessory':  # too few of what was asked for: add the same kind of product from other brands (best rated first), never a different kind
        close = [p for p in prods if _within(p, lo, hi) and p.stock > 0]
        if len(close) < 3:
            have = {p.id for p in prods}
            others = sorted((p for p in Product.objects.filter(stock__gt=0) if product_kind(p) == kind and p.id not in have and _within(p, lo, hi)),
                            key=lambda p: -(p.rating or 0))
            if others:
                extras = others[:4 - len(close)]
                prods, alt = prods + extras, ('topup' if close else 'none')
                extra_ids = {p.id for p in extras}
    if lo or hi:
        within = [p for p in prods if _within(p, lo, hi)]
        if not within and prods:  # nothing in budget: show the cheapest matches and say so, instead of an empty answer
            cheapest = sorted(prods, key=lambda p: p.price)[:3]
            return {'products': [product_dict(p) for p in cheapest], 'passages': passages, 'over_budget': True}
        prods = within
    near = product_qa.near_map([p.id for p in prods], loc)
    if not sort:  # keep the best name match on top, then order the rest by rating
        head = [p for p in found[:1] if p in prods]
        prods = head + _order([p for p in prods if p not in head], '', near)
    else:
        prods = _order(prods, sort, near)
    if extra_ids:  # what the shopper asked for first, the other brands' alternatives after it
        prods = [p for p in prods if p.id not in extra_ids] + [p for p in prods if p.id in extra_ids]
    shown = prods[:4]
    if all(t in KIND_WORDS for t in toks):  # "phones", "laptop": the shopper asked for the kind itself, so nothing here is a substitute
        alt = ''
    elif kind and alt != 'none' and any(any(c.isdigit() for c in t) and not any(t in set(re.findall(r'[a-z0-9]+', p.name.lower())) for p in shown) for t in toks):
        alt = 'nomodel'  # "iphone 17": no shown product carries that model number, so say these are only the closest
    return {'products': [product_dict(p) for p in shown], 'passages': passages, 'kind': kind, 'alt': alt}


SORT_LABEL = {'price_asc': 'cheapest first', 'price_desc': 'most premium first', 'rating': 'best rated first', 'discount': 'biggest discount first',
              'popular': 'most popular first', 'new': 'newest first'}


def _badges(prods: List[Dict[str, Any]], sort: str) -> None:
    """A short label on the products worth pointing out, written into the card dicts."""
    if not prods:
        return
    prods[0]['badge'] = {'price_asc': 'Lowest price', 'price_desc': 'Premium pick', 'discount': 'Biggest discount', 'popular': 'Most popular', 'new': 'Newest'}.get(sort, 'Top pick')
    if len(prods) > 1:
        cheapest = min(prods, key=lambda p: p['price'])
        best = max(prods, key=lambda p: p.get('rating') or 0)
        if cheapest is not prods[0] and not cheapest.get('badge'):
            cheapest['badge'] = 'Lowest price'
        if best is not prods[0] and not best.get('badge') and (best.get('rating') or 0) >= (prods[0].get('rating') or 0) + 0.2:
            best['badge'] = 'Best rated'


def _label(state: State) -> str:
    q = nlu.clean_query(state['message'])
    toks = [t for t in re.findall(r'[a-z0-9]+', q) if t not in GENERIC and t not in STOP]
    return ' '.join(toks)


SYSTEM = (
    "You are Saathi, the friendly shopping assistant of AutoCart, a marketplace of local Mumbai stores. "
    "Use ONLY the FACTS provided. Never invent products, prices, stock, discounts or policies. "
    "Keep it under 50 words, warm and plain. If the question is not about shopping, orders or our policies, say kindly what you can help with. "
    "If the facts do not answer it, say so and suggest calling the support number in the facts."
)


def answer(state: State) -> State:
    prods, passages = state.get('products') or [], state.get('passages') or []
    lo, cap, sort, name = state.get('budget_min'), state.get('budget'), state.get('sort') or '', state.get('name')
    loc = state.get('loc')
    if state['intent'] == 'faq':
        text = passages[0] if passages else 'I do not have that in my notes, and I would rather not guess. A person can tell you for sure.'
        out: State = {'reply': text, 'provider': 'retrieval', 'actions': ['Track my order', 'Return an item']}
        if not passages:
            out['contact'] = product_qa.contact_card(None, loc)
        return out
    if prods and state.get('over_budget'):
        limit = f'under ₹{cap:,}' if cap else f'above ₹{lo:,}'
        return {'reply': f"Nothing matches {limit} right now. The closest options are below, from ₹{prods[0]['price']:,.0f}. Tell me another budget and I will look again.",
                'provider': 'rules', 'actions': ['Show cheaper options', 'Show me popular products']}
    if prods:
        _badges(prods, sort)
        near = product_qa.near_map([p['id'] for p in prods], loc)
        for p in prods:
            if p['id'] in near:
                p['near'] = near[p['id']]
        top = prods[0]
        what = _label(state)
        scope = (f' under ₹{cap:,}' if cap and not lo else f' between ₹{lo:,} and ₹{cap:,}' if cap and lo else f' above ₹{lo:,}' if lo else '')
        label = KIND_LABEL.get(state.get('kind') or '', 'products')
        if state.get('alt') == 'none':  # we have none of what was named: say so, and offer the same kind from other brands
            head = f"We don't have **{what}** right now{scope}. Here {'is' if len(prods) == 1 else 'are'} {len(prods)} other {label[:-1] if len(prods) == 1 and label.endswith('s') else label} you may like."
        elif state.get('alt') == 'nomodel':  # the exact model is not stocked: these are the closest
            head = f"I don't have **{what}** exactly{scope}. Here {'is the closest' if len(prods) == 1 else f'are the {len(prods)} closest'}."
        else:
            more = f", plus similar {label} from other brands" if state.get('alt') == 'topup' else ''
            head = f"Here {'is' if len(prods) == 1 else 'are'} {len(prods)} option{'s' if len(prods) > 1 else ''}{' for **' + what + '**' if what else ''}{scope}{more}{', ' + SORT_LABEL[sort] if sort else ''}."
        rating = f", {top['rating']:.1f}★" + (f" from {top['reviewCount']:,} reviews" if top.get('reviewCount') else '') if top.get('rating') else ''
        off = f", ₹{top['originalPrice'] - top['price']:,.0f} off" if top.get('originalPrice') and top['originalPrice'] > top['price'] else ''
        pick = f"My pick: **{top['name']}** at ₹{top['price']:,.0f}{off}{rating}."
        where = f" It is at **{top['near']['store']}**, {top['near']['km']} km from you." if top.get('near') else ''
        reply = f'{head}\n{pick}{where}\nAsk me anything about them (reviews, warranty, stock near you), or tap Buy now.'
        return {'reply': reply, 'provider': 'rules', 'products': prods, 'actions': [str(i) for i in range(1, len(prods) + 1)] + ['Show cheaper options']}
    # Nothing matched. Only now is a language model worth waiting for: it can still place a vague or off-topic question.
    fallback = {'reply': f"I could not find a match{f' under ₹{cap:,}' if cap else ''}. Try another word or a higher budget, or call us and a person will help you find it.",
                'provider': 'rules', 'contact': product_qa.contact_card(None, loc), 'actions': ['Show me popular products', 'Talk to a person']}
    if _llm.is_configured:
        facts = '\n'.join([f'POLICY: {t}' for _, t in POLICY[:6]] + [f'SUPPORT PHONE: {product_qa.SUPPORT_PHONE} ({product_qa.SUPPORT_HOURS})'])
        out = _llm.generate(SYSTEM, f"Customer first name: {name or 'unknown'}\nWhat we know about them: {state.get('memory') or 'nothing yet'}\nFACTS:\n{facts}\nQUESTION: {state['message']}", 0.3, 200)
        if out.get('text'):
            return {**fallback, 'reply': out['text'].strip(), 'provider': out['provider']}
    return fallback


def _route(state: State) -> str:
    return {'buy': 'buy', 'greet': 'greet', 'ack': 'ack', 'bye': 'bye', 'ask': 'ask', 'compare': 'compare', 'contact': 'contact', 'detail': 'detail'}.get(state['intent'], 'retrieve')


def _after_ask(state: State) -> str:
    return 'retrieve' if state.get('fallback') else END


def _build():
    g = StateGraph(State)
    for name, fn in (('classify', classify), ('greet', greet), ('ack', ack), ('bye', bye), ('buy', buy), ('ask', ask), ('compare', compare),
                     ('contact', contact), ('detail', detail), ('retrieve', retrieve), ('answer', answer)):
        g.add_node(name, fn)
    g.add_edge(START, 'classify')
    g.add_conditional_edges('classify', _route, {k: k for k in ('buy', 'greet', 'ack', 'bye', 'ask', 'compare', 'contact', 'detail', 'retrieve')})
    g.add_conditional_edges('ask', _after_ask, {'retrieve': 'retrieve', END: END})
    g.add_edge('retrieve', 'answer')
    for end in ('greet', 'ack', 'bye', 'buy', 'compare', 'contact', 'detail', 'answer'):
        g.add_edge(end, END)
    return g.compile()


GRAPH = _build()


def run(message: str, name: str = '', memory: str = '', last_cards: Optional[List[Dict[str, Any]]] = None, loc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run the agent for one customer message. Returns the same shape the chat endpoint already uses."""
    out = GRAPH.invoke({'message': message, 'name': name, 'memory': memory, 'last_cards': last_cards or [], 'loc': loc})
    return {'agent': 'saathi-langgraph', 'reply': out.get('reply', ''), 'products': out.get('products') or [], 'suggestedActions': out.get('actions') or [],
            'llmProvider': out.get('provider', 'retrieval'), 'buyProductId': out.get('buy_id', ''), 'intent': out.get('intent'), 'contact': out.get('contact')}
