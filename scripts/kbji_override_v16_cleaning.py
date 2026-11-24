"""
Koreksi Manual Klasifikasi KBJI 2014  (v16 -- addendum atas v15)
=================================================================
Instruksi pembimbing (dosen): "Cleaning service harusnya masuk ke Pekerja Kasar
(golongan 9)" -- ditemukan 28 lowongan cleaning service/petugas kebersihan yang
masih terklasifikasi ke golongan 5 (Tenaga Usaha Jasa dan Tenaga Penjualan) di
dashboard, meski sudah melalui pipeline lexicon -> fuzzy -> k-NN embedding.

Skrip ini adalah ADDENDUM, dijalankan SETELAH kbji_override.py (v15) yang
sudah ada -- tidak menggantikannya. Idempoten, aman dijalankan berkali-kali.

CATATAN PENTING -- yang SENGAJA TIDAK ikut dikoreksi skrip ini:
  - "Supervisor Cleaning Service" (2 lowongan, sudah golongan 1 / Manajer):
    dibiarkan, karena posisi ini bersifat manajerial (mengawasi tim), bukan
    pelaksana kebersihan langsung -- konsisten dengan cara v15 mengecualikan
    "Kepala Divisi Kasir" dari koreksi kasir.
  - "Cleaning Service Officer" (1 lowongan, golongan 3 / Teknisi dan Asisten
    Profesional): TIDAK termasuk lingkup instruksi pembimbing kali ini
    (instruksi menyebut lowongan yang MASIH di golongan 5), jadi dibiarkan
    apa adanya -- perlu ditanyakan terpisah ke pembimbing bila memang mau
    disamakan.

CATATAN AMBIGU -- ikut dikoreksi ke golongan 9 karena tetap secara harfiah
memuat "cleaning service" dan berada di golongan 5, TAPI sebaiknya
dikonfirmasi ulang ke pembimbing karena mencampur fungsi/senioritas lain:
  - "Doorman & Cleaning Service" -- menggabungkan fungsi penjaga pintu (Tenaga
    Usaha Jasa) dan cleaning service dalam satu judul.
  - "Tl Cleaning Service" -- "Tl" kemungkinan singkatan "Team Leader"
    (berarti peran koordinasi), bukan pelaksana biasa.
Bila pembimbing ingin dua judul ini TETAP di golongan 5 atau dipindah ke
golongan lain, tinggal tambahkan ke KOREKSI_EKSAK (persis seperti pola v15).

CARA PAKAI
----------
    python kbji_override.py outputs/ner_jobposting.sqlite
    python kbji_override_v16_cleaning.py outputs/ner_jobposting.sqlite
"""
import sys
import sqlite3
import re

GOLONGAN = {
    1: "Manajer",
    2: "Profesional",
    3: "Teknisi dan Asisten Profesional",
    4: "Tenaga Tata Usaha",
    5: "Tenaga Usaha Jasa dan Tenaga Penjualan",
    6: "Pekerja Terampil Pertanian, Kehutanan dan Perikanan",
    7: "Pekerja Pengolahan, Kerajinan, dan Ybdi",
    8: "Operator dan Perakit Mesin",
    9: "Pekerja Kasar",
}

# ---------------------------------------------------------------------------
# Koreksi pola -- hanya menyentuh baris yang SAAT INI golongan 5, judul
# memuat "cleaning service" atau "petugas kebersihan". Judul yang berawalan
# "supervisor" DIKECUALIKAN lewat negative lookahead (jaga-jaga bila nanti ada
# supervisor cleaning service yang entah kenapa masih golongan 5).
# Sumber: catatan pembimbing (dosen), telaah 30 Agustus 2026.
# ---------------------------------------------------------------------------
KOREKSI_POLA = [
    (r"^(?!supervisor\b).*(?:cleaning service|petugas kebersihan)", 9,
     "Keputusan pembimbing: cleaning service/petugas kebersihan tergolong "
     "Pekerja Kasar (KBJI 9112 Pembersih dan sejenisnya di gedung), bukan "
     "Tenaga Usaha Jasa dan Tenaga Penjualan. Salah terklasifikasi otomatis "
     "kemungkinan karena kata 'Service' cocok dengan pola tenaga jasa."),
]

# Hanya menyentuh baris yang saat ini golongan 5 -- supaya Supervisor (gol. 1)
# dan Cleaning Service Officer (gol. 3) yang di luar lingkup instruksi tidak
# ikut tersentuh meski judulnya juga memuat frasa yang sama.
SCOPE_GOLONGAN_ASAL = 5

# Dua judul ini ikut terkoreksi tapi dicatat sebagai perlu-konfirmasi-ulang
# (lihat docstring). Dipakai hanya untuk pelaporan, tidak mengubah query.
PERLU_KONFIRMASI_ULANG = {
    "Doorman & Cleaning Service": "menggabungkan fungsi doorman dan cleaning service",
    "Tl Cleaning Service": "'Tl' kemungkinan Team Leader, bukan pelaksana biasa",
}


def apply_overrides(db_path, verbose=True):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cols = [r[1] for r in cur.execute("PRAGMA table_info(jobs)")]
    if "kbji_source" not in cols:
        cur.execute("ALTER TABLE jobs ADD COLUMN kbji_source TEXT DEFAULT 'otomatis'")

    total = 0
    log = []

    judul_scope = [r[0] for r in cur.execute(
        "SELECT DISTINCT title FROM jobs WHERE kbji_golongan_pokok_kode=? AND title != ''",
        (SCOPE_GOLONGAN_ASAL,))]

    for pola, kode, alasan in KOREKSI_POLA:
        rx = re.compile(pola, re.IGNORECASE)
        cocok = [t for t in judul_scope if rx.search(t.lower())]
        if not cocok:
            continue
        ph = ",".join("?" * len(cocok))
        cur.execute(
            f"""UPDATE jobs SET kbji_golongan_pokok_kode=?, kbji_golongan_pokok_nama=?,
                                kbji_confidence=1.0, kbji_source='manual_review'
                WHERE kbji_golongan_pokok_kode=? AND title IN ({ph})""",
            (kode, GOLONGAN[kode], SCOPE_GOLONGAN_ASAL, *cocok))
        n = cur.rowcount
        total += n
        log.append((f"[pola v16] {pola}  ->  {len(cocok)} judul unik", GOLONGAN[kode], n, alasan))

    conn.commit()

    if verbose:
        print(f"\nKoreksi manual KBJI (v16 -- cleaning service) diterapkan pada: {db_path}")
        print("=" * 78)
        for judul, gol, n, alasan in log:
            print(f"  {judul}")
            print(f"      -> {gol}   ({n} lowongan)")
            print(f"      alasan: {alasan}")
        print("=" * 78)
        print(f"Total baris lowongan yang dikoreksi (v16): {total}\n")

        print("PERLU DIKONFIRMASI ULANG ke pembimbing (ikut terkoreksi, tapi judulnya ambigu):")
        for judul, catatan in PERLU_KONFIRMASI_ULANG.items():
            print(f"  - {judul}: {catatan}")
        print()

        print("SENGAJA TIDAK disentuh skrip ini (di luar lingkup instruksi pembimbing):")
        print("  - Supervisor Cleaning Service (golongan 1, Manajer) -- posisi manajerial")
        print("  - Cleaning Service Officer (golongan 3, Teknisi dan Asisten Profesional)")
        print()

        print("Distribusi golongan pokok setelah koreksi v16:")
        for nama, n in cur.execute(
                """SELECT kbji_golongan_pokok_nama, COUNT(*) FROM jobs
                   GROUP BY 1 ORDER BY 2 DESC"""):
            print(f"  {n:>5}  {nama}")
        print()

    conn.close()
    return total


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "outputs/ner_jobposting.sqlite"
    apply_overrides(path)
