"""
Data cleaning & structural validation pipeline (pandas).

Usage (from the repository root):
    python src/clean_pipeline.py data/sample/messy_customers.csv --out outputs/demo_cleaning
Outputs (in the --out folder, default ./cleaned_output):
    cleaned.csv       - analysis-ready data
    quarantine.csv    - rows that failed validation (kept, never silently dropped)
    audit_log.csv     - every change made, with counts
    report.txt        - before/after summary
Edit SCHEMA below to describe your columns.
"""
import argparse, os, re
import numpy as np
import pandas as pd

# ---------------------------------------------------------------- SCHEMA ----
# type: str | int | float | date | category | email | phone
# required: row is quarantined if missing   | rng: (min, max) for numerics
SCHEMA = {
    "customer_id": {"type": "str",      "required": True, "key": True},
    "name":        {"type": "str",      "required": True},
    "email":       {"type": "email",    "required": False},
    "signup_date": {"type": "date",     "required": True},
    "age":         {"type": "int",      "required": False, "rng": (0, 110)},
    "country":     {"type": "category", "required": False,
                    "map": {"usa": "US", "u.s.": "US", "united states": "US",
                            "india": "IN", "bharat": "IN", "uk": "GB",
                            "united kingdom": "GB", "england": "GB"}},
    "spend":       {"type": "float",    "required": False, "rng": (0, 1e6)},
}
NULL_TOKENS = {"", "na", "n/a", "nan", "null", "none", "-", "--", "?", "missing", "unknown"}
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")

audit = []
def log(step, column, n, note=""):
    if n:
        audit.append({"step": step, "column": column, "rows_affected": int(n), "note": note})

# ------------------------------------------------------------------ STEPS ---
def standardize_columns(df):
    new = [re.sub(r"\W+", "_", c.strip().lower()).strip("_") for c in df.columns]
    log("standardize_columns", "*", sum(a != b for a, b in zip(df.columns, new)))
    df.columns = new
    return df

def normalize_nulls_and_whitespace(df):
    for c in df.select_dtypes(include=["object","string"]):
        s = df[c].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
        mask = s.str.lower().isin(NULL_TOKENS)
        log("null_tokens_to_NaN", c, mask.sum())
        df[c] = s.mask(mask, pd.NA)
    return df

def coerce_types(df):
    for c, spec in SCHEMA.items():
        if c not in df: 
            log("missing_column", c, 1, "column absent from input"); continue
        t, before = spec["type"], df[c].isna().sum()
        if t == "int" or t == "float":
            cleaned = df[c].astype("string").str.replace(r"[^\d.\-]", "", regex=True)
            df[c] = pd.to_numeric(cleaned, errors="coerce")
            if t == "int": df[c] = df[c].round().astype("Int64")
        elif t == "date":
            df[c] = pd.to_datetime(df[c], errors="coerce", format="mixed", dayfirst=False)
        elif t == "email":
            df[c] = df[c].str.lower()
            bad = df[c].notna() & ~df[c].fillna("").str.match(EMAIL_RE)
            log("invalid_email_nulled", c, bad.sum()); df.loc[bad, c] = pd.NA
        elif t == "category":
            low = df[c].str.lower().str.strip()
            mapped = low.map(spec.get("map", {}))
            changed = (mapped.notna() & (mapped != df[c])).sum()
            df[c] = mapped.fillna(df[c].str.upper())
            log("category_standardized", c, changed)
        elif t == "str" and c == "name":
            df[c] = df[c].str.title()
        log("type_coercion_failed", c, df[c].isna().sum() - before, f"cast to {t}")
    return df

def drop_duplicates(df):
    keys = [c for c, s in SCHEMA.items() if s.get("key")]
    exact = df.duplicated(keep="first"); log("exact_duplicates_removed", "*", exact.sum())
    df = df[~exact]
    if keys:
        # Keep the most complete record per key, then the most recent one
        df = df.assign(_filled=df.notna().sum(axis=1))
        df = df.sort_values(["_filled"], ascending=False, kind="stable")
        dup = df.duplicated(subset=keys, keep="first")
        log("key_duplicates_removed", ",".join(keys), dup.sum(), "kept most complete row")
        df = df[~dup].drop(columns="_filled").sort_index()
    return df

def validate(df):
    """Return (clean, quarantine). Flag, don't delete."""
    reasons = pd.Series("", index=df.index)
    for c, spec in SCHEMA.items():
        if c not in df: continue
        if spec.get("required"):
            m = df[c].isna(); reasons[m] += f"missing_{c};"
        if "rng" in spec:
            lo, hi = spec["rng"]
            m = df[c].notna() & ((df[c] < lo) | (df[c] > hi)); reasons[m] += f"out_of_range_{c};"
    if "signup_date" in df:
        m = df["signup_date"] > pd.Timestamp.today(); reasons[m] += "future_date;"
    bad = reasons != ""
    log("rows_quarantined", "*", bad.sum())
    q = df[bad].assign(fail_reason=reasons[bad])
    return df[~bad].copy(), q

def impute_optional(df):
    """Conservative: only numeric optional columns, median, with an indicator flag."""
    for c, spec in SCHEMA.items():
        if c in df and not spec.get("required") and spec["type"] in ("int", "float"):
            n = df[c].isna().sum()
            if n:
                df[f"{c}_was_missing"] = df[c].isna()
                med = df[c].median()
                df[c] = df[c].fillna(round(med, 2) if spec["type"] == "float" else int(round(med)))
                log("median_imputed", c, n, "flag column added")
    return df

def structural_checks(df):
    """Post-clean assertions: the pipeline fails loudly if guarantees are broken."""
    key = [c for c, s in SCHEMA.items() if s.get("key")]
    assert not df.duplicated(subset=key).any(), "duplicate keys remain"
    for c, s in SCHEMA.items():
        if s.get("required") and c in df:
            assert df[c].notna().all(), f"nulls remain in required column {c}"
    return True

# ------------------------------------------------------------------- MAIN ---
def run(df, outdir="cleaned_output"):
    audit.clear()
    os.makedirs(outdir, exist_ok=True)
    raw_rows = len(df)
    df = standardize_columns(df.copy())
    df = normalize_nulls_and_whitespace(df)
    df = coerce_types(df)
    df = drop_duplicates(df)
    df, quarantine = validate(df)
    df = impute_optional(df)
    structural_checks(df)

    df.to_csv(f"{outdir}/cleaned.csv", index=False)
    quarantine.to_csv(f"{outdir}/quarantine.csv", index=False)
    pd.DataFrame(audit).to_csv(f"{outdir}/audit_log.csv", index=False)
    rep = [f"Raw rows:        {raw_rows}",
           f"Clean rows:      {len(df)}",
           f"Quarantined:     {len(quarantine)}",
           f"Duplicates gone: {raw_rows - len(df) - len(quarantine)}",
           "", "Audit summary:", pd.DataFrame(audit).to_string(index=False)]
    open(f"{outdir}/report.txt", "w").write("\n".join(rep))
    print("\n".join(rep))

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Clean and validate a CSV file.")
    p.add_argument("path", help="input CSV file")
    p.add_argument("--out", default="cleaned_output", help="output folder")
    a = p.parse_args()
    # keep_default_na=False: let this pipeline detect and log every placeholder null itself
    run(pd.read_csv(a.path, dtype=str, keep_default_na=False), outdir=a.out)
