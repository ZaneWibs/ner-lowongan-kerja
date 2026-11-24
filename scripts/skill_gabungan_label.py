"""
Pelabelan sheet "Skill Gabungan"
================================
Permintaan pembimbing (Bu Tri, 27 September 2026): sheet "Skill Gabungan" diberi
label label_ner, kategori_escudero, dan subkategori_escudero -- termasuk untuk
baris yang berasal dari metadata situs, yang sebelumnya kosong.

Cara pengisiannya berjenjang, dan tiap baris diberi kolom sumber_label supaya
dasar pelabelannya bisa ditelusuri:

  1. Baris dari anotasi  -> label apa adanya dari basis data.
  2. Baris metadata yang namanya SAMA PERSIS dengan salah satu skill hasil
     anotasi -> label diwarisi dari skill tersebut. Mencakup 731 istilah
     metadata (14.459 penyebutan).
  3. Sisanya -> diklasifikasikan dengan lexicon kata kunci bahasa Inggris yang
     ditulis eksplisit di berkas ini. Tidak ada tahap embedding atau kemiripan
     teks, sesuai prinsip yang sudah dipakai untuk taksonomi Escudero.
  4. Yang tidak tertangkap lexicon dibiarkan kosong dan ditandai, tidak dipaksa
     masuk ke kategori terdekat.

label_ner untuk baris metadata hanya diisi bila diwarisi dari skill anotasi
yang identik. Selain itu dikosongkan, karena tag metadata tidak punya rentang
teks pada lowongan sehingga tidak pernah melalui pelabelan entitas.
"""
import collections
import json
import re
import sqlite3
import sys
import unicodedata

import pandas as pd

BROAD = {
    "Cognitive skills (narrow sense)": "Cognitive Skills",
    "Computer (general) skills": "Cognitive Skills",
    "Software (specific) skills and technical support": "Cognitive Skills",
    "Financial skills": "Cognitive Skills",
    "Writing skills": "Cognitive Skills",
    "Project management skills": "Cognitive Skills",
    "Machine Learning and Artificial Intelligence": "Cognitive Skills",
    "Character skills (conscientiousness, emotional stability and openness to "
    "experience)": "Socioemotional Skills",
    "Social skills (including agreeableness and extraversion)": "Socioemotional Skills",
    "People management skills": "Socioemotional Skills",
    "Customer service skills": "Socioemotional Skills",
    "Finger-dexterity skills": "Manual Skills",
    "Hand-foot-eye coordination skills": "Manual Skills",
    "Physical skills": "Manual Skills",
}
KARAKTER = ("Character skills (conscientiousness, emotional stability and "
            "openness to experience)")
SOSIAL = "Social skills (including agreeableness and extraversion)"

# Lexicon kata kunci bahasa Inggris untuk istilah metadata. Urutan penting:
# pola yang lebih khusus ditaruh lebih dulu. Dicocokkan sebagai kata utuh.
LEXICON = [
    # --- Socioemotional ---
    (r"customer (service|relations|care|support|satisfaction)|client (service|"
     r"relations)|guest (service|relations|handling)|complaint handling|"
     r"after sales|hospitality service|reception|receptionist|waiter|waitress|"
     r"barista service", "Customer service skills"),
    (r"leadership|team lead|supervisor|supervision|people management|"
     r"staff management|recruitment|human resource|hrd|hris|hr admin|"
     r"performance appraisal|coaching|mentoring|training delivery|"
     r"employee relations|talent", "People management skills"),
    (r"teamwork|team work|collaboration|communication|communicative|"
     r"negotiation|public speaking|presentation|interpersonal|persuasion|"
     r"networking|relationship building|counseling|teaching|tutoring|"
     r"language teaching|classroom management|hosting|host|mc\b|selling|"
     r"sales|marketing|promotion|telemarketing|canvassing", SOSIAL),
    (r"discipline|disciplined|diligent|diligence|honest|integrity|"
     r"positive attitude|hardworking|hard working|responsib|initiative|"
     r"adaptab|flexib|time management|punctual|attention to detail|"
     r"detail oriented|thorough|under pressure|self motivat|work ethic|"
     r"patience|\bpatient\b|neat\b|tidy", KARAKTER),
    # --- Cognitive: khusus dulu ---
    # Disetarakan dengan klasifikasi yang sudah dipakai pada skill hasil
    # anotasi: "mesin kasir"/"sistem kasir" -> Financial skills.
    (r"\bcashier\b|point of sale|\bpos\b|fee collection|cash handling",
     "Financial skills"),
    (r"machine learning|artificial intelligence|deep learning|neural network|"
     r"\bai\b|data science|nlp\b", "Machine Learning and Artificial Intelligence"),
    (r"accounting|accountancy|bookkeeping|finance|financial|tax|taxation|"
     r"audit|payroll|budget|cost control|accounts (payable|receivable)|"
     r"invoic|billing|treasury|banking|credit analysis|cash (flow|management)",
     "Financial skills"),
    (r"project (management|coordination|planning)|scheduling|"
     r"construction management|site management|production management|"
     r"operations management|store management|restaurant management|"
     r"inventory management|supply chain|logistics|warehouse management|"
     r"procurement|purchasing|quality (management|assurance|control)|"
     r"\bqa\b|\bqc\b|iso\b|\bsop\b|risk management|event (management|"
     r"organiz)", "Project management skills"),
    # "fotografi", "animasi", "seo", "interview" pada data anotasi masuk
    # Cognitive skills (narrow sense); istilah metadata yang sepadan
    # disamakan supaya tidak muncul dua perlakuan berbeda.
    (r"photograph|videograph|animation|3d (rendering|sculpting|modeling)|"
     r"search engine optimization|\bseo\b|interviewing|\binterview\b|"
     r"illustration|\bediting\b|storyboard", "Cognitive skills (narrow sense)"),
    (r"writing|copywriting|content creation|report writing|journalis|"
     r"editing|translation|proofread|documentation|correspondence",
     "Writing skills"),
    (r"software development|programming|coding|web development|"
     r"mobile development|database|sql\b|python|java\b|javascript|php\b|"
     r"framework|api\b|troubleshooting|network|it support|technical support|"
     r"system administration|cyber ?security|devops|cloud|server|"
     r"computer hardware|hardware|software (specific|engineering)|"
     r"autocad|sketchup|photoshop|illustrator|corel|figma|canva|"
     r"adobe|solidworks|revit|erp\b|sap\b|odoo|tally",
     "Software (specific) skills and technical support"),
    (r"microsoft (office|excel|word|powerpoint)|ms (office|excel|word)|"
     r"google (sheets|docs|workspace|drive)|spreadsheet|computer (skill|"
     r"literacy|operation)|data entry|typing|internet|email|"
     r"office (software|application)", "Computer (general) skills"),
    (r"analysis|analytic|research|reporting|statistic|forecasting|"
     r"problem solving|planning|strategy|strategic|evaluation|"
     r"monitoring|calculation|numeracy|mathematic|accuracy of data|"
     r"market research|business (development|strategy|growth|analysis)|"
     r"decision making|critical thinking|curriculum|lesson planning|"
     r"knowledge|law\b|legal|regulation|compliance|medical|healthcare|"
     r"nursing|pharmac|diagnos|engineering|design\b|architecture",
     "Cognitive skills (narrow sense)"),
    # --- Manual ---
    (r"driving|driver|riding|forklift|operat(or|ing) (machine|mesin)|"
     r"machine operation|heavy equipment|welding|soldering|"
     r"vehicle maintenance|mechanical maintenance|electrical maintenance|"
     r"installation|repair|assembly|automotive|technician service",
     "Hand-foot-eye coordination skills"),
    (r"cooking|cook\b|baking|bartender|barista|food preparation|drink preparation|"
     r"sewing|tailoring|craft|handicraft|packing|packaging|"
     r"beauty|makeup|hairdress|nail|massage|grooming|"
     r"cleaning|housekeeping|laundry|gardening|planting|harvest|"
     r"food handling|food safety|elderly care|child care|babysit",
     "Finger-dexterity skills"),
    (r"lifting|loading|unloading|physical|stamina|security guard|"
     r"patrol|warehouse (operator|staff)|manual handling|bongkar muat",
     "Physical skills"),
]
LEXICON = [(re.compile(p), s) for p, s in LEXICON]

# ---------------------------------------------------------------------------
# Lapis kedua lexicon, atas permintaan pembimbing (28 September 2026) supaya
# tidak ada baris metadata yang kosong labelnya. Aturan di sini hanya diuji
# SETELAH seluruh aturan di atas tidak ada yang cocok, sehingga tidak dapat
# menggeser klasifikasi yang sudah benar. Kata kuncinya mencakup bahasa
# Indonesia karena sebagian tag metadata memang ditulis berbahasa Indonesia.
# ---------------------------------------------------------------------------
LEXICON_TAMBAHAN = [
    # --- Manual: produksi, mesin, dan pekerjaan tangan ---
    (r"mesin|machine|lathe|bubut|forging|molding|extrusion|injection|"
     r"drill|drilling|cutting|potong|pemotongan|parting|setter|panel maker|"
     r"welding|las|solder|wiring|kabel|sirkuit|breaker|elevator|"
     r"genset|overhaul|hydraulic|pneumatic|air conditioning|service ac|"
     r"perbaikan|reparasi|montir|mekanik|teknisi|technician|engineer|"
     r"perakitan|assembly|instalasi|maintenance|automobile|vehicle|"
     r"kendaraan|mobil|motor|truck|trucking|dump truck|viar|sim [ab]|"
     r"forklift|alat berat|scaffold|scafhold|waspang|nahkoda|tugboat|"
     r"port captain|power lineman|optical (cable|transmission)|fiber optic|"
     r"radiograf|ct scan|mri|elektromedik|elekromedik|"
     r"total station|waterpass|theodolite|surveying|refraction test",
     "Hand-foot-eye coordination skills"),
    (r"produksi|production|manufactur|pabrik|garmen|garment|jahit|menjahit|"
     r"sewing|tailor|pola|pattern|carver|stonecutter|wood|kayu|furniture|"
     r"finishing|printing|cetak|percetakan|rotogravure|sablon|"
     r"makanan|minuman|food|beverage|drink|restaurant|restoran|dapur|"
     r"kitchen|masak|memasak|roti|baker|bakery|kopi|coffee|espresso|"
     r"latte|brew|matcha|bingsu|frozen|meat|ikan|ayam|udang|serving|"
     r"pelayan|waiter|pramusaji|barbecue|culinary|kuliner|menu|"
     r"salon|hairstylist|hair |skin care|cosmetic|kosmetik|estetik|"
     r"eyelash|spa|grooming|flower|bunga|landscap|taman|park maintenance|"
     r"cuci|mencuci|menyetrika|gosok|washing|laundry|pest control|"
     r"pembersihan|bersih|dispensing|sample preparation|laboratorium|"
     r"laboratory|chemical testing|formulasi|formulation|craft|artwork|"
     r"sketsa|menggambar|drawing|painting|coating|display|layout|"
     r"jilid|hardcover|hardbox|numbering|picking|picker|packing|"
     r"perkebunan|pertanian|agricultur|agronomi|animal|ternak|husbandry",
     "Finger-dexterity skills"),
    (r"angkat|panggul|beban|fisik|physical|stamina|jasmani|berdiri lama|"
     r"suhu dingin|ketinggian|security|satpam|keamanan|patrol|courier|"
     r"kurir|dispatch|helper|crew|pantry|checker|shopper|staff|"
     r"keselamatan|safety|k3|hiperkes|kesehatan kerja|limbah|waste|"
     r"climb|claimbing|inspection|inspeksi",
     "Physical skills"),
    # --- Socioemotional ---
    (r"pelanggan|customer|client|tamu|guest|complaint|keluhan|"
     r"pramuniaga|spg|spb|kasir|teller|reservation|reservasi|"
     r"ticketing|tiket|tour guide|travel|hotel|villa|penginapan|"
     r"service (delivery|recovery)|handling|inbound call|call|"
     r"relasi|relations|greeting|hospitality",
     "Customer service skills"),
    (r"manajer|manager|kepala|pengawas|supervis|leadership|hiring|"
     r"training and development|general affairs|human capital|hr|"
     r"organizational|change management|partnership|konsultan|consulting|"
     r"koordinasi|coordination|community operation|stakeholder",
     "People management skills"),
    (r"komunikasi|communication|presentasi|presentation|negosiasi|"
     r"bahasa|language|mandarin|inggris|english|arab|japanese|korean|"
     r"qur'an|tajwid|phonics|vocabulary|interpretation|ielts|toefl|"
     r"mengajar|teaching|guru|education|pendidikan|pembelajaran|"
     r"konseling|counsel|storytelling|empathy|active listening|"
     r"kerjasama|kerja sama|tim|team|organisasi|jaringan|networking|"
     r"promotor|promosi|advertising|iklan|brand|marketing|penjualan|"
     r"sales|dagang|jualan|akuisisi|acquisition|engagement|"
     r"media|social media|content|konten|live|broadcast|siaran|"
     r"host|entertain|event|exhibition|game community",
     SOSIAL),
    (r"disiplin|tekun|teliti|telitih|jujur|ramah|sopan|rapi|"
     r"komitmen|inisiatif|tanggung jawab|patuh|sigap|cepat|"
     r"beradaptasi|adaptif|menyesuaikan diri|belajar|learner|"
     r"pembelajar|willingness|kreat|creativ|mandiri|independe|"
     r"tekanan|pressure|lembur|shift|menarik|penampilan|"
     r"ketahanan mental|passion|target|sehat|tidak bertatto|"
     r"kepribadian|logical thinking|enthusias",
     KARAKTER),
    # --- Cognitive ---
    (r"keuangan|akuntansi|akutansi|pajak|perpajakan|kas|biaya|"
     r"costing|cost|hpp|valuation|invest|kredit|credit|insurance|"
     r"asuransi|bpjs|claim|klaim|bank|reconciliation|penjurnalan|"
     r"real estate|property|properti|tender|bidding|merger|acquisition|"
     r"trade settlement|economic", "Financial skills"),
    (r"software|aplikasi|sistem|system|komputer|computer|it|"
     r"database|server|network|jaringan wifi|router|website|web|"
     r"development|developer|frontend|backend|android|ios|"
     r"programming|coding|testing|regression|penetration|security|"
     r"blockchain|crypto|big data|data integration|pytorch|tensorflow|"
     r"unity|unreal|maya|caffe|postman|sublime|zahir|accurate|accurat|"
     r"xero|hubspot|zimbra|litespeed|winform|angular|wordpress|"
     r"digital ocean|amazon web|google (earth|tag|keyword)|"
     r"microsoft teams|proyektor|handphone|motherboard|mainboard|"
     r"skematik|embedded|signal processing|pattern recognition|"
     r"computer vision|logic analyzer|cadcam|bim|cad|"
     r"articulate storyline|learning management|wms|tms|mes|"
     r"esb|omnichannel|shopee|lazada|tiktok|e-commerce|ecommerce",
     "Software (specific) skills and technical support"),
    (r"dokumen|document|arsip|filing|korespondensi|laporan|report|"
     r"penulisan|menyusun|copywrit|editor|editorial|book layout|"
     r"page layout|artikel|content production", "Writing skills"),
    (r"manajemen|management|operasional|operation|pengendalian|"
     r"pengadaan|procurement|logistik|logistic|gudang|warehouse|"
     r"stok|stock|inventory|distribusi|transport|import|export|"
     r"ekspor|impor|vendor|supplier|kontrak|contract|proyek|project|"
     r"perencanaan|planning|penjadwalan|pejadwalan|schedul|"
     r"efisiensi|optimasi|optimization|improvement|kpi|"
     r"standar|standart|sop|iso|fssc|vlk|fsc|prosedur|"
     r"sustainability|policy|kebijakan|regulasi|government|"
     r"public (service|policy)|field operation",
     "Project management skills"),
    (r"analis|analy|data|statistik|riset|research|survey|penelitian|"
     r"pemahaman|paham|pengetahuan|knowledge|teori|theory|"
     r"science|sains|kimia|chemistry|biolog|physic|fisika|matematik|"
     r"hitung|perancangan|design|desain|estimasi|interpret|"
     r"medic|medis|dokter|dentist|midwife|bidan|perawat|nurse|"
     r"gizi|nutrition|rehabilitation|terapi|therapy|apoteker|"
     r"pharmac|obat|drug|veterinary|klinik|clinic|acls|"
     r"hukum|legal|notaris|ppat|sertifik|certified",
     "Cognitive skills (narrow sense)"),
]
LEXICON_TAMBAHAN = [(re.compile(p), s) for p, s in LEXICON_TAMBAHAN]

# ---------------------------------------------------------------------------
# Penetapan langsung, satu per satu, untuk istilah metadata yang tidak
# tertangkap kedua lapis lexicon. Ditulis eksplisit supaya tiap keputusan bisa
# diperiksa pembimbing. Acuannya konvensi yang sudah dipakai pada skill hasil
# anotasi (misalnya "administrasi" -> Cognitive skills (narrow sense),
# "percaya diri" -> Character skills, "listrik" -> Hand-foot-eye coordination).
# ---------------------------------------------------------------------------
_C = "Cognitive skills (narrow sense)"
_KOM = "Computer (general) skills"
_SW = "Software (specific) skills and technical support"
_PM = "Project management skills"
_FIN = "Financial skills"
_TUL = "Writing skills"
_CS = "Customer service skills"
_PEO = "People management skills"
_HFE = "Hand-foot-eye coordination skills"
_FD = "Finger-dexterity skills"
_FIS = "Physical skills"

PENETAPAN = {
    "secretarial skills": _C, "electricity": _HFE, "general k3": _FIS,
    "telephone collection": _CS, "self confident": KARAKTER,
    "market trends": _C, "fashion stylist": _FD, "agile methodologies": _PM,
    "e commerce products": _C, "key performance indicators kpi": _PM,
    "linkedin recruiter": _PEO, "outpatient doctor": _C,
    "structural bim": _SW, "video color grading": _FD,
    "resource allocation": _PM, "psychological assessment": _C,
    "active learning": KARAKTER, "baby care": _FD,
    "image photo retouching": _FD, "environmental awareness": _C,
    "fluently read the qur an": _C, "international business": _C,
    "technology": _C, "digital sculpting": _FD, "hr policies": _PEO,
    "electrical performance test": _HFE, "video recording": _FD,
    "art direction": _C, "concept art": _FD, "fitting model": _FD,
    "audio products": _C, "cosmetology": _FD, "digital image": _FD,
    "sketmath": _C, "assistant director": _PEO,
    "assistant rumah tangga": _FD, "bisnis digital": _C, "dll": "",
    "making bolt threads": _HFE, "dol": _HFE, "clear bi cheking": _FIN,
    "user vape": _CS, "vaporista": _FD, "sopir": _HFE, "tuning": _HFE,
    "tourism products": _C, "electronic components": _HFE,
    "kemampuan pengoprasian alat ukur": _HFE, "build business": _C,
    "documen control": _TUL, "formula stability test": _C,
    "dan pekerja keras": KARAKTER, "elderycare": _FD, "spg": _CS,
    "fsc": _PM, "vlk": _PM, "produce audio material": _FD,
    "siap dipanggil sesuai kebutuhan": KARAKTER, "fresh graduate": "",
    "working under preassure": KARAKTER, "business expansion": _C,
    "bisa bekerja": "", "baik lisan maupun tulisan": SOSIAL,
    "oil and gas": _C, "pre spraying treatment": _FD, "b2g": SOSIAL,
    "staff": "", "childcare": _FD,
    "memiliki sense of business yang kuat": _C, "terutama excel": _KOM,
    "admin timbangan": _C, "operator timbangan": _HFE,
    "menguasai teknik injeksi": _C, "sim b": _HFE,
    "general skills training": _PEO, "dfd": _SW, "sport activity": _FIS,
    "kerja individu": KARAKTER, "process quality review": _PM,
    "esb order": _SW, "ganti sparepart": _HFE, "freelance": "",
    "service ac": _HFE, "horeca": _C,
    "membaca dan menafsirkan gambar konstruksi": _C,
    "aspen hysys": _SW, "feed ded": _C, "glass curtain wall": _HFE,
    "metal curtain wall": _HFE, "gamer": "", "domestic air tickets": _CS,
    "international flights": _CS, "paint tool sai": _SW, "las": _HFE,
    "mri": _C, "radiologi": _C, "mechanical and electrical bim": _SW,
    "engineer": "", "service minboard": _HFE, "spb": _CS,
    "prompt engineer": _SW, "higienis": _FD, "inshoot": _SW,
    "keluar masuk arus kas perusahaan": _FIN, "performance ads": SOSIAL,
    "affair": "",
}




def _n(t):
    t = unicodedata.normalize("NFKD", str(t))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


# ---------------------------------------------------------------------------
# Penetapan label_ner untuk baris metadata yang tidak punya padanan pada skill
# hasil anotasi. Perlu ditegaskan: ini BUKAN keluaran model NER. Tag metadata
# tidak punya rentang teks pada lowongan sehingga tidak pernah melalui
# pelabelan entitas. Nilainya ditetapkan dengan aturan di bawah, mengikuti
# batasan jenis entitas pada pedoman anotasi, dan kolom sumber_label menandai
# baris mana saja yang labelnya berasal dari penetapan aturan ini.
# ---------------------------------------------------------------------------
RX_BAHASA_PEMROGRAMAN = re.compile(
    r"\b(python|java|javascript|typescript|php|golang|kotlin|swift|"
    r"c\+\+|c#|ruby|scala|rust|dart|perl|r language|matlab|vba)\b")
RX_PERKAKAS = re.compile(
    r"\b(microsoft|ms office|ms excel|excel|word|powerpoint|outlook|teams|"
    r"google (sheets|docs|drive|earth|tag|keyword|ads|analytics)|"
    r"autocad|sketchup|solidworks|revit|photoshop|illustrator|indesign|"
    r"corel|figma|canva|adobe|premiere|after effects|blender|maya|unity|"
    r"unreal|zbrush|paint tool sai|sap|odoo|tally|zahir|accurate|accurat|"
    r"xero|hubspot|zimbra|wordpress|angular|litespeed|postman|sublime|"
    r"pytorch|tensorflow|aws|amazon web|digital ocean|linkedin|"
    r"shopee|lazada|tiktok|aspen hysys|inshoot|articulate storyline|"
    r"sql|mysql|erp|crm|hris|wms|tms|mes|cad|bim)\b")
RX_SOFT = re.compile(
    r"teamwork|team work|collaboration|communicat|negotiation|leadership|"
    r"interpersonal|public speaking|presentation|persuasion|empathy|"
    r"active listening|discipline|diligen|honest|integrity|initiative|"
    r"adaptab|flexib|positive attitude|hardworking|responsib|patience|"
    r"time management|under pressure|preassure|problem solving|"
    r"critical thinking|logical thinking|creativ|willingness to learn|"
    r"self motivat|self confident|work ethic|komunikasi|kerjasama|"
    r"kerja sama|disiplin|tekun|teliti|telitih|jujur|ramah|sopan|"
    r"tanggung jawab|inisiatif|beradaptasi|menyesuaikan diri|"
    r"percaya diri|kreat|mandiri|tekanan|pembelajar|komitmen|"
    r"kepribadian|penampilan|pekerja keras|kerja keras|kerja individu|"
    r"sigap|patuh|cekatan|bertanggung jawab|niat untuk belajar|"
    r"ketahanan mental|target oriented|target orented|target oridented")


def tetapkan_label_ner(nama):
    k = _n(nama)
    if RX_BAHASA_PEMROGRAMAN.search(k):
        return "PROGRAMMING_LANGUAGE"
    if RX_PERKAKAS.search(k):
        return "TOOL"
    if RX_SOFT.search(k):
        return "SOFT_SKILL"
    return "SKILL"


def klasifikasi_lexicon(nama):
    """Kembalikan (kategori, subkategori, lapis) untuk sebuah istilah."""
    k = _n(nama)
    for rx, sub in LEXICON:
        if rx.search(k):
            return BROAD[sub], sub, "lexicon kata kunci"
    for rx, sub in LEXICON_TAMBAHAN:
        if rx.search(k):
            return BROAD[sub], sub, "lexicon kata kunci lapis kedua"
    sub = PENETAPAN.get(k)
    if sub:
        return BROAD[sub], sub, "penetapan langsung per istilah"
    return "", "", ""


# Konsep yang dipakai untuk menandai dugaan pengulangan makna antara istilah
# metadata berbahasa Inggris dan skill hasil anotasi berbahasa Indonesia pada
# lowongan yang sama. Ditulis eksplisit; daftar ini tidak mengklaim lengkap.
KONSEP_SAMA = {
    "komunikasi": (["communication", "communicative"],
                   ["komunikasi", "komunikatif", "berkomunikasi"]),
    "kerja sama tim": (["teamwork", "team work", "collaboration"],
                       ["kerja sama", "kerjasama", "tim", "teamwork"]),
    "layanan pelanggan": (["customer service", "customer relations",
                           "client service"],
                          ["pelayanan pelanggan", "customer service",
                           "melayani pelanggan", "layanan pelanggan"]),
    "penjualan": (["sales"], ["penjualan", "sales", "menjual"]),
    "pemasaran": (["marketing"], ["pemasaran", "marketing"]),
    "negosiasi": (["negotiation"], ["negosiasi", "negoisasi"]),
    "kepemimpinan": (["leadership"], ["kepemimpinan", "leadership", "memimpin"]),
    "microsoft excel": (["microsoft excel", "ms excel"],
                        ["excel", "microsoft excel", "ms excel"]),
    "microsoft office": (["microsoft office", "ms office"],
                         ["microsoft office", "ms office"]),
    "administrasi": (["administration", "administrative"], ["administrasi"]),
    "kasir": (["cashier"], ["kasir"]),
    "mengemudi": (["driving", "safe driving"],
                  ["mengemudi", "menyetir", "driving", "berkendara"]),
    "teliti": (["attention to detail", "detail oriented", "thorough"],
               ["teliti", "ketelitian", "detail"]),
    "disiplin": (["discipline", "disciplined"], ["disiplin"]),
    "kerja di bawah tekanan": (["working under pressure", "work under pressure"],
                               ["bawah tekanan", "dibawah tekanan"]),
    "pemecahan masalah": (["problem solving"],
                          ["problem solving", "pemecahan masalah",
                           "memecahkan masalah"]),
    "public speaking": (["public speaking"],
                        ["public speaking", "berbicara di depan umum"]),
    "bahasa inggris": (["english"], ["bahasa inggris", "english"]),
}


def bangun(db_path, json_path):
    con = sqlite3.connect(db_path)
    anotasi = pd.read_sql("""
        SELECT js.job_id AS id_lowongan, s.name AS skill, s.label AS label_ner,
               s.escudero_broad_category AS kategori_escudero,
               s.escudero_subcategory AS subkategori_escudero
        FROM job_skills js JOIN skills s ON s.id = js.skill_id""", con)
    anotasi["sumber_skill"] = "anotasi teks"
    anotasi["sumber_label"] = "hasil anotasi dan klasifikasi Escudero"

    peta_skill = {}
    for nm, lab, kat, sub in con.execute(
            "SELECT name, label, escudero_broad_category, escudero_subcategory "
            "FROM skills"):
        peta_skill.setdefault(_n(nm), (lab, kat, sub))
    pekerjaan = pd.read_sql(
        "SELECT id AS id_lowongan, url AS _url, title AS judul_pekerjaan,"
        " kbji_golongan_pokok_nama AS jabatan_kbji FROM jobs", con)
    con.close()

    by_url = dict(zip(pekerjaan._url, pekerjaan.id_lowongan))
    set_anotasi = collections.defaultdict(set)
    for jid, nm in zip(anotasi.id_lowongan, anotasi.skill):
        set_anotasi[jid].add(_n(nm))

    with open(json_path, encoding="utf-8") as f:
        gold = json.load(f)

    baris = []
    for r in gold:
        jid = by_url.get(r["url"])
        if jid is None:
            continue
        for x in str((r.get("data") or {}).get("skills") or "").split(","):
            x = x.strip()
            if x:
                baris.append((jid, x))
    metadata = pd.DataFrame(baris, columns=["id_lowongan", "skill"])

    # Baris metadata yang namanya sama persis dengan skill anotasi pada
    # lowongan yang sama tidak digandakan; baris anotasinya yang ditandai.
    kembar = {(j, _n(s)) for j, s in zip(metadata.id_lowongan, metadata.skill)
              } & {(j, _n(s)) for j, s in zip(anotasi.id_lowongan, anotasi.skill)}
    anotasi.loc[[(j, _n(s)) in kembar
                 for j, s in zip(anotasi.id_lowongan, anotasi.skill)],
                "sumber_skill"] = "kedua sumber"
    metadata = metadata[[(j, _n(s)) not in kembar
                         for j, s in zip(metadata.id_lowongan, metadata.skill)]].copy()

    lab_l, kat_l, sub_l, src_l, ulang_l = [], [], [], [], []
    for jid, nama in zip(metadata.id_lowongan, metadata.skill):
        k = _n(nama)
        warisan = peta_skill.get(k)
        if warisan:
            lab, kat, sub = warisan
            src = "diwarisi dari skill hasil anotasi yang namanya sama"
        else:
            kat, sub, lapis = klasifikasi_lexicon(nama)
            if kat:
                lab = tetapkan_label_ner(nama)
                src = (f"Escudero: {lapis}; label_ner: penetapan aturan "
                       "(bukan keluaran model NER)")
            else:
                lab = ""
                src = ("bukan keterampilan -- tidak diberi label "
                       "(misalnya \"Dll\", \"Staff\", \"Fresh graduate\")")
        lab_l.append(lab); kat_l.append(kat); sub_l.append(sub); src_l.append(src)

        # Dugaan pengulangan makna dengan skill anotasi di lowongan yang sama.
        ada = set_anotasi.get(jid, set())
        tanda = ""
        for konsep, (en, idn) in KONSEP_SAMA.items():
            if any(e in k for e in en) and any(
                    any(i in s for s in ada) for i in idn):
                tanda = konsep
                break
        ulang_l.append(tanda)

    metadata["label_ner"] = lab_l
    metadata["kategori_escudero"] = kat_l
    metadata["subkategori_escudero"] = sub_l
    metadata["sumber_skill"] = "metadata situs"
    metadata["sumber_label"] = src_l
    metadata["dugaan_pengulangan_makna"] = ulang_l
    anotasi["dugaan_pengulangan_makna"] = ""

    gab = pd.concat([anotasi, metadata], ignore_index=True)
    gab = gab.merge(pekerjaan[["id_lowongan", "judul_pekerjaan", "jabatan_kbji"]],
                    on="id_lowongan", how="left")
    gab = gab[["id_lowongan", "judul_pekerjaan", "jabatan_kbji", "skill",
               "sumber_skill", "label_ner", "kategori_escudero",
               "subkategori_escudero", "sumber_label",
               "dugaan_pengulangan_makna"]]
    return gab.sort_values(["id_lowongan", "sumber_skill", "skill"]
                           ).reset_index(drop=True)


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else "db.sqlite"
    js = sys.argv[2] if len(sys.argv) > 2 else "gold.json"
    g = bangun(db, js)
    print("total baris:", f"{len(g):,}")
    print(g.sumber_skill.value_counts().to_string())
    print()
    m = g[g.sumber_skill == "metadata situs"]
    print("baris metadata:", f"{len(m):,}")
    print(m.sumber_label.value_counts().to_string())
    print()
    print("kategori Escudero terisi:",
          f"{(g.kategori_escudero.astype(str).str.len() > 0).sum():,} dari {len(g):,}")
    print()
    print("dugaan pengulangan makna:",
          f"{(g.dugaan_pengulangan_makna.astype(str).str.len() > 0).sum():,} baris")
    print(g[g.dugaan_pengulangan_makna != ""].dugaan_pengulangan_makna
          .value_counts().to_string())
