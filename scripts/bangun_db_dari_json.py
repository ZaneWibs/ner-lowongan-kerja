"""Bangun ulang tabel turunan entitas pada basis data dashboard dari file anotasi (gold ATAU prediksi model).

Tabel metadata (jobs, KBJI, lokasi, gaji, perusahaan, peta_*) tidak disentuh.
Tabel yang dibangun ulang: entities, job_skills (+ skill baru di skills), job_jenjang, job_bidang_studi.
(skill_bukti dan job_deskripsi dibangun ulang sesudahnya dengan bangun_bukti.py)

Pemakaian:
    python3 bangun_db_dari_json.py DB_DASAR JSON_ANOTASI DB_KELUARAN NOTEBOOK
Contoh (dashboard dari keluaran model):
    python3 bangun_db_dari_json.py data/ner_jobposting.sqlite data/prediksi_ner_lowongan.json \
        data/ner_jobposting_prediksi.sqlite notebooks/01_ner_indobert_pelatihan_inferensi.ipynb
    python3 bangun_bukti.py data/ner_jobposting_prediksi.sqlite data/prediksi_ner_lowongan.json
"""
import json, re, sqlite3, shutil, sys, unicodedata
from collections import Counter
import pandas as pd
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from muat_fungsi import muat

DB0, JS, DB1, NB = sys.argv[1:5]
F = muat(NB)
import contextlib, io
enrich_document, normalize_skill = F["enrich_document"], F["normalize_skill"]
esc_tagger, SUB2BROAD = F["escudero_tagger"], F["ESCUDERO_SUB_TO_BROAD"]
SKILL_LABELS = ("SKILL", "SOFT_SKILL", "TOOL", "PROGRAMMING_LANGUAGE")

shutil.copy(DB0, DB1)
con = sqlite3.connect(DB1); cur = con.cursor()

# ---------------------------------------------------------------- dokumen
data = json.load(open(JS, encoding="utf-8"))
jobs = pd.read_sql("SELECT id, url FROM jobs", con)
url2job = dict(zip(jobs.url, jobs.id))
docs, st = [], Counter()
for g in data:
    jid = url2job.get(g.get("url"))
    if jid is None: st["lowongan_tak_dikenal"] += 1; continue
    text = (g.get("data") or {}).get("description") or ""
    spans, seen = [], set()
    for a in g.get("gold_annotations", []):
        s, e, t, lab = a.get("start"), a.get("end"), a.get("text", ""), a.get("label")
        if s is None or e is None or not text: st["tanpa_offset"] += 1; continue
        if text[s:e] != t:
            p = text.find(t)
            if p < 0: st["gagal_align"] += 1; continue
            s, e = p, p + len(t)
        if (s, e, lab) in seen: st["duplikat"] += 1; continue
        seen.add((s, e, lab)); spans.append({"start": s, "end": e, "text": text[s:e], "label": lab})
    docs.append({"job_id": jid, "text": text, "spans": spans})
print("dokumen:", len(docs), dict(st))

# ---------------------------------------------------------------- entities
cur.execute("DELETE FROM entities")
cur.executemany("INSERT INTO entities(job_id,label,text,start,end) VALUES(?,?,?,?,?)",
                [(d["job_id"], s["label"], s["text"], s["start"], s["end"]) for d in docs for s in d["spans"]])

# ---------------------------------------------------------------- skills & job_skills
sk = pd.read_sql("SELECT id, name, label FROM skills", con)
cur_id = {(n, l): i for i, n, l in sk.itertuples(index=False)}
log = pd.read_sql("SELECT skill_id_lama, nama_lama, label, skill_id_baru FROM log_normalisasi_skill", con)
lama2baru = dict(zip(log.skill_id_lama, log.skill_id_baru))
log_nama = {(n, l): (il, ib) for il, n, l, ib in log[["skill_id_lama", "nama_lama", "label", "skill_id_baru"]].itertuples(index=False)}
dig = pd.read_sql("SELECT id, name, label FROM skills_digabung", con)
dig_id = {(n, l): i for i, n, l in dig.itertuples(index=False)}

def ikuti(i):
    seen = set()
    while i in lama2baru and i not in seen:
        seen.add(i); i = lama2baru[i]
    return i

def esc_klasifikasi(s):
    sub, method, score = esc_tagger.classify(s["text"])
    if sub is None:
        if s["label"] in F["ESC_FALLBACK_LABEL"]: sub = F["ESC_FALLBACK_LABEL"][s["label"]]
        elif s["label"] == "TOOL": sub, _ = F["_tool_subcategory"](s["text"])
        elif s.get("skill_domain") in F["ESC_FALLBACK_DOMAIN"]: sub = F["ESC_FALLBACK_DOMAIN"][s["skill_domain"]]
        else: sub = "Cognitive skills (narrow sense)"
    return SUB2BROAD[sub], sub

cara = Counter(); baru = 0; rows = []
with contextlib.redirect_stdout(io.StringIO()):
    enr = [(d["job_id"], enrich_document(d)) for d in docs]
for jid, ss in enr:
    for s in ss:
        nm, lab = normalize_skill(s["text"]), s["label"]
        if (nm, lab) in cur_id:
            asli = sid = cur_id[(nm, lab)]; cara["langsung"] += 1
        elif (nm, lab) in log_nama:
            asli, sid = log_nama[(nm, lab)]; sid = ikuti(sid); cara["log_normalisasi"] += 1
        elif (nm, lab) in dig_id:
            asli = dig_id[(nm, lab)]; sid = ikuti(asli); cara["skills_digabung"] += 1
        else:
            broad, sub = esc_klasifikasi(s)
            cur.execute("""INSERT INTO skills(name,label,skill_type,skill_domain,skill_function,transferability,
                           escudero_broad_category,escudero_subcategory) VALUES(?,?,?,?,?,?,?,?)""",
                        (nm, lab, s["skill_type"], s["skill_domain"], s["skill_function"], s["transferability"], broad, sub))
            asli = sid = cur.lastrowid; cur_id[(nm, lab)] = sid; baru += 1; cara["skill_baru"] += 1
        rows.append((jid, sid, s["importance"], s["proficiency"], asli))
cur.execute("DELETE FROM job_skills")
cur.executemany("INSERT INTO job_skills(job_id,skill_id,importance,proficiency,skill_id_asli) VALUES(?,?,?,?,?)", rows)
print("job_skills:", len(rows), "| pemetaan:", dict(cara), "| skill baru:", baru)

# ---------------------------------------------------------------- jenjang & bidang studi
def kunci(t):
    t = unicodedata.normalize("NFKC", str(t)).replace(" ", " ")
    t = re.sub(r"\s+", " ", t.lower()).strip()
    return t.strip(" .,;:-/()[]\"'")
pj = pd.read_sql("SELECT kunci_istilah, jenjang_baku, kelompok_jenjang FROM peta_jenjang WHERE jenjang_baku IS NOT NULL", con)
pb = pd.read_sql("SELECT kunci_istilah, nama_program_studi, rumpun_ilmu FROM peta_bidang_studi WHERE nama_program_studi IS NOT NULL", con)
ent = pd.read_sql("SELECT job_id, label, text FROM entities WHERE label IN ('EDUCATION_LEVEL','DEGREE_FIELD')", con)
ent["k"] = ent.text.map(kunci)
jj = ent[ent.label == "EDUCATION_LEVEL"].merge(pj, left_on="k", right_on="kunci_istilah")
jj = jj[["job_id", "text", "jenjang_baku", "kelompok_jenjang"]].rename(columns={"text": "istilah"}).drop_duplicates()
jb = ent[ent.label == "DEGREE_FIELD"].merge(pb, left_on="k", right_on="kunci_istilah")
jb = jb[["job_id", "text", "nama_program_studi", "rumpun_ilmu"]].rename(columns={"text": "istilah"}).drop_duplicates(["job_id", "istilah", "nama_program_studi"])
for nama, df, lab in (("job_jenjang", jj, "EDUCATION_LEVEL"), ("job_bidang_studi", jb, "DEGREE_FIELD")):
    cur.execute(f"DELETE FROM {nama}")
    df.to_sql(nama, con, if_exists="append", index=False)
    e = ent[ent.label == lab]
    print(f"{nama}: {len(df)} baris | entitas {lab} terpetakan: {e.k.isin(set(df.istilah.map(kunci))).mean():.1%}")
con.commit(); con.close()
print("selesai:", DB1)
