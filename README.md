# Ekstraksi Keterampilan dari Lowongan Kerja Berbahasa Indonesia dengan NER IndoBERT dan Dashboard Analisis Pasar Kerja

Repositori ini berisi kode penelitian **implementasi *Named Entity Recognition* (NER) berbasis Transformer untuk membangun dashboard analisis pasar kerja** dari lowongan kerja berbahasa Indonesia.

Model IndoBERT (`indolem/indobert-base-uncased`) di-*fine-tune* untuk mengenali 14 jenis entitas lowongan, seperti jabatan, keterampilan, *soft skill*, perangkat lunak, jenjang pendidikan, dan bidang studi. Entitas hasil ekstraksi kemudian dinormalisasi dan dipetakan ke taksonomi keterampilan Escudero dkk., KBJI 2014, serta program studi dan jenjang baku. Hasilnya disajikan dalam dashboard Streamlit berisi 16 halaman analisis.

| | |
|---|---|
| Data | 5.121 lowongan (Glints dan Dealls), April 2023 – Mei 2026 |
| Entitas | 14 jenis, skema IOB2 (29 label) |
| Kinerja model (data uji) | F1 mikro 0,727 (ketat), 0,858 (sebagian); baseline kamus 0,116 |
| Dashboard | Streamlit + Plotly, 16 halaman, dengan bukti kalimat sumber |

## Struktur repositori

```
.
├── notebooks/
│   ├── 01_ner_indobert_pelatihan_inferensi.ipynb   # pipeline utama (Kaggle, GPU)
│   └── 02_benchmark_5_model.ipynb                  # perbandingan 5 model pra-latih
├── scripts/            # pascaproses basis data & ekspor (lihat tabel di bawah)
├── dashboard/
│   ├── app.py          # aplikasi Streamlit
│   └── .streamlit/config.toml
├── results/
│   └── benchmark/      # hasil benchmark 5 model (CSV, JSON, LaTeX) + 9 grafik
├── docs/
│   └── Panduan_Penggunaan_Dashboard_Pasar_Kerja.pdf
├── data/               # TIDAK disertakan di repo (lihat data/README.md)
├── requirements.txt
└── README.md
```

## Alur penelitian

```
Lowongan (JSON berlabel) ──► Notebook 01 ──► model NER + ner_jobposting.sqlite
                                │                       │
                                │                       ▼
                                │             scripts/ (pascaproses: normalisasi skill,
                                │             prodi & jenjang, KBJI 4 digit, bukti kalimat)
                                │                       │
                                ▼                       ▼
                     Notebook 02 (benchmark)     dashboard/app.py
```

### 1. Notebook utama: `notebooks/01_ner_indobert_pelatihan_inferensi.ipynb`

Dijalankan di **Kaggle dengan GPU T4** (Settings → Accelerator → GPU T4 x2). Data anotasi dipasang lewat *Add Input*. Isinya:

| Bagian | Isi |
|---|---|
| 0–2 | Instalasi, konfigurasi (`CONFIG`), pemuatan dan pemeriksaan kualitas data |
| 3–4 | Tokenisasi, konversi IOB2, *chunking* 180 kata, pembagian data tingkat dokumen (seed 42) |
| 5 | Baseline pencocokan kamus |
| 6–7 | *Fine-tuning* IndoBERT, evaluasi ketat dan sebagian, dekode Viterbi berkendala, analisis kesalahan |
| 8 | Pengayaan: atribut Layer 2, taksonomi Escudero, KBJI 2014, normalisasi judul |
| 8f | Inferensi model ke seluruh lowongan dan validasi indikator dashboard (model vs label manual pada data uji) |
| 9 | Pembangunan basis data SQLite untuk dashboard |
| 10 | Visualisasi dan grafik untuk artikel (disimpan ke `outputs/figures/`) |

> **Catatan RAM:** bagian 8f dan 9 memakan banyak memori. Bila *kernel* mati di bagian 9, unduh `outputs/prediksi_ner_lowongan.json` lalu bangun basis data secara lokal dengan `scripts/bangun_db_dari_json.py`.

Notebook ini disimpan **beserta keluarannya** dari run Kaggle (seed 42), mencakup pelatihan, evaluasi, dekode Viterbi, pengayaan, inferensi, dan validasi indikator (bagian 0–8f). Bagian 9 ke bawah tidak memiliki keluaran karena *kernel* kehabisan RAM pada run tersebut; basis data dashboard dibangun dengan `scripts/bangun_db_dari_json.py`.

### 2. Benchmark model: `notebooks/02_benchmark_5_model.ipynb`

Melatih lima model pra-latih dengan konfigurasi identik (3 model khusus Indonesia, 2 model multibahasa), lalu membuat grafik perbandingannya. Hasil per model disimpan ke `hasil_benchmark.json`, sehingga notebook dapat dilanjutkan bila sesi terputus. Notebook disimpan beserta keluarannya (Kaggle, 2× GPU T4, ±3 jam).

Hasil (data uji, F1 entitas ketat, dekode Viterbi, seed 42; berkas lengkap di `results/benchmark/`):

| Model | Jenis | Parameter (juta) | Presisi | Recall | F1 | Waktu latih (menit) |
|---|---|---:|---:|---:|---:|---:|
| **indolem/indobert-base-uncased** | Khusus Indonesia | 110 | 0,708 | **0,758** | **0,732** | 38 |
| bert-base-multilingual-cased | Umum (multibahasa) | 177 | **0,713** | 0,745 | 0,728 | 49 |
| cahya/bert-base-indonesian-1.5G | Khusus Indonesia | 110 | 0,700 | 0,743 | 0,721 | 30 |
| distilbert-base-multilingual-cased | Umum (multibahasa) | 135 | 0,701 | 0,725 | 0,713 | 30 |
| indobenchmark/indobert-base-p2 | Khusus Indonesia | 124 | 0,706 | 0,716 | 0,711 | 38 |

Selisih di bawah sekitar 0,01 F1 masih dalam rentang variasi antareksekusi, sehingga keunggulan IndoBERT atas mBERT (0,004) belum dapat dianggap pasti tanpa pengulangan beberapa *seed*. Grafik untuk artikel (Gambar 7–9) dibuat ulang dari berkas ini dengan `scripts/gambar_artikel_benchmark.py results/benchmark <folder_keluaran>`.

### 3. Skrip pascaproses: `scripts/`

Semua skrip berada di satu folder karena saling meng-*import*. Jalankan dari dalam folder `scripts/`.

| Skrip | Fungsi |
|---|---|
| `parse_regulasi.py` | Membaca tiga peraturan acuan nama program studi dan jenjang (Permendikbud 154/2014, Kepdirjen Diksi 27/D/M/2022, Kepdirjen Dikti 96/B/KPT/2025) |
| `build_prodi_jenjang.py` | Membuat *workbook* telaah pemetaan istilah bidang studi dan jenjang ke nama baku |
| `terapkan_telaah_prodi.py` | Menerapkan keputusan pembimbing atas pemetaan program studi |
| `gabung_prodi_v19.py` | Menggabungkan nama program studi yang merujuk prodi yang sama (salah ketik, istilah Inggris, nama lama/baru) |
| `parse_kbji.py` | Membaca struktur KBJI 2014 (kode dan uraian) dari teks PDF BPS menjadi `kbji.pkl` |
| `aturan_kbji4.py` | Aturan pemetaan judul pekerjaan ke subgolongan KBJI 2014 (4 digit) |
| `klasifikasi_kbji4.py` | Memberi kode KBJI 2/3/4 digit pada setiap judul dan membuat daftar telaah |
| `kbji_override_v16_cleaning.py` | Koreksi manual golongan pokok KBJI (addendum) |
| `terapkan_kbji_v18.py` | Menerapkan telaah pembimbing atas kode KBJI per pekerjaan |
| `bangun_v17.py` | Memasukkan koreksi pembimbing (normalisasi skill, prodi) ke basis data |
| `skill_gabungan_label.py` | Melabeli skill gabungan (anotasi + metadata situs) dengan label NER dan kategori Escudero |
| `bangun_bukti.py` | Membuat tabel bukti kalimat (`skill_bukti`, `job_deskripsi`) untuk fitur *view evidence* di dashboard |
| `bangun_db_dari_json.py` + `muat_fungsi.py` | Membangun ulang tabel turunan entitas dari file anotasi atau prediksi model, memakai fungsi pengayaan yang sama dengan notebook |
| `ekspor_dataset_excel.py` | Mengekspor seluruh data ke satu berkas Excel beserta kamus data |
| `tambah_sheet_mingguan.py` | Menambah sheet taksonomi Escudero per minggu ke *workbook* Escudero |

Contoh: membangun basis data dashboard dari keluaran model.

```bash
cd scripts
python3 bangun_db_dari_json.py ../data/ner_jobposting.sqlite ../data/prediksi_ner_lowongan.json \
        ../data/ner_jobposting_prediksi.sqlite ../notebooks/01_ner_indobert_pelatihan_inferensi.ipynb
python3 bangun_bukti.py ../data/ner_jobposting_prediksi.sqlite ../data/prediksi_ner_lowongan.json
```

### 4. Dashboard: `dashboard/app.py`

```bash
pip install -r requirements-dashboard.txt
# letakkan basis data di data/ner_jobposting.sqlite
cd dashboard
streamlit run app.py
```

Dashboard terbuka di `http://localhost:8501`. Panduan penggunaan lengkapnya ada di [`docs/Panduan_Penggunaan_Dashboard_Pasar_Kerja.pdf`](docs/Panduan_Penggunaan_Dashboard_Pasar_Kerja.pdf).

## Instalasi

```bash
git clone https://github.com/USERNAME/ner-lowongan-kerja.git
cd ner-lowongan-kerja
pip install -r requirements.txt            # notebook & skrip
pip install -r requirements-dashboard.txt  # dashboard saja
```

## Data dan model

Dataset lowongan, anotasi, basis data, dan bobot model **tidak disertakan** di repositori ini. Lihat [`data/README.md`](data/README.md) untuk daftar berkas yang dibutuhkan.

- Dataset: `[tautan dataset — Kaggle/Zenodo/Drive]`
- Model NER terlatih: `[tautan Hugging Face Hub]`

## Penulis

- Dzaky Muhammad Zidane — Informatika, Universitas Sebelas Maret
- Pembimbing: [nama pembimbing]

## Sitasi

Bila memakai kode ini, mohon sitasi artikel terkait: `[sitasi artikel setelah terbit]`
