"""
Identifikasi kode KBJI 2014 tingkat pekerjaan (2/3/4 digit) untuk setiap judul
=============================================================================
Permintaan pembimbing (Bu Tri, 2 Oktober 2026): golongan pokok (1 digit) sudah
ada di data; sekarang setiap pekerjaan (judul lowongan) diberi kode
subgolongan pokok (2 digit), golongan (3 digit), dan subgolongan (4 digit)
beserta labelnya menurut dokumen KBJI 2014 (BPS). Pekerjaan yang
membingungkan atau tidak dapat diklasifikasikan dibuatkan daftar untuk
ditelaah pembimbing.

Prinsip:
  - Kode 4 digit HARUS bersarang di golongan pokok yang sudah ditetapkan
    (sebagian sudah ditelaah pembimbing). Bila padanan terbaik ada di
    golongan pokok lain dan tidak ada padanan sah di golongan pokok yang
    ada, judul tidak dipaksa -- dimasukkan ke daftar konflik.
  - Tidak ada pencocokan kemiripan teks atau embedding. Setiap kode berasal
    dari aturan eksplisit di aturan_kbji4.py yang mencatat dasarnya.

    python klasifikasi_kbji4.py
"""
import re
import sqlite3

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

import aturan_kbji4 as A

DB = "ner_jobposting_v17.sqlite"
KELUARAN = "5_Kode_KBJI_per_Pekerjaan.xlsx"

F = "Calibri"
HDR = PatternFill("solid", fgColor="1F4E79")
SUB = PatternFill("solid", fgColor="DDEBF7")
KUNING = PatternFill("solid", fgColor="FFF2CC")
thin = Side(style="thin", color="D9D9D9")
BD = Border(thin, thin, thin, thin)

KB = pd.read_pickle("kbji.pkl")
JUDUL = dict(zip(KB.kode, KB.judul))


def label(kode):
    return JUDUL.get(kode, "")


def normal(t):
    t = str(t).lower()
    t = re.sub(r"[/\\\-_&+,.()\[\]:;|'\"!?#*]", " ", t)
    t = re.sub(r"\bstaf\b", "staff", t)
    return re.sub(r"\s+", " ", t).strip()


# Alternatif hanya sah bila digit pertamanya sama dengan golongan pokoknya.
ATURAN = []
for pola, best, alt, cat in A.ATURAN:
    alt_sah = {g: c for g, c in alt.items() if c and int(c[0]) == g}
    ATURAN.append((re.compile(pola), best, alt_sah, cat, pola))


def klasifikasi(judul, gol):
    k = normal(judul)
    for i, (rx, best, alt, cat, _) in enumerate(ATURAN):
        if not rx.search(k):
            continue
        if best is None:
            return dict(kode4="", status="tidak terklasifikasi -- judul terlalu umum",
                        kode_terbaik="", dasar=cat, aturan=i)
        if gol is None:
            return dict(kode4=best, status="golongan pokok belum ada",
                        kode_terbaik=best, dasar=cat, aturan=i)
        if int(best[0]) == gol:
            return dict(kode4=best, status="sesuai", kode_terbaik=best,
                        dasar=cat, aturan=i)
        if gol in alt:
            return dict(kode4=alt[gol],
                        status="disesuaikan dengan golongan pokok",
                        kode_terbaik=best, dasar=cat, aturan=i)
        return dict(kode4="", status="konflik dengan golongan pokok",
                    kode_terbaik=best, dasar=cat, aturan=i)
    return dict(kode4="", status="tidak terklasifikasi -- belum ada padanan",
                kode_terbaik="", dasar="", aturan=-1)


def bangun():
    con = sqlite3.connect(DB)
    d = pd.read_sql("""SELECT title AS pekerjaan, kbji_golongan_pokok_kode AS gol,
                              kbji_golongan_pokok_nama AS golongan_pokok,
                              COALESCE(kbji_source,'otomatis') AS sumber_gol,
                              COUNT(*) AS n
                       FROM jobs WHERE COALESCE(kbji_ditangguhkan,0)=0
                       GROUP BY 1,2,3,4""", con)
    con.close()
    # Satu judul bisa tersebar di >1 golongan pokok; klasifikasi per pasangan.
    d["gol"] = d.gol.map(lambda x: int(x) if pd.notna(x) else None)
    hasil = [klasifikasi(t, g) for t, g in zip(d.pekerjaan, d.gol)]
    h = pd.DataFrame(hasil)
    d = pd.concat([d.reset_index(drop=True), h], axis=1)

    d["kode2"] = d.kode4.str[:2]
    d["kode3"] = d.kode4.str[:3]
    d["label4"] = d.kode4.map(label)
    d["label3"] = d.kode3.map(label)
    d["label2"] = d.kode2.map(label)
    d["label_terbaik"] = d.kode_terbaik.map(label)
    d.loc[d.kode4 == "", ["kode2", "kode3"]] = ""
    return d


def tulis(ws, df, judul, catatan, lebar, hdr=4):
    ws.cell(1, 1, judul).font = Font(F, size=13, bold=True)
    c = ws.cell(2, 1, catatan)
    c.font = Font(F, size=9, italic=True, color="808080")
    c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[2].height = 52
    for j, h in enumerate(df.columns, 1):
        cell = ws.cell(hdr, j, h)
        cell.font = Font(F, bold=True, color="FFFFFF", size=10)
        cell.fill = HDR
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BD
    ws.row_dimensions[hdr].height = 32
    for i, row in enumerate(df.itertuples(index=False), hdr + 1):
        for j, v in enumerate(row, 1):
            if isinstance(v, float) and pd.isna(v):
                v = None
            cell = ws.cell(i, j, v)
            cell.font = Font(F, size=10)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    ws.freeze_panes = ws.cell(hdr + 1, 2).coordinate
    ws.auto_filter.ref = f"A{hdr}:{get_column_letter(len(df.columns))}{hdr + len(df)}"
    for j, w in lebar.items():
        ws.column_dimensions[get_column_letter(j)].width = w
    return ws


def kolom_kuning(ws, cols, n, hdr=4):
    for i in range(hdr + 1, hdr + 1 + n):
        for j in cols:
            ws.cell(i, j).fill = KUNING
            ws.cell(i, j).border = BD


def ekspor(d):
    wb = Workbook(); wb.remove(wb.active)
    tot = d.n.sum()
    grp = d.groupby("status").agg(judul=("pekerjaan", "size"), lowongan=("n", "sum"))
    def ambil(s):
        return (int(grp.judul.get(s, 0)), int(grp.lowongan.get(s, 0)))

    ok = d[d.kode4 != ""]
    # ------------------------------------------------------------- Ringkasan
    baris = [
        ("ACUAN", "", "", ""),
        ("Klasifikasi Baku Jabatan Indonesia (KBJI) 2014, BPS", "", "",
         "10 golongan pokok (1 digit), 43 subgolongan pokok (2 digit), 130 golongan "
         "(3 digit), 446 subgolongan (4 digit), 2.137 jabatan (6 digit). Seluruhnya "
         "terbaca utuh dari dokumen dan tercantum di sheet 'Acuan KBJI 2014'."),
        ("", "", "", ""),
        ("HASIL", "Judul", "Lowongan", "Keterangan"),
        ("Pasangan judul x golongan pokok", f"{len(d):,}", f"{tot:,}",
         "Satu judul bisa muncul di lebih dari satu golongan pokok."),
        ("Sudah punya kode 4 digit", f"{len(ok):,}", f"{ok.n.sum():,}",
         f"{ok.n.sum() / tot * 100:.1f}% lowongan"),
        ("   - sesuai", *[f"{x:,}" for x in ambil("sesuai")],
         "Padanan terbaik berada di golongan pokok yang sudah ditetapkan."),
        ("   - disesuaikan dengan golongan pokok",
         *[f"{x:,}" for x in ambil("disesuaikan dengan golongan pokok")],
         "Padanan terbaik ada di golongan pokok lain, tetapi ada kode yang sah di "
         "golongan pokok yang sudah ditetapkan. Kode terbaiknya tetap dicatat."),
        ("Konflik dengan golongan pokok",
         *[f"{x:,}" for x in ambil("konflik dengan golongan pokok")],
         "Golongan pokok yang ada tidak punya padanan sah untuk pekerjaan ini. "
         "Lihat sheet 'Perlu Keputusan - Konflik'."),
        ("Tidak terklasifikasi -- judul terlalu umum",
         *[f"{x:,}" for x in ambil("tidak terklasifikasi -- judul terlalu umum")],
         "Misalnya 'Supervisor', 'Management Trainee', 'Staff Operasional'."),
        ("Tidak terklasifikasi -- belum ada padanan",
         *[f"{x:,}" for x in ambil("tidak terklasifikasi -- belum ada padanan")],
         "Lihat sheet 'Perlu Keputusan - Belum Ada Kode'."),
        ("", "", "", ""),
        ("CARA MEMBACA", "", "", ""),
        ("Kode bersarang", "", "",
         "Kode 4 digit selalu diawali golongan pokok yang sudah ditetapkan. Kode "
         "2 dan 3 digit adalah induknya, sehingga satu kolom kode 4 digit sudah "
         "menentukan ketiganya."),
        ("Istilah baru", "", "",
         "KBJI 2014 tidak memuat istilah seperti content creator, KOL specialist, "
         "atau host live streaming. Kodenya dipilih dari kesamaan fungsi dengan "
         "uraian tugas KBJI, dan dasarnya tercatat di kolom 'dasar'."),
        ("Kode 4 digit 'YTDL'", "", "",
         "Untuk judul yang tidak menyebut jenis mesin atau bidangnya (misalnya "
         "'Operator Produksi'), dipakai subgolongan 'YTDL' (yang tidak termasuk "
         "di tempat lain) dari golongan yang paling dekat."),
    ]
    ring = pd.DataFrame(baris, columns=["Hal", "Judul", "Lowongan", "Keterangan"])
    ws = tulis(wb.create_sheet("Ringkasan"), ring,
               "Kode KBJI 2014 per Pekerjaan",
               "Identifikasi subgolongan pokok (2 digit), golongan (3 digit), dan "
               "subgolongan (4 digit) untuk setiap judul pekerjaan di dashboard.",
               {1: 44, 2: 12, 3: 12, 4: 100})
    for i in range(5, 5 + len(ring)):
        if ws.cell(i, 1).value and not ws.cell(i, 2).value and not ws.cell(i, 4).value:
            for j in range(1, 5):
                ws.cell(i, j).fill = SUB
                ws.cell(i, j).font = Font(F, bold=True, size=10)
        if ws.cell(i, 1).value == "HASIL":
            for j in range(1, 5):
                ws.cell(i, j).fill = SUB
                ws.cell(i, j).font = Font(F, bold=True, size=10)

    # ---------------------------------------------- Rekap per subgolongan
    rek = (ok.groupby(["kode4", "label4", "kode3", "label3", "kode2", "label2"])
           .agg(jumlah_judul=("pekerjaan", "size"), jumlah_lowongan=("n", "sum"))
           .reset_index().sort_values("jumlah_lowongan", ascending=False))
    tulis(wb.create_sheet("Rekap per Kode"), rek,
          f"Rekap per Subgolongan KBJI ({len(rek)} kode terpakai)",
          "Jumlah judul pekerjaan dan lowongan pada setiap kode 4 digit yang terpakai.",
          {1: 9, 2: 46, 3: 8, 4: 46, 5: 8, 6: 46, 7: 12, 8: 14})

    # ---------------------------------------------- Kode per pekerjaan
    utama = d[["pekerjaan", "n", "gol", "golongan_pokok", "sumber_gol",
               "kode2", "label2", "kode3", "label3", "kode4", "label4",
               "status", "kode_terbaik", "label_terbaik", "dasar"]].rename(columns={
        "n": "jumlah_lowongan", "gol": "kode_golongan_pokok",
        "sumber_gol": "sumber_golongan_pokok",
        "kode2": "kode_subgolongan_pokok", "label2": "subgolongan_pokok",
        "kode3": "kode_golongan", "label3": "golongan",
        "kode4": "kode_subgolongan", "label4": "subgolongan"})
    utama = utama.sort_values("jumlah_lowongan", ascending=False)
    tulis(wb.create_sheet("Kode per Pekerjaan"), utama,
          f"Kode KBJI 2014 per Pekerjaan ({len(utama):,} baris)",
          "Satu baris satu pasangan judul pekerjaan dan golongan pokoknya. Kolom "
          "kode_terbaik diisi bila kodenya disesuaikan dengan golongan pokok atau "
          "berkonflik, agar pembimbing bisa membandingkan.",
          {1: 34, 2: 10, 3: 9, 4: 30, 5: 16, 6: 9, 7: 32, 8: 8, 9: 34, 10: 9,
           11: 36, 12: 26, 13: 9, 14: 32, 15: 60})

    # ---------------------------------------------- Konflik (dikelompokkan)
    kf = d[d.status == "konflik dengan golongan pokok"].copy()
    kf_grp = (kf.groupby(["aturan", "gol", "golongan_pokok", "kode_terbaik", "label_terbaik",
                          "dasar"])
              .agg(jumlah_judul=("pekerjaan", "size"), jumlah_lowongan=("n", "sum"),
                   contoh_judul=("pekerjaan", lambda s: "; ".join(
                       s.iloc[:10].tolist()) + (f"; ... ({len(s) - 10} lagi)" if len(s) > 10 else "")))
              .reset_index().sort_values("jumlah_lowongan", ascending=False))
    kf_grp = kf_grp[["contoh_judul", "jumlah_judul", "jumlah_lowongan", "gol",
                     "golongan_pokok", "kode_terbaik", "label_terbaik", "dasar"]].rename(
        columns={"gol": "golongan_pokok_saat_ini_kode",
                 "golongan_pokok": "golongan_pokok_saat_ini",
                 "kode_terbaik": "usulan_kode_KBJI", "label_terbaik": "usulan_label"})
    kf_grp["usulan_golongan_pokok"] = kf_grp.usulan_kode_KBJI.str[0].map(
        lambda x: f"{x} {label(x).title()}")
    kf_grp["keputusan_pembimbing"] = ""
    kf_grp["kode_pilihan_pembimbing"] = ""
    kf_grp["catatan_pembimbing"] = ""
    ws = tulis(wb.create_sheet("Perlu Keputusan - Konflik"), kf_grp,
               f"Konflik Golongan Pokok ({len(kf_grp)} kelompok, "
               f"{int(kf_grp.jumlah_judul.sum())} judul, {int(kf_grp.jumlah_lowongan.sum())} lowongan)",
               "Pekerjaan yang padanan KBJI-nya berada di golongan pokok berbeda dari "
               "golongan pokok yang sudah ditetapkan, dan tidak ada kode sah di golongan "
               "pokok yang sekarang. Dikelompokkan per pola supaya cukup diputuskan sekali "
               "per kelompok. Pilihan: 'ikuti usulan' (golongan pokok ikut berubah) atau "
               "'pertahankan golongan pokok' (isi kode_pilihan_pembimbing).",
               {1: 60, 2: 9, 3: 10, 4: 10, 5: 30, 6: 10, 7: 34, 8: 50, 9: 28, 10: 24,
                11: 16, 12: 34})
    dv = DataValidation(type="list", allow_blank=True,
                        formula1='"ikuti usulan,pertahankan golongan pokok,lainnya"')
    ws.add_data_validation(dv); dv.add(f"J5:J{4 + len(kf_grp)}")
    kolom_kuning(ws, (10, 11, 12), len(kf_grp))

    # Rincian konflik per judul
    kf_r = kf[["pekerjaan", "n", "gol", "golongan_pokok", "kode_terbaik",
               "label_terbaik"]].sort_values("n", ascending=False).rename(columns={
        "n": "jumlah_lowongan", "gol": "golongan_pokok_saat_ini_kode",
        "golongan_pokok": "golongan_pokok_saat_ini", "kode_terbaik": "usulan_kode_KBJI",
        "label_terbaik": "usulan_label"})
    tulis(wb.create_sheet("Rincian Konflik per Judul"), kf_r,
          f"Rincian Konflik per Judul ({len(kf_r)} judul)",
          "Daftar lengkap judul pada sheet sebelumnya, untuk rujukan.",
          {1: 40, 2: 10, 3: 10, 4: 34, 5: 10, 6: 40})

    # ---------------------------------------------- Belum ada kode
    bt = d[d.status.str.startswith("tidak terklasifikasi")][
        ["pekerjaan", "n", "gol", "golongan_pokok", "status", "dasar"]].copy()
    bt = bt.sort_values("n", ascending=False).rename(columns={
        "n": "jumlah_lowongan", "gol": "golongan_pokok_kode", "dasar": "keterangan"})
    bt["kode_KBJI_pembimbing"] = ""
    bt["catatan_pembimbing"] = ""
    ws = tulis(wb.create_sheet("Perlu Keputusan - Belum Berkode"), bt,
               f"Pekerjaan Belum Ada Kode ({len(bt):,} judul, {int(bt.jumlah_lowongan.sum()):,} lowongan)",
               "Judul yang terlalu umum atau belum punya padanan pada aturan. Kolom "
               "kuning untuk kode 4 digit pilihan pembimbing. Daftar kode lengkap ada di "
               "sheet 'Acuan KBJI 2014'.",
               {1: 44, 2: 10, 3: 10, 4: 30, 5: 34, 6: 50, 7: 16, 8: 34})
    kolom_kuning(ws, (7, 8), len(bt))

    # ---------------------------------------------- Acuan KBJI
    ac = KB[KB.digit.isin([1, 2, 3, 4])][["kode", "tingkat", "judul", "uraian"]].copy()
    ac["uraian"] = ac.uraian.str.slice(0, 600)
    tulis(wb.create_sheet("Acuan KBJI 2014"), ac,
          f"Acuan KBJI 2014 ({len(ac)} kode, 1 s.d. 4 digit)",
          "Seluruh kode golongan pokok, subgolongan pokok, golongan, dan subgolongan "
          "beserta uraiannya (dipotong 600 karakter).",
          {1: 9, 2: 18, 3: 50, 4: 120})
    jb = KB[KB.digit == 6][["kode", "judul"]].copy()
    jb["kode_subgolongan"] = jb.kode.str[:4]
    tulis(wb.create_sheet("Acuan Jabatan 6 Digit"), jb,
          f"Acuan Jabatan KBJI 2014 ({len(jb):,} jabatan, 6 digit)",
          "Daftar jabatan sebagai bantuan memilih kode.", {1: 10, 2: 60, 3: 16})

    wb.save(KELUARAN)
    return kf_grp, bt, rek


if __name__ == "__main__":
    d = bangun()
    d.to_pickle("kbji4_hasil.pkl")
    kf, bt, rek = ekspor(d)
    print(d.groupby("status").agg(judul=("pekerjaan", "size"), lowongan=("n", "sum")).to_string())
    print(f"\nkode terpakai: {len(rek)} | konflik: {len(kf)} kelompok | belum ada kode: {len(bt)} judul")
