"""
Ekspor Dataset Lengkap ke Excel
================================
Membuat satu berkas Excel berisi seluruh data yang sudah dikumpulkan dan
diidentifikasi, untuk diserahkan ke pembimbing.

    python ekspor_dataset_excel.py outputs/ner_jobposting.sqlite

Sheet yang dihasilkan:
  1. Kamus Data          — penjelasan tiap kolom dan cara pembentukannya
  2. Lowongan            — 5.121 baris, satu baris satu lowongan
  3. Skill per Lowongan  — 44.400 baris, satu baris satu penyebutan skill
  4. Daftar Skill        — 13.829 skill unik beserta atribut Layer 2
  5. Entitas Lain        — entitas NER di luar skill (pendidikan, lokasi, dll)
  6. Rekap Atribut       — tabulasi seluruh atribut Layer 2 dengan rumus hidup

Catatan: sheet Entitas Lain berisi puluhan ribu baris. Bila berkasnya terlalu
berat dibuka, jalankan dengan argumen --tanpa-entitas.
"""
import ast
import json
import re
import sys
import sqlite3

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

F = "Calibri"
HDR = PatternFill("solid", fgColor="1F4E79")
SUB = PatternFill("solid", fgColor="DDEBF7")
thin = Side(style="thin", color="D9D9D9")
BD = Border(thin, thin, thin, thin)


def tulis_sheet(wb, nama, df, judul, catatan=None, lebar=None, freeze="A4"):
    ws = wb.create_sheet(nama)
    ws["A1"] = judul
    ws["A1"].font = Font(F, size=13, bold=True)
    if catatan:
        ws["A2"] = catatan
        ws["A2"].font = Font(F, size=9, italic=True, color="808080")

    baris_hdr = 3
    for j, h in enumerate(df.columns, 1):
        c = ws.cell(baris_hdr, j, h)
        c.font = Font(F, bold=True, color="FFFFFF", size=10)
        c.fill = HDR
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BD
    ws.row_dimensions[baris_hdr].height = 30

    for i, row in enumerate(df.itertuples(index=False), baris_hdr + 1):
        for j, v in enumerate(row, 1):
            c = ws.cell(i, j, v)
            c.font = Font(F, size=10)
            c.alignment = Alignment(vertical="top")

    ws.freeze_panes = freeze
    ws.auto_filter.ref = (f"A{baris_hdr}:"
                          f"{get_column_letter(len(df.columns))}{baris_hdr + len(df)}")
    if lebar:
        for j, w in lebar.items():
            ws.column_dimensions[get_column_letter(j)].width = w
    return ws


def _as_dict(v):
    if isinstance(v, dict):
        return v
    try:
        return ast.literal_eval(v)
    except Exception:
        try:
            return eval(v, {"__builtins__": {}}, {"nan": float("nan")})
        except Exception:
            return {}


def muat_metadata(json_path):
    """Ambil SELURUH kolom metadata dari gold annotations.

    Basis data hanya menyimpan 10 kolom lowongan, padahal sumbernya memuat 31 --
    termasuk deskripsi, persyaratan, tunjangan, ukuran perusahaan, provinsi,
    mode kerja, dan batas usia. Semuanya disertakan di sini karena pembimbing
    meminta dataset yang memuat seluruh kolom yang sudah dikumpulkan.
    """
    with open(json_path, encoding="utf-8") as f:
        gold = json.load(f)
    baris = []
    for r in gold:
        d = _as_dict(r.get("data"))
        d["_url"] = r.get("url")
        baris.append(d)
    df = pd.DataFrame(baris)
    # Excel menolak sel di atas 32.767 karakter; teks terpanjang saat ini 6.172
    # karakter, tetapi pemotongan tetap dipasang sebagai pengaman.
    for kol in ("description", "requirements", "benefits"):
        if kol in df.columns:
            df[kol] = df[kol].astype(str).str.slice(0, 32000)
    return df


def _kunci(t):
    """Kunci pembanding longgar antara skill hasil anotasi dan skill metadata."""
    return re.sub(r"[^a-z0-9]+", " ", str(t).lower()).strip()


def bangun_skill_gabungan(con, meta):
    """Gabungkan skill hasil anotasi teks dengan skill metadata situs sumber.

    Dibuat atas permintaan pembimbing (Bu Tri, 20 September 2026): ada 303
    lowongan yang kolom jumlah_skill-nya 0 padahal kolom skill_dari_sumber
    berisi data. Kedua sumber itu memang berbeda:

      - skill hasil anotasi  : dibaca dari teks deskripsi/persyaratan lowongan,
                               berbahasa Indonesia, inilah objek ekstraksi NER.
      - skill metadata       : tag yang dipilih perusahaan dari daftar pilihan
                               situs Glints, berbahasa Inggris dan sudah baku.

    Sheet ini menyatukan keduanya TANPA mengubah variabel utama, dengan kolom
    sumber_skill sebagai penanda, supaya pembimbing bisa menilai dampaknya
    sebelum memutuskan apakah gabungan ini dipakai sebagai variabel analisis.

    Catatan yang wajib diingat saat membacanya:
      - skill metadata hanya ada di lowongan Glints (4.213 lowongan); tidak ada
        satu pun di 908 lowongan Dealls, sehingga penggabungan menambah skill
        secara tidak merata antar portal.
      - hanya 11,7% frasa metadata yang benar-benar muncul di teks lowongan,
        jadi sebagian besar bukan bukti tekstual.
    """
    anotasi = pd.read_sql("""
        SELECT js.job_id AS id_lowongan, s.name AS skill, s.label AS label_ner,
               s.escudero_broad_category AS kategori_escudero,
               s.escudero_subcategory AS subkategori_escudero
        FROM job_skills js JOIN skills s ON s.id = js.skill_id""", con)
    anotasi["sumber_skill"] = "anotasi teks"

    peta_url = pd.read_sql("SELECT id AS id_lowongan, url AS _url, title AS judul_pekerjaan,"
                           " kbji_golongan_pokok_nama AS jabatan_kbji FROM jobs", con)

    baris = []
    if meta is not None and "skills" in meta.columns:
        m = meta[["_url", "skills"]].merge(peta_url[["id_lowongan", "_url"]], on="_url")
        for jid, s in zip(m.id_lowongan, m.skills):
            for x in str(s or "").split(","):
                x = x.strip()
                if x:
                    baris.append((jid, x))
    metadata = pd.DataFrame(baris, columns=["id_lowongan", "skill"])
    metadata["label_ner"] = ""
    metadata["kategori_escudero"] = ""
    metadata["subkategori_escudero"] = ""
    metadata["sumber_skill"] = "metadata situs"

    # Tandai yang muncul di kedua sumber, dibandingkan dengan kunci longgar.
    # Baris kembar tidak digandakan: yang dipertahankan adalah baris anotasi
    # (karena membawa label NER dan klasifikasi Escudero), hanya penandanya
    # yang diubah menjadi "kedua sumber".
    pasangan_anotasi = {(j, _kunci(s)) for j, s in zip(anotasi.id_lowongan, anotasi.skill)}
    if len(metadata):
        kembar = {(j, _kunci(s)) for j, s in zip(metadata.id_lowongan, metadata.skill)
                  } & pasangan_anotasi
        metadata = metadata[[(j, _kunci(s)) not in kembar
                             for j, s in zip(metadata.id_lowongan, metadata.skill)]].copy()
        anotasi.loc[[(j, _kunci(s)) in kembar
                     for j, s in zip(anotasi.id_lowongan, anotasi.skill)],
                    "sumber_skill"] = "kedua sumber"

    gab = pd.concat([anotasi, metadata], ignore_index=True)
    gab = gab.merge(peta_url[["id_lowongan", "judul_pekerjaan", "jabatan_kbji"]],
                    on="id_lowongan", how="left")
    gab = gab[["id_lowongan", "judul_pekerjaan", "jabatan_kbji", "skill", "sumber_skill",
               "label_ner", "kategori_escudero", "subkategori_escudero"]]
    return gab.sort_values(["id_lowongan", "sumber_skill", "skill"]).reset_index(drop=True)


def ekspor(db_path, keluaran, json_path=None, sertakan_entitas=True):
    con = sqlite3.connect(db_path)
    meta = muat_metadata(json_path) if json_path else None
    wb = Workbook()
    wb.remove(wb.active)

    # ---------------------------------------------------------------- sheet 1
    kamus = pd.DataFrame([
        ("SHEET: Lowongan", "", "", ""),
        ("id_lowongan", "Pengenal internal lowongan", "Basis data", "1–5121"),
        ("judul_pekerjaan", "Judul setelah normalisasi ejaan", "Normalisasi otomatis", "teks"),
        ("judul_asli", "Judul apa adanya dari sumber", "Scraping", "teks"),
        ("perusahaan", "Nama perusahaan pemasang", "Scraping", "teks"),
        ("lokasi", "Lokasi penempatan", "Scraping", "teks"),
        ("industri", "Sektor industri", "Scraping", "teks"),
        ("tanggal_posting", "Tanggal lowongan dipasang", "Scraping", "YYYY-MM-DD"),
        ("kode_kbji_1digit", "Kode golongan pokok KBJI 2014 (1 digit)",
         "Lexicon → fuzzy → k-NN, diperiksa ulang lewat pemetaan 4 digit, lalu telaah pembimbing",
         "1–9 (satuan analisis)"),
        ("jabatan_kbji", "Nama golongan pokok KBJI 2014", "Sama seperti di atas", "9 golongan pokok"),
        ("kode_kbji_4digit", "Kode subgolongan KBJI 2014 (4 digit)",
         "Aturan eksplisit per judul pekerjaan, ditelaah pembimbing. Informasi pendukung; "
         "analisis memakai 1 digit karena judul lowongan umumnya terlalu umum",
         "kode 4 digit; kosong bila judul terlalu umum atau belum berpadanan"),
        ("label_kbji_4digit", "Nama subgolongan KBJI 2014", "Dokumen KBJI 2014 (BPS)",
         "teks; pengertian lengkapnya di sheet 'Acuan KBJI 4 Digit'"),
        ("sumber_klasifikasi", "Asal golongan pokok", "Penanda proses",
         "otomatis / manual_review / telaah_pembimbing / telaah_pembimbing_kbji4"),
        ("gaji_min", "Batas bawah gaji per bulan", "Metadata lowongan (BUKAN model NER)", "rupiah"),
        ("gaji_max", "Batas atas gaji per bulan", "Metadata lowongan (BUKAN model NER)", "rupiah"),
        ("gaji_teks_asli", "Teks gaji apa adanya", "Metadata lowongan", "teks"),
        ("jumlah_skill", "Banyaknya penyebutan skill hasil ANOTASI teks lowongan. "
                         "Inilah variabel utama yang dipakai seluruh analisis.",
         "Anotasi manual atas deskripsi/persyaratan", "bilangan"),
        ("jumlah_skill_metadata", "Banyaknya skill versi metadata situs sumber",
         "Tag pilihan perusahaan di situs Glints", "bilangan (0 untuk seluruh lowongan Dealls)"),
        ("jumlah_skill_gabungan", "Gabungan kedua sumber tanpa pengulangan",
         "Anotasi ∪ metadata", "bilangan"),
        ("status_sumber_skill", "Asal data skill lowongan ini",
         "Turunan dari dua kolom di atas",
         "ada skill hasil anotasi / hanya dari metadata situs / "
         "tidak ada skill di kedua sumber"),
        ("ukuran_perusahaan", "Rentang jumlah karyawan", "Scraping", "teks"),
        ("situs_perusahaan", "Alamat situs perusahaan", "Scraping", "URL"),
        ("provinsi / negara", "Wilayah penempatan", "Scraping", "teks"),
        ("kategori_sumber", "Kategori pekerjaan menurut situs sumber", "Scraping",
         "teks (berbeda dari KBJI)"),
        ("jenis_kerja", "Full-Time, Part-Time, dan sejenisnya", "Scraping", "teks"),
        ("mode_kerja", "Onsite, Hybrid, atau Remote", "Scraping", "teks"),
        ("pengalaman_min / pengalaman_min_tahun", "Pengalaman minimal diminta", "Scraping",
         "teks / angka tahun"),
        ("kelompok_pengalaman", "Pengelompokan jenjang pengalaman", "Scraping", "teks"),
        ("jenjang_pendidikan", "Pendidikan minimal menurut situs sumber", "Scraping",
         "teks (berbeda dari entitas EDUCATION_LEVEL hasil NER)"),
        ("jenjang_pendidikan_baku", "Jenjang pendidikan yang diminta di teks lowongan, "
         "dibakukan", "Entitas EDUCATION_LEVEL hasil NER, dipetakan ke jenjang baku "
         "(Permendikbud 154/2014 dan Kepdirjen) lalu ditelaah pembimbing",
         "SD / SMP / SMA / SMK / Diploma I–III / Sarjana Terapan / Sarjana / Magister / "
         "Doktor ...; dipisah '; ' bila lebih dari satu"),
        ("program_studi_baku", "Program studi yang diminta, sudah dibakukan. Istilah "
         "berbeda yang mengacu pada prodi sama digabung (mis. 'accounting', 'akutansi', "
         "'akuntansi' → Akuntansi; 'marketing', 'pemasaran' → Manajemen)",
         "Entitas DEGREE_FIELD hasil NER, dipetakan ke nama prodi Kepdirjen Diksi "
         "27/D/M/2022 & Kepdirjen Dikti 96/B/KPT/2025, ditelaah pembimbing",
         "nama prodi baku; dipisah '; ' bila lebih dari satu"),
        ("usia_min / usia_max", "Batas usia pelamar", "Scraping", "angka"),
        ("skill_dari_sumber", "Daftar skill versi situs sumber", "Scraping",
         "teks (pembanding hasil NER)"),
        ("batas_lamaran", "Tanggal penutupan lamaran", "Scraping", "tanggal"),
        ("masih_dibuka", "Status lowongan saat pengambilan data", "Scraping", "True / False"),
        ("dilihat / pelamar", "Jumlah tayangan dan pelamar", "Scraping",
         "angka (hanya 17,7% terisi)"),
        ("sumber_data", "Situs asal data", "Scraping", "glints"),
        ("deskripsi", "TEKS LENGKAP deskripsi pekerjaan", "Scraping",
         "teks panjang; inilah bahan mentah model NER"),
        ("persyaratan", "Teks lengkap bagian persyaratan", "Scraping", "teks panjang"),
        ("tunjangan", "Daftar tunjangan yang ditawarkan", "Scraping", "teks"),
        ("tautan", "URL lowongan asli", "Scraping", "URL"),
        ("", "", "", ""),
        ("SHEET: Skill per Lowongan", "", "", ""),
        ("id_lowongan", "Merujuk sheet Lowongan", "Basis data", "1–5121"),
        ("judul_pekerjaan", "Disalin agar sheet ini bisa dibaca sendiri", "Basis data", "teks"),
        ("jabatan_kbji", "Disalin agar bisa dipivot langsung", "Basis data", "9 golongan"),
        ("skill", "Teks skill hasil ekstraksi model NER", "Model IndoBERT NER", "teks"),
        ("label_ner", "Jenis entitas menurut model", "Model IndoBERT NER",
         "SKILL / SOFT_SKILL / TOOL / PROGRAMMING_LANGUAGE"),
        ("importance", "Wajib atau nilai tambah", "Kata pemicu di kalimat sekitar",
         "REQUIRED / PREFERRED / UNKNOWN"),
        ("proficiency", "Tingkat penguasaan diminta", "Kata pemicu di kalimat sekitar",
         "BASIC / INTERMEDIATE / ADVANCED / UNKNOWN"),
        ("jenis_skill", "Atribut Layer 2", "Pemetaan satu-satu dari label_ner",
         "TECHNICAL_SKILL / SOFT_SKILL / TOOL / PROGRAMMING_LANGUAGE"),
        ("domain_skill", "Bidang keilmuan", "Aturan + lexicon + fuzzy + embedding",
         "10 nilai"),
        ("fungsi_skill", "Fungsi kerja", "Lexicon kata kunci", "11 nilai"),
        ("transferability", "Kemudahan dipindah antar pekerjaan",
         "Aturan deterministik dari label_ner dan domain", "HIGH / MEDIUM / LOW"),
        ("kategori_escudero", "Kategori luas Escudero et al. (2025)", "Lexicon + fuzzy + aturan",
         "Cognitive / Socioemotional / Manual"),
        ("subkategori_escudero", "Subkategori Escudero", "Lexicon + fuzzy + aturan",
         "14 subkategori"),
        ("", "", "", ""),
        ("SHEET: Skill Gabungan", "", "", ""),
        ("(penjelasan)", "Menyatukan skill hasil anotasi teks dengan skill metadata situs, "
                         "atas permintaan pembimbing. Dibuat terpisah supaya variabel utama "
                         "di sheet 'Skill per Lowongan' tidak berubah.", "", ""),
        ("skill", "Teks skill dari salah satu atau kedua sumber", "Anotasi ∪ metadata", "teks"),
        ("sumber_skill", "Penanda asal baris", "Pembandingan kedua sumber",
         "anotasi teks / kedua sumber / metadata situs"),
        ("label_ner", "Jenis entitas menurut model NER",
         "Baris anotasi: apa adanya. Baris metadata: hanya diisi bila ada skill "
         "hasil anotasi yang namanya sama persis, karena tag metadata tidak punya "
         "rentang teks pada lowongan sehingga tidak pernah dilabeli entitas.",
         "SKILL / SOFT_SKILL / TOOL / PROGRAMMING_LANGUAGE atau kosong"),
        ("kategori_escudero / subkategori_escudero", "Taksonomi Escudero et al. (2025)",
         "Berjenjang: (1) apa adanya untuk baris anotasi; (2) diwarisi dari skill "
         "anotasi yang namanya sama; (3) lexicon kata kunci bahasa Inggris; "
         "(4) sisanya dibiarkan kosong, tidak dipaksa masuk kategori terdekat.",
         "3 kategori luas / 14 subkategori atau kosong"),
        ("sumber_label", "Dasar pelabelan baris ini", "Penanda proses",
         "hasil anotasi dan klasifikasi Escudero (42.365 baris) / diwarisi dari "
         "skill hasil anotasi yang namanya sama (12.582) / lexicon kata kunci "
         "(4.705) / lexicon kata kunci lapis kedua (1.304) / penetapan langsung "
         "per istilah (260) / bukan keterampilan, tidak diberi label (8)"),
        ("dugaan_pengulangan_makna", "Menandai baris metadata yang maknanya sama "
         "dengan skill hasil anotasi pada lowongan yang sama, meski tulisannya "
         "berbeda bahasa (misalnya metadata \"Communication Skills\" sementara "
         "anotasi menulis \"komunikasi\")",
         "Pembandingan 18 konsep yang ditulis eksplisit",
         "nama konsep atau kosong; daftar konsepnya belum lengkap"),
        ("", "", "", ""),
        ("SHEET: Daftar Skill", "", "", ""),
        ("skill", "Satu baris satu skill unik", "Model IndoBERT NER", "teks"),
        ("jumlah_penyebutan", "Berapa kali muncul di seluruh korpus", "Hitungan", "bilangan"),
        ("jumlah_lowongan", "Pada berapa lowongan berbeda skill ini muncul", "Hitungan", "bilangan"),
        ("(kolom atribut lain)", "Sama dengan sheet Skill per Lowongan", "", ""),
        ("", "", "", ""),
        ("SHEET: Program Studi per Lowongan", "", "", ""),
        ("(penjelasan)", "Satu baris satu pasangan lowongan–program studi baku. Gunakan sheet "
         "ini (bukan teks DEGREE_FIELD mentah) untuk menghitung bidang studi, karena istilah "
         "bersinonim sudah digabung.", "", ""),
        ("istilah_di_lowongan", "Teks bidang studi apa adanya di lowongan", "Model NER", "teks"),
        ("program_studi_baku / rumpun_ilmu", "Hasil pembakuan", "Pemetaan yang ditelaah pembimbing",
         "nama prodi / rumpun ilmu Permendikbud 154/2014"),
        ("", "", "", ""),
        ("SHEET: Rekap Program Studi", "", "", ""),
        ("jumlah_lowongan", "Banyaknya lowongan berbeda yang meminta prodi ini",
         "COUNT DISTINCT id_lowongan", "bilangan"),
        ("istilah_yang_digabung", "Semua istilah di lowongan yang dipetakan ke prodi ini",
         "Pemetaan", "teks"),
        ("", "", "", ""),
        ("SHEET: Entitas Lain", "", "", ""),
        ("nilai_baku", "Untuk DEGREE_FIELD: program studi baku; untuk EDUCATION_LEVEL: "
         "jenjang baku. Kosong untuk jenis entitas lain atau istilah yang dikeluarkan "
         "pembimbing.", "Pemetaan yang ditelaah pembimbing", "teks"),
    ], columns=["Kolom", "Keterangan", "Cara Pembentukan", "Nilai yang Mungkin"])

    ws = tulis_sheet(
        wb, "Kamus Data", kamus,
        "Kamus Data — Dataset NER Lowongan Kerja Indonesia",
        "Penjelasan setiap kolom pada sheet berikutnya, beserta cara nilainya dibentuk.",
        lebar={1: 26, 2: 46, 3: 44, 4: 44})
    for i in range(4, 4 + len(kamus)):
        if str(ws.cell(i, 1).value or "").startswith("SHEET:"):
            for j in range(1, 5):
                ws.cell(i, j).fill = SUB
                ws.cell(i, j).font = Font(F, bold=True, size=10)
    for i in range(4, 4 + len(kamus)):
        for j in range(1, 5):
            ws.cell(i, j).alignment = Alignment(vertical="top", wrap_text=True)

    # ---------------------------------------------------------------- sheet 2
    lowongan = pd.read_sql("""
        SELECT j.id AS id_lowongan, j.title AS judul_pekerjaan,
               j.title_raw AS judul_asli, c.name AS perusahaan, l.name AS lokasi,
               j.industry AS industri, j.posted_date AS tanggal_posting,
               j.kbji_golongan_pokok_kode AS kode_kbji_1digit,
               j.kbji_golongan_pokok_nama AS jabatan_kbji,
               j.kbji_kode4 AS kode_kbji_4digit,
               j.kbji_label4 AS label_kbji_4digit,
               COALESCE(j.kbji_source,'otomatis') AS sumber_klasifikasi,
               j.salary_min AS gaji_min, j.salary_max AS gaji_max,
               j.salary_raw AS gaji_teks_asli,
               (SELECT COUNT(*) FROM job_skills js WHERE js.job_id=j.id) AS jumlah_skill,
               j.url AS tautan
        FROM jobs j
        LEFT JOIN companies c ON c.id=j.company_id
        LEFT JOIN locations l ON l.id=j.location_id
        ORDER BY j.id""", con)

    if meta is not None:
        tambahan = {
            "company_size": "ukuran_perusahaan", "company_website": "situs_perusahaan",
            "province": "provinsi", "country": "negara", "category": "kategori_sumber",
            "job_type": "jenis_kerja", "work_mode": "mode_kerja",
            "experience_min": "pengalaman_min", "experience_min_years": "pengalaman_min_tahun",
            "experience_level_group": "kelompok_pengalaman",
            "education_level": "jenjang_pendidikan", "min_age": "usia_min",
            "max_age": "usia_max", "skills": "skill_dari_sumber",
            "description": "deskripsi", "requirements": "persyaratan",
            "benefits": "tunjangan", "deadline": "batas_lamaran",
            "is_open": "masih_dibuka", "views": "dilihat", "applicants": "pelamar",
            "source": "sumber_data",
        }
        kol = ["_url"] + [k for k in tambahan if k in meta.columns]
        gab = meta[kol].rename(columns={**tambahan, "_url": "tautan"})
        lowongan = lowongan.merge(gab, on="tautan", how="left")
        # Susun ulang: tautan dan tiga kolom teks panjang ditaruh paling kanan
        # supaya kolom-kolom ringkas tetap terbaca saat sheet dibuka.
        # Nilai boolean ditulis Excel sebagai =FALSE(); diubah ke teks agar
        # terbaca wajar dan tidak dianggap rumus.
        if "masih_dibuka" in lowongan.columns:
            lowongan["masih_dibuka"] = lowongan["masih_dibuka"].map(
                {True: "Ya", False: "Tidak", "True": "Ya", "False": "Tidak"}).fillna("")

        ekor = ["deskripsi", "persyaratan", "tunjangan", "tautan"]
        lowongan = lowongan[[c for c in lowongan.columns if c not in ekor]
                            + [c for c in ekor if c in lowongan.columns]]

    # --- kolom tambahan: hitungan skill dari kedua sumber --------------------
    import skill_gabungan_label as SGL
    gabungan = SGL.bangun(db_path, json_path)
    rekap = (gabungan.groupby(["id_lowongan", "sumber_skill"]).size()
             .unstack(fill_value=0).reindex(columns=["anotasi teks", "kedua sumber",
                                                     "metadata situs"], fill_value=0))
    rekap = rekap.reindex(lowongan["id_lowongan"].values, fill_value=0)
    lowongan["jumlah_skill_metadata"] = (rekap["metadata situs"] + rekap["kedua sumber"]).values
    lowongan["jumlah_skill_gabungan"] = rekap.sum(axis=1).values

    def _status(a, g):
        if g == 0:
            return "tidak ada skill di kedua sumber"
        if a == 0:
            return "hanya dari metadata situs"
        return "ada skill hasil anotasi"

    lowongan["status_sumber_skill"] = [
        _status(a, g) for a, g in zip(lowongan["jumlah_skill"],
                                      lowongan["jumlah_skill_gabungan"])]

    # Ditaruh tepat setelah jumlah_skill supaya mudah dibandingkan.
    urut = list(lowongan.columns)
    for c in ("jumlah_skill_metadata", "jumlah_skill_gabungan", "status_sumber_skill"):
        urut.remove(c)
    sisip = urut.index("jumlah_skill") + 1
    urut[sisip:sisip] = ["jumlah_skill_metadata", "jumlah_skill_gabungan",
                         "status_sumber_skill"]
    lowongan = lowongan[urut]

    # --- program studi & jenjang baku per lowongan (sinonim sudah digabung) ---
    _jb = pd.read_sql("SELECT DISTINCT job_id, nama_program_studi FROM job_bidang_studi", con)
    _jj = pd.read_sql("SELECT DISTINCT job_id, jenjang_baku FROM job_jenjang", con)
    _urut_j = ["SD", "SMP", "SMA", "SMK", "Diploma I", "Diploma II", "Diploma III",
               "Sarjana Terapan", "Sarjana", "Magister Terapan", "Magister", "Doktor Terapan", "Doktor"]
    lowongan["jenjang_pendidikan_baku"] = lowongan["id_lowongan"].map(
        _jj.groupby("job_id").jenjang_baku.agg(lambda x: "; ".join(
            sorted(set(x), key=lambda v: (_urut_j.index(v) if v in _urut_j else 99, v)))))
    lowongan["program_studi_baku"] = lowongan["id_lowongan"].map(
        _jb.groupby("job_id").nama_program_studi.agg(lambda x: "; ".join(sorted(set(x)))))
    _urut = list(lowongan.columns)
    for c in ("jenjang_pendidikan_baku", "program_studi_baku"):
        _urut.remove(c)
    _pos = (_urut.index("jenjang_pendidikan") + 1) if "jenjang_pendidikan" in _urut \
        else _urut.index("status_sumber_skill") + 1
    _urut[_pos:_pos] = ["jenjang_pendidikan_baku", "program_studi_baku"]
    lowongan = lowongan[_urut]

    ws = tulis_sheet(
        wb, "Lowongan", lowongan,
        f"Lowongan Kerja ({len(lowongan):,} baris, {len(lowongan.columns)} kolom)",
        "Satu baris satu lowongan. Kolom deskripsi, persyaratan, dan tunjangan ditaruh "
        "di ujung kanan karena isinya panjang. Kolom gaji berasal dari metadata lowongan, "
        "bukan model NER. Pengertian kode KBJI 4 digit ada di sheet 'Acuan KBJI 4 Digit'.",
        lebar={1: 11, 2: 30, 3: 34, 4: 26, 5: 18, 6: 22, 7: 14, 8: 10, 9: 34,
               10: 10, 11: 40, 12: 22, 13: 13, 14: 13, 15: 22, 16: 11})
    kol_idx = {c: i + 1 for i, c in enumerate(lowongan.columns)}
    for i in range(4, 4 + len(lowongan)):
        for nama_kol in ("gaji_min", "gaji_max"):
            if nama_kol in kol_idx:
                ws.cell(i, kol_idx[nama_kol]).number_format = '#,##0'

    # ---------------------------------------------------------------- sheet 3
    skill_lowongan = pd.read_sql("""
        SELECT j.id AS id_lowongan, j.title AS judul_pekerjaan,
               j.kbji_golongan_pokok_nama AS jabatan_kbji,
               s.name AS skill, s.label AS label_ner,
               js.importance, js.proficiency,
               s.skill_type AS jenis_skill, s.skill_domain AS domain_skill,
               s.skill_function AS fungsi_skill, s.transferability,
               s.escudero_broad_category AS kategori_escudero,
               s.escudero_subcategory AS subkategori_escudero
        FROM job_skills js
        JOIN jobs j  ON j.id = js.job_id
        JOIN skills s ON s.id = js.skill_id
        ORDER BY j.id, s.name""", con)
    tulis_sheet(
        wb, "Skill per Lowongan", skill_lowongan,
        f"Skill per Lowongan ({len(skill_lowongan):,} baris)",
        "Satu baris satu penyebutan skill. Inilah sheet yang paling siap untuk PivotTable.",
        lebar={1: 11, 2: 28, 3: 32, 4: 30, 5: 18, 6: 13, 7: 14, 8: 20, 9: 18,
               10: 22, 11: 15, 12: 20, 13: 44})

    # --------------------------------------------------- sheet 3b (gabungan)
    tulis_sheet(
        wb, "Skill Gabungan", gabungan,
        f"Skill Gabungan: Anotasi Teks + Metadata Situs ({len(gabungan):,} baris)",
        "Permintaan pembimbing: menyatukan skill hasil anotasi teks lowongan dengan skill "
        "metadata situs sumber. Kolom sumber_skill menandai asal tiap baris. PERHATIAN: "
        "skill metadata HANYA tersedia pada lowongan Glints (4.213 lowongan), tidak ada "
        "pada 908 lowongan Dealls, dan hanya 11,7% frasanya benar-benar muncul di teks "
        "lowongan. Kolom sumber_label menjelaskan dari mana label tiap baris "
        "berasal, dan kolom dugaan_pengulangan_makna menandai baris metadata yang "
        "maknanya sama dengan skill hasil anotasi pada lowongan yang sama. Sheet "
        "'Skill per Lowongan' tetap memuat variabel utama hasil anotasi.",
        lebar={1: 11, 2: 28, 3: 32, 4: 34, 5: 18, 6: 20, 7: 18, 8: 40,
               9: 46, 10: 26})

    # ------------------------------------------------- sheet acuan KBJI 4 digit
    kb = pd.read_pickle("kbji.pkl")
    judul = dict(zip(kb.kode, kb.judul))
    ac = kb[(kb.digit == 4) & ~kb.kode.str.startswith("0")][["kode", "judul", "uraian"]].copy()
    ac["kode_1digit"] = ac.kode.str[0]
    ac["golongan_pokok"] = ac.kode_1digit.map(judul).str.title()
    ac["kode_2digit"] = ac.kode.str[:2]
    ac["subgolongan_pokok"] = ac.kode_2digit.map(judul)
    ac["kode_3digit"] = ac.kode.str[:3]
    ac["golongan"] = ac.kode_3digit.map(judul)
    n4 = lowongan.groupby("kode_kbji_4digit").size()
    ac["jumlah_lowongan_di_data"] = ac.kode.map(n4).fillna(0).astype(int)
    ac = ac.rename(columns={"kode": "kode_4digit", "judul": "label_4digit",
                            "uraian": "pengertian"})
    ac["pengertian"] = ac.pengertian.str.slice(0, 3000)
    ac = ac[["kode_4digit", "label_4digit", "pengertian", "jumlah_lowongan_di_data",
             "kode_1digit", "golongan_pokok", "kode_2digit", "subgolongan_pokok",
             "kode_3digit", "golongan"]]
    ws_ac = tulis_sheet(
        wb, "Acuan KBJI 4 Digit", ac,
        f"Acuan Subgolongan KBJI 2014 ({len(ac)} kode 4 digit)",
        "Pengertian setiap subgolongan (4 digit) menurut dokumen Klasifikasi Baku Jabatan "
        "Indonesia 2014 (BPS), beserta induknya. Golongan pokok 0 (TNI/POLRI) tidak "
        "dicantumkan. Kolom jumlah_lowongan_di_data menunjukkan berapa lowongan di dataset "
        "ini yang memakai kode tersebut.",
        lebar={1: 9, 2: 38, 3: 100, 4: 12, 5: 8, 6: 30, 7: 8, 8: 34, 9: 8, 10: 34})
    for i in range(4, 4 + len(ac)):
        ws_ac.cell(i, 3).alignment = Alignment(vertical="top", wrap_text=True)

    # ---------------------------------------------------------------- sheet 4
    daftar = pd.read_sql("""
        SELECT s.name AS skill,
               (SELECT COUNT(*) FROM job_skills js WHERE js.skill_id=s.id) AS jumlah_penyebutan,
               (SELECT COUNT(DISTINCT js.job_id) FROM job_skills js WHERE js.skill_id=s.id)
                   AS jumlah_lowongan,
               s.label AS label_ner, s.skill_type AS jenis_skill,
               s.skill_domain AS domain_skill, s.skill_function AS fungsi_skill,
               s.transferability,
               s.escudero_broad_category AS kategori_escudero,
               s.escudero_subcategory AS subkategori_escudero
        FROM skills s ORDER BY jumlah_penyebutan DESC, s.name""", con)
    tulis_sheet(
        wb, "Daftar Skill", daftar,
        f"Daftar Skill Unik ({len(daftar):,} baris)",
        "Satu baris satu skill unik beserta seluruh atribut Layer 2 dan klasifikasi Escudero.",
        lebar={1: 38, 2: 16, 3: 15, 4: 18, 5: 20, 6: 18, 7: 22, 8: 15, 9: 20, 10: 44})

    # ---------------------------------------------------------------- sheet 5
    if sertakan_entitas:
        lain = pd.read_sql("""
            SELECT e.job_id AS id_lowongan, j.title AS judul_pekerjaan,
                   e.label AS jenis_entitas, e.text AS teks_entitas
            FROM entities e JOIN jobs j ON j.id=e.job_id
            WHERE e.label NOT IN ('SKILL','SOFT_SKILL','TOOL','PROGRAMMING_LANGUAGE')
            ORDER BY e.job_id, e.label""", con)
        import unicodedata as _ud
        def _kunci_prodi(t):
            t = _ud.normalize("NFKC", str(t)).replace("\u00a0", " ")
            t = re.sub(r"\s+", " ", t.lower()).strip()
            return t.strip(" .,;:-/()[]\"'")
        _pb = pd.read_sql("SELECT kunci_istilah, nama_program_studi FROM peta_bidang_studi "
                          "WHERE nama_program_studi IS NOT NULL", con)
        _pj = pd.read_sql("SELECT kunci_istilah, jenjang_baku FROM peta_jenjang "
                          "WHERE jenjang_baku IS NOT NULL", con)
        _mb = _pb.groupby("kunci_istilah").nama_program_studi.agg(lambda x: "; ".join(sorted(set(x))))
        _mj = _pj.groupby("kunci_istilah").jenjang_baku.agg(lambda x: "; ".join(sorted(set(x))))
        _k = lain.teks_entitas.map(_kunci_prodi)
        lain["nilai_baku"] = None
        _d = lain.jenis_entitas == "DEGREE_FIELD"
        _e = lain.jenis_entitas == "EDUCATION_LEVEL"
        lain.loc[_d, "nilai_baku"] = _k[_d].map(_mb)
        lain.loc[_e, "nilai_baku"] = _k[_e].map(_mj)
        tulis_sheet(
            wb, "Entitas Lain", lain,
            f"Entitas NER Selain Skill ({len(lain):,} baris)",
            "Tanggung jawab, pendidikan, bidang studi, pengalaman, lokasi, perusahaan, "
            "jenis kerja, industri, gaji, dan judul pekerjaan hasil ekstraksi model.",
            lebar={1: 12, 2: 30, 3: 22, 4: 80, 5: 36})

    # ------------------------------------------- sheet program studi per lowongan
    ps = pd.read_sql("""
        SELECT b.job_id AS id_lowongan, j.title AS judul_pekerjaan,
               j.kbji_golongan_pokok_nama AS jabatan_kbji,
               b.istilah AS istilah_di_lowongan, b.nama_program_studi AS program_studi_baku,
               b.rumpun_ilmu
        FROM job_bidang_studi b JOIN jobs j ON j.id = b.job_id
        ORDER BY b.job_id, b.nama_program_studi""", con)
    tulis_sheet(
        wb, "Program Studi per Lowongan", ps,
        f"Program Studi per Lowongan ({len(ps):,} baris, {ps.id_lowongan.nunique():,} lowongan)",
        "Bidang studi (DEGREE_FIELD) yang sudah dibakukan ke nama program studi resmi dan "
        "ditelaah pembimbing. Istilah bersinonim sudah digabung, mis. accounting/akutansi/"
        "akuntansi → Akuntansi; marketing/pemasaran/manajemen pemasaran → Manajemen. "
        "Hitung jumlah lowongan per prodi dengan COUNT DISTINCT id_lowongan.",
        lebar={1: 12, 2: 32, 3: 30, 4: 34, 5: 40, 6: 26})
    def _gabung_istilah(x):
        lihat = {}
        for v in x:
            v = str(v).strip(" ,.;:-/()[]\"'")
            lihat.setdefault(v.lower(), v)
        return ", ".join(sorted(lihat.values(), key=str.lower))
    rk = (ps.groupby(["program_studi_baku", "rumpun_ilmu"])
            .agg(jumlah_lowongan=("id_lowongan", "nunique"),
                 istilah_yang_digabung=("istilah_di_lowongan", _gabung_istilah))
            .reset_index().sort_values("jumlah_lowongan", ascending=False))
    tulis_sheet(
        wb, "Rekap Program Studi", rk,
        f"Rekap Program Studi ({len(rk):,} prodi baku)",
        "Jumlah lowongan per program studi baku beserta istilah di lowongan yang digabung "
        "ke dalamnya. Satu lowongan bisa meminta lebih dari satu prodi.",
        lebar={1: 40, 2: 26, 3: 16, 4: 100})

    # Lebar kolom teks panjang pada sheet Lowongan.
    wsL = wb["Lowongan"]
    for nama_kol, w in (("deskripsi", 70), ("persyaratan", 60), ("tunjangan", 45),
                        ("tautan", 40), ("skill_dari_sumber", 45),
                        ("jenjang_pendidikan_baku", 26), ("program_studi_baku", 40)):
        if nama_kol in kol_idx:
            wsL.column_dimensions[get_column_letter(kol_idx[nama_kol])].width = w

    # ---------------------------------------------------------------- sheet 6
    ws = wb.create_sheet("Rekap Atribut")
    ws["A1"] = "Rekap Distribusi Atribut Layer 2"
    ws["A1"].font = Font(F, size=13, bold=True)
    ws["A2"] = ("Dihitung dengan rumus COUNTIF langsung dari sheet 'Skill per Lowongan', "
                "sehingga angkanya ikut menyesuaikan bila data disaring atau diubah.")
    ws["A2"].font = Font(F, size=9, italic=True, color="808080")

    n = len(skill_lowongan) + 3
    blok = [
        ("Jenis Skill", "jenis_skill", "H"),
        ("Domain Skill", "domain_skill", "I"),
        ("Fungsi Skill", "fungsi_skill", "J"),
        ("Transferability", "transferability", "K"),
        ("Importance", "importance", "F"),
        ("Proficiency", "proficiency", "G"),
        ("Kategori Escudero", "kategori_escudero", "L"),
    ]
    r = 4
    for judul, kolom, huruf in blok:
        ws.cell(r, 1, judul).font = Font(F, bold=True, size=11)
        for j, h in enumerate(["Nilai", "Jumlah Penyebutan", "Persentase"], 1):
            c = ws.cell(r + 1, j, h)
            c.font = Font(F, bold=True, color="FFFFFF", size=10)
            c.fill = HDR
            c.border = BD
        nilai = sorted(skill_lowongan[kolom].dropna().unique())
        for k, v in enumerate(nilai, r + 2):
            ws.cell(k, 1, str(v)).font = Font(F, size=10)
            c = ws.cell(k, 2, f"=COUNTIF('Skill per Lowongan'!{huruf}$4:{huruf}${n},A{k})")
            c.font = Font(F, size=10)
            c.number_format = '#,##0'
            c.border = BD
            c2 = ws.cell(k, 3, f"=B{k}/$B${r + 2 + len(nilai)}")
            c2.font = Font(F, size=10)
            c2.number_format = '0.0%'
            c2.border = BD
        tot = r + 2 + len(nilai)
        ws.cell(tot, 1, "Total").font = Font(F, bold=True, size=10)
        c = ws.cell(tot, 2, f"=SUM(B{r + 2}:B{tot - 1})")
        c.font = Font(F, bold=True, size=10)
        c.number_format = '#,##0'
        c.border = BD
        c = ws.cell(tot, 3, f"=B{tot}/$B${tot}")
        c.font = Font(F, bold=True, size=10)
        c.number_format = '0.0%'
        c.border = BD
        r = tot + 2

    ws.column_dimensions["A"].width = 48
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 14

    wb.save(keluaran)
    con.close()

    print(f"Tersimpan: {keluaran}")
    print(f"  Lowongan            : {len(lowongan):,} baris")
    print(f"  Skill per Lowongan  : {len(skill_lowongan):,} baris")
    print(f"  Daftar Skill        : {len(daftar):,} baris")
    if sertakan_entitas:
        print(f"  Entitas Lain        : {len(lain):,} baris")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    db = args[0] if args else "ner_jobposting_v18.sqlite"
    js = args[1] if len(args) > 1 else "ALL_batches_gold_annotations.json"
    out = args[2] if len(args) > 2 else "Dataset_NER_Lowongan_Kerja.xlsx"
    ekspor(db, out, json_path=js, sertakan_entitas="--tanpa-entitas" not in sys.argv)
