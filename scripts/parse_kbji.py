"""Membaca struktur KBJI 2014 (BPS) dari teks PDF: kode 1/2/3/4/6 digit + judul + uraian."""
import re, pandas as pd

RX = re.compile(r"^(\d{4}\.\d{2}|\d{4}|\d{3}|\d{2}|\d)\s+(\S.*)$")
LEVEL = {1: "golongan_pokok", 2: "subgolongan_pokok", 3: "golongan", 4: "subgolongan", 7: "jabatan"}

def parse(path="kbji.txt", mulai=1170):
    baris = open(path, encoding="utf-8").read().split("\n")[mulai:]
    out, cur = [], None
    for ln in baris:
        if ln.startswith("Klasifikasi Baku Jabatan Indonesia Tahun") or re.match(r"^Halaman \d+", ln) \
           or re.match(r"^\s{20,}Golongan Pokok \d\s*$", ln) or re.match(r"^Golongan Pokok \d\s*$", ln):
            continue
        m = RX.match(ln)          # kode harus di kolom 0
        if m and not ln.startswith(" "):
            kode, judul = m.group(1), m.group(2).strip()
            if len(kode.replace(".", "")) in (1, 2, 3, 4, 6) and judul[:1].isupper():
                cur = {"kode": kode, "judul": judul, "uraian": []}
                out.append(cur); continue
        if cur is not None and ln.strip():
            # baris lanjutan judul (judul panjang patah ke baris berikut tanpa indentasi dalam)
            if not cur["uraian"] and ln.startswith("    ") and not ln.startswith("     ") is False:
                pass
            cur["uraian"].append(ln.strip())
    df = pd.DataFrame(out)
    df["uraian"] = df.uraian.map(lambda x: " ".join(x))
    df["digit"] = df.kode.str.replace(".", "", regex=False).str.len()
    df["tingkat"] = df.digit.map({1: "golongan pokok", 2: "subgolongan pokok", 3: "golongan",
                                  4: "subgolongan", 6: "jabatan"})
    # buang duplikat (kode muncul di daftar isi/uraian) -> ambil kemunculan pertama dengan uraian terpanjang
    df["pj"] = df.uraian.str.len()
    df = df.sort_values(["kode", "pj"], ascending=[True, False]).drop_duplicates("kode")
    # konsistensi hierarki: kode anak harus diawali kode induk yang ada
    return df.drop(columns="pj").sort_values("kode").reset_index(drop=True)

if __name__ == "__main__":
    df = parse()
    print(df.tingkat.value_counts().to_string())
    for k in ["2", "24", "243", "2431", "2431.01", "4110", "5223", "5223.01", "9112", "8322"]:
        r = df[df.kode == k]
        print(k, "->", r.judul.values[:1], "|", (r.uraian.values[0][:120] if len(r) else ""))
