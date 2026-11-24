"""
Penerapan telaah pembimbing atas pemetaan program studi
========================================================
Bu Tri sudah memeriksa seluruh 569 istilah bidang studi pada sheet "Pemetaan
Program Studi" dan mengisi kolom keputusan_pembimbing serta catatan_pembimbing.
Skrip ini menerjemahkan isian itu menjadi pemetaan akhir yang siap dipakai.

Isi kolom catatan beliau ada tiga macam, dan ketiganya diperlakukan berbeda:

  1. Nama program studi pengganti, misalnya "Seni Kuliner" untuk "tata boga".
     -> langsung dipakai sebagai nama akhir.
  2. Arahan bersyarat yang bergantung jenjang, misalnya "Apabila Vokasi maka
     Analisis Farmasi dan Makanan; apabila S1 maka Farmasi".
     -> belum bisa diterapkan otomatis, dikumpulkan tersendiri.
  3. Perintah memeriksa isi lowongan, misalnya "cek apakah lowongan untuk guru
     PAUD, atau SD untuk menyesuaikan dengan bidang ilmu".
     -> juga dikumpulkan tersendiri karena perlu penelaahan per lowongan.

Tidak ada isian pembimbing yang ditebak atau dilengkapi sendiri. Baris yang
arahannya belum bisa diterapkan tetap ditandai apa adanya.

    python terapkan_telaah_prodi.py bt.xlsx
"""
import re
import sys
import unicodedata

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

import parse_regulasi as REG

F = "Calibri"
HDR = PatternFill("solid", fgColor="1F4E79")
SUB = PatternFill("solid", fgColor="DDEBF7")
KUNING = PatternFill("solid", fgColor="FFF2CC")
thin = Side(style="thin", color="D9D9D9")
BD = Border(thin, thin, thin, thin)

# Penanda bahwa isi catatan berupa arahan, bukan nama program studi.
RX_ARAHAN = re.compile(
    r"\bs1\s*:|diploma\s*:|\bcek\b|\bcekdi\b|dicke|dicek|mohon diperhatikan|apabila|paling dekat|"
    r"tidak spesifik|dikategori menjadi dua|perbaikan|diperhatikan|"
    r"mohon dice|sesuaikan dengan|deskripsi pekerjaan|jenjangnya", re.IGNORECASE)


# Penyelarasan ejaan: nama yang ditulis pembimbing disamakan dengan bentuk
# tertulis pada peraturan acuan. Maknanya tidak diubah -- hanya bentuk
# tulisannya, supaya satu program studi tidak terpecah menjadi beberapa
# kelompok (misalnya "Teknik Mesin", "Teknik atau Rekayasa Mesin", dan
# "Rekayasa Mesin" yang sebetulnya satu program studi yang sama).
SELARAS = {
    "Analis Keuangan": "Analisis Keuangan",
    "Statistik": "Statistika",
    "Teknik Mesin": "Rekayasa Mesin",
    "Teknik atau Rekayasa Mesin": "Rekayasa Mesin",
    "Teknik atau Rekayasa Industri": "Rekayasa Industri",
    "Teknik atau Rekayasa Sipil": "Rekayasa Sipil",
    "Teknik atau Rekayasa Elektro": "Rekayasa Elektro",
    "Ilmu dan Sains Komunikasi": "Ilmu atau Sains Komunikasi",
    "Ilmu Kimia": "Kimia",
    "Ilmu Fisika": "Fisika",
    "Ilmu Kesehatan Masyarakat": "Kesehatan Masyarakat",
    "Rekayasa Instrumentasi & Automasi": "Rekayasa Instrumentasi dan Automasi",
    "Teknologi Rekayasa Pengelasan & Fabrikasi":
        "Teknologi Rekayasa Pengelasan dan Fabrikasi",
    "Spesialis Dermatologi, Venereologi, dan Estetika":
        "Dermatologi Venereologi dan Estetika",
    "Teknologi Pendingin dan Tata Udara (Diploma)":
        "Teknologi Pendingin dan Tata Udara",
    # Pembimbing menulis "Teknik" pada satu baris dan "Teknik (tidak
    # spesifik)" pada baris lain untuk maksud yang sama.
    "Teknik": "Teknik (tidak spesifik)",
    # Pembimbing memetakan "Teknik Informatika" (77 penyebutan) ke Ilmu
    # Komputer atau Informatika, tetapi "Teknik/Teknologi Informatika" ke
    # "Teknik Informatika"; disamakan ke yang pertama.
    "Teknik Informatika": "Ilmu Komputer atau Informatika",
}

# Nama yang ditetapkan pembimbing tetapi tidak tercantum pada ketiga peraturan
# acuan. Namanya tetap dipakai sesuai keputusan beliau; rumpun ilmunya hanya
# diusulkan dari nama resmi terdekat dan ditandai sebagai usulan.
USULAN_RUMPUN = {
    "Seni Kuliner": ("Ilmu Terapan", "terdekat: Pendidikan Vokasional Seni Kuliner"),
    "Teknik Informatika": ("Ilmu Formal", "terdekat: Ilmu Komputer atau Informatika"),
    "Komunikasi": ("Ilmu Terapan", "terdekat: Ilmu atau Sains Komunikasi"),
    "Teknik Cetak dan Grafis": ("Ilmu Terapan",
                                "terdekat: Teknologi Rekayasa Cetak dan Grafis"),
    "Teknologi Rekayasa Industri": ("Ilmu Terapan", "terdekat: Rekayasa Industri"),
    "Pekerja Sosial Pelayanan": ("Ilmu Terapan",
                                 "terdekat: Pekerja Sosial Pelayanan Anak dan sejenisnya"),
    "Refraksi dan Optimasi Visual": ("Ilmu Terapan",
                                     "rumpun kesehatan pada Ilmu Terapan"),
    "Urusan Publik": ("Ilmu Sosial", "padanan Public Affairs; rumpun administrasi publik"),
    "Ilmu Agama": ("Ilmu Agama", "Permendikbud 154/2014 Pasal 2 huruf a"),
    "Ilmu Sosial": ("Ilmu Sosial", "Permendikbud 154/2014 Pasal 2 huruf c"),
    "Teknik (tidak spesifik)": ("Ilmu Terapan",
                                "bidang Teknik atau Rekayasa pada Ilmu Terapan"),
    "Bahasa Asing": ("Ilmu Humaniora", "kelompok Linguistik pada Ilmu Humaniora"),
    "MIPA (tidak spesifik)": ("Ilmu Alam", "Matematika dan Ilmu Pengetahuan Alam"),
    "Kesehatan (tidak spesifik)": ("Ilmu Terapan", "bidang Kesehatan pada Ilmu Terapan"),
    "Sastra Asing": ("Ilmu Humaniora", "kelompok Susastra pada Ilmu Humaniora"),
    "Bahasa": ("Ilmu Humaniora", "kelompok Linguistik pada Ilmu Humaniora"),
    "Ilmu Sains": ("", "terlalu umum; bisa Ilmu Alam atau Ilmu Formal"),
}

# ---------------------------------------------------------------------------
# Penerapan arahan pembimbing yang meminta pemeriksaan isi lowongan.
# Setiap lowongan yang memuat istilah bersangkutan sudah dibaca, dan aturan
# beliau diterapkan apa adanya. Kolom "bukti" mencatat kutipan lowongan yang
# menjadi dasar keputusan, supaya bisa diperiksa ulang.
#
# Tiga jenis hasil:
#   - "diterapkan"      : aturan beliau bisa diterapkan langsung.
#   - "usul dihapus"    : setelah dibaca, entitasnya ternyata bukan bidang studi
#                         (salah label anotasi). Perlu konfirmasi beliau.
#   - "perlu keputusan" : pemeriksaan sudah dilakukan, tetapi hasilnya tidak
#                         tercakup aturan beliau, sehingga dikembalikan.
# ---------------------------------------------------------------------------
RESOLUSI = {
    "administrasi": ("diterapkan", ["Administrasi Bisnis"],
        "Sesuai catatan pembimbing: \"Administrasi\" saja masuk Administrasi Bisnis. "
        "Istilah administrasi lain (Kesehatan, Rumah Sakit, Publik) sudah punya "
        "baris dan nama sendiri."),
    "teknik": ("diterapkan", ["Teknik (tidak spesifik)"],
        "Sesuai catatan pembimbing: \"Teknik (tidak spesifik)\"."),
    "supply chain": ("diterapkan", ["Manajemen Logistik"],
        "Sesuai catatan pembimbing: \"yang paling dekat adalah Manajemen Logistik\"."),
    "sastra bahasa jepang": ("diterapkan", ["Bahasa Jepang", "Sastra Jepang"],
        "Sesuai catatan pembimbing: dikategorikan menjadi dua, lulusan Bahasa "
        "Jepang ATAU Sastra Jepang. Penyebutannya dihitung pada kedua kelompok."),
    "sastra bahasa asing": ("diterapkan", ["Bahasa Asing", "Sastra Asing"],
        "Sesuai catatan pembimbing: dikategorikan menjadi dua, lulusan Bahasa "
        "Asing ATAU Sastra Asing. Penyebutannya dihitung pada kedua kelompok."),
    "apoteker": ("diterapkan", ["Farmasi"],
        "Aturan pembimbing: vokasi -> Analisis Farmasi dan Makanan; S1 -> Farmasi. "
        "Kedelapan lowongan dibaca, tidak ada yang berjenjang vokasi saja: 5 "
        "menyebut S1/Sarjana Farmasi (381, 3266, 4691, 5103, 1412), 3 menyebut "
        "profesi Apoteker yang mensyaratkan S1 Farmasi (496, 4067, 4899). "
        "Seluruhnya -> Farmasi."),
    "teknologi": ("diterapkan", ["Teknologi Pangan dan Hasil Pertanian"],
        "Lowongan 3963 (Kepala Produksi): \"Lulusan S1 Teknologi / Teknik Pangan\". "
        "\"Teknologi\" adalah potongan dari \"Teknologi Pangan\", sehingga "
        "disamakan dengan kelompok Teknologi Pangan."),
    "teknik textile": ("diterapkan", ["Rekayasa Tekstil"],
        "Aturan pembimbing: S1 -> Teknologi atau Rekayasa Tekstil; diploma -> "
        "Produksi Tekstil. Lowongan 3689 (Staff R&D) tidak menyebut jenjang di "
        "teks, tetapi metadata situs mencatat Bachelor -> S1 -> Rekayasa Tekstil "
        "(nama resmi pada Kepdirjen 96/B/KPT/2025)."),
    "quality control": ("diterapkan", ["Teknologi Rekayasa Industri"],
        "Aturan pembimbing: sarjana -> Teknologi Rekayasa Industri; vokasi -> "
        "Teknologi Industri. Lowongan 1118: \"Pendidikan minimal S1 di bidang "
        "Teknik, Quality Control, Manajemen Industri\" -> sarjana."),
    "kpn": ("diterapkan", ["Transportasi"],
        "Lowongan 4258 menjelaskan sendiri singkatannya: \"KPN (Ketatalaksanaan "
        "Pelayaran Niaga)\", disebut berdampingan dengan KALK (Ketatalaksanaan "
        "Angkutan Laut dan Kepelabuhanan). Pembimbing sudah memetakan KALK ke "
        "Transportasi, jadi KPN disamakan."),
    "qa": ("usul dihapus", [],
        "Lowongan 2649: \"Memberikan data dan laporan pendukung kepada bagian QA\". "
        "QA di sini nama bagian/divisi, bukan bidang studi -- salah label anotasi."),
    "mekanikal": ("usul dihapus", [],
        "Kedua lowongan bukan bidang otomotif, dan \"mekanikal\" di sana bukan "
        "bidang studi. Lowongan 96: \"inspeksi rutin pada sistem listrik, "
        "plumbing, dan mekanikal\"; lowongan 1270: \"perbaikan mekanikal & "
        "elektrikal\". Keduanya menyebut jenis sistem/pekerjaan -- salah label."),
    "umum": ("usul dihapus", [],
        "Lowongan 2824 (Admin Logistik), bukan guru: \"Pend SMA/K Administrasi/"
        "Akuntansi/ dan Umum\". \"Umum\" di sini jurusan SMA, bukan program "
        "studi pendidikan tinggi, sehingga aturan Pendidikan Umum dan Karakter "
        "tidak berlaku."),
    "mipa": ("perlu keputusan", [],
        "Sudah dicek sesuai arahan: ketiga lowongan berjenjang S1 (2050 Pengajar "
        "SD, 2417 R&D Flexible Packaging, 3483 Proofreader). MIPA adalah nama "
        "fakultas, bukan program studi; mohon arahan dipetakan ke mana."),
    "ipa": ("perlu keputusan", [],
        "Sudah dicek: lowongan 1318 menyebut \"SMA/SMK Jurusan IPA\" (jurusan "
        "SMA, bukan program studi); lowongan 3491 Guru IPA menyebut \"S1 linier "
        "dengan mapel IPA\" -- kemungkinan Pendidikan IPA. Mohon arahan."),
    "pendidikan guru": ("perlu keputusan", [],
        "Sudah dicek: keduanya BUKAN guru PAUD maupun SD. Lowongan 2877 guru "
        "Bahasa Jepang; lowongan 4327 guru Manajemen Perkantoran (SMK). Aturan "
        "PAUD/SD tidak berlaku; kemungkinan Pendidikan Bahasa Jepang dan "
        "Pendidikan Administrasi Perkantoran. Mohon arahan."),
    "produksi": ("perlu keputusan", [],
        "Sudah dicek: lowongan 2898 magang produksi serial video -- \"jurusan "
        "Komunikasi, Manajemen, Film, Produksi, Media\". Konteksnya produksi "
        "film, bukan industri, sehingga aturan Teknologi Rekayasa Industri "
        "tampaknya tidak cocok; padanan terdekat Produksi Film dan Televisi. "
        "Mohon arahan."),
    "kesehatan": ("perlu keputusan", [],
        "Catatan pembimbing \"Perbaikan\" belum menyebut nama pengganti. Keenam "
        "lowongan menulis \"jurusan Kesehatan\" secara umum (786, 1053, 1406, "
        "1556, 1787, 4694) tanpa rincian program studi."),
}

# ---------------------------------------------------------------------------
# Usulan yang diterapkan untuk butir yang belum diputuskan pembimbing
# (permintaan 29 September 2026: "sesuaikan usulan saja"). Setiap usulan
# mengikuti pola keputusan pembimbing sendiri pada istilah sejenis, supaya
# konsisten -- misalnya seluruh varian SDM beliau masukkan ke Manajemen, maka
# "Human Resource Management" juga ke Manajemen. Statusnya ditandai berbeda
# dari keputusan pembimbing agar tetap bisa ditelusuri.
# Nilai: (nama akhir atau "" untuk dikeluarkan, dasar usulan)
# ---------------------------------------------------------------------------
USULAN_DITERAPKAN = {
    "human resource management": ("Manajemen",
        "mengikuti keputusan pembimbing untuk Manajemen SDM, MSDM, SDM, dan "
        "Manajemen Sumber Daya Manusia -> Manajemen"),
    "hukum bisnis": ("Hukum", "mengikuti keputusan pembimbing untuk Hukum Perdata -> Hukum"),
    "hukum korporasi": ("Hukum", "mengikuti keputusan pembimbing untuk Hukum Perdata -> Hukum"),
    "hukum ketenagakerjaan": ("Hukum", "mengikuti keputusan pembimbing untuk Hukum Perdata -> Hukum"),
    "hubungan masyarakat": ("Hubungan Masyarakat",
        "mengikuti keputusan pembimbing untuk Public Relation(s) -> Hubungan Masyarakat"),
    "ilmu computer": ("Ilmu Komputer atau Informatika",
        "salah ketik \"computer\"; mengikuti keputusan pembimbing untuk Informatika"),
    "manajemen informatika": ("Ilmu Komputer atau Informatika",
        "Manajemen Informatika tidak tercantum pada peraturan acuan; mengikuti "
        "keputusan pembimbing untuk Informatika dan Teknik Informatika"),
    "tkr": ("Pemeliharaan Kendaraan Ringan",
        "mengikuti keputusan pembimbing untuk Teknik Kendaraan Ringan (TKR)"),
    "konstruksi": ("Rekayasa Sipil",
        "mengikuti keputusan pembimbing untuk Teknik Sipil dan Sipil"),
    "instrumen": ("Rekayasa Instrumentasi dan Automasi",
        "mengikuti keputusan pembimbing untuk Instrumentasi"),
    "penyakit dalam": ("Kedokteran",
        "mengikuti keputusan pembimbing untuk Dokter Spesialis dan Dokter "
        "Spesialis Bedah -> Kedokteran"),
    "robotika": ("Teknik Robotika dan Kecerdasan Buatan",
        "kandidat akademik; nama resmi pada Kepdirjen 96/B/KPT/2025"),
    "kota": ("Perencanaan Wilayah dan Kota",
        "mengikuti keputusan pembimbing untuk Planologi -> Perencanaan Wilayah dan Kota"),
    "pendidikan guru": ("Pendidikan",
        "mengikuti keputusan pembimbing untuk seluruh istilah Pendidikan X "
        "(PGSD, Pendidikan IPA, Pendidikan Bahasa Jepang) -> Pendidikan"),
    "mipa": ("MIPA (tidak spesifik)",
        "MIPA nama fakultas, bukan program studi; mengikuti pola pembimbing "
        "untuk \"Teknik (tidak spesifik)\""),
    "ipa": ("MIPA (tidak spesifik)",
        "mengikuti usulan untuk MIPA; satu dari dua lowongan menyebut jurusan "
        "IPA di SMA"),
    "kesehatan": ("Kesehatan (tidak spesifik)",
        "keenam lowongan menulis \"jurusan Kesehatan\" tanpa rincian; mengikuti "
        "pola pembimbing untuk \"Teknik (tidak spesifik)\""),
    "produksi": ("Produksi Film dan Televisi",
        "lowongan 2898 magang produksi serial video; nama resmi pada Kepdirjen "
        "Diksi 27/D/M/2022"),
    "administrasi pendidikan": ("Administrasi Pendidikan",
        "mengikuti catatan pembimbing sendiri pada istilah \"Administrasi\" "
        "bahwa Administrasi Pendidikan dikelompokkan terpisah"),
    "supply chain": ("Manajemen",
        "pembimbing mengarahkan ke Manajemen Logistik, sedangkan Manajemen "
        "Logistik sendiri beliau masukkan ke Manajemen; disamakan ke Manajemen"),
    "qa": ("", "salah label anotasi: \"bagian QA\" nama divisi, bukan bidang studi"),
    "mekanikal": ("", "salah label anotasi: menyebut jenis sistem/pekerjaan, "
                      "bukan bidang studi"),
    "umum": ("", "jurusan SMA (\"SMA/K ... dan Umum\"), bukan program studi"),
}

def _n(t):
    t = unicodedata.normalize("NFKD", str(t))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9/+&' -]", " ", t.lower())).strip()


def baca_acuan():
    ac = REG.daftar_acuan()
    peta = {}
    for r in ac.itertuples(index=False):
        for nm in (r.nama_program_studi, r.nama_inggris):
            nm = re.sub(r"\bl(?=n[a-z])", "I", str(nm))
            k = _n(nm)
            if k:
                peta.setdefault(k, r)
                # Baris acuan yang terpotong saat dipindai, misalnya
                # "Teknologi Rekayasa Pengelasan dan", tetap bisa dirujuk.
                if k.endswith(" dan"):
                    peta.setdefault(k + " fabrikasi", r)
    return ac, peta


def terapkan(path_telaah):
    ac, peta = baca_acuan()
    d = pd.read_excel(path_telaah, sheet_name="Pemetaan Program Studi", header=3)
    d.columns = [c.strip() for c in d.columns]
    d["jumlah_kandidat"] = pd.to_numeric(d.get("jumlah_kandidat"), errors="coerce").fillna(0)
    for c in ("keputusan_pembimbing", "catatan_pembimbing",
              "usulan_nama_program_studi", "rumpun_ilmu", "kandidat_nama_resmi"):
        # Kosong dijadikan string kosong supaya tidak ada nilai NA yang ambigu.
        d[c] = d[c].astype("string").str.strip().fillna("")

    nama, status, alasan = [], [], []
    for r in d.itertuples(index=False):
        kep = (r.keputusan_pembimbing or "").lower()
        cat = r.catatan_pembimbing
        usul = r.usulan_nama_program_studi
        catatan_ada = bool(cat)

        if kep == "hapus":
            nama.append("")
            status.append("dikeluarkan atas keputusan pembimbing")
            alasan.append("Bukan nama bidang studi (misalnya \"Jurusan Relevan\").")
        elif kep in ("perbaiki", "gabungkan"):
            if not catatan_ada:
                nama.append("")
                status.append("masih perlu keputusan")
                alasan.append("Ditandai perlu diperbaiki, tetapi kolom catatan kosong.")
            elif RX_ARAHAN.search(str(cat)):
                nama.append("")
                status.append("perlu ditelaah per lowongan")
                alasan.append(str(cat))
            else:
                nama.append(str(cat))
                status.append("nama diganti sesuai catatan pembimbing")
                alasan.append("")
        elif kep == "setuju":
            if usul:
                nama.append(str(usul))
                status.append("usulan disetujui")
                alasan.append("")
            elif catatan_ada and not RX_ARAHAN.search(str(cat)):
                nama.append(str(cat))
                status.append("nama diambil dari catatan pembimbing")
                alasan.append("")
            elif r.jumlah_kandidat == 1 and r.kandidat_nama_resmi:
                # Hanya ada satu kandidat yang ditawarkan, jadi "setuju" jelas
                # merujuk ke kandidat itu.
                nama.append(str(r.kandidat_nama_resmi).strip())
                status.append("kandidat tunggal disetujui")
                alasan.append("")
            else:
                nama.append("")
                status.append("masih perlu keputusan")
                alasan.append("Ditandai setuju, tetapi ada lebih dari satu kandidat "
                              "sehingga belum jelas kandidat mana yang dimaksud: "
                              + str(r.kandidat_nama_resmi))
        else:
            nama.append(usul)
            status.append("masih perlu keputusan")
            alasan.append("Kolom keputusan pembimbing belum diisi.")

    # Terapkan hasil pemeriksaan per lowongan.
    for i, ist in enumerate(d.istilah_di_lowongan):
        res = RESOLUSI.get(str(ist).strip().lower())
        if not res:
            continue
        jenis, nm, ket = res
        if jenis == "diterapkan":
            nama[i] = " | ".join(nm)
            status[i] = "arahan pembimbing diterapkan setelah lowongan diperiksa"
        elif jenis == "usul dihapus":
            nama[i] = ""
            status[i] = "diusulkan dikeluarkan -- bukan bidang studi"
        else:
            nama[i] = ""
            status[i] = "sudah diperiksa, perlu arahan lanjutan"
        alasan[i] = ket

    # Keputusan pembimbing (29 September 2026): istilah yang tidak beliau
    # putuskan tidak perlu dimasukkan. Seluruhnya dikeluarkan dari
    # pengelompokan. Pengecualian: dua istilah yang SUDAH beliau putuskan
    # (Administrasi Pendidikan dan Supply Chain) tetap memakai keputusan beliau
    # apa adanya, tanpa penyesuaian dari saya.
    DIPUTUSKAN_PEMBIMBING = {"administrasi pendidikan", "supply chain"}
    for i, ist in enumerate(d.istilah_di_lowongan):
        k = str(ist).strip().lower()
        if k not in USULAN_DITERAPKAN or k in DIPUTUSKAN_PEMBIMBING:
            continue
        nama[i] = ""
        status[i] = "dikeluarkan -- tidak diputuskan pembimbing"
        alasan[i] = ("Tidak diputuskan pembimbing; atas arahan beliau tidak "
                     "dimasukkan ke pengelompokan.")

    # Galat OCR pada daftar acuan: huruf "I" kapital terbaca "l" di awal kata,
    # misalnya "lnformasi", "lnternasional", "lndustri", "lnstrumentasi".
    nama = [re.sub(r"\bl(?=n[a-z])", "I", x) for x in nama]
    selaras = [SELARAS.get(x, "") for x in nama]
    d["nama_ditulis_pembimbing"] = [x if s_ else "" for x, s_ in zip(nama, selaras)]
    nama = [s_ or x for x, s_ in zip(nama, selaras)]
    d["nama_program_studi_final"] = nama
    d["status_penerapan"] = status
    d["keterangan"] = alasan

    # Rumpun ilmu untuk nama akhir, bila namanya ada pada daftar acuan.
    rum, jen = [], []
    for x in d.nama_program_studi_final:
        x = x.split(" | ")[0] if x else x
        r = peta.get(_n(x)) if x else None
        rum.append(r.rumpun_ilmu if r is not None else "")
        jen.append(r.jenis_pendidikan if r is not None else "")
    d["rumpun_ilmu_final"] = rum
    d["jenis_pendidikan_final"] = jen
    d["dasar_rumpun"] = ["sesuai daftar acuan" if x else "" for x in rum]
    for i, x in d.nama_program_studi_final.items():
        x = x.split(" | ")[0] if x else x
        if x and not d.at[i, "rumpun_ilmu_final"]:
            r_, dasar = USULAN_RUMPUN.get(x, ("", ""))
            d.at[i, "rumpun_ilmu_final"] = r_
            d.at[i, "dasar_rumpun"] = (
                f"USULAN -- nama tidak tercantum pada peraturan acuan; {dasar}"
                if dasar else "belum ditentukan")
    for i, x in d.nama_ditulis_pembimbing.items():
        if x:
            d.at[i, "keterangan"] = (f"Ejaan diselaraskan dengan peraturan acuan; "
                                     f"pembimbing menulis \"{x}\".")

    keluar = d[["istilah_di_lowongan", "jumlah_penyebutan", "jumlah_lowongan",
                "keputusan_pembimbing", "usulan_nama_program_studi",
                "catatan_pembimbing", "nama_program_studi_final",
                "rumpun_ilmu_final", "dasar_rumpun", "jenis_pendidikan_final",
                "status_penerapan", "keterangan"]].copy()
    return keluar, ac


def tulis_sheet(ws, df, judul, catatan, lebar=None, hdr=4):
    ws.cell(1, 1, judul).font = Font(F, size=13, bold=True)
    c = ws.cell(2, 1, catatan)
    c.font = Font(F, size=9, italic=True, color="808080")
    c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[2].height = 44
    for j, h in enumerate(df.columns, 1):
        cell = ws.cell(hdr, j, h)
        cell.font = Font(F, bold=True, color="FFFFFF", size=10)
        cell.fill = HDR
        cell.alignment = Alignment(horizontal="center", vertical="center",
                                   wrap_text=True)
        cell.border = BD
    ws.row_dimensions[hdr].height = 32
    for i, row in enumerate(df.itertuples(index=False), hdr + 1):
        for j, v in enumerate(row, 1):
            cell = ws.cell(i, j, v)
            cell.font = Font(F, size=10)
            cell.alignment = Alignment(vertical="top", wrap_text=(j > 3))
    ws.freeze_panes = ws.cell(hdr + 1, 1).coordinate
    ws.auto_filter.ref = f"A{hdr}:{get_column_letter(len(df.columns))}{hdr + len(df)}"
    if lebar:
        for j, w in lebar.items():
            ws.column_dimensions[get_column_letter(j)].width = w
    return ws


INKONSISTENSI = [
    ("Administrasi Pendidikan", 1,
     "Dipetakan ke Administrasi Publik, padahal catatan pembimbing pada istilah "
     "\"Administrasi\" menyebut Administrasi Pendidikan harus dikelompokkan "
     "terpisah.",
     "Pisahkan menjadi kelompok Administrasi Pendidikan (nama resmi ada pada "
     "Kepdirjen 96/B/KPT/2025)."),
    ("Manajemen Logistik / Supply Chain", 13,
     "\"Manajemen Logistik\" (9 penyebutan) dipetakan ke Manajemen, sedangkan "
     "\"Supply Chain\" (4) diarahkan ke Manajemen Logistik. Akibatnya kelompok "
     "Manajemen Logistik hanya berisi Supply Chain.",
     "Pilih salah satu: keduanya ke Manajemen, atau keduanya ke Manajemen "
     "Logistik."),
]

# Usulan untuk baris yang kolom keputusannya belum diisi atau belum jelas.
USULAN_KEPUTUSAN = {
    "human resource management": "Manajemen Sumber Daya Manusia (sudah diusulkan sebelumnya)",
    "hukum bisnis": "Hukum Bisnis (sudah diusulkan sebelumnya)",
    "hubungan masyarakat": "Hubungan Masyarakat (sudah diusulkan sebelumnya)",
    "hukum korporasi": "Hukum -- disamakan dengan Hukum Bisnis/Hukum",
    "hukum ketenagakerjaan": "Hukum",
    "ilmu computer": "Ilmu Komputer atau Informatika (salah ketik \"computer\")",
    "tkr": "Pemeliharaan Kendaraan Ringan -- sama dengan keputusan Ibu untuk "
           "\"Teknik Kendaraan Ringan (TKR)\"",
    "konstruksi": "Rekayasa Sipil, atau Teknologi Konstruksi Bangunan Gedung "
                  "untuk jenjang vokasi",
    "instrumen": "Rekayasa Instrumentasi dan Automasi -- sama dengan keputusan "
                 "Ibu untuk \"Instrumentasi\"",
    "manajemen informatika": "Manajemen Informatika (nama program studi vokasi)",
    "penyakit dalam": "Kedokteran -- sama dengan keputusan Ibu untuk istilah "
                      "spesialis lain",
    "robotika": "Teknik Robotika dan Kecerdasan Buatan (akademik) atau "
                "Teknologi Rekayasa Robotika (vokasi)",
    "kota": "Perencanaan Wilayah dan Kota",
}


def bangun(path_telaah, keluaran):
    d, ac = terapkan(path_telaah)
    siap = d[d.nama_program_studi_final != ""]

    # Pengelompokan akhir. Istilah yang oleh pembimbing dibagi menjadi dua
    # (misalnya Bahasa Jepang ATAU Sastra Jepang) dihitung pada kedua kelompok.
    pecah = siap.assign(nama_program_studi_final=siap.nama_program_studi_final
                        .str.split(r" \| ")).explode("nama_program_studi_final")
    kel = (pecah.groupby("nama_program_studi_final")
           .agg(jumlah_istilah_digabung=("istilah_di_lowongan", "size"),
                jumlah_penyebutan=("jumlah_penyebutan", "sum"),
                jumlah_lowongan=("jumlah_lowongan", "sum"),
                rumpun_ilmu=("rumpun_ilmu_final", "first"),
                dasar_rumpun=("dasar_rumpun", "first"),
                daftar_istilah=("istilah_di_lowongan",
                                lambda s: "; ".join(sorted(s)[:12])
                                + (f"; ... ({len(s) - 12} lagi)" if len(s) > 12 else "")))
           .reset_index()
           .sort_values("jumlah_penyebutan", ascending=False))
    rump = (kel.groupby("rumpun_ilmu").agg(
        jumlah_program_studi=("nama_program_studi_final", "size"),
        jumlah_penyebutan=("jumlah_penyebutan", "sum"))
        .reset_index().sort_values("jumlah_penyebutan", ascending=False))
    rump["persen_penyebutan"] = rump.jumlah_penyebutan / rump.jumlah_penyebutan.sum()

    # Daftar usulan yang diterapkan, untuk dilaporkan ke pembimbing.
    perlu = d[d.status_penerapan == "dikeluarkan -- tidak diputuskan pembimbing"][
        ["istilah_di_lowongan", "jumlah_penyebutan", "keputusan_pembimbing",
         "catatan_pembimbing", "nama_program_studi_final", "keterangan"]].rename(
        columns={"keterangan": "keterangan"})
    perlu = perlu.drop(columns=["nama_program_studi_final"])

    cek = d[d.istilah_di_lowongan.str.strip().str.lower().isin(RESOLUSI.keys())][
        ["istilah_di_lowongan", "jumlah_penyebutan", "catatan_pembimbing",
         "nama_program_studi_final", "status_penerapan", "keterangan"]].rename(
        columns={"keterangan": "hasil_pemeriksaan_lowongan"})

    wb = Workbook(); wb.remove(wb.active)
    total = d.jumlah_penyebutan.sum()
    n_siap = siap.jumlah_penyebutan.sum()
    ring = pd.DataFrame([
        ("Istilah yang ditelaah pembimbing", f"{len(d):,}",
         f"{int(total):,} penyebutan"),
        ("", "", ""),
        ("HASIL PENERAPAN", "", ""),
        ("Sudah punya nama program studi akhir", f"{len(siap):,} istilah",
         f"{int(n_siap):,} penyebutan ({n_siap / total * 100:.1f}%)"),
        ("Digabung menjadi", f"{len(kel):,} program studi",
         "lihat sheet 'Kelompok Akhir' dan 'Per Rumpun Ilmu'"),
        ("Arahan \"cek lowongan\" yang sudah dikerjakan",
         f"{len(cek):,} istilah",
         "setiap lowongan dibaca dan aturan Ibu diterapkan; buktinya di sheet "
         "'Hasil Cek Lowongan'"),
        ("Dikeluarkan karena tidak diputuskan Ibu", f"{len(perlu):,} istilah",
         f"{int(perlu.jumlah_penyebutan.sum()):,} penyebutan "
         f"({perlu.jumlah_penyebutan.sum() / total * 100:.1f}%); sesuai arahan "
         "Ibu tidak dimasukkan; lihat sheet 'Tidak Dimasukkan'"),
        ("Dikeluarkan atas keputusan Ibu",
         f"{(d.status_penerapan == 'dikeluarkan atas keputusan pembimbing').sum():,} istilah",
         "TKJ, Linear, Jurusan Relevan, Ilmu Sains, ATEM"),
        ("", "", ""),
        ("PENYESUAIAN YANG SAYA LAKUKAN", "", ""),
        ("Penyelarasan ejaan", f"{(d.keterangan.str.startswith('Ejaan diselaraskan')).sum():,} istilah",
         "Nama yang Ibu tulis disamakan bentuknya dengan tulisan pada peraturan "
         "acuan supaya satu program studi tidak terpecah, misalnya \"Teknik "
         "Mesin\" dan \"Teknik atau Rekayasa Mesin\" -> Rekayasa Mesin; "
         "\"Statistik\" -> Statistika; \"Analis Keuangan\" -> Analisis Keuangan. "
         "Maknanya tidak diubah; tulisan asli Ibu tetap tercatat di kolom "
         "keterangan."),
        ("Setuju tanpa nama usulan", f"{(d.status_penerapan == 'kandidat tunggal disetujui').sum():,} istilah",
         "Ibu menandai setuju pada baris yang hanya punya satu kandidat nama "
         "resmi, sehingga kandidat itulah yang dipakai (misalnya Teknologi Pangan "
         "-> Teknologi Pangan dan Hasil Pertanian)."),
        ("Rumpun ilmu untuk nama di luar peraturan",
         f"{(pecah.dasar_rumpun.str.startswith('USULAN')).sum():,} istilah",
         "Beberapa nama yang Ibu tetapkan tidak tercantum pada ketiga peraturan "
         "(misalnya Seni Kuliner, Teknik Informatika). Namanya tetap dipakai; "
         "rumpun ilmunya saya usulkan dari nama resmi terdekat dan ditandai "
         "USULAN pada kolom dasar_rumpun."),
    ], columns=["Hal", "Jumlah", "Keterangan"])
    ws = tulis_sheet(wb.create_sheet("Ringkasan"), ring,
                     "Penerapan Telaah Pembimbing atas Pemetaan Program Studi",
                     "Hasil penerapan kolom keputusan_pembimbing dan catatan_pembimbing "
                     "yang diisi Bu Tri.",
                     lebar={1: 42, 2: 22, 3: 96})
    for i in range(5, 5 + len(ring)):
        if not str(ws.cell(i, 2).value or "") and str(ws.cell(i, 1).value or ""):
            for j in range(1, 4):
                ws.cell(i, j).fill = SUB
                ws.cell(i, j).font = Font(F, bold=True, size=10)

    tulis_sheet(wb.create_sheet("Tidak Dimasukkan"), perlu,
                f"Tidak Dimasukkan ({len(perlu):,} istilah)",
                "Istilah yang tidak diputuskan pembimbing. Atas arahan beliau, "
                "istilah ini tidak dimasukkan ke pengelompokan program studi.",
                lebar={1: 30, 2: 12, 3: 16, 4: 60, 5: 60})

    ws = tulis_sheet(wb.create_sheet("Per Rumpun Ilmu"), rump,
                     "Rekap per Rumpun Ilmu (Permendikbud 154/2014 Pasal 2)",
                     "Jumlah program studi dan penyebutan pada tiap rumpun ilmu.",
                     lebar={1: 22, 2: 20, 3: 18, 4: 18})
    for i in range(5, 5 + len(rump)):
        ws.cell(i, 4).number_format = "0.0%"

    tulis_sheet(wb.create_sheet("Kelompok Akhir"), kel,
                f"Kelompok Akhir Program Studi ({len(kel):,} nama)",
                "Satu baris satu program studi hasil penggabungan. Kolom "
                "daftar_istilah memperlihatkan istilah asli di lowongan yang "
                "digabungkan ke nama tersebut.",
                lebar={1: 42, 2: 14, 3: 14, 4: 14, 5: 18, 6: 44, 7: 86})

    tulis_sheet(wb.create_sheet("Hasil Cek Lowongan"), cek,
                f"Hasil Pemeriksaan Lowongan ({len(cek):,} istilah)",
                "Istilah yang catatan pembimbingnya meminta isi lowongan diperiksa. "
                "Kolom hasil_pemeriksaan_lowongan memuat kutipan lowongan yang "
                "menjadi dasar keputusan.",
                lebar={1: 24, 2: 12, 3: 60, 4: 36, 5: 30, 6: 110})

    tulis_sheet(wb.create_sheet("Pemetaan Akhir"), d,
                f"Pemetaan Akhir per Istilah ({len(d):,} baris)",
                "Seluruh istilah beserta keputusan pembimbing, nama akhirnya, dan "
                "status penerapannya.",
                lebar={1: 34, 2: 12, 3: 12, 4: 16, 5: 30, 6: 62, 7: 34, 8: 18,
                       9: 40, 10: 16, 11: 30, 12: 62})

    wb.save(keluaran)
    print(f"Tersimpan: {keluaran}")
    print(d.status_penerapan.value_counts().to_string())
    print(f"\nprogram studi akhir: {len(kel)} | tidak dimasukkan: {len(perlu)} istilah, "
          f"{int(perlu.jumlah_penyebutan.sum())} penyebutan")
    print(f"sudah punya nama: {n_siap / total * 100:.1f}% penyebutan")
    print(rump.to_string(index=False))
    return d, kel, perlu


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else "bt.xlsx"
    bangun(p, "2b_Pemetaan_Program_Studi_Final.xlsx")
