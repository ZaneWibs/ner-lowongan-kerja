"""Tabel bukti (evidence) untuk dashboard:
  job_deskripsi(job_id, deskripsi)          : teks deskripsi lowongan dari gold annotations
  skill_bukti(job_id, skill_id, start, end, sumber) : posisi kata skill di deskripsi
Pencocokan: entitas NER di lowongan itu yang teksnya sama dengan nama skill
(nama baku atau nama sebelum normalisasi); bila tidak ada, cari nama tsb di deskripsi."""
import json, re, sqlite3, sys
import pandas as pd

DB, GOLD = sys.argv[1], sys.argv[2]
LABEL_SKILL = ("SKILL", "SOFT_SKILL", "TOOL", "PROGRAMMING_LANGUAGE")

def norm(t):
    return re.sub(r"\s+", " ", str(t).lower().strip(" .,;:-•*()\t\n"))

con = sqlite3.connect(DB)
gold = json.load(open(GOLD))
jobs = pd.read_sql("SELECT id, url FROM jobs", con)
desk = {g["url"]: g["data"].get("description") or "" for g in gold}
jobs["deskripsi"] = jobs.url.map(desk)
print("deskripsi terisi:", jobs.deskripsi.notna().sum(), "/", len(jobs))

js = pd.read_sql("""SELECT js.job_id, js.skill_id, js.skill_id_asli, s.name FROM job_skills js
                    JOIN skills s ON s.id = js.skill_id""", con).drop_duplicates(["job_id", "skill_id", "skill_id_asli"])
nama_lama = pd.concat([pd.read_sql("SELECT id, name FROM skills", con),
                       pd.read_sql("SELECT id, name FROM skills_digabung", con)]).drop_duplicates("id")
js["nama_asli"] = js.skill_id_asli.map(dict(zip(nama_lama.id, nama_lama.name)))
ent = pd.read_sql(f"SELECT job_id, text, start, end FROM entities WHERE label IN {LABEL_SKILL}", con)
ent["k"] = ent.text.map(norm)

baris = []
D = dict(zip(jobs.id, jobs.deskripsi.fillna("")))
E = {k: g for k, g in ent.groupby("job_id")}
for (jid, sid), g in js.groupby(["job_id", "skill_id"]):
    nama = {norm(x) for x in list(g.name) + list(g.nama_asli.dropna())}
    e = E.get(jid)
    hit = e[e.k.isin(nama)] if e is not None else []
    if len(hit):
        baris += [(jid, sid, int(r.start), int(r.end), "entitas NER") for r in hit.itertuples()]
        continue
    teks = D.get(jid, "")
    cocok = []
    for n in sorted(nama, key=len, reverse=True):
        if len(n) < 2: continue
        cocok = [(m.start(), m.end()) for m in re.finditer(r"(?<!\w)" + re.escape(n) + r"(?!\w)", teks, re.I)]
        if cocok: break
    baris += [(jid, sid, a, b, "pencarian teks") for a, b in cocok[:3]]

b = pd.DataFrame(baris, columns=["job_id", "skill_id", "start", "end", "sumber"])
pasang = js[["job_id", "skill_id"]].drop_duplicates()
ada = b[["job_id", "skill_id"]].drop_duplicates()
print("pasangan lowongan-skill:", len(pasang), "| punya bukti:", len(ada), f"({len(ada)/len(pasang):.1%})")
print(b.sumber.value_counts())

con.execute("DROP TABLE IF EXISTS job_deskripsi"); con.execute("DROP TABLE IF EXISTS skill_bukti")
jobs[["id", "deskripsi"]].rename(columns={"id": "job_id"}).to_sql("job_deskripsi", con, index=False)
b.to_sql("skill_bukti", con, index=False)
con.execute("CREATE INDEX ix_bukti ON skill_bukti(skill_id, job_id)")
con.execute("CREATE INDEX IF NOT EXISTS ix_js_skill ON job_skills(skill_id, job_id)")
con.execute("CREATE INDEX IF NOT EXISTS ix_js_job ON job_skills(job_id)")
con.commit(); con.execute("VACUUM"); con.close()
