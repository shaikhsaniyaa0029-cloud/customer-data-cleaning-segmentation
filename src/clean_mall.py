"""Cleans Mall_Customers.csv using clean_pipeline.py (keep both files in the same folder).
Usage (from the repository root):
    python src/clean_mall.py data/raw/Mall_Customers.csv --out outputs/mall_cleaning
"""
import argparse
import pandas as pd
import clean_pipeline as c

# Column names below are AFTER auto-standardizing the headers:
#   CustomerID -> customerid | Annual Income (k$) -> annual_income_k
#   Spending Score (1-100) -> spending_score_1_100
c.SCHEMA = {
    "customerid":            {"type": "str",      "required": True, "key": True},
    "gender":                {"type": "category", "required": False,
                              "map": {"male": "Male", "m": "Male", "female": "Female", "f": "Female"}},
    "age":                   {"type": "int",      "required": True, "rng": (0, 110)},
    "annual_income_k":       {"type": "float",    "required": True, "rng": (0, 1000)},
    "spending_score_1_100":  {"type": "int",      "required": True, "rng": (1, 100)},
}

ap = argparse.ArgumentParser()
ap.add_argument("path", nargs="?", default="data/raw/Mall_Customers.csv")
ap.add_argument("--out", default="outputs/mall_cleaning")
args = ap.parse_args()
c.run(pd.read_csv(args.path, dtype=str, keep_default_na=False), outdir=args.out)
