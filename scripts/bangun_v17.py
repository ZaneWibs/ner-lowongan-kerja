"""
Basis data v17: seluruh hasil koreksi pembimbing masuk ke SQLite
================================================================
Arahan pembimbing (Bu Tri, 29 September 2026): "semua data yang dikoreksi masuk
sql, lalu tampilkan tab baru untuk bagian ini. Normalisasi juga sudah bisa
disesuaikan di sql."

Yang dilakukan skrip ini terhadap salinan v16:

  1. NORMALISASI SKILL
     Kelompok pada 1_Kandidat_Normalisasi_Skill.xlsx (513 kelompok: kata
     penguat, stemming imbuhan, sinonim) diterapkan: setiap varian diarahkan
     ke nama usulan kelompoknya. Ditambah penyatuan nama yang hanya berbeda
     huruf besar/kecil, spasi, atau tanda baca di ujung.

     Label NER TIDAK diubah. Label adalah fakta anotasi per penyebutan, jadi
     varian berlabel SOFT_SKILL tetap SOFT_SKILL setelah namanya disatukan.
     Karena skills unik per (nama, label), satu nama bisa tetap punya
     beberapa baris dengan label berbeda -- sama seperti sebelumnya.

     Dapat dilacak dan dibatalkan sepenuhnya:
       - job_skills.skill_id_asli   : skill_id sebelum normalisasi
       - skills_digabung            : salinan utuh baris skill yang dilebur
       - log_normalisasi_skill      : varian -> nama akhir, beserta alasannya
     Jumlah penyebutan (baris job_skills) tidak berubah.

  2. PROGRAM STUDI (DEGREE_FIELD)
     Pemetaan final hasil telaah pembimbing (2b_Pemetaan_Program_Studi_Final
     .xlsx) disimpan ke peta_bidang_studi, lalu diterapkan per lowongan ke
     job_bidang_studi. Istilah yang dikeluarkan pembimbing tidak masuk.

  3. JENJANG PENDIDIKAN (EDUCATION_LEVEL)
     Pemetaan ke jenjang baku Permendikbud 154/2014 disimpan ke peta_jenjang
     dan job_jenjang. Satu istilah bisa menghasilkan beberapa jenjang
     (mis. "SMA/SMK/D3/S1"), dan "diploma" tanpa angka dipetakan ke keempat
     jenjang diploma sesuai arahan pembimbing.

  4. SKILL GABUNGAN (anotasi + metadata situs)
     Disimpan sebagai tabel terpisah skill_gabungan, tidak menggantikan
     job_skills.

    python bangun_v17.py
"""
import re
import shutil
import sqlite3
import unicodedata
from collections import Counter, defaultdict

import pandas as pd

import build_prodi_jenjang as BPJ
import skill_gabungan_label as SGL

SUMBER = "ner_jobposting_v16.sqlite"
TUJUAN = "ner_jobposting_v17.sqlite"
WB_NORMALISASI = "1_Kandidat_Normalisasi_Skill.xlsx"
WB_PRODI = "2b_Pemetaan_Program_Studi_Final.xlsx"
GOLD = "gold.json"


def kunci(t):
    """Kunci penyatuan ringan: huruf kecil, spasi dirapikan, tanda baca di
    ujung dibuang. Tidak mengubah ejaan di tengah kata."""
    t = unicodedata.normalize("NFKC", str(t)).replace(" ", " ")
    t = re.sub(r"\s+", " ", t.lower()).strip()
    return t.strip(" .,;:-/()[]\"'")


# ---------------------------------------------------------------------------
# 1. Normalisasi skill
# ---------------------------------------------------------------------------
def baca_kelompok_normalisasi(path):
    df = pd.read_excel(path, sheet_name="Kandidat Normalisasi", header=4)
    peta, alasan = {}, {}
    for r in df.itertuples(index=False):
        usul = str(r[1]).strip()
        why = str(r[7]).strip()
        for item in str(r[2]).split("; "):
            m = re.match(r"^(.*) \((\d+)\)$", item.strip())
            if not m:
                continue
            k = kunci(m.group(1))
            if k and k not in peta:          # kelompok yang lebih besar menang
                peta[k] = usul
                alasan[k] = why
    return peta, alasan


def normalisasi_skill(con):
    cur = con.cursor()
    peta_wb, alasan_wb = baca_kelompok_normalisasi(WB_NORMALISASI)

    skills = pd.read_sql("SELECT * FROM skills", con)
    sebut = dict(con.execute("SELECT skill_id, COUNT(*) FROM job_skills GROUP BY 1"))
    skills["n"] = skills.id.map(sebut).fillna(0).astype(int)
    skills["k"] = skills.name.map(kunci)

    # Bentuk paling sering untuk tiap kunci (dipakai bila tidak ada kelompok).
    bentuk = (skills.groupby(["k", "name"]).n.sum().reset_index()
              .sort_values(["k", "n"], ascending=[True, False])
              .drop_duplicates("k").set_index("k").name.to_dict())

    def target(nama):
        k = kunci(nama)
        seen = set()
        # Ikuti rantai: usulan satu kelompok bisa menjadi varian kelompok lain.
        while k in peta_wb and k not in seen:
            seen.add(k)
            nxt = peta_wb[k]
            if kunci(nxt) == k:
                return nxt, alasan_wb[k]
            k = kunci(nxt)
            nama = nxt
        if seen:
            return nama, alasan_wb[next(iter(seen))]
        if bentuk.get(k, nama) != nama:
            return bentuk[k], "Hanya beda huruf besar/kecil, spasi, atau tanda baca"
        return nama, ""

    skills[["target", "alasan"]] = skills.name.apply(lambda x: pd.Series(target(x)))
    ubah = skills[skills.target != skills.name]

    cur.execute("ALTER TABLE job_skills ADD COLUMN skill_id_asli INT")
    cur.execute("UPDATE job_skills SET skill_id_asli = skill_id")
    cur.execute("CREATE TABLE skills_digabung AS SELECT * FROM skills WHERE 0")
    cur.execute("""CREATE TABLE log_normalisasi_skill(
        skill_id_lama INT, nama_lama TEXT, label TEXT, jumlah_penyebutan INT,
        skill_id_baru INT, nama_baru TEXT, alasan TEXT)""")

    log = []
    for (tgt, lab), grp in skills[skills.name.isin(ubah.name) |
                                  skills.target.isin(ubah.target)].groupby(["target", "label"]):
        # Semua baris berlabel sama yang tujuannya nama ini, termasuk baris yang
        # namanya sudah persis sama dengan tujuan.
        semua = skills[(skills.target == tgt) & (skills.label == lab)]
        if len(semua) == 1 and semua.iloc[0]["name"] == tgt:
            continue
        persis = semua[semua.name == tgt]
        if len(persis):
            kanon = persis.iloc[0]
        else:
            kanon = semua.sort_values("n", ascending=False).iloc[0]
            cur.execute("UPDATE skills SET name=? WHERE id=?", (tgt, int(kanon.id)))
            log.append((int(kanon.id), kanon["name"], lab, int(kanon.n),
                        int(kanon.id), tgt, kanon.alasan))
        for r in semua.itertuples(index=False):
            if r.id == kanon.id:
                continue
            cur.execute("UPDATE job_skills SET skill_id=? WHERE skill_id=?",
                        (int(kanon.id), int(r.id)))
            cur.execute("INSERT INTO skills_digabung SELECT * FROM skills WHERE id=?",
                        (int(r.id),))
            cur.execute("DELETE FROM skills WHERE id=?", (int(r.id),))
            log.append((int(r.id), r.name, lab, int(r.n), int(kanon.id), tgt, r.alasan))

    cur.executemany("INSERT INTO log_normalisasi_skill VALUES (?,?,?,?,?,?,?)", log)
    con.commit()
    return pd.DataFrame(log, columns=["skill_id_lama", "nama_lama", "label", "n",
                                      "skill_id_baru", "nama_baru", "alasan"])


# ---------------------------------------------------------------------------
# 2. Program studi
# ---------------------------------------------------------------------------
def masukkan_program_studi(con):
    d = pd.read_excel(WB_PRODI, sheet_name="Pemetaan Akhir", header=3)
    d = d.fillna("")
    baris = []
    for r in d.itertuples(index=False):
        for nm in [x for x in str(r.nama_program_studi_final).split(" | ") if x]:
            baris.append((kunci(r.istilah_di_lowongan), r.istilah_di_lowongan, nm,
                          r.rumpun_ilmu_final, r.dasar_rumpun,
                          r.jenis_pendidikan_final, r.status_penerapan))
        if not str(r.nama_program_studi_final):
            baris.append((kunci(r.istilah_di_lowongan), r.istilah_di_lowongan, None,
                          None, None, None, r.status_penerapan))
    peta = pd.DataFrame(baris, columns=[
        "kunci_istilah", "istilah", "nama_program_studi", "rumpun_ilmu",
        "dasar_rumpun", "jenis_pendidikan", "status_penerapan"])
    peta.to_sql("peta_bidang_studi", con, index=False)

    ent = pd.read_sql("SELECT job_id, text FROM entities WHERE label='DEGREE_FIELD'", con)
    ent["kunci_istilah"] = ent.text.map(kunci)
    jb = ent.merge(peta.dropna(subset=["nama_program_studi"]), on="kunci_istilah")
    jb = jb[["job_id", "text", "nama_program_studi", "rumpun_ilmu"]].rename(
        columns={"text": "istilah"})
    jb.to_sql("job_bidang_studi", con, index=False)
    con.execute("CREATE INDEX ix_jbs_job ON job_bidang_studi(job_id)")
    return peta, jb, ent


# ---------------------------------------------------------------------------
# 3. Jenjang pendidikan
# ---------------------------------------------------------------------------
KELOMPOK = {n[0]: "Pendidikan Tinggi" for n in BPJ.JENJANG_DIKTI}
KELOMPOK.update(dict(BPJ.JENJANG_LUAR))


def masukkan_jenjang(con):
    ent = pd.read_sql("SELECT job_id, text FROM entities WHERE label='EDUCATION_LEVEL'", con)
    baris = []
    for teks in sorted(set(ent.text.map(lambda x: str(x).strip()))):
        jj, status, cat = BPJ.petakan_jenjang(teks)
        if jj:
            for j in jj:
                baris.append((kunci(teks), teks, j, KELOMPOK.get(j), status, cat))
        else:
            baris.append((kunci(teks), teks, None, None, status, cat))
    peta = pd.DataFrame(baris, columns=["kunci_istilah", "istilah", "jenjang_baku",
                                        "kelompok_jenjang", "status", "catatan"])
    peta = peta.drop_duplicates(["kunci_istilah", "jenjang_baku"])
    peta.to_sql("peta_jenjang", con, index=False)

    ent["kunci_istilah"] = ent.text.map(kunci)
    jj = ent.merge(peta.dropna(subset=["jenjang_baku"])[
        ["kunci_istilah", "jenjang_baku", "kelompok_jenjang"]], on="kunci_istilah")
    jj = jj[["job_id", "text", "jenjang_baku", "kelompok_jenjang"]].rename(
        columns={"text": "istilah"})
    jj.to_sql("job_jenjang", con, index=False)
    con.execute("CREATE INDEX ix_jj_job ON job_jenjang(job_id)")
    return peta, jj, ent


# ---------------------------------------------------------------------------
# 4. Skill gabungan
# ---------------------------------------------------------------------------
def masukkan_skill_gabungan(con, db_path):
    g = SGL.bangun(db_path, GOLD)
    g.to_sql("skill_gabungan", con, index=False, if_exists="replace")
    return g


def main():
    shutil.copy(SUMBER, TUJUAN)
    con = sqlite3.connect(TUJUAN)

    sebelum = con.execute("SELECT COUNT(DISTINCT name), COUNT(*) FROM skills").fetchone()
    js_sebelum = con.execute("SELECT COUNT(*) FROM job_skills").fetchone()[0]
    log = normalisasi_skill(con)
    sesudah = con.execute("SELECT COUNT(DISTINCT name), COUNT(*) FROM skills").fetchone()
    js_sesudah = con.execute("SELECT COUNT(*) FROM job_skills").fetchone()[0]
    print("NORMALISASI SKILL")
    print(f"  nama skill unik     : {sebelum[0]:,} -> {sesudah[0]:,}")
    print(f"  baris tabel skills  : {sebelum[1]:,} -> {sesudah[1]:,}")
    print(f"  penyebutan job_skills: {js_sebelum:,} -> {js_sesudah:,} (harus sama)")
    print(f"  baris log           : {len(log):,}")
    print(log.alasan.value_counts().to_string())

    peta_p, jb, ent_p = masukkan_program_studi(con)
    print("\nPROGRAM STUDI")
    print(f"  entitas DEGREE_FIELD: {len(ent_p):,}, terpetakan: "
          f"{jb.drop_duplicates(['job_id','istilah']).shape[0]:,}")
    print(f"  lowongan dengan program studi: {jb.job_id.nunique():,}")
    print(f"  program studi unik: {jb.nama_program_studi.nunique():,}")

    peta_j, jj, ent_j = masukkan_jenjang(con)
    print("\nJENJANG")
    print(f"  entitas EDUCATION_LEVEL: {len(ent_j):,}, lowongan berjenjang: "
          f"{jj.job_id.nunique():,}")
    print(jj.drop_duplicates(["job_id", "jenjang_baku"]).jenjang_baku
          .value_counts().to_string())

    con.commit()
    con.close()

    con = sqlite3.connect(TUJUAN)
    g = masukkan_skill_gabungan(con, TUJUAN)
    print(f"\nSKILL GABUNGAN: {len(g):,} baris")
    con.execute("VACUUM")
    con.commit()
    con.close()
    print(f"\nTersimpan: {TUJUAN}")


if __name__ == "__main__":
    main()
