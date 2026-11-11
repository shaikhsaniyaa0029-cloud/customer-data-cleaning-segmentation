import pandas as pd
import clean_pipeline as cp


def run_clean(rows, tmp_path):
    cols = ["Customer ID", "Name", "Email", "Signup Date", "Age", "Country", "Spend"]
    df = pd.DataFrame(rows, columns=cols)
    cp.run(df, outdir=str(tmp_path))
    clean = pd.read_csv(tmp_path / "cleaned.csv")
    quarantine = pd.read_csv(tmp_path / "quarantine.csv")
    return clean, quarantine


GOOD = ["C1", "  alice   smith ", "A@X.COM", "03/22/2023", "34.0", "USA", "$1,200.50"]


def test_formats_are_standardized(tmp_path):
    clean, _ = run_clean([GOOD], tmp_path)
    r = clean.iloc[0]
    assert r["name"] == "Alice Smith"
    assert r["email"] == "a@x.com"
    assert r["signup_date"] == "2023-03-22"
    assert r["age"] == 34
    assert r["country"] == "US"
    assert r["spend"] == 1200.50


def test_exact_and_key_duplicates_removed(tmp_path):
    partial = ["C1", "Alice Smith", "", "03/22/2023", "", "USA", ""]
    clean, _ = run_clean([GOOD, GOOD, partial], tmp_path)
    assert len(clean) == 1
    assert clean.iloc[0]["email"] == "a@x.com"      # kept the most complete record


def test_impossible_age_is_quarantined_not_deleted(tmp_path):
    bad = ["C2", "Bob Jones", "b@x.com", "2023-01-01", "250", "UK", "10"]
    clean, quarantine = run_clean([GOOD, bad], tmp_path)
    assert list(clean["customer_id"]) == ["C1"]
    assert "out_of_range_age" in quarantine.iloc[0]["fail_reason"]


def test_missing_required_field_is_quarantined(tmp_path):
    bad = ["C3", "N/A", "c@x.com", "2023-01-01", "30", "IN", "10"]
    _, quarantine = run_clean([GOOD, bad], tmp_path)
    assert "missing_name" in quarantine.iloc[0]["fail_reason"]


def test_invalid_email_is_blanked_but_row_kept(tmp_path):
    row = ["C4", "Dev Patel", "not-an-email", "2023-01-01", "30", "IN", "10"]
    clean, quarantine = run_clean([row], tmp_path)
    assert len(clean) == 1 and len(quarantine) == 0
    assert pd.isna(clean.iloc[0]["email"])


def test_missing_optional_numbers_are_imputed_and_flagged(tmp_path):
    rows = [GOOD, ["C5", "Eve Adams", "e@x.com", "2023-01-01", "", "IN", "10"]]
    clean, _ = run_clean(rows, tmp_path)
    flagged = clean[clean["age_was_missing"]]
    assert list(flagged["customer_id"]) == ["C5"]
    assert flagged.iloc[0]["age"] == 34
