"""
Plain-language understanding for Saathi, the shopping assistant. No model download, no network: it runs in a millisecond.

It turns a sentence into the parts the rest of the assistant needs:
    budget     "under 2k", "between 500 and 1500", "around 1.5 lakh"     -> (low, high)
    sort       "cheapest laptop", "best rated", "latest"                  -> price_asc | price_desc | rating | discount | popular | new
    aspects    "does it have warranty", "battery life?", "in stock?"      -> {'warranty', 'battery', 'stock', ...}
    reference  "it", "the second one", "the cheaper one"                  -> how the shopper points at a product already on screen
    kind       is it a question, a request for a phone number, something too detailed for a bot?

Hinglish helpers (sasta, kitna, dikhao, ...) are mapped to the English words used below.
"""

import re
from typing import Dict, Optional, Set, Tuple

HINGLISH = {
    'sasta': 'cheap', 'sasti': 'cheap', 'sastha': 'cheap', 'kitna': 'price', 'kitne': 'price', 'kimat': 'price', 'dikhao': 'show', 'dikha': 'show',
    'batao': 'tell', 'chahiye': 'want', 'chahie': 'want', 'wapas': 'return', 'kharidna': 'buy', 'lena': 'buy', 'milega': 'available',
}

UNIT = {'k': 1_000, 'thousand': 1_000, 'lakh': 100_000, 'lac': 100_000, 'l': 100_000, 'crore': 10_000_000, 'cr': 10_000_000}
_AMT = r'(?:rs\.?|inr|₹)?\s*(\d[\d,]*(?:\.\d+)?)\s*(k|thousand|lakhs?|lacs?|l|crores?|cr)?\b'


def amount(num: str, unit: Optional[str]) -> int:
    """'1,499' -> 1499, '1.5' + 'lakh' -> 150000."""
    value = float(num.replace(',', ''))
    key = (unit or '').lower().rstrip('s')
    return int(round(value * UNIT.get(key, 1)))


def parse_budget(text: str) -> Tuple[Optional[int], Optional[int]]:
    """(low, high) in rupees. Either may be None. Model numbers such as "iphone 13" are never read as a price."""
    t = text.lower()
    m = re.search(rf'between\s+{_AMT}\s+(?:and|to|&|-)\s+{_AMT}', t)
    if m:
        a, b = amount(m.group(1), m.group(2) or m.group(4)), amount(m.group(3), m.group(4))
        return (min(a, b), max(a, b))
    m = re.search(rf'{_AMT}\s*(?:-|to)\s*{_AMT}\s*(?:rs|rupees|₹|k)?', t)
    if m and (m.group(2) or m.group(4) or len(m.group(1).replace(',', '')) >= 3):
        a, b = amount(m.group(1), m.group(2) or m.group(4)), amount(m.group(3), m.group(4))
        if a >= 100 and b >= 100:
            return (min(a, b), max(a, b))
    m = re.search(rf'(?:under|below|less than|within|upto|up to|max(?:imum)?|not more than|at most|cheaper than|budget(?: of)?|<=?)\s*{_AMT}', t)
    if m:
        return (None, amount(m.group(1), m.group(2)))
    m = re.search(rf'(?:above|over|more than|at least|min(?:imum)?|starting (?:from|at)|>=?)\s*{_AMT}', t)
    if m:
        return (amount(m.group(1), m.group(2)), None)
    m = re.search(rf'(?:around|about|approx(?:imately)?|near|close to)\s*{_AMT}', t)
    if m:
        mid = amount(m.group(1), m.group(2))
        return (int(mid * 0.75), int(mid * 1.25))
    m = re.search(rf'\b(?:for|in)\s*{_AMT}\s*(?:rs|rupees|rupee|₹|bucks)\b', t)
    if m:
        return (None, amount(m.group(1), m.group(2)))
    return (None, None)


SORTS = [
    ('price_asc', r'\b(cheap(?:est|er)?|lowest price|low price|least expensive|affordable|budget friendly|economical)\b'),
    ('price_desc', r'\b(most expensive|costliest|priciest|premium|high[- ]?end|flagship|luxury|expensive)\b'),
    ('discount', r'\b(biggest discount|best deal|best offer|most discount|on sale|discounted|deals?|offers?)\b'),
    ('new', r'\b(latest|newest|new arrivals?|just launched)\b'),
    ('popular', r'\b(popular|trending|best[- ]?sell(?:er|ing|ers)|most sold|top selling)\b'),
    ('rating', r'\b(best|top[- ]?rated|highest rated|best rated|well reviewed|good reviews?|top)\b'),
]
SORT_WORDS = {'cheapest', 'cheaper', 'cheap', 'lowest', 'affordable', 'premium', 'costliest', 'priciest', 'expensive', 'best', 'top', 'rated', 'latest',
              'newest', 'popular', 'trending', 'deal', 'deals', 'offer', 'offers', 'discounted', 'flagship', 'luxury', 'highest', 'price'}


def parse_sort(text: str) -> str:
    t = text.lower()
    for key, rx in SORTS:
        if re.search(rx, t):
            return key
    return ''


# What a shopper can ask about one product. Each aspect: words that signal it.
ASPECTS: Dict[str, str] = {
    'warranty': r'warrant|guarantee|guarantie',
    'return': r'\b(return|refund|exchange|replace(ment)?)\b',
    'battery': r'battery|backup|mah\b|charging|charge time|playtime|play time',
    'storage': r'\bstorage\b|\brom\b|\b\d+\s?(gb|tb)\b',
    'ram': r'\bram\b',
    'display': r'display|screen|resolution|\binch(es)?\b|amoled|oled|refresh rate',
    'camera': r'camera|megapixel|\bmp\b|selfie',
    'colour': r'colou?rs?\b|shade',
    'size': r'\bsize|dimension|\bfit\b|length|width|height|capacity|litre|\bml\b',
    'weight': r'weigh|heavy|lightweight',
    'material': r'material|made of|made from|fabric|leather|cotton|stainless|plastic|ingredient',
    'processor': r'processor|\bcpu\b|chipset|snapdragon|bionic|\bchip\b',
    'delivery': r'deliver|arrive|reach me|shipping|dispatch|how soon|how long',
    'stock': r'in stock|out of stock|availab|\bstock\b|\bleft\b|\bavail\b',
    'price': r'\bprice\b|\bcost\b|how much|\brate\b|discount|\bemi\b|mrp',
    'reviews': r'review|rating|rated|\bgood\b|\bbad\b|reliable|quality|feedback|recommend|should i (buy|get)|worth (it|buying|the)|durable|\bdetails?\b|tell me about|about (it|this|that)',
    'seller': r'\bseller\b|sold by|who sells|which store|\bshop\b|brand|manufactur',
    'payment': r'cash on delivery|\bcod\b|pay on delivery|\bupi\b|pay online|pay at (the )?store',
    'compare': r'\bcompare\b|\bvs\b|versus|difference between|which (one )?is better|better than',
}
# Aspects answered from our policy text rather than a product's own data.
POLICY_ASPECTS = {'delivery', 'return', 'payment'}


def aspects(text: str) -> Set[str]:
    t = text.lower()
    return {k for k, rx in ASPECTS.items() if re.search(rx, t)}


QUESTION_START = re.compile(r'^\s*(is|are|was|do|does|did|can|could|will|would|should|what|which|who|whom|whose|when|where|why|how|any|tell me|give me details|show me details|kya|kaun|kab)\b', re.I)


def is_question(text: str) -> bool:
    return '?' in text or bool(QUESTION_START.search(text))


def wants_phone(text: str) -> bool:
    """Asking for a phone number: "seller phone number", "give me your number", "customer care number", "whatsapp"."""
    low = text.lower()
    if re.search(r'\b(phone|mobile|contact|helpline|customer care|support) (number|no\.?)|\bwhatsapp\b|\bhelpline\b', low):
        return True
    return bool(re.search(r'\bnumber\b', low) and re.search(r'\b(your|seller|store|shop|support|care|call)\b', low) and not re.search(r'\b(order|tracking|model|pin)\b', low))


# Questions too specific to answer from the catalogue. The assistant suggests a phone call instead of guessing.
DETAIL_RE = re.compile(
    r'\b(bulk|wholesale|gst invoice|gst bill|invoice for|corporate|custom(?:i[sz]e|ised|ized)?|engrav\w*|installation|install|compatib\w*|fits? (my|with)|will it work with|'
    r'demo|test drive|exchange offer|trade[- ]in|emi (plan|option)|no[- ]cost emi|negotiat\w*|bargain|discount for|lower the price|best price|service cent(?:re|er)|'
    r'repair|spare parts?|authentic|original|genuine|fake|imported|import duty|customs|ship abroad|international|out of india)\b', re.I)


def needs_person(text: str) -> bool:
    return bool(DETAIL_RE.search(text))


ORDINALS = {'first': 0, '1st': 0, 'second': 1, '2nd': 1, 'third': 2, '3rd': 2, 'fourth': 3, '4th': 3}


def reference(text: str, count: int) -> Optional[str]:
    """How the shopper points at one of `count` products on screen: an index as text ('0', '1'..), 'cheapest', 'best', or None.
    "it", "this" and "that" mean the first one."""
    t = text.lower()
    m = re.search(r'(?:\b(?:no\.?|number|option|#)\s*|^\s*)([1-9])\b', t)
    if m and int(m.group(1)) <= count:
        return str(int(m.group(1)) - 1)
    for word, idx in ORDINALS.items():
        if re.search(rf'\b{word}\b', t) and idx < count:
            return str(idx)
    if re.search(r'\blast\b', t) and count > 1:
        return str(count - 1)
    if re.search(r'\b(cheaper|cheapest|lowest priced?|least expensive)\b', t) and count > 1:
        return 'cheapest'
    if re.search(r'\b(best|top rated|highest rated|better one)\b', t) and count > 1:
        return 'best'
    if re.search(r'\b(it|this|that|this one|that one|the same|them)\b', t) or count == 1:
        return '0'
    return None


def clean_query(text: str) -> str:
    """The product words left in a sentence once budget, sorting and filler are removed: "cheapest laptop under 50k" -> "laptop"."""
    t = text.lower()
    if None not in parse_budget(text):  # a range such as "between 500 and 1500" or "1500-3000"
        t = re.sub(rf'(?:between\s+)?{_AMT}\s*(?:and|&|-|to)\s*{_AMT}\s*(?:rs|rupees|₹)?', ' ', t, count=1)
    t = re.sub(rf'(?:under|below|less than|within|upto|up to|max(?:imum)?|not more than|at most|cheaper than|budget(?: of)?|above|over|more than|at least|min(?:imum)?|around|about|approx(?:imately)?|for|in)\s*{_AMT}\s*(?:rs|rupees|rupee|₹)?', ' ', t)
    words = [HINGLISH.get(w, w) for w in re.findall(r"[a-z0-9][a-z0-9.+&'-]*", t)]
    return ' '.join(w for w in words if w and w not in SORT_WORDS)
