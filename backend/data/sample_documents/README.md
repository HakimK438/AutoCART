# Fake documents for testing seller onboarding

Seven sample sellers. Every image says "SAMPLE FOR TESTING ONLY". The names, numbers, banks and addresses are made up, and the Aadhaar shows only its last 4 digits (as a masked card does). `seller3` to `seller7` are drawn by `backend/scripts/make_sample_documents.py`.

| Folder | Person | Business (from bank proof) | Store address | Bank |
|---|---|---|---|---|
| `seller1/` | Rahul Mohan Sharma | Sharma Electronics | 12 Hill Road, Andheri East, Mumbai 400069 | HDFC |
| `seller2/` | Priya Suresh Nair | Priya Nair Fashions | 45 Linking Road, Bandra West, Mumbai 400050 | - |
| `seller3/` | Amit Prakash Joshi | Joshi Mobile Hub | 8 Station Road, Borivali West, Mumbai 400092 | State Bank of India |
| `seller4/` | Fatima Aslam Khan | Khan Home Needs | 27 Market Road, Lokhandwala, Andheri West, Mumbai 400053 | ICICI Bank |
| `seller5/` | Suresh Ramesh Patil | Patil Organics | 5 LBS Marg, Ghatkopar West, Mumbai 400086 | Axis Bank |
| `seller6/` | Kavita Anil Menon | Menon Beauty Bazaar | 33 Hill Road, Bandra West, Mumbai 400050 | Kotak Mahindra Bank |
| `seller7/` | Imran Yusuf Shaikh | Shaikh Sports Mart | 14 Station Road, Kurla West, Mumbai 400070 | Bank of Baroda |

Each folder has `aadhaar_masked.png`, `pan_card.png` and `bank_proof.png`. Use the three files from one folder together: the name, PAN, date of birth and address must agree across them, which is what the checks compare.

## How to test

1. Open `/seller/login?mode=create`, create a seller account (any new email, for example `seller3@test.com`).
2. On the apply page choose the three files from one folder. Each is read as you choose it.
3. Check the prefilled details (name, PAN, address, city, PIN, business name, bank, map pin), tick the box and submit.
4. Sign in as admin, open Sellers, then "Seller onboarding". It shows whether the application is ready to approve, needs documents, or needs a person to look.
5. Approve it, sign out and sign in again on `/seller/login`. You land on the seller dashboard with the store profile and map.

To see a **mismatch**, upload the Aadhaar from one folder with the PAN from another: the checks flag the different name and autopilot sends it to "needs your eye".

Close the browser halfway and sign in again on `/seller/login`: you carry on where you left off.
