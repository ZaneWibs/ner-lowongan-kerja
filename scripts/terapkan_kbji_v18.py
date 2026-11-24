"""
Basis data v18: penerapan telaah pembimbing atas kode KBJI 2014 per pekerjaan
=============================================================================
Bu Tri (6 Oktober 2026) mengisi 5_Kode_KBJI_per_Pekerjaan.xlsx:
  - sheet "Perlu Keputusan - Konflik": 152 kelompok "ikuti usulan",
    3 "pertahankan golongan pokok", 1 "lainnya" (Port Captain -> Profesional).
  - sheet "Perlu Keputusan - Belum Berkode": 22 judul diberi golongan pokok;
    judul tanpa isian berarti disetujui apa adanya.
  - Kesimpulan beliau: karena judul pekerjaan masih sangat umum, analisis
    cukup sampai golongan pokok (1 digit). Kode 4 digit disimpan sebagai
    informasi pendukung saja, tidak dipakai sebagai satuan analisis.

Yang berubah di basis data:
  - jobs.kbji_golongan_pokok_kode / _nama  : mengikuti keputusan beliau
  - jobs.kbji_source = 'telaah_pembimbing_kbji4' untuk baris yang berubah
  - kolom baru jobs.kbji_kode4, kbji_label4 : kode subgolongan pendukung
  - tabel baru log_kbji_v18                 : setiap perubahan golongan pokok

    python terapkan_kbji_v18.py
"""
import shutil
import sqlite3

import pandas as pd

SUMBER = "ner_jobposting_v17.sqlite"
TUJUAN = "ner_jobposting_v18.sqlite"
TELAAH = "bt_kbji2.xlsx"

GOLONGAN = {
    1: "Manajer", 2: "Profesional", 3: "Teknisi dan Asisten Profesional",
    4: "Tenaga Tata Usaha", 5: "Tenaga Usaha Jasa dan Tenaga Penjualan",
    6: "Pekerja Terampil Pertanian, Kehutanan dan Perikanan",
    7: "Pekerja Pengolahan, Kerajinan, dan Ybdi",
    8: "Operator dan Perakit Mesin", 9: "Pekerja Kasar",
}

KB = pd.read_pickle("kbji.pkl")
LABEL = dict(zip(KB.kode, KB.judul))

# Konflik yang TIDAK "ikuti usulan" (diidentifikasi per judul karena masing-
# masing kelompoknya hanya berisi satu judul).
KHUSUS = {
    # judul: (golongan pokok baru, kode4, alasan)
    "Port Captain (Tugboat)": (2, "", "Keputusan pembimbing: Profesional (golongan pokok 2). "
                               "KBJI 2014 tidak memuat jabatan pemimpin transportasi air "
                               "di golongan pokok 2; padanan terdekat 3152.01 Kapten Kapal "
                               "atau 1324.09 Kepala Pelabuhan Laut."),
    "Sales Safety": (None, "", "Keputusan pembimbing: pertahankan golongan pokok."),
    "Cleaning Service (CS)": (None, "", "Keputusan pembimbing: pertahankan golongan pokok."),
    "Fitness Manager": (None, "", "Keputusan pembimbing: pertahankan golongan pokok."),
}


def rencana():
    d = pd.read_pickle("kbji4_hasil.pkl")   # hasil klasifikasi yang dikirim 2 Oktober
    k = pd.read_excel(TELAAH, sheet_name="Perlu Keputusan - Konflik", header=3)
    b = pd.read_excel(TELAAH, sheet_name="Perlu Keputusan - Belum Berkode", header=3)

    keputusan = k.keputusan_pembimbing.fillna("").str.strip()
    assert set(keputusan) <= {"ikuti usulan", "pertahankan golongan pokok", "lainnya"}, set(keputusan)
    assert (keputusan != "ikuti usulan").sum() == len(KHUSUS)

    baris = []
    for r in d.itertuples(index=False):
        gol, kode4, alasan = r.gol, r.kode4, ""
        if r.status == "konflik dengan golongan pokok":
            if r.pekerjaan in KHUSUS:
                g_baru, kode4, alasan = KHUSUS[r.pekerjaan]
                gol = g_baru if g_baru else r.gol
            else:
                kode4 = r.kode_terbaik
                gol = int(kode4[0])
                alasan = (f"Keputusan pembimbing 'ikuti usulan': KBJI 2014 {kode4} "
                          f"{LABEL.get(kode4, '')}.")
        baris.append((r.pekerjaan, r.gol, gol, kode4, r.status, alasan))
    p = pd.DataFrame(baris, columns=["title", "gol_lama", "gol_baru", "kode4",
                                     "status_kode4", "alasan"])

    # Belum berkode: golongan pokok dari pembimbing
    bb = b[b.kode_KBJI_pembimbing.notna()]
    for r in bb.itertuples(index=False):
        g = int(float(r.kode_KBJI_pembimbing))
        m = (p.title == r.pekerjaan) & (p.gol_lama == r.golongan_pokok_kode)
        assert m.sum() == 1, r.pekerjaan
        p.loc[m, "gol_baru"] = g
        p.loc[m, "alasan"] = f"Keputusan pembimbing: golongan pokok {g} {GOLONGAN[g]}."
    return p


def main():
    p = rencana()
    shutil.copy(SUMBER, TUJUAN)
    con = sqlite3.connect(TUJUAN)
    cur = con.cursor()
    cur.execute("ALTER TABLE jobs ADD COLUMN kbji_kode4 TEXT")
    cur.execute("ALTER TABLE jobs ADD COLUMN kbji_label4 TEXT")
    cur.execute("""CREATE TABLE log_kbji_v18(job_id INT, title TEXT, gol_lama INT,
                   gol_baru INT, kode4 TEXT, alasan TEXT)""")

    n_ubah = 0
    for r in p.itertuples(index=False):
        ids = [x[0] for x in cur.execute(
            """SELECT id FROM jobs WHERE title=? AND kbji_golongan_pokok_kode=?
               AND COALESCE(kbji_ditangguhkan,0)=0""", (r.title, int(r.gol_lama)))]
        if not ids:
            continue
        ph = ",".join("?" * len(ids))
        cur.execute(f"UPDATE jobs SET kbji_kode4=?, kbji_label4=? WHERE id IN ({ph})",
                    (r.kode4 or None, LABEL.get(r.kode4) if r.kode4 else None, *ids))
        if int(r.gol_baru) != int(r.gol_lama):
            cur.execute(f"""UPDATE jobs SET kbji_golongan_pokok_kode=?,
                            kbji_golongan_pokok_nama=?, kbji_confidence=1.0,
                            kbji_source='telaah_pembimbing_kbji4' WHERE id IN ({ph})""",
                        (int(r.gol_baru), GOLONGAN[int(r.gol_baru)], *ids))
            cur.executemany("INSERT INTO log_kbji_v18 VALUES (?,?,?,?,?,?)",
                            [(i, r.title, int(r.gol_lama), int(r.gol_baru), r.kode4, r.alasan)
                             for i in ids])
            n_ubah += len(ids)
    con.commit()

    print(f"Lowongan yang golongan pokoknya berubah: {n_ubah:,}")
    print(pd.read_sql("""SELECT gol_lama, gol_baru, COUNT(*) n FROM log_kbji_v18
                         GROUP BY 1,2 ORDER BY n DESC""", con).to_string(index=False))
    print()
    print(pd.read_sql("""SELECT kbji_golongan_pokok_kode kode, kbji_golongan_pokok_nama nama,
                                COUNT(*) n FROM jobs WHERE COALESCE(kbji_ditangguhkan,0)=0
                         GROUP BY 1,2 ORDER BY 1""", con).to_string(index=False))
    print("kode4 terisi:", con.execute("SELECT COUNT(*) FROM jobs WHERE kbji_kode4 IS NOT NULL").fetchone()[0])
    con.execute("VACUUM")
    con.close()
    p.to_pickle("rencana_v18.pkl")


if __name__ == "__main__":
    main()
