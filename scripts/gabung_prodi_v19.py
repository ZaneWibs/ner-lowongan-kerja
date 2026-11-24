"""Penggabungan nama program studi yang jelas merujuk prodi yang sama (v19).
Hanya kasus pasti: salah ketik, istilah bahasa Inggris, nama lama vs nama baru
Kepdirjen Dikti 96/B/KPT/2025, dan bentrok kunci istilah (varian tanda baca yang
mendapat keputusan berbeda). Kasus lain diserahkan ke pembimbing."""
import sqlite3, sys, pandas as pd
GABUNG = {  # nama lama -> nama baku, alasan
    "Perikianan": ("Periklanan", "salah ketik"),
    "Graphic design": ("Desain Grafis", "istilah bahasa Inggris untuk prodi yang sama"),
    "Gizi": ("Ilmu atau Sains Gizi", "nama lama; Kepdirjen Dikti 96/B/KPT/2025 memakai 'Ilmu atau Sains Gizi'"),
    "Komunikasi": ("Ilmu atau Sains Komunikasi", "nama lama; Kepdirjen Dikti 96/B/KPT/2025 memakai 'Ilmu atau Sains Komunikasi'"),
}
BENTROK = {  # (kunci, nama_salah) -> dibuang karena varian tanda baca berbeda keputusan
    ("keuangan", "Manajemen"): "varian ', Keuangan' (1 penyebutan) berbeda keputusan dari 'Keuangan' (48 penyebutan → Analisis Keuangan); ikut keputusan mayoritas",
}
def terapkan(db):
    con = sqlite3.connect(db)
    if "log_gabung_prodi_v19" in [r[0] for r in con.execute("select name from sqlite_master")]:
        print(db, "sudah diterapkan"); return
    log = []
    for (k, salah), alasan in BENTROK.items():
        n = con.execute("""DELETE FROM job_bidang_studi WHERE nama_program_studi=? AND job_id IN (
            SELECT e.job_id FROM entities e WHERE e.label='DEGREE_FIELD')
            AND lower(trim(istilah, ' ,.;:-/()[]"''')) = ?""", (salah, k)).rowcount
        con.execute("DELETE FROM peta_bidang_studi WHERE kunci_istilah=? AND nama_program_studi=?", (k, salah))
        log.append((f"{k} → {salah}", "dihapus", alasan, n))
    for lama, (baru, alasan) in GABUNG.items():
        n = con.execute("UPDATE job_bidang_studi SET nama_program_studi=? WHERE nama_program_studi=?", (baru, lama)).rowcount
        con.execute("UPDATE peta_bidang_studi SET nama_program_studi=?, status_penerapan=status_penerapan||' + digabung v19' WHERE nama_program_studi=?", (baru, lama))
        log.append((lama, baru, alasan, n))
    # rumpun ikut prodi baku
    rp = dict(con.execute("SELECT nama_program_studi, rumpun_ilmu FROM peta_bidang_studi GROUP BY 1").fetchall())
    for lama, (baru, _) in GABUNG.items():
        con.execute("UPDATE job_bidang_studi SET rumpun_ilmu=? WHERE nama_program_studi=?", (rp.get(baru), baru))
        con.execute("UPDATE peta_bidang_studi SET rumpun_ilmu=? WHERE nama_program_studi=?", (rp.get(baru), baru))
    # hapus duplikat (job, prodi, istilah)
    con.execute("""DELETE FROM job_bidang_studi WHERE rowid NOT IN (
        SELECT MIN(rowid) FROM job_bidang_studi GROUP BY job_id, istilah, nama_program_studi)""")
    pd.DataFrame(log, columns=["nama_lama", "nama_baru", "alasan", "baris_berubah"]).to_sql("log_gabung_prodi_v19", con, index=False)
    con.commit()
    print(db, log, con.execute("select count(distinct nama_program_studi) from job_bidang_studi").fetchone())
for db in sys.argv[1:]: terapkan(db)
