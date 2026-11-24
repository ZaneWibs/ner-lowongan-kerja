"""
Pembacaan tiga peraturan acuan penamaan program studi dan jenjang pendidikan
============================================================================
Permintaan pembimbing (Bu Tri, 20 September 2026): penggabungan program studi
(DEGREE_FIELD) dan jenjang pendidikan (EDUCATION_LEVEL) mengacu pada:

  1. Permendikbud No. 154 Tahun 2014 -- Rumpun Ilmu Pengetahuan dan Teknologi
     serta Gelar Lulusan Perguruan Tinggi.
     (berkas dikirim dengan nama permendikbud_14_2014.pdf)
  2. Kepdirjen Pendidikan Vokasi No. 27/D/M/2022 -- Daftar Nama Program Studi
     Jenis Pendidikan Tinggi Vokasi, pelaksanaan Pasal 7 Permendikbudristek
     No. 32 Tahun 2021 tentang Penamaan Program Studi pada Perguruan Tinggi.
     (berkas dikirim dengan nama permendikbudristek_32_2021.pdf)
  3. Kepdirjen Pendidikan Tinggi No. 96/B/KPT/2025 -- Nama Program Studi pada
     Jenis Pendidikan Akademik dan Pendidikan Profesi.

Skrip ini membaca teks hasil ekstraksi ketiga berkas dan menghasilkan daftar
acuan nama program studi resmi beserta rumpun ilmu dan inisial gelarnya.

Catatan: PDF-nya hasil pindaian sehingga teksnya mengandung galat OCR. Kolom
centang jenjang (S/M/Dr pada berkas akademik; D.Satu/D.Dua/D.Tiga/S.Tr/M.Tr/
D.Tr pada berkas vokasi) sengaja TIDAK diambil karena posisi kolomnya bergeser
antar halaman dan tanda centangnya terbaca beragam (v, ,J, ,;) sehingga tidak
bisa dipertanggungjawabkan. Yang diambil hanya nama program studi, padanan
bahasa Inggrisnya, kelompok, rumpun ilmu, dan inisial gelar.
"""
import re
import unicodedata

import pandas as pd

BERKAS_AKADEMIK = "e89ee173-7-70_-Salinan-96_B_KPT_2025.txt"
BERKAS_VOKASI = "7f006b29-permendikbudristek_32_2021.txt"
BERKAS_RUMPUN = "69cff106-permendikbud_14_2014.txt"

# Judul rumpun terbaca beragam oleh OCR: "RUM PUN ILMU SOSIAL",
# "RUMPUN ILM U ALAM", "RbJMPUJN ILMU FORMAL", "RWMPUJN ILMIJ ALAM". Karena
# itu yang dicocokkan bukan frasa "RUMPUN ILMU" melainkan kata rumpunnya
# sendiri pada baris yang memang berupa judul (huruf besar dan memuat penanda
# "PUN" atau "SCIENCES"/"HUMANITIES").
RX_RUMPUN_KATA = re.compile(
    r"\b(AGAMA|HUMANIORA|SOSIAL|ALAM|FORMAL|TERAPAN)\b")
RX_PENANDA_RUMPUN = re.compile(r"PUN|SCIENCES|HUMANITIES")
# Judul bidang di dalam Rumpun Ilmu Terapan: "A  PERTANIAN (AGRICULTURE)".
RX_BIDANG = re.compile(r"^\s*([A-Z])\s{2,}([A-Z][A-Z ,.]{3,})")
# Inisial gelar di kolom terakhir, misalnya "Sn.", "Hum.", "T.", "Kom.".
RX_GELAR = re.compile(r"^[A-Z][A-Za-z.]{0,10}\.$")

RUMPUN_RESMI = {
    "AGAMA": "Ilmu Agama",
    "HUMANIORA": "Ilmu Humaniora",
    "SOSIAL": "Ilmu Sosial",
    "ALAM": "Ilmu Alam",
    "FORMAL": "Ilmu Formal",
    "TERAPAN": "Ilmu Terapan",
}


def bersihkan(t):
    t = unicodedata.normalize("NFKC", str(t))
    t = t.replace("’", "'").replace("‘", "'")
    t = re.sub(r"\s+", " ", t).strip()
    # Sisa kolom centang yang ikut terbaca di ujung nama.
    t = re.sub(r"(?:\s+(?:[Vv]|,[Jj;]|√|-))+$", "", t).strip()
    return t


def _layak(nama):
    if not nama or len(nama) < 3:
        return False
    if not re.search(r"[A-Za-z]{3}", nama):
        return False
    if re.fullmatch(r"[-\d\s.]+", nama):
        return False
    buang = ("keputusan", "peraturan", "lembaran negara", "direktur jenderal",
             "kementerian", "lampiran", "undang-undang", "nomor ", "tahun ",
             "menimbang", "mengingat", "menetapkan", "berita negara", "nip ",
             "ditetapkan", "salinan", "halaman", "program studi dalam bahasa")
    r = nama.lower()
    return not any(b in r for b in buang)



def _rumpun_dari_baris(ln):
    """Kembalikan nama rumpun bila baris ini judul rumpun, selain itu None."""
    besar = ln.upper()
    if not RX_PENANDA_RUMPUN.search(besar):
        return None
    huruf = re.sub(r"[^A-Z]", "", besar)
    if len(huruf) < 8 or sum(ch.islower() for ch in ln) > len(ln) * 0.25:
        return None
    m = RX_RUMPUN_KATA.search(besar)
    return RUMPUN_RESMI.get(m.group(1)) if m else None


def _bidang_dari_baris(ln):
    m = RX_BIDANG.match(ln.rstrip())
    if not m:
        return None
    nama = bersihkan(re.sub(r"[{(\[].*", "", m.group(2)))
    return nama.title() if len(nama) >= 4 else None


def parse_akademik(path):
    """Lampiran I dan II Kepdirjen 96/B/KPT/2025.

    Baris judul kelompok dan baris program studi sama-sama diawali nomor, dan
    indentasinya bergeser antar halaman sehingga tidak bisa dipakai sebagai
    pembeda. Yang dipakai adalah kesinambungan nomor: nomor program studi
    berjalan menerus 1..N di seluruh lampiran, sedangkan nomor kelompok punya
    deret sendiri 1..M. Sebuah baris dianggap kelompok bila nomornya sama
    dengan nomor kelompok berikutnya yang ditunggu, dan dianggap program studi
    bila sama dengan nomor program studi berikutnya yang ditunggu.
    """
    baris = open(path, encoding="utf-8", errors="replace").read().split("\n")
    hasil = []
    rumpun = kelompok = bidang = ""
    jenis = "Akademik"
    n_kel = n_prodi = 0
    for ln in baris:
        if "PENDIDIKAN PROFESI" in ln and "PROGRAM STUDI PADA JENIS" in ln:
            jenis = "Profesi"
            n_kel = n_prodi = 0
            continue
        r = _rumpun_dari_baris(ln)
        if r:
            rumpun, bidang = r, ""
            continue
        b = _bidang_dari_baris(ln)
        if b:
            bidang = b
            continue
        if not ln.strip():
            continue
        potong = [p for p in re.split(r"\s{2,}", ln.rstrip()) if p.strip()]
        if len(potong) < 2:
            continue
        m = re.fullmatch(r"(\d{1,4})\s*(.*)", potong[0].strip())
        if not m:
            continue
        nomor, sisa = int(m.group(1)), m.group(2).strip()
        kolom = ([sisa] + potong[1:]) if sisa else potong[1:]
        nama_id = bersihkan(kolom[0] if kolom else "")
        nama_en = bersihkan(kolom[1]) if len(kolom) > 1 else ""
        if not _layak(nama_id):
            continue
        gelar = ""
        for k in reversed(kolom):
            k = k.strip()
            if RX_GELAR.fullmatch(k):
                gelar = k
                break
        # Baris yang membawa kolom inisial gelar pasti baris program studi;
        # nomornya dipakai untuk menyelaraskan ulang pencacah, karena OCR
        # kerap menghilangkan satu-dua baris sehingga deret nomor terputus.
        prodi = bool(gelar) or nomor == n_prodi + 1
        # Judul kelompok tidak punya kolom gelar dan nomornya kecil serta
        # berurutan tersendiri.
        if not prodi and nomor == n_kel + 1:
            n_kel = nomor
            kelompok = nama_id
            continue
        if prodi:
            n_prodi = max(n_prodi, nomor)
            hasil.append({
                "sumber_acuan": "Kepdirjen Dikti 96/B/KPT/2025",
                "jenis_pendidikan": jenis, "rumpun_ilmu": rumpun,
                "bidang": bidang, "kelompok": kelompok,
                "kolom_lengkap": "ya" if gelar else "tidak (kolom terpotong saat pindai)",
                "nama_program_studi": nama_id,
                "nama_inggris": nama_en, "inisial_gelar": gelar,
            })
    return pd.DataFrame(hasil)


def parse_vokasi(path):
    """Lampiran I dan II Kepdirjen Diksi 27/D/M/2022.

    Di berkas ini hanya baris judul kelompok yang bernomor; baris program studi
    tidak bernomor dan selalu diakhiri kolom inisial gelar.
    """
    baris = open(path, encoding="utf-8", errors="replace").read().split("\n")
    hasil = []
    rumpun = kelompok = bidang = ""
    mulai = False
    for ln in baris:
        if "Daftar Nama Program Studi Jenis Pendidikan Tinggi Vokasi" in ln:
            mulai = True
        r = _rumpun_dari_baris(ln)
        if r:
            rumpun, bidang = r, ""
            mulai = True
            continue
        b = _bidang_dari_baris(ln)
        if b:
            bidang = b
            continue
        if not mulai or not ln.strip():
            continue
        potong = [p for p in re.split(r"\s{2,}", ln.rstrip()) if p.strip()]
        if not potong:
            continue
        m = re.fullmatch(r"(\d{1,4})\s*(.*)", potong[0].strip())
        if m:
            nama_id = bersihkan(m.group(2) or (potong[1] if len(potong) > 1 else ""))
            if _layak(nama_id):
                kelompok = nama_id
            continue
        nama_id = bersihkan(potong[0])
        nama_en = bersihkan(potong[1]) if len(potong) > 1 else ""
        if not _layak(nama_id):
            continue
        gelar = ""
        for k in reversed(potong):
            k = k.strip()
            if RX_GELAR.fullmatch(k):
                gelar = k
                break
        # OCR pada berkas vokasi sering memecah kolom Indonesia dan Inggris ke
        # baris yang berbeda, sehingga sebagian baris program studi hanya berisi
        # namanya saja tanpa kolom gelar. Baris seperti itu tetap diambil bila
        # bentuknya memang menyerupai nama program studi, dan diberi penanda
        # supaya ketahuan bahwa kolomnya tidak lengkap.
        lengkap = bool(gelar)
        if not lengkap:
            if len(potong) > 2 or len(nama_id) > 60:
                continue
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9 ,.'\-/&]+", nama_id):
                continue
            if nama_id.upper() == nama_id:
                continue
        hasil.append({
            "sumber_acuan": "Kepdirjen Diksi 27/D/M/2022",
            "jenis_pendidikan": "Vokasi", "rumpun_ilmu": rumpun,
            "bidang": bidang, "kelompok": kelompok,
            "kolom_lengkap": "ya" if lengkap else "tidak (kolom terpotong saat pindai)",
            "nama_program_studi": nama_id,
            "nama_inggris": nama_en, "inisial_gelar": gelar,
        })
    return pd.DataFrame(hasil)


def daftar_acuan():
    df = pd.concat([parse_akademik(BERKAS_AKADEMIK), parse_vokasi(BERKAS_VOKASI)],
                   ignore_index=True)
    df = df[df["nama_program_studi"].str.len() >= 3]
    df = df.drop_duplicates(subset=["jenis_pendidikan", "nama_program_studi"])
    return df.reset_index(drop=True)


if __name__ == "__main__":
    df = daftar_acuan()
    print("Total nama program studi resmi:", len(df))
    print(df.groupby(["jenis_pendidikan", "rumpun_ilmu"]).size().to_string())
    print()
    print(df.sample(15, random_state=1).to_string(index=False))
