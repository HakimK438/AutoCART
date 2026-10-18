"""
Draws the fake Aadhaar (masked), PAN and bank-proof images used to test seller onboarding.

    python scripts/make_sample_documents.py

Writes data/sample_documents/seller3 .. seller7 (seller1 and seller2 were made earlier). Every image says "SAMPLE FOR TESTING ONLY",
every name, number, bank branch and address is made up, and Aadhaar shows only the last 4 digits, like the real masked card.
Safe to run again: it overwrites the same files with the same content.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import _bootstrap  # noqa: F401  (also gives DATA below)
from _bootstrap import DATA

OUT = DATA / 'sample_documents'
NOTE = 'SAMPLE FOR TESTING ONLY - NOT A REAL DOCUMENT'
FONTS = ['arial.ttf', 'Arial.ttf', 'LiberationSans-Regular.ttf', 'DejaVuSans.ttf']
BOLD = ['arialbd.ttf', 'Arial Bold.ttf', 'LiberationSans-Bold.ttf', 'DejaVuSans-Bold.ttf']

SELLERS = {
    'seller3': dict(name='Amit Prakash Joshi', father='PRAKASH JOSHI', dob='02/08/1988', sex='MALE', aadhaar='6034', pan='FGHPJ4471L',
                    address='8 Station Road, Borivali West, Mumbai, Maharashtra - 400092', business='Joshi Mobile Hub',
                    bank='State Bank of India', account='30987654321012', ifsc='SBIN0004321', branch='Borivali West'),
    'seller4': dict(name='Fatima Aslam Khan', father='ASLAM KHAN', dob='19/11/1992', sex='FEMALE', aadhaar='2759', pan='KLMPK8826R',
                    address='27 Market Road, Lokhandwala, Andheri West, Mumbai, Maharashtra - 400053', business='Khan Home Needs',
                    bank='ICICI Bank', account='012345678901', ifsc='ICIC0005678', branch='Andheri West'),
    'seller5': dict(name='Suresh Ramesh Patil', father='RAMESH PATIL', dob='05/06/1985', sex='MALE', aadhaar='9418', pan='PQRPP3309D',
                    address='5 LBS Marg, Ghatkopar West, Mumbai, Maharashtra - 400086', business='Patil Organics',
                    bank='Axis Bank', account='918020045678123', ifsc='UTIB0002468', branch='Ghatkopar West'),
    'seller6': dict(name='Kavita Anil Menon', father='ANIL MENON', dob='23/01/1990', sex='FEMALE', aadhaar='3846', pan='STUPM5517H',
                    address='33 Hill Road, Bandra West, Mumbai, Maharashtra - 400050', business='Menon Beauty Bazaar',
                    bank='Kotak Mahindra Bank', account='7412589630147', ifsc='KKBK0001357', branch='Bandra West'),
    'seller7': dict(name='Imran Yusuf Shaikh', father='YUSUF SHAIKH', dob='30/09/1987', sex='MALE', aadhaar='5172', pan='VWXPS6648M',
                    address='14 Station Road, Kurla West, Mumbai, Maharashtra - 400070', business='Shaikh Sports Mart',
                    bank='Bank of Baroda', account='29120100012345', ifsc='BARB0000784', branch='Kurla West'),
}


def font(names, size):
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    return ImageFont.load_default()


def card(path: Path, title: str, lines: list) -> None:
    """One plain card: bold title, one line per row, the red sample note at the bottom (same look as seller1 and seller2)."""
    h = 160 + 62 * len(lines) + 70
    img = Image.new('RGB', (1900, h), '#fafaf5')
    d = ImageDraw.Draw(img)
    d.rectangle([10, 10, 1889, h - 11], outline='#444444', width=4)
    d.text((50, 40), title, font=font(BOLD, 38), fill='black')
    body = font(FONTS, 34)
    for i, line in enumerate(lines):
        d.text((50, 120 + 62 * i), line, font=body, fill='black')
    d.text((50, h - 55), NOTE, font=font(FONTS, 24), fill='#b00000')
    img.save(path)


def make(folder: str, s: dict) -> None:
    out = OUT / folder
    out.mkdir(parents=True, exist_ok=True)
    card(out / 'aadhaar_masked.png', 'Government of India',
         [s['name'], f"DOB: {s['dob']}", s['sex'], f"XXXX XXXX {s['aadhaar']}", f"Address: {s['address']}"])
    card(out / 'pan_card.png', 'INCOME TAX DEPARTMENT',
         ['Permanent Account Number', s['pan'], 'Name', s['name'].upper(), "Father's Name", s['father'], 'Date of Birth', s['dob']])
    card(out / 'bank_proof.png', s['bank'],
         [f"Account Holder Name: {s['business']}", f"Account No: {s['account']}", f"IFSC: {s['ifsc']}", f"Branch: {s['branch']}", 'Cancelled cheque'])


def main() -> None:
    for folder, s in SELLERS.items():
        make(folder, s)
        print(f"{folder}: {s['name']} / {s['business']}")


if __name__ == '__main__':
    main()
