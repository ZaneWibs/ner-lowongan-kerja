"""
Workbook telaah: Penggabungan Program Studi dan Jenjang Pendidikan
==================================================================
Permintaan pembimbing (Bu Tri, 20 September 2026): penggabungan program studi
(entitas DEGREE_FIELD) dan jenjang pendidikan (entitas EDUCATION_LEVEL)
mengacu pada tiga peraturan yang beliau kirim.

Prinsip yang dipakai -- sama dengan yang sudah disepakati untuk taksonomi
Escudero dan domain skill: TIDAK ada tahap pencocokan paksa. Nilai yang tidak
punya padanan resmi yang meyakinkan ditandai apa adanya sebagai "belum ada
padanan" supaya pembimbing yang memutuskan, bukan dipaksa masuk ke kategori
terdekat oleh kemiripan teks.

    python build_prodi_jenjang.py db.sqlite
"""
import re
import sqlite3
import sys
import unicodedata
from collections import Counter

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

import parse_regulasi as REG

F = "Calibri"
HDR = PatternFill("solid", fgColor="1F4E79")
SUB = PatternFill("solid", fgColor="DDEBF7")
KUNING = PatternFill("solid", fgColor="FFF2CC")
thin = Side(style="thin", color="D9D9D9")
BD = Border(thin, thin, thin, thin)

# ---------------------------------------------------------------------------
# Acuan 1: Permendikbud 154/2014 Pasal 2 -- rumpun ilmu
# ---------------------------------------------------------------------------
RUMPUN_154 = [
    ("Ilmu Agama", "Mengkaji keyakinan tentang ketuhanan atau ketauhidan serta "
                   "teks-teks suci agama."),
    ("Ilmu Humaniora", "Mengkaji dan mendalami nilai kemanusiaan dan pemikiran "
                       "manusia."),
    ("Ilmu Sosial", "Mengkaji dan mendalami hubungan antar manusia dan berbagai "
                    "fenomena masyarakat."),
    ("Ilmu Alam", "Mengkaji dan mendalami alam semesta."),
    ("Ilmu Formal", "Mengkaji dan mendalami sistem formal teoritis."),
    ("Ilmu Terapan", "Mengkaji dan mendalami aplikasi ilmu bagi kehidupan "
                     "manusia."),
]

# ---------------------------------------------------------------------------
# Acuan 2: Permendikbud 154/2014 Pasal 11 -- jenjang dan penulisan gelar,
# dilengkapi jenjang vokasi menurut Permendikbudristek 32/2021 jo. Kepdirjen
# Diksi 27/D/M/2022.
# ---------------------------------------------------------------------------
JENJANG_DIKTI = [
    ("Diploma I", "D1", "Ahli Pratama", "AP.", "Vokasi",
     "Permendikbud 154/2014 Pasal 11 ayat (1) huruf a"),
    ("Diploma II", "D2", "Ahli Muda", "AM.", "Vokasi",
     "Permendikbud 154/2014 Pasal 11 ayat (1) huruf b"),
    ("Diploma III", "D3", "Ahli Madya", "AMd.", "Vokasi",
     "Permendikbud 154/2014 Pasal 11 ayat (1) huruf c"),
    ("Sarjana Terapan", "D4", "Sarjana Terapan", "S.Tr.", "Vokasi",
     "Permendikbud 154/2014 Pasal 11 ayat (1) huruf e"),
    ("Magister Terapan", "-", "Magister Terapan", "M.Tr.", "Vokasi",
     "Permendikbud 154/2014 Pasal 11 ayat (1) huruf g"),
    ("Doktor Terapan", "-", "Doktor Terapan", "Dr.Tr.", "Vokasi",
     "Permendikbud 154/2014 Pasal 11 ayat (1) huruf i"),
    ("Sarjana", "S1", "Sarjana", "S.", "Akademik",
     "Permendikbud 154/2014 Pasal 11 ayat (1) huruf d"),
    ("Magister", "S2", "Magister", "M.", "Akademik",
     "Permendikbud 154/2014 Pasal 11 ayat (1) huruf f"),
    ("Doktor", "S3", "Doktor", "Dr.", "Akademik",
     "Permendikbud 154/2014 Pasal 11 ayat (1) huruf h"),
    ("Profesi", "-", "sesuai inisial gelar profesi", "(di depan/belakang nama)",
     "Profesi", "Permendikbud 154/2014 Pasal 11 ayat (1) huruf j"),
    ("Spesialis", "-", "sesuai inisial gelar spesialis", "(di depan/belakang nama)",
     "Spesialis", "Permendikbud 154/2014 Pasal 11 ayat (1) huruf j"),
]

# Jenjang di bawah pendidikan tinggi. TIDAK diatur oleh ketiga peraturan yang
# dikirim pembimbing (ketiganya khusus pendidikan tinggi), jadi acuannya
# disebut terpisah supaya tidak terkesan ikut diatur di sana.
JENJANG_LUAR = [
    ("SD/MI sederajat", "Pendidikan Dasar"),
    ("SMP/MTs sederajat", "Pendidikan Dasar"),
    ("SMA/MA sederajat", "Pendidikan Menengah"),
    ("SMK/MAK sederajat", "Pendidikan Menengah"),
]

URUT_JENJANG = ([j[0] for j in JENJANG_DIKTI] + [j[0] for j in JENJANG_LUAR])
PRIORITAS = {n: i for i, n in enumerate(
    ["SD/MI sederajat", "SMP/MTs sederajat", "SMA/MA sederajat",
     "SMK/MAK sederajat", "Diploma I", "Diploma II", "Diploma III",
     "Sarjana Terapan", "Sarjana", "Profesi", "Spesialis", "Magister",
     "Magister Terapan", "Doktor", "Doktor Terapan"])}


def _n(t):
    t = unicodedata.normalize("NFKD", str(t))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower().replace("’", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9/+&' -]", " ", t)).strip()


# ---------------------------------------------------------------------------
# Pemetaan nilai EDUCATION_LEVEL ke jenjang baku.
# Setiap pola dicocokkan pada seluruh teks, jadi satu nilai bisa menghasilkan
# beberapa jenjang sekaligus -- misalnya "SMA/SMK/D3/S1" menghasilkan empat.
# ---------------------------------------------------------------------------
POLA_JENJANG = [
    (r"\bs\s?-?\s?3\b|\bdoktor(?!\s*terapan)\b|\bph\.?d\b", "Doktor"),
    (r"\bdoktor\s*terapan\b", "Doktor Terapan"),
    (r"\bs\s?-?\s?2\b|\bmagister(?!\s*terapan)\b|\bmaster\b|\bm\s?sc\b", "Magister"),
    (r"\bmagister\s*terapan\b", "Magister Terapan"),
    # Tanpa batas kata di ujung kanan, karena OCR/anotasi menghasilkan bentuk
    # menempel seperti "S1Psikologi", "S1jurusan", dan "pendS1".
    (r"\bs\s?-?\s?1|\bsarjana(?!\s*terapan)\b|\bstrata\s*1\b|\bbachelor\b|"
     r"\bs (?:pd|kom|ked|e|t|h|si|psi|sos|ip|pt|farm)\b", "Sarjana"),
    (r"\bsarjana\s*terapan\b|\bd\s?-?\s?4\b|\bd\s?iv\b", "Sarjana Terapan"),
    (r"\bd\s?-?\s?3\b|\bd\s?iii\b|\bdiploma\s*3\b|\bdiploma\s*iii\b", "Diploma III"),
    (r"\bd\s?-?\s?2\b|\bd\s?ii\b|\bdiploma\s*2\b", "Diploma II"),
    (r"\bd\s?-?\s?1\b|\bd\s?i\b(?!ii)|\bdiploma\s*1\b", "Diploma I"),
    (r"\bprofesi\b|\bners\b|\bapoteker\b|\bdokter\b|\bdr\b", "Profesi"),
    (r"\bspesialis\b", "Spesialis"),
    (r"\bsmk\b|\bstm\b|\bsmea\b|\bmak\b|\bsekolah menengah kejuruan\b|\bsmak\b",
     "SMK/MAK sederajat"),
    (r"\bsma\b|\bsmu\b|\bslta\b|\bma\b|\bmadrasah aliyah\b|\bpaket c\b|"
     r"\bsekolah menengah atas\b|\bsma/k\b", "SMA/MA sederajat"),
    (r"\bsmp\b|\bsltp\b|\bmts\b|\bsekolah menengah pertama\b|\bpaket b\b",
     "SMP/MTs sederajat"),
    (r"\bsd\b|\bmi\b|\bsekolah dasar\b|\bpaket a\b", "SD/MI sederajat"),
]
# "Diploma" tanpa angka. Menurut keterangan pembimbing, bentuk ini di lowongan
# berarti lulusan diploma mana pun, jadi dipetakan ke keempat jenjang diploma
# (Permendikbud 154/2014 Pasal 11 huruf a, b, c, dan e).
RX_DIPLOMA_UMUM = re.compile(r"\bdiploma\b|\bdiplima\b")
DIPLOMA_SEMUA = ["Diploma I", "Diploma II", "Diploma III", "Sarjana Terapan"]
# Keterangan status mahasiswa, bukan jenjang yang sudah dimiliki.
RX_STATUS = re.compile(
    r"\bmahasiswa\b|\bmahasiswi\b|\bsemester\b|\bsemster\b|\bfresh graduate\b|"
    r"\brecent graduate\b|\bcurrently enrolled\b|\bkuliah\b|\bbersekolah\b|"
    r"\btingkat akhir\b|\btidak sedang berkuliah\b")


def petakan_jenjang(teks):
    t = _n(teks)
    # "sma/k" dan "sma/ k" adalah singkatan SMA/SMK.
    if re.search(r"\bsma\s*/\s*k\b", t):
        t += " smk"
    hasil = []
    for pola, nama in POLA_JENJANG:
        if re.search(pola, t):
            hasil.append(nama)
    # Bentuk terapan lebih spesifik daripada bentuk akademiknya.
    if "Sarjana Terapan" in hasil and "Sarjana" in hasil and not re.search(
            r"\bs\s?-?\s?1\b|\bbachelor\b", t):
        hasil.remove("Sarjana")
    for induk, khusus in (("Magister", "Magister Terapan"),
                          ("Doktor", "Doktor Terapan")):
        if khusus in hasil and induk in hasil and not re.search(
                r"\bs\s?-?\s?[23]\b", t):
            hasil.remove(induk)
    hasil = sorted(set(hasil), key=lambda x: PRIORITAS.get(x, 99))

    if hasil:
        status = "terpetakan"
        catatan = ""
    elif RX_DIPLOMA_UMUM.search(t):
        hasil = list(DIPLOMA_SEMUA)
        status = "terpetakan"
        catatan = ("Menyebut \"diploma\" tanpa angka. Menurut keterangan "
                   "pembimbing, yang dimaksud adalah seluruh lulusan diploma, "
                   "sehingga dipetakan ke keempat jenjang diploma "
                   "(Permendikbud 154/2014 Pasal 11 huruf a, b, c, dan e).")
    elif RX_STATUS.search(t):
        status = "bukan jenjang"
        catatan = ("Keterangan status mahasiswa atau kelulusan, bukan jenjang "
                   "pendidikan yang sudah dimiliki.")
    elif len(t) > 45 or re.search(r"\btahun\b|\bmembersihkan\b|\bmenjaga\b|"
                                  r"\bmengambil\b|\bmembantu\b|\bmenyediakan\b|"
                                  r"\bmemastikan\b|\bmenerjemahkan\b", t):
        status = "salah label"
        catatan = ("Teksnya bukan jenjang pendidikan; kemungkinan kesalahan "
                   "anotasi atau prediksi model.")
    else:
        status = "perlu keputusan"
        catatan = "Tidak cocok dengan jenjang mana pun pada acuan."
    return hasil, status, catatan


# ---------------------------------------------------------------------------
# Padanan istilah program studi.
# Ditulis eksplisit, bukan hasil kemiripan teks, supaya tiap baris bisa
# dipertanggungjawabkan. Sisi kiri adalah bentuk yang muncul di lowongan,
# sisi kanan nama resmi pada Kepdirjen 96/B/KPT/2025 atau 27/D/M/2022.
# ---------------------------------------------------------------------------
PADANAN = {
    "dkv": "Desain Komunikasi Visual",
    "it": "Teknologi Informasi",
    "ti": "Teknologi Informasi",
    "si": "Sistem Informasi",
    "sdm": "Manajemen Sumber Daya Manusia",
    "msdm": "Manajemen Sumber Daya Manusia",
    "manajemen sdm": "Manajemen Sumber Daya Manusia",
    "manajemen sumber daya manusia": "Manajemen Sumber Daya Manusia",
    "hrd": "Manajemen Sumber Daya Manusia",
    "marketing": "Pemasaran",
    "digital marketing": "Pemasaran Digital",
    "management": "Manajemen",
    "accounting": "Akuntansi",
    "finance": "Keuangan",
    "human resource": "Manajemen Sumber Daya Manusia",
    "business": "Bisnis",
    "law": "Hukum",
    "psychology": "Psikologi",
    "engineering": "Rekayasa",
    "informatics": "Informatika",
    "computer science": "Ilmu Komputer",
    "information system": "Sistem Informasi",
    "public relation": "Hubungan Masyarakat",
    "public relations": "Hubungan Masyarakat",
    "humas": "Hubungan Masyarakat",
    "tata boga": "Seni Kuliner",
    "perkantoran": "Administrasi Perkantoran",
    "administrasi perkantoran": "Administrasi Perkantoran",
    "sekretaris": "Administrasi Perkantoran",
    "k3": "Keselamatan dan Kesehatan Kerja",
}
# Pada Kepdirjen 96/B/KPT/2025 program akademik bidang keteknikan diberi nama
# "Rekayasa ..." menggantikan "Teknik ..." (misalnya Teknik Mesin -> Rekayasa
# Mesin), sedangkan pada daftar vokasi bentuk "Teknik ..." dan "Teknologi
# Rekayasa ..." tetap dipakai. Karena itu bentuk "Teknik X" dicoba dua-duanya.
AWALAN_SETARA = [("teknik ", "rekayasa "), ("rekayasa ", "teknik "),
                 ("teknik ", ""), ("teknologi ", ""),
                 ("ilmu ", ""), ("", "ilmu "), ("", "teknik "),
                 ("", "teknologi "), ("", "rekayasa ")]


def bangun_padanan_prodi(acuan, nilai):
    """Cocokkan tiap nilai DEGREE_FIELD ke nama program studi resmi."""
    # Kepdirjen 96/B/KPT/2025 banyak memakai nama berbentuk pilihan, misalnya
    # "Ilmu Komputer atau Informatika" dan "Ilmu atau Sains Komunikasi". Kedua
    # bentuknya didaftarkan sebagai kunci supaya istilah di lowongan yang hanya
    # menyebut salah satunya tetap ketemu.
    def varian(nama):
        n = _n(nama)
        if not n:
            return []
        hasil = {n}
        if " atau " in n:
            kiri, kanan = (x.strip() for x in n.split(" atau ", 1))
            if len(kiri.split()) == 1 and len(kanan.split()) >= 2:
                # Bentuk "kata pilihan + ekor bersama", misalnya
                # "Ilmu atau Sains Komunikasi" dan "Teknik atau Rekayasa
                # Militer". Kata pilihannya TIDAK berdiri sendiri sebagai nama
                # program studi, jadi yang didaftarkan hanya gabungan dengan
                # ekornya.
                ekor = kanan.split(" ", 1)[1]
                hasil.update({f"{kiri} {ekor}", kanan})
            else:
                # Bentuk dua nama utuh, misalnya "Ilmu Komputer atau
                # Informatika" dan "Susastra atau Sastra".
                hasil.update({kiri, kanan})
        return [h for h in hasil if len(h) >= 3]

    peta = {}
    for r in acuan.itertuples(index=False):
        for nama in (r.nama_program_studi, r.nama_inggris):
            for kunci in varian(nama):
                peta.setdefault(kunci, r)
    baris = []
    for teks, jumlah, n_lowongan in nilai:
        k = _n(teks)
        cocok = cara = ""
        r = peta.get(k)
        if r is not None:
            cara = "cocok persis dengan nama resmi"
        elif k in PADANAN and _n(PADANAN[k]) in peta:
            r = peta[_n(PADANAN[k])]
            cara = "cocok lewat padanan istilah"
        else:
            for a, b in AWALAN_SETARA:
                if a and not k.startswith(a):
                    continue
                alt = b + k[len(a):] if a else b + k
                if alt in peta:
                    r = peta[alt]
                    cara = f"cocok setelah penyetaraan awalan ({a.strip() or '-'} -> {b.strip() or '-'})"
                    break
        # Nama resmi yang memuat istilah ini sebagai kata utuh. Ini TIDAK
        # dipakai sebagai usulan -- hanya ditawarkan sebagai daftar pilihan,
        # karena "Manajemen Bisnis" bukan "Manajemen Bisnis Internasional".
        kandidat = sorted({v.nama_program_studi for kk, v in peta.items()
                           if kk.startswith(k + " ") or kk.endswith(" " + k)
                           or f" {k} " in f" {kk} "})
        if r is None:
            cara = ("belum ada padanan persis -- lihat kolom kandidat"
                    if kandidat else "belum ada padanan resmi")
        baris.append({
            "istilah_di_lowongan": teks,
            "jumlah_penyebutan": jumlah,
            "jumlah_lowongan": n_lowongan,
            "usulan_nama_program_studi": r.nama_program_studi if r is not None else "",
            "rumpun_ilmu": r.rumpun_ilmu if r is not None else "",
            "jenis_pendidikan": r.jenis_pendidikan if r is not None else "",
            "inisial_gelar": r.inisial_gelar if r is not None else "",
            "cara_pencocokan": cara,
            "jumlah_kandidat": len(kandidat),
            "kandidat_nama_resmi": "; ".join(kandidat[:8]) + (
                f"; ... ({len(kandidat) - 8} lagi)" if len(kandidat) > 8 else ""),
            "keputusan_pembimbing": "",
            "catatan_pembimbing": "",
        })
    return pd.DataFrame(baris)


# ---------------------------------------------------------------------------
def tulis(ws, df, judul, catatan, lebar=None, baris_hdr=4):
    ws.cell(1, 1, judul).font = Font(F, size=13, bold=True)
    c = ws.cell(2, 1, catatan)
    c.font = Font(F, size=9, italic=True, color="808080")
    c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[2].height = 46
    for j, h in enumerate(df.columns, 1):
        cell = ws.cell(baris_hdr, j, h)
        cell.font = Font(F, bold=True, color="FFFFFF", size=10)
        cell.fill = HDR
        cell.alignment = Alignment(horizontal="center", vertical="center",
                                   wrap_text=True)
        cell.border = BD
    ws.row_dimensions[baris_hdr].height = 34
    for i, row in enumerate(df.itertuples(index=False), baris_hdr + 1):
        for j, v in enumerate(row, 1):
            cell = ws.cell(i, j, v)
            cell.font = Font(F, size=10)
            cell.alignment = Alignment(vertical="top", wrap_text=(j > 2))
    ws.freeze_panes = ws.cell(baris_hdr + 1, 1).coordinate
    ws.auto_filter.ref = (f"A{baris_hdr}:"
                          f"{get_column_letter(len(df.columns))}{baris_hdr + len(df)}")
    if lebar:
        for j, w in lebar.items():
            ws.column_dimensions[get_column_letter(j)].width = w
    return ws


def bangun(db_path, keluaran):
    acuan = REG.daftar_acuan()
    acuan = acuan[["sumber_acuan", "jenis_pendidikan", "rumpun_ilmu",
                   "nama_program_studi", "nama_inggris", "inisial_gelar",
                   "kolom_lengkap"]]

    con = sqlite3.connect(db_path)
    df_field = pd.read_sql("""
        SELECT TRIM(text) AS teks, COUNT(*) AS jumlah,
               COUNT(DISTINCT job_id) AS n_lowongan
        FROM entities WHERE label='DEGREE_FIELD' AND TRIM(text)<>''
        GROUP BY LOWER(TRIM(text)) ORDER BY jumlah DESC""", con)
    df_level = pd.read_sql("""
        SELECT TRIM(text) AS teks, COUNT(*) AS jumlah,
               COUNT(DISTINCT job_id) AS n_lowongan
        FROM entities WHERE label='EDUCATION_LEVEL' AND TRIM(text)<>''
        GROUP BY LOWER(TRIM(text)) ORDER BY jumlah DESC""", con)
    con.close()

    prodi = bangun_padanan_prodi(
        acuan, list(zip(df_field.teks, df_field.jumlah, df_field.n_lowongan)))

    baris_lv = []
    for t, n, nl in zip(df_level.teks, df_level.jumlah, df_level.n_lowongan):
        jj, status, cat = petakan_jenjang(t)
        baris_lv.append({
            "istilah_di_lowongan": t, "jumlah_penyebutan": n,
            "jumlah_lowongan": nl,
            "usulan_jenjang_baku": ", ".join(jj),
            "banyak_jenjang": len(jj),
            "kelompok_jenjang": ", ".join(sorted({
                "Pendidikan Tinggi" if x in [k[0] for k in JENJANG_DIKTI]
                else dict(JENJANG_LUAR)[x] for x in jj})) if jj else "",
            "status": status, "catatan": cat,
            "keputusan_pembimbing": "", "catatan_pembimbing": "",
        })
    level = pd.DataFrame(baris_lv)

    wb = Workbook()
    wb.remove(wb.active)

    # ---------------------------------------------------------------- sheet 1
    ringkas = pd.DataFrame([
        ("ACUAN YANG DIPAKAI", "", ""),
        ("Permendikbud No. 154 Tahun 2014",
         "Rumpun Ilmu Pengetahuan dan Teknologi serta Gelar Lulusan Perguruan Tinggi",
         "Dipakai untuk: enam rumpun ilmu (Pasal 2) dan jenjang beserta penulisan "
         "gelarnya (Pasal 11). Berkas dikirim dengan nama permendikbud_14_2014.pdf, "
         "isinya Permendikbud 154 Tahun 2014."),
        ("Permendikbudristek No. 32 Tahun 2021",
         "Penamaan Program Studi pada Perguruan Tinggi",
         "Berkas yang dikirim memuat pelaksanaannya, yaitu Kepdirjen Pendidikan "
         "Vokasi No. 27/D/M/2022 tentang Daftar Nama Program Studi Jenis "
         "Pendidikan Tinggi Vokasi (D1, D2, D3, Sarjana Terapan, Magister "
         "Terapan, Doktor Terapan). Dipakai untuk nama program studi vokasi."),
        ("Kepdirjen Dikti No. 96/B/KPT/2025",
         "Nama Program Studi pada Jenis Pendidikan Akademik dan Pendidikan Profesi",
         "Dipakai untuk nama program studi sarjana, magister, doktor, profesi, "
         "dan spesialis. Mencabut Kepdirjen 163/E/KPT/2022."),
        ("", "", ""),
        ("HASIL PEMETAAN", "", ""),
        ("Nilai DEGREE_FIELD unik", f"{len(prodi):,}",
         f"{int(prodi.jumlah_penyebutan.sum()):,} penyebutan"),
        ("Nilai EDUCATION_LEVEL unik", f"{len(level):,}",
         f"{int(level.jumlah_penyebutan.sum()):,} penyebutan"),
        ("Nama program studi resmi terbaca", f"{len(acuan):,}",
         "dari Lampiran ketiga peraturan"),
        ("", "", ""),
        ("YANG PERLU DIKETAHUI", "", ""),
        ("Berkas peraturan berupa hasil pindaian",
         "Lampirannya dibaca dengan OCR",
         "Sebagian baris pada Lampiran I Kepdirjen 96/B/KPT/2025 kehilangan kolom "
         "nama Indonesia saat dipindai, sehingga daftar acuan pada sheet 'Acuan "
         "Nama Program Studi' belum tentu lengkap. Kolom centang jenjang (S/M/Dr "
         "dan D1-D4) sengaja tidak diambil karena tanda centangnya terbaca "
         "beragam dan tidak bisa dipertanggungjawabkan."),
        ("Penamaan keteknikan berubah",
         "Teknik ... -> Rekayasa ...",
         "Pada Kepdirjen 96/B/KPT/2025 program akademik keteknikan bernama "
         "\"Rekayasa Mesin\", \"Rekayasa Elektro\", dan seterusnya, bukan lagi "
         "\"Teknik Mesin\". Bentuk \"Teknik ...\" masih dipakai pada daftar "
         "vokasi. Karena itu istilah \"Teknik X\" di lowongan dicocokkan ke "
         "dua-duanya dan ditandai pada kolom cara_pencocokan."),
        ("Istilah \"diploma\" tanpa angka",
         "119 penyebutan",
         "Menurut keterangan pembimbing, penyebutan \"diploma\" saja di lowongan "
         "berarti seluruh lulusan diploma, sehingga dipetakan sekaligus ke "
         "Diploma I, Diploma II, Diploma III, dan Sarjana Terapan (D4) -- bukan "
         "disamakan dengan D3 saja. Keempatnya punya gelar berbeda menurut "
         "Permendikbud 154/2014 Pasal 11 huruf a, b, c, dan e."),
        ("Jenjang di bawah pendidikan tinggi",
         "SD, SMP, SMA, SMK",
         "Ketiga peraturan acuan seluruhnya mengatur pendidikan tinggi, sehingga "
         "SD/SMP/SMA/SMK tidak diatur di sana. Penamaannya pada sheet 'Acuan "
         "Jenjang dan Gelar' mengikuti jenjang pendidikan formal pada "
         "UU No. 20 Tahun 2003, dan diberi penanda tersendiri."),
        ("Tidak ada pencocokan paksa",
         "Nilai tanpa padanan dibiarkan kosong",
         "Sesuai prinsip yang sudah dipakai pada taksonomi Escudero dan domain "
         "skill: nilai yang tidak punya padanan resmi yang meyakinkan ditandai "
         "\"belum ada padanan resmi\", tidak dipaksa masuk ke nama terdekat."),
    ], columns=["Hal", "Isi", "Keterangan"])
    ws = tulis(wb.create_sheet("Ringkasan"), ringkas,
               "Penggabungan Program Studi dan Jenjang Pendidikan",
               "Acuan, cara kerja, dan hal-hal yang perlu diketahui sebelum "
               "membaca sheet berikutnya.",
               lebar={1: 38, 2: 34, 3: 86})
    for i in range(5, 5 + len(ringkas)):
        if not str(ws.cell(i, 2).value or "") and str(ws.cell(i, 1).value or ""):
            for j in range(1, 4):
                ws.cell(i, j).fill = SUB
                ws.cell(i, j).font = Font(F, bold=True, size=10)

    # ---------------------------------------------------------------- sheet 2
    rumpun = pd.DataFrame(RUMPUN_154, columns=["rumpun_ilmu", "pengertian"])
    rumpun["jumlah_program_studi_terbaca"] = rumpun.rumpun_ilmu.map(
        acuan.rumpun_ilmu.value_counts()).fillna(0).astype(int)
    tulis(wb.create_sheet("Acuan Rumpun Ilmu"), rumpun,
          "Rumpun Ilmu Pengetahuan dan Teknologi",
          "Permendikbud No. 154 Tahun 2014 Pasal 2. Keenam rumpun inilah tingkat "
          "pengelompokan tertinggi yang dipakai untuk menggabungkan program studi.",
          lebar={1: 22, 2: 84, 3: 22})

    # ---------------------------------------------------------------- sheet 3
    jen = pd.DataFrame(
        [(n, s, g, tul, jp, "Pendidikan Tinggi", sb)
         for n, s, g, tul, jp, sb in JENJANG_DIKTI]
        + [(n, "-", "-", "-", "-", k,
            "UU No. 20 Tahun 2003 (di luar lingkup ketiga peraturan acuan)")
           for n, k in JENJANG_LUAR],
        columns=["jenjang_baku", "sebutan_umum", "gelar", "penulisan_gelar",
                 "jenis_pendidikan", "kelompok", "dasar_hukum"])
    tulis(wb.create_sheet("Acuan Jenjang dan Gelar"), jen,
          "Jenjang Pendidikan dan Penulisan Gelar",
          "Jenjang pendidikan tinggi beserta gelarnya menurut Permendikbud No. 154 "
          "Tahun 2014 Pasal 11; jenjang vokasi Magister Terapan dan Doktor Terapan "
          "juga tercantum pada daftar program studi vokasi Kepdirjen 27/D/M/2022. "
          "Empat baris terakhir berada di luar lingkup ketiga peraturan acuan dan "
          "dicantumkan karena nilai EDUCATION_LEVEL di lowongan banyak yang "
          "menyebut jenjang menengah.",
          lebar={1: 20, 2: 14, 3: 26, 4: 22, 5: 16, 6: 20, 7: 56})

    # ---------------------------------------------------------------- sheet 4
    ws = tulis(wb.create_sheet("Pemetaan Jenjang"), level,
               f"Pemetaan Jenjang Pendidikan ({len(level):,} istilah unik)",
               "Satu baris satu istilah yang muncul di lowongan. Satu istilah bisa "
               "menghasilkan beberapa jenjang sekaligus (misalnya \"SMA/SMK/D3/S1\"). "
               "Kolom kuning untuk diisi pembimbing.",
               lebar={1: 42, 2: 12, 3: 12, 4: 34, 5: 10, 6: 24, 7: 16, 8: 60,
                      9: 22, 10: 34})
    dv = DataValidation(type="list", allow_blank=True, formula1='"setuju,perbaiki,hapus"')
    ws.add_data_validation(dv)
    dv.add(f"I5:I{4 + len(level)}")
    for i in range(5, 5 + len(level)):
        for j in (9, 10):
            ws.cell(i, j).fill = KUNING
            ws.cell(i, j).border = BD

    # ---------------------------------------------------------------- sheet 5
    ws = tulis(wb.create_sheet("Pemetaan Program Studi"), prodi,
               f"Pemetaan Program Studi ({len(prodi):,} istilah unik)",
               "Satu baris satu istilah bidang studi yang muncul di lowongan, beserta "
               "usulan nama resminya. Kolom cara_pencocokan menjelaskan dasar tiap "
               "usulan; istilah tanpa padanan yang meyakinkan sengaja dibiarkan "
               "kosong; nama resmi yang memuat istilah itu tetap ditawarkan pada "
               "kolom kandidat_nama_resmi sebagai bahan pilihan, bukan sebagai "
               "jawaban. Kolom kuning untuk diisi pembimbing.",
               lebar={1: 34, 2: 12, 3: 12, 4: 34, 5: 18, 6: 16, 7: 12, 8: 44,
                      9: 12, 10: 64, 11: 22, 12: 34})
    dv2 = DataValidation(type="list", allow_blank=True,
                         formula1='"setuju,perbaiki,gabungkan,hapus"')
    ws.add_data_validation(dv2)
    dv2.add(f"K5:K{4 + len(prodi)}")
    for i in range(5, 5 + len(prodi)):
        for j in (11, 12):
            ws.cell(i, j).fill = KUNING
            ws.cell(i, j).border = BD

    # ---------------------------------------------------------------- sheet 6
    tulis(wb.create_sheet("Acuan Nama Program Studi"), acuan,
          f"Nama Program Studi Resmi ({len(acuan):,} baris terbaca)",
          "Hasil pembacaan Lampiran Kepdirjen 96/B/KPT/2025 (akademik dan profesi) "
          "dan Kepdirjen Diksi 27/D/M/2022 (vokasi). Berkasnya hasil pindaian, jadi "
          "daftar ini belum tentu lengkap dan sebagian ejaannya masih mengandung "
          "galat OCR. Dipakai sebagai daftar bantu pencocokan, bukan pengganti "
          "naskah resmi.",
          lebar={1: 32, 2: 16, 3: 18, 4: 42, 5: 42, 6: 14, 7: 34})

    wb.save(keluaran)

    print(f"Tersimpan: {keluaran}")
    print(f"  Acuan nama program studi : {len(acuan):,}")
    print(f"  Pemetaan program studi   : {len(prodi):,} istilah")
    print(prodi.cara_pencocokan.str.replace(r" \(.*", "", regex=True)
          .value_counts().to_string())
    print(f"  Pemetaan jenjang         : {len(level):,} istilah")
    print(level.status.value_counts().to_string())
    return prodi, level


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else "db.sqlite"
    bangun(db, "2_Program_Studi_dan_Jenjang_Pendidikan.xlsx")
