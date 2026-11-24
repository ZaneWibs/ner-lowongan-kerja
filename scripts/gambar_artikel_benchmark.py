"""Gambar 7-9 artikel dari hasil benchmark Kaggle (23 Nov 2026)."""
import json, csv, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator

SRC, OUT = sys.argv[1], sys.argv[2]
plt.rcParams.update({"font.family": "Inter", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "savefig.dpi": 220, "savefig.bbox": "tight"})
BIRU, ORANYE, HIJAU = "#2c7bd6", "#ea6a35", "#1fae7a"
NAMA = {"indolem/indobert-base-uncased": "IndoBERT-base-uncased",
        "bert-base-multilingual-cased": "mBERT-cased",
        "cahya/bert-base-indonesian-1.5G": "BERT-Indonesian-1.5G",
        "distilbert-base-multilingual-cased": "DistilmBERT-cased",
        "indobenchmark/indobert-base-p2": "IndoBERT-base-p2"}
PENDEK = {"IndoBERT-base-uncased": "IndoBERT-uncased", "mBERT-cased": "mBERT",
          "BERT-Indonesian-1.5G": "BERT-Indonesian-1.5G", "DistilmBERT-cased": "DistilmBERT",
          "IndoBERT-base-p2": "IndoBERT-p2"}
UMUM = {"mBERT-cased", "DistilmBERT-cased"}
koma = lambda d: FuncFormatter(lambda v, _: f"{v:.{d}f}".replace(".", ","))
fk = lambda v, d=3: f"{v:.{d}f}".replace(".", ",").replace("-", "−")

H = json.load(open(f"{SRC}/hasil_benchmark.json"))
for h in H: h["nama"] = NAMA[h["model"]]
H.sort(key=lambda h: -h["f1_viterbi"])
nm = [h["nama"] for h in H]; pd_ = [PENDEK[n] for n in nm]
war = [ORANYE if n in UMUM else BIRU for n in nm]
leg = [plt.Rectangle((0, 0), 1, 1, color=BIRU), plt.Rectangle((0, 0), 1, 1, color=ORANYE)]
legl = ["Khusus Indonesia", "Umum (multibahasa)"]

# ---------- Gambar 7 ----------
fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.1), gridspec_kw={"wspace": 0.75})
f1 = [h["f1_viterbi"] for h in H]
y = np.arange(len(H))[::-1]
a.barh(y, f1, color=war, height=0.78)
for yy, v in zip(y, f1): a.text(v + 0.001, yy, fk(v), va="center", fontsize=10)
a.set_yticks(y, nm); a.set_xlim(0.68, 0.745); a.xaxis.set_major_formatter(koma(2))
a.set_xlabel("F1 strict (mikro)"); a.set_title("(a) F1 data uji", fontweight="bold")
mn = [h["menit"] for h in H]; par = [h["parameter_juta"] for h in H]
b.scatter(mn, f1, s=[p * 4 for p in par], c=war, alpha=0.9, edgecolor="none")
for x_, y_, n in zip(mn, f1, nm): b.annotate(n.replace("-cased", ""), (x_, y_), xytext=(8, -3),
                                              textcoords="offset points", fontsize=9)
b.set_xlim(26, 58); b.set_ylim(0.708, 0.735); b.yaxis.set_major_locator(MultipleLocator(0.01)); b.yaxis.set_major_formatter(koma(2))
b.set_xlabel("Waktu latih (menit)"); b.set_ylabel("F1")
b.set_title("(b) Akurasi vs biaya (ukuran = parameter)", fontweight="bold")
fig.legend(leg, legl, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.4, -0.2), fontsize=10)
fig.savefig(f"{OUT}/g09_benchmark.png"); plt.close(fig)

# ---------- Gambar 8 ----------
fig, ax = plt.subplots(1, 3, figsize=(11, 3.9), gridspec_kw={"wspace": 0.42})
a, b, c = ax
x = np.arange(len(H)); w = 0.27
for i, (k, lab, col) in enumerate([("presisi", "Presisi", BIRU), ("recall", "Recall", ORANYE),
                                    ("f1_viterbi", "F1", HIJAU)]):
    a.bar(x + (i - 1) * w, [h[k] for h in H], w, color=col, label=lab)
a.set_ylim(0.68, 0.77); a.yaxis.set_major_locator(MultipleLocator(0.02)); a.yaxis.set_major_formatter(koma(2))
a.set_xticks(x, pd_, rotation=35, ha="right"); a.legend(ncol=3, frameon=False, fontsize=9, loc="upper center")
a.set_title("(a) Metrik mikro", fontweight="bold")
w = 0.38
b.bar(x - w / 2, [h["f1_argmax"] for h in H], w, color="#a3aebd", label="Argmax")
b.bar(x + w / 2, f1, w, color=war, label="Viterbi")
for i, h in enumerate(H):
    d = h["f1_viterbi"] - h["f1_argmax"]
    b.text(i, max(h["f1_viterbi"], h["f1_argmax"]) + 0.0008, ("+" if d >= 0 else "") + fk(d, 4),
           ha="center", fontsize=8.5)
b.set_ylim(0.705, 0.738); b.yaxis.set_major_locator(MultipleLocator(0.01)); b.yaxis.set_major_formatter(koma(2))
b.set_xticks(x, pd_, rotation=35, ha="right")
b.legend(handles=[plt.Rectangle((0, 0), 1, 1, color="#a3aebd"), plt.Rectangle((0, 0), 1, 1, color=BIRU)],
         labels=["Argmax", "Viterbi"], frameon=False, fontsize=9, loc="upper right")
b.set_title("(b) Argmax vs Viterbi", fontweight="bold")
R = [h["recall"] for h in H]; P = [h["presisi"] for h in H]
rr = np.linspace(0.705, 0.775, 200)
for F in (0.71, 0.72, 0.73):
    pp = F * rr / (2 * rr - F); c.plot(rr, pp, ":", color="gray", lw=1)
    j = np.argmin(abs(pp - 0.6975)); c.text(rr[j], 0.6972, f"F1={fk(F, 2)}", fontsize=7.5, color="gray")
c.scatter(R, P, c=war, s=60, zorder=3)
for r_, p_, n in zip(R, P, pd_): c.annotate(n, (r_, p_), xytext=(5, 4), textcoords="offset points", fontsize=8.5)
c.set_xlim(0.712, 0.768); c.set_ylim(0.697, 0.716)
c.xaxis.set_major_formatter(koma(2)); c.yaxis.set_major_locator(MultipleLocator(0.005)); c.yaxis.set_major_formatter(koma(3))
c.set_xlabel("Recall"); c.set_ylabel("Presisi"); c.set_title("(c) Presisi vs recall", fontweight="bold")
fig.legend(leg, legl, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.3), fontsize=10)
fig.savefig(f"{OUT}/g18_model_metrik.png"); plt.close(fig)

# ---------- Gambar 9 ----------
rows = list(csv.DictReader(open(f"{SRC}/perbandingan_per_entitas.csv")))
kol = {"indobert-base-uncased": "IndoBERT-base-uncased", "bert-base-multilingual-cased": "mBERT-cased",
       "bert-base-indonesian-1.5G": "BERT-Indonesian-1.5G",
       "distilbert-base-multilingual-cased": "DistilmBERT-cased", "indobert-base-p2": "IndoBERT-base-p2"}
inv = {v: k for k, v in kol.items()}
M = np.array([[float(r[inv[n]]) for n in nm] for r in rows]); ent = [r["Entitas"] for r in rows]
o = np.argsort(-M.mean(1)); M = M[o]; ent = [ent[i] for i in o]
fig, (a, b) = plt.subplots(1, 2, figsize=(10.5, 5.6), gridspec_kw={"width_ratios": [5, 4], "wspace": 0.05})
a.imshow(M, cmap="YlGnBu", vmin=0.3, vmax=1.0, aspect="auto")
for i in range(M.shape[0]):
    jb = M[i].argmax()
    for j in range(M.shape[1]):
        a.text(j, i, fk(M[i, j], 2), ha="center", va="center", fontsize=9,
               fontweight="bold" if j == jb else "normal", color="white" if M[i, j] > 0.85 else "#222")
a.set_yticks(range(len(ent)), ent); a.set_xticks(range(len(nm)), pd_, rotation=35, ha="right")
a.set_title("(a) F1 per entitas (tebal = terbaik)", fontweight="bold")
D = M[:, 1:] - M[:, [0]]; lim = np.abs(D).max()
im = b.imshow(D, cmap="RdBu", vmin=-lim, vmax=lim, aspect="auto")
for i in range(D.shape[0]):
    for j in range(D.shape[1]):
        b.text(j, i, fk(D[i, j] + 0.0, 2) if abs(D[i, j]) >= 0.005 else "0,00", ha="center", va="center",
               fontsize=9, color="white" if abs(D[i, j]) > 0.6 * lim else "#222")
b.set_yticks(range(len(ent)), [""] * len(ent)); b.set_xticks(range(len(nm) - 1), pd_[1:], rotation=35, ha="right")
b.set_title("(b) Selisih terhadap IndoBERT-uncased", fontweight="bold")
for s in ("left", "bottom"): a.spines[s].set_visible(False); b.spines[s].set_visible(False)
cb = fig.colorbar(im, ax=b, fraction=0.05, pad=0.03); cb.set_label("ΔF1")
cb.ax.yaxis.set_major_formatter(koma(2))
fig.savefig(f"{OUT}/g19_model_per_entitas.png"); plt.close(fig)
print("ok")
