"""Memuat fungsi pengayaan dari notebook utama tanpa menjalankan pelatihan.

Dipakai oleh bangun_db_dari_json.py agar pengayaan (normalisasi skill, atribut Layer 2,
taksonomi Escudero) memakai kode yang SAMA PERSIS dengan notebook.

Sel yang dimuat (indeks sel pada notebooks/01_ner_indobert_pelatihan_inferensi.ipynb):
  12 import & seed, 14 CONFIG, 18 tokenisasi, 25-27 tagger Layer 2,
  29-30 taksonomi Escudero, 41 normalisasi judul.
Perulangan/assert yang memakai DOCS dilewati (DOCS dibuat kosong).
"""
import ast, json, sys

SEL_BAWAAN = (12, 14, 18, 25, 26, 27, 29, 30, 41)

def muat(nb_path, sel=SEL_BAWAAN):
    nb = json.load(open(nb_path, encoding="utf-8"))
    g = {"__name__": "nbfunc", "DOCS": [], "all_en": []}
    for i in sel:
        src = "".join(nb["cells"][i]["source"])
        src = "\n".join(l for l in src.split("\n") if not l.lstrip().startswith(("!", "%")))
        for node in ast.parse(src).body:
            try:
                exec(compile(ast.Module(body=[node], type_ignores=[]), f"<sel {i}>", "exec"), g)
            except Exception as e:
                penting = isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom)) or \
                          (isinstance(node, ast.Assign) and "IndoBERTEncoder" not in ast.unparse(node))
                if penting:
                    print(f"[sel {i}] gagal: {ast.unparse(node)[:80]} -> {type(e).__name__}: {e}", file=sys.stderr)
    return g

if __name__ == "__main__":
    g = muat(sys.argv[1])
    for k in ["enrich_document", "escudero_tagger", "normalize_skill", "ESCUDERO_SUB_TO_BROAD"]:
        print(f"{k:24s}", "OK" if k in g else "TIDAK ADA")
