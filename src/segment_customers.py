"""
Customer segmentation (K-means) on the cleaned Mall Customers data.

Setup (one time):   pip install scikit-learn matplotlib
Run (from the repository root):
    python src/segment_customers.py
    python src/segment_customers.py --k 4          # force 4 segments
    python src/segment_customers.py --src other.csv --out my_results
Outputs (default ./outputs/segmentation):
    customers_segmented.csv  - every customer with a segment label
    segment_profiles.csv     - average age / income / spending per segment
    elbow_silhouette.png     - evidence for choosing the number of segments
    segments.png             - scatter plot of the segments
"""
import argparse, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

ap = argparse.ArgumentParser()
ap.add_argument("--src", default="outputs/mall_cleaning/cleaned.csv", help="cleaned CSV")
ap.add_argument("--out", default="outputs/segmentation", help="output folder")
ap.add_argument("--k", type=int, default=None, help="number of segments (default: auto)")
args = ap.parse_args()
SRC, OUT, K_FIXED = args.src, args.out, args.k
INC, SPD = "annual_income_k", "spending_score_1_100"
os.makedirs(OUT, exist_ok=True)

df = pd.read_csv(SRC)
scaler = StandardScaler()
X = scaler.fit_transform(df[[INC, SPD]])   # scale so both features count equally

# ---- 1. choose k: elbow (inertia) + silhouette for k = 2..10
ks = list(range(2, 11))
inertia, sil = [], []
for k in ks:
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
    inertia.append(km.inertia_)
    sil.append(silhouette_score(X, km.labels_))
best_k = ks[int(np.argmax(sil))]
k = K_FIXED or best_k
print(f"Best k by silhouette: {best_k}   |   Using k = {k}")

fig, ax = plt.subplots(1, 2, figsize=(10, 4))
ax[0].plot(ks, inertia, "o-"); ax[0].set(title="Elbow method", xlabel="k", ylabel="Inertia")
ax[1].plot(ks, sil, "o-", color="tab:orange"); ax[1].set(title="Silhouette score", xlabel="k")
ax[1].axvline(k, ls="--", color="gray")
plt.tight_layout(); plt.savefig(f"{OUT}/elbow_silhouette.png", dpi=150); plt.close()

# ---- 2. final model
km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
df["segment"] = km.labels_

# ---- 3. human-readable names: compare each segment to the overall low/high thirds
q = df[[INC, SPD]].quantile([1/3, 2/3])
def tier(v, col):
    return "Low" if v < q.loc[1/3, col] else ("High" if v >= q.loc[2/3, col] else "Average")
prof = df.groupby("segment").agg(customers=("segment", "size"), avg_age=("age", "mean"),
                                 avg_income_k=(INC, "mean"), avg_spending_score=(SPD, "mean")).round(1)
prof["label"] = prof.apply(lambda r: f"{tier(r.avg_income_k, INC)} income, "
                                     f"{tier(r.avg_spending_score, SPD).lower()} spend", axis=1)
df["segment_label"] = df["segment"].map(prof["label"])

df.to_csv(f"{OUT}/customers_segmented.csv", index=False)
prof.to_csv(f"{OUT}/segment_profiles.csv")
print("\nSegment profiles:\n", prof.to_string())

# ---- 4. scatter plot
plt.figure(figsize=(8, 6))
for s, g in df.groupby("segment"):
    plt.scatter(g[INC], g[SPD], s=45, alpha=.8, label=f"{s}: {prof.loc[s, 'label']}")
cent = scaler.inverse_transform(km.cluster_centers_)
plt.scatter(cent[:, 0], cent[:, 1], c="black", marker="X", s=200, label="Centroids")
plt.xlabel("Annual income (k$)"); plt.ylabel("Spending score (1-100)")
plt.title("Customer segments"); plt.legend(fontsize=8, loc="upper right", bbox_to_anchor=(1.0, -0.12), ncol=2)
plt.tight_layout(); plt.savefig(f"{OUT}/segments.png", dpi=150, bbox_inches="tight"); plt.close()
print(f"\nSaved results to {OUT}")
