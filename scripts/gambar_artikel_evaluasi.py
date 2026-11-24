"""Gambar 4, 5, 6, 10 artikel dari keluaran notebook 01 (run Kaggle)."""
import json, re, ast, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

NB, OUT = sys.argv[1], sys.argv[2]
plt.rcParams.update({"font.family": "Inter", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "savefig.dpi": 220, "savefig.bbox": "tight"})
BIRU, ORANYE, HIJAU, UNGU = "#2c7bd6", "#ea6a35", "#1fae7a", "#4b3aa8"
fk = lambda v, d=3: f"{v:.{d}f}".replace(".", ",")
ribu = lambda n: f"{n:,}".replace(",", ".")

nb = json.load(open(NB))
teks = {}
for i, c in enumerate(nb["cells"]):
    if c["cell_type"] == "code":
        teks[i] = "".join("".join(o.get("text", "")) + "".join(o.get("data", {}).get("text/plain", ""))
                          for o in c.get("outputs", []))
latih = [t for t in teks.values() if "train_runtime" in t][0]
eval_ = [t for t in teks.values() if "entity-level F1 STRICT" in t][0]
base = [t for t in teks.values() if "Baseline (Dictionary Matching)" in t][0]
kes = [t for t in teks.values() if "Analisis kesalahan (entity-level)" in t][0]

# ---- log pelatihan
log = [ast.literal_eval(l) for l in latih.splitlines() if l.startswith("{'")]
tr = [d for d in log if "loss" in d]; ev = [d for d in log if "eval_loss" in d]
fig, ax = plt.subplots(1, 3, figsize=(10, 3), gridspec_kw={"wspace": 0.45})
a, b, c = ax
a.plot([d["epoch"] for d in tr], [d["loss"] for d in tr], color=BIRU, lw=1.4, label="latih")
a.plot([d["epoch"] for d in ev], [d["eval_loss"] for d in ev], "-o", color=ORANYE, ms=3.5, label="validasi")
a.set_ylim(0, 1.2); a.set_xlabel("Epoch"); a.set_ylabel("Loss"); a.legend(frameon=False, fontsize=9)
a.set_title("(a) Loss", fontweight="bold")
ep = [d["epoch"] for d in ev]
for k, lab, col in [("eval_precision", "Presisi", BIRU), ("eval_recall", "Recall", HIJAU), ("eval_f1", "F1", ORANYE)]:
    b.plot(ep, [d[k] for d in ev], "-o", ms=3.5, color=col, label=lab)
best = max(ev, key=lambda d: d["eval_f1"])["epoch"]
b.axvline(best, ls="--", color="gray", lw=1); b.text(best + 0.3, 0.78, f"terbaik: epoch {int(best)}", fontsize=8.5, color="#555")
b.set_ylim(0.2, 0.8); b.set_xlabel("Epoch"); b.legend(frameon=False, fontsize=9, loc="lower right")
b.set_title("(b) Metrik validasi", fontweight="bold")
c.plot([d["epoch"] for d in tr], [d["learning_rate"] * 1e5 for d in tr], color=UNGU, lw=1.6)
c.set_xlabel("Epoch"); c.set_ylabel("Learning rate (×10⁻⁵)"); c.set_title("(c) Jadwal learning rate", fontweight="bold")
for x in ax:
    x.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",")))
fig.savefig(f"{OUT}/g05_kurva_pelatihan.png"); plt.close(fig)

# ---- per entitas
def tabel(t, judul_re):
    blok = t[re.search(judul_re, t).end():]
    d = {}
    for l in blok.splitlines():
        m = re.match(r"\s*([A-Z_]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s*$", l)
        if m: d[m.group(1)] = tuple(map(float, m.groups()[1:4]))
        if "micro avg" in l: break
    return d
S = tabel(eval_, r"F1 STRICT \(micro\)")
Bk = tabel(base, r"Baseline \(Dictionary Matching\)")
part = {}
pblok = eval_[eval_.find("F1 PARTIAL"):]
for l in pblok.splitlines():
    m = re.match(r"\s*\d+\s+([A-Z_]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+\d+", l)
    if m: part[m.group(1)] = float(m.group(4))
ent = sorted(S, key=lambda e: S[e][2])
fig, a = plt.subplots(figsize=(9, 5.2))
y = np.arange(len(ent)); h = 0.27
a.barh(y - h, [S[e][0] for e in ent], h, color=BIRU, label="Presisi")
a.barh(y, [S[e][1] for e in ent], h, color=HIJAU, label="Recall")
a.barh(y + h, [S[e][2] for e in ent], h, color=ORANYE, label="F1")
a.scatter([Bk[e][2] for e in ent], y + h, marker="|", s=180, color="#222", lw=2.2, zorder=4, label="F1 baseline kamus")
a.set_yticks(y, ent); a.set_xlim(0, 1); a.set_xlabel("Skor (strict, data uji)")
a.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.1f}".replace(".", ",")))
a.legend(ncol=4, frameon=False, fontsize=9, loc="lower center", bbox_to_anchor=(0.5, 1.0))
fig.savefig(f"{OUT}/g06_per_entitas.png"); plt.close(fig)

ent2 = sorted(S, key=lambda e: part[e])
fig, a = plt.subplots(figsize=(9, 4.4))
for i, e in enumerate(ent2):
    a.plot([S[e][2], part[e]], [i, i], color="#bbb", lw=2.5, zorder=1)
    a.text(part[e] + 0.012, i, "+" + fk(part[e] - S[e][2]), va="center", fontsize=8.5, color="#444")
a.scatter([S[e][2] for e in ent2], range(len(ent2)), color=BIRU, zorder=3, label="Strict", s=40)
a.scatter([part[e] for e in ent2], range(len(ent2)), color=ORANYE, zorder=3, label="Partial", s=40)
a.set_yticks(range(len(ent2)), ent2); a.set_xlim(0.45, 1.05); a.set_xlabel("F1 (data uji)")
a.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.1f}".replace(".", ",")))
a.legend(frameon=False, fontsize=9, loc="lower right")
fig.savefig(f"{OUT}/g07_strict_vs_partial.png"); plt.close(fig)

# ---- kesalahan
jenis = {k: int(v.replace(",", "")) for k, v in re.findall(r"(\w+_?\w*): ([\d,]+)", kes.split("Top")[0])}
lbl = [("boundary_error", "Batas span", ORANYE), ("spurious_entity", "Entitas palsu", "#eea200"),
       ("missed_entity", "Entitas terlewat", HIJAU), ("wrong_label", "Salah label", "#e57aa6")]
tot = sum(jenis[k] for k, _, _ in lbl)
pas = re.findall(r"  ([A-Z_]+) -> ([A-Z_]+): (\d+)", kes)[:8]
fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.2), gridspec_kw={"wspace": 0.75, "width_ratios": [1, 1.25]})
yy = np.arange(len(lbl))[::-1]
a.barh(yy, [jenis[k] for k, _, _ in lbl], color=[c for _, _, c in lbl], height=0.8)
for y_, (k, _, _) in zip(yy, lbl):
    a.text(jenis[k] + 40, y_, f"{ribu(jenis[k])} ({fk(100 * jenis[k] / tot, 1)}%)", va="center", fontsize=9)
a.set_yticks(yy, [n for _, n, _ in lbl]); a.set_xlim(0, 3500); a.set_xlabel("Jumlah")
a.set_title("(a) Jenis kesalahan", fontweight="bold")
yb = np.arange(len(pas))[::-1]
b.barh(yb, [int(n) for *_, n in pas], color=BIRU, height=0.8)
for y_, (_, _, n) in zip(yb, pas): b.text(int(n) + 0.8, y_, n, va="center", fontsize=9)
b.set_yticks(yb, [f"{g}→{p}" for g, p, _ in pas]); b.set_xlabel("Jumlah span")
b.set_title("(b) Kebingungan label (acuan→prediksi)", fontweight="bold")
fig.savefig(f"{OUT}/g08_analisis_kesalahan.png"); plt.close(fig)
print(jenis, tot, pas[:4]); print({e: (S[e][2], part[e]) for e in S})
