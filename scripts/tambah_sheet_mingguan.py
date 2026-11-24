"""
Tambahan sheet: Taksonomi Escudero per Periode Pengamatan (Mingguan)
====================================================================
Permintaan pembimbing (Bu Tri, 20 September 2026): menambah satu sheet pada
4_Taksonomi_Escudero.xlsx berisi taksonomi Escudero per periode pengamatan,
dengan periode mingguan.

Minggu didefinisikan Senin--Minggu (ISO), diambil dari kolom posted_date.
Seluruh 5.121 lowongan punya tanggal posting, tersebar pada 89 minggu, tetapi
sebarannya sangat tidak merata:

  - 2023-04-03 s.d. 2025-04-27  : 60 lowongan pada 34 minggu (1--7 per minggu).
    Ini iklan lama yang masih tayang saat pengambilan data, bukan hasil
    pengamatan mingguan. Ditandai "sebelum periode pengamatan".
  - 2025-04-28 s.d. 2026-05-03  : inti periode pengamatan, 41--404 per minggu.
  - 2026-05-04 s.d. 2026-05-17  : 16 lowongan, terpotong batas akhir
    pengambilan data. Ditandai "terpotong batas pengambilan data".

Penandaan itu dibuat supaya pembacaan tren tidak tertipu oleh minggu-minggu
yang isinya cuma satu-dua lowongan.

    python tambah_sheet_mingguan.py db.sqlite 4_Taksonomi_Escudero.xlsx
"""
import sys
import sqlite3

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

F = "Calibri"
HDR = PatternFill("solid", fgColor="1F4E79")
SUB = PatternFill("solid", fgColor="DDEBF7")
thin = Side(style="thin", color="D9D9D9")
BD = Border(thin, thin, thin, thin)

BROAD = ["Cognitive Skills", "Socioemotional Skills", "Manual Skills"]

AWAL_PENGAMATAN = pd.Timestamp("2025-04-28")
AKHIR_PENGAMATAN = pd.Timestamp("2026-05-03")


def keterangan(mulai):
    if mulai < AWAL_PENGAMATAN:
        return "sebelum periode pengamatan (iklan lama, data renggang)"
    if mulai > AKHIR_PENGAMATAN:
        return "terpotong batas pengambilan data"
    return "periode pengamatan"


def bangun(db_path):
    con = sqlite3.connect(db_path)
    df = pd.read_sql("""
        SELECT j.id AS id_lowongan, j.posted_date,
               s.escudero_broad_category AS kategori,
               s.escudero_subcategory AS subkategori
        FROM job_skills js
        JOIN jobs j   ON j.id = js.job_id
        JOIN skills s ON s.id = js.skill_id""", con)
    semua = pd.read_sql("SELECT id, posted_date FROM jobs", con)
    con.close()

    for d in (df, semua):
        t = pd.to_datetime(d["posted_date"], utc=True, errors="coerce").dt.tz_convert(None)
        d["mulai"] = t.dt.to_period("W-SUN").dt.start_time
        d["selesai"] = t.dt.to_period("W-SUN").dt.end_time.dt.normalize()

    minggu = pd.DataFrame({"mulai": sorted(semua["mulai"].unique())})
    minggu["selesai"] = minggu["mulai"] + pd.Timedelta(days=6)
    minggu["minggu"] = minggu["mulai"].dt.strftime("%G-W%V")
    minggu["keterangan_periode"] = minggu["mulai"].map(keterangan)

    n_low = semua.groupby("mulai").size().rename("jumlah_lowongan")
    n_low_skill = df.groupby("mulai")["id_lowongan"].nunique().rename(
        "jumlah_lowongan_berskill")
    n_sebut = df.groupby("mulai").size().rename("total_penyebutan_skill")

    tab = minggu.merge(n_low, on="mulai", how="left") \
                .merge(n_low_skill, on="mulai", how="left") \
                .merge(n_sebut, on="mulai", how="left")

    kat = df.pivot_table(index="mulai", columns="kategori", aggfunc="size", fill_value=0)
    kat = kat.reindex(columns=BROAD, fill_value=0)
    tab = tab.merge(kat, on="mulai", how="left")

    sub_kol = sorted(df["subkategori"].dropna().unique())
    sub = df.pivot_table(index="mulai", columns="subkategori", aggfunc="size", fill_value=0)
    sub = sub.reindex(columns=sub_kol, fill_value=0)
    tab = tab.merge(sub, on="mulai", how="left")

    angka = (["jumlah_lowongan", "jumlah_lowongan_berskill", "total_penyebutan_skill"]
             + BROAD + sub_kol)
    tab[angka] = tab[angka].fillna(0).astype(int)

    # Proporsi tiap kategori luas terhadap total penyebutan minggu itu.
    for b in BROAD:
        tab[f"% {b}"] = tab.apply(
            lambda r: r[b] / r["total_penyebutan_skill"] if r["total_penyebutan_skill"] else 0,
            axis=1)

    tab["rata2_skill_per_lowongan"] = tab.apply(
        lambda r: r["total_penyebutan_skill"] / r["jumlah_lowongan"]
        if r["jumlah_lowongan"] else 0, axis=1)

    urut = (["minggu", "mulai", "selesai", "keterangan_periode", "jumlah_lowongan",
             "jumlah_lowongan_berskill", "total_penyebutan_skill",
             "rata2_skill_per_lowongan"]
            + BROAD + [f"% {b}" for b in BROAD] + sub_kol)
    tab = tab[urut].rename(columns={"mulai": "tanggal_mulai", "selesai": "tanggal_selesai"})
    return tab, sub_kol


def tulis(tab, sub_kol, xlsx):
    wb = load_workbook(xlsx)
    nama = "Escudero per Minggu"
    if nama in wb.sheetnames:
        del wb[nama]
    ws = wb.create_sheet(nama)

    ws["A1"] = f"Taksonomi Escudero per Periode Pengamatan Mingguan ({len(tab)} minggu)"
    ws["A1"].font = Font(F, size=13, bold=True)
    ws["A2"] = ("Minggu Senin–Minggu berdasarkan tanggal posting lowongan. Kolom "
                "keterangan_periode menandai minggu yang isinya terlalu sedikit untuk "
                "dibaca sebagai tren: 34 minggu pertama hanya memuat 60 lowongan "
                "(iklan lama yang masih tayang), dan dua minggu terakhir terpotong "
                "batas akhir pengambilan data. Inti periode pengamatan adalah "
                "28 April 2025 – 3 Mei 2026.")
    ws["A2"].font = Font(F, size=9, italic=True, color="808080")
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[2].height = 42

    h = 4
    for j, c in enumerate(tab.columns, 1):
        cell = ws.cell(h, j, c)
        cell.font = Font(F, bold=True, color="FFFFFF", size=10)
        cell.fill = HDR
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BD
    ws.row_dimensions[h].height = 58

    for i, row in enumerate(tab.itertuples(index=False), h + 1):
        for j, v in enumerate(row, 1):
            if isinstance(v, pd.Timestamp):
                v = v.date()
            cell = ws.cell(i, j, v)
            cell.font = Font(F, size=10)
            cell.alignment = Alignment(vertical="top")

    kol = {c: i + 1 for i, c in enumerate(tab.columns)}
    for i in range(h + 1, h + 1 + len(tab)):
        ws.cell(i, kol["tanggal_mulai"]).number_format = "yyyy-mm-dd"
        ws.cell(i, kol["tanggal_selesai"]).number_format = "yyyy-mm-dd"
        ws.cell(i, kol["rata2_skill_per_lowongan"]).number_format = "0.00"
        for b in BROAD:
            ws.cell(i, kol[f"% {b}"]).number_format = "0.0%"
        # Baris di luar inti periode pengamatan diredupkan.
        if ws.cell(i, kol["keterangan_periode"]).value != "periode pengamatan":
            for j in range(1, len(tab.columns) + 1):
                ws.cell(i, j).font = Font(F, size=10, color="A6A6A6", italic=True)

    ws.freeze_panes = "E5"
    ws.auto_filter.ref = f"A{h}:{get_column_letter(len(tab.columns))}{h + len(tab)}"
    for c, w in (("minggu", 11), ("tanggal_mulai", 13), ("tanggal_selesai", 13),
                 ("keterangan_periode", 40), ("jumlah_lowongan", 12),
                 ("jumlah_lowongan_berskill", 14), ("total_penyebutan_skill", 14),
                 ("rata2_skill_per_lowongan", 14)):
        ws.column_dimensions[get_column_letter(kol[c])].width = w
    for c in BROAD + [f"% {b}" for b in BROAD]:
        ws.column_dimensions[get_column_letter(kol[c])].width = 15
    for c in sub_kol:
        ws.column_dimensions[get_column_letter(kol[c])].width = 17

    # Baris total, hanya untuk inti periode pengamatan.
    inti = tab[tab["keterangan_periode"] == "periode pengamatan"]
    r = h + len(tab) + 2
    ws.cell(r, 1, "TOTAL inti periode pengamatan").font = Font(F, bold=True, size=10)
    ws.cell(r, kol["keterangan_periode"], f"{len(inti)} minggu").font = Font(F, bold=True, size=10)
    for c in ["jumlah_lowongan", "jumlah_lowongan_berskill", "total_penyebutan_skill"] + BROAD + sub_kol:
        cell = ws.cell(r, kol[c], int(inti[c].sum()))
        cell.font = Font(F, bold=True, size=10)
        cell.number_format = "#,##0"
    for b in BROAD:
        cell = ws.cell(r, kol[f"% {b}"],
                       inti[b].sum() / inti["total_penyebutan_skill"].sum())
        cell.font = Font(F, bold=True, size=10)
        cell.number_format = "0.0%"

    wb.save(xlsx)
    return ws.title


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else "db.sqlite"
    xl = sys.argv[2] if len(sys.argv) > 2 else "4_Taksonomi_Escudero.xlsx"
    t, sk = bangun(db)
    nm = tulis(t, sk, xl)
    inti = t[t["keterangan_periode"] == "periode pengamatan"]
    print(f"Sheet '{nm}' ditambahkan ke {xl}")
    print(f"  total minggu           : {len(t)}")
    print(f"  inti periode pengamatan: {len(inti)} minggu, "
          f"{int(inti['jumlah_lowongan'].sum()):,} lowongan, "
          f"{int(inti['total_penyebutan_skill'].sum()):,} penyebutan skill")
    print(f"  kolom                  : {len(t.columns)}")
