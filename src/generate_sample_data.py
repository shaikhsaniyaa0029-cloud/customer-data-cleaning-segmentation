"""
Generate data/sample/messy_customers.csv: a reproducible, deliberately dirty dataset.
Injected problems: exact duplicates, duplicate IDs with partial records, placeholder nulls,
invalid emails, mixed date formats, impossible ages, inconsistent country names, currency strings.

Usage:  python src/generate_sample_data.py
"""
import os
from datetime import date, timedelta
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
N = 400
NAMES = ["Alice Smith", "Bob Jones", "Carol Lee", "Dev Patel", "Emma Brown", "Farid Khan",
         "Grace Kim", "Hiro Tanaka", "Isha Rao", "Jack Wilson", "Kavya Nair", "Liam Chen",
         "Maya Singh", "Noah Davis", "Olivia Martin", "Pooja Shah", "Quinn Taylor",
         "Rahul Mehta", "Sara Ali", "Tom Green"]
COUNTRIES = ["USA", "U.S.", "United States", "India", "Bharat", "UK", "United Kingdom", "england"]
NULLS = ["", "NA", "N/A", "-", "null"]
DATE_FMTS = ["%Y-%m-%d", "%m/%d/%Y", "%d %b %Y", "%B %d, %Y"]

def chance(p): return rng.random() < p

rows = []
for i in range(1, N + 1):
    name = NAMES[rng.integers(len(NAMES))]
    email = name.lower().replace(" ", ".") + f"{i}@example.com"
    d = date(2021, 1, 1) + timedelta(days=int(rng.integers(0, 365 * 5)))
    age = str(int(rng.integers(18, 76)))
    spend = f"{rng.uniform(20, 5000):.2f}"

    # --- inject dirt ---
    name = rng.choice([name.lower(), name.upper(), "  " + name + " ", name.replace(" ", "   "), name])
    if chance(.04): name = rng.choice(NULLS)
    if chance(.10): email = email.upper()
    if chance(.04): email = rng.choice(["bad-email", "john@@x", "no_at_sign.com"])
    if chance(.06): email = rng.choice(NULLS)
    ds = d.strftime(DATE_FMTS[rng.integers(len(DATE_FMTS))])
    if chance(.03): ds = rng.choice(["garbage", "", "N/A"])
    if chance(.01): ds = "2031-01-01"                       # future date
    if chance(.05): age = age + ".0"
    if chance(.03): age = "unknown"
    if chance(.015): age = rng.choice(["-5", "250"])        # impossible
    if chance(.04): age = ""
    country = COUNTRIES[rng.integers(len(COUNTRIES))] if not chance(.05) else ""
    if chance(.25): spend = f"${float(spend):,.2f}"
    elif chance(.1): spend = "USD " + spend
    if chance(.04): spend = "n/a"
    if chance(.04): spend = ""
    if chance(.01): spend = "9999999"                       # out of range
    rows.append([f"C{i:04d}", name, email, ds, age, country, spend])

df = pd.DataFrame(rows, columns=["Customer ID", "Name", "Email", "Signup Date", "Age", "Country", "Spend"])

# exact duplicates
df = pd.concat([df, df.sample(15, random_state=1)], ignore_index=True)
# duplicate IDs with a less complete record
part = df.sample(10, random_state=2).copy()
part.loc[:, ["Email", "Age", "Spend"]] = ""
df = pd.concat([df, part], ignore_index=True).sample(frac=1, random_state=3).reset_index(drop=True)

os.makedirs("data/sample", exist_ok=True)
df.to_csv("data/sample/messy_customers.csv", index=False)
print(f"Wrote data/sample/messy_customers.csv  ({len(df)} rows)")
