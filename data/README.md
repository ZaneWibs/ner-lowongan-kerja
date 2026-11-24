# Folder data

Berkas data **tidak disertakan** di repositori. Letakkan berkas berikut di folder ini sebelum menjalankan skrip atau dashboard.

| Berkas | Dipakai oleh | Keterangan |
|---|---|---|
| `ALL_batches_gold_annotations.json` | Notebook 01, skrip ekspor | 5.121 lowongan beserta anotasi entitas (hasil adjudikasi) |
| `ner_jobposting.sqlite` | Dashboard, skrip pascaproses | Basis data dashboard (keluaran notebook 01 bagian 9 + pascaproses) |
| `prediksi_ner_lowongan.json` | `bangun_db_dari_json.py` | Keluaran model NER untuk seluruh lowongan (notebook 01 bagian 8f) |
| `kbji.pkl` | Skrip KBJI | Hasil `parse_kbji.py` dari dokumen KBJI 2014 (BPS) |
| Berkas PDF peraturan | `parse_regulasi.py` | Permendikbud 154/2014, Kepdirjen Diksi 27/D/M/2022, Kepdirjen Dikti 96/B/KPT/2025 |

Tautan unduhan: `[isi tautan dataset]`
