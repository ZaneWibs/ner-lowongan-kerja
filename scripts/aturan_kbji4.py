"""
Aturan pemetaan judul pekerjaan -> subgolongan KBJI 2014 (kode 4 digit)
=======================================================================
Setiap aturan berbentuk:
    (pola_regex, kode_terbaik, {golongan_pokok: kode_alternatif}, catatan)

- pola_regex dicocokkan pada judul yang sudah dinormalkan (huruf kecil,
  tanda baca diganti spasi, "staf" -> "staff").
- kode_terbaik  : subgolongan KBJI 2014 yang paling sesuai dengan fungsi
  pekerjaan menurut uraian tugas pada dokumen KBJI 2014 (BPS).
- alternatif    : kode yang MASIH SAH di golongan pokok lain, dipakai bila
  golongan pokok lowongan sudah ditetapkan (dan sebagian sudah ditelaah
  pembimbing) di golongan tersebut. Dengan begitu kode 4 digit tetap
  bersarang di golongan pokok yang sudah disepakati.
- Bila golongan pokok yang ada tidak punya kode yang sah untuk pekerjaan itu,
  judul TIDAK dipaksa masuk: ditandai sebagai konflik untuk diputuskan
  pembimbing.

KBJI 2014 adalah terjemahan ISCO-08 dan tidak memuat istilah baru seperti
content creator, KOL specialist, atau host live streaming. Untuk istilah
seperti itu kodenya dipilih berdasarkan kesamaan FUNGSI dengan uraian tugas
KBJI, dan dasarnya dicatat pada kolom catatan.

Urutan aturan penting: yang lebih spesifik ditaruh lebih dulu.
"""

ATURAN = [
    # =====================================================================
    # Judul terlalu umum -- sengaja tidak diklasifikasikan
    # =====================================================================
    (r"^(staff|karyawan|pegawai|crew|tim|team|freelance|freelancer|part time|"
     r"magang|intern|internship|lowongan|pekerja|general|umum|all position|"
     r"various position|staff umum|staff kantor umum)$", None, {},
     "Judul tidak menyebut fungsi pekerjaan."),
    (r"^(management trainee|mt|officer development program|odp|graduate "
     r"development program|trainee)$", None, {},
     "Program pelatihan; bidang kerjanya tidak disebut di judul."),
    (r"^(supervisor|spv|koordinator|coordinator|team leader|leader|kepala|"
     r"head|manager|manajer|asisten manager|assistant manager|"
     r"operasional|staff operasional|operational staff|operation staff|"
     r"staff operational)$", None, {},
     "Judul hanya menyebut jenjang jabatan atau 'operasional', tanpa bidang kerjanya."),

    # =====================================================================
    # Tambahan (putaran 2): sinonim dan salah ketik yang sering muncul
    # =====================================================================
    (r"\b(human capital|hcbp|hc regional|hc development|hris)\b(?!.*\b(manager|head)\b)",
     "2423", {4: "4416"}, "Profesional personalia (human capital = SDM)."),
    (r"\b(human capital manager|hc manager)\b", "1212", {}, "Manajer sumber daya manusia."),
    (r"\b(livestreamer|life streaming|live tiktok|e commerce livestreamer)\b", "5242",
     {2: "2656"}, "Peraga penjualan (siaran langsung penjualan)."),
    (r"\b(nailist|makeup artis|karyawati salon)\b", "5142", {}, "Perawat kecantikan."),
    (r"\b(kru outlet|kru konter|kru store|karyawati outlet|karyawan outlet|karyawan booth|"
     r"jaga konter|jaga stand|penjaga konter|penjaga lapak|booth keeper|shopkeeper|"
     r"shop attendant|staff outlet|store associate|retail associate|greeter)\b",
     "5223", {}, "Asisten penjualan toko."),
    (r"\b(front liner|frontliner)\b", "4226", {}, "Resepsionis."),
    (r"\b(quliaty control)\b", "7543", {3: "3119"}, "Penguji kualitas produk (salah ketik 'quality')."),
    (r"\b(tellemarketing|telemarketing)\b", "5244", {4: "4222"}, "Telemarketing."),
    (r"\b(officebo y|officeboy)\b", "9112", {}, "Office boy."),
    (r"\b(casier|kasir)\b", "5230", {}, "Kasir."),
    (r"\b(supervisor|spv|leader|line leader|group leader|kepala regu)\b.*\b(cutting|embroidery|"
     r"machining|manufaktur|line|stockfit|sewing|assembling|boiler)\b|^line leader$",
     "3122", {1: "1321"}, "Supervisor manufaktur."),
    (r"\b(kepala bengkel|kepala bagian bengkel|head service|supervisor body repair)\b",
     "7231", {1: "1439"}, "Mekanik kendaraan (kepala bengkel)."),
    (r"\b(information technology|it service|it development|it generalist|it operational|"
     r"it system|it middleware|it data platform)\b", "3512", {2: "2512", 1: "1330"},
     "Teknisi pendukung TIK."),
    (r"^(?!.*\b(customer service|cs|admin|administrasi)\b).*\b(content planner|content strategist|content specialist|content ai planner|"
     r"tiktok strategist|creative digital content|brand activation|marketplace|"
     r"digital advertising|online marketplace|b2b specialist|creative media)\b",
     "2431", {1: "1221"}, "Profesional periklanan dan pemasaran."),
    (r"\b(multimedia|3d generalist|rotoscoping)\b", "2166", {}, "Perancang grafis dan multimedia."),
    (r"\b(regulatory|regulasi)\b", "2619", {}, "Profesional hukum YTDL (urusan regulasi)."),
    (r"\b(relationship manager|funding officer|financing officer|bancassurance|"
     r"credit reviewer)\b", "3312", {1: "1346", 2: "2412"}, "Petugas kredit dan pinjaman."),
    (r"\b(demand planning|demand planner|logistics transportation planner|planner logistik)\b",
     "4322", {2: "2141"}, "Juru tata usaha produksi (perencanaan)."),
    (r"\b(logistic officer|logistics officer|staff logistik|staf logistik|"
     r"staf distribusi|logistic claim)\b", "4323", {}, "Juru tata usaha transportasi/logistik."),
    (r"\b(inputer|data process|data management)\b", "4132", {}, "Petugas entri data."),
    (r"\b(asisten laboratorium|staff laboratorium|technical lab)\b", "3111", {}, "Teknisi laboratorium."),
    (r"\b(pengawas gizi)\b", "2265", {3: "3259"}, "Ahli gizi."),
    (r"\b(paramedis)\b", "3256", {}, "Asisten medis."),
    (r"\b(refraksi|optisi)\b", "3254", {}, "Optisien."),
    (r"\b(pelayanan apotek|karyawan apotek|staf pelayanan apotek)\b", "3213",
     {5: "5223"}, "Asisten apoteker / pelayan toko obat."),
    (r"\b(penjaga lansia)\b", "5322", {}, "Pekerja perawatan pribadi di rumah."),
    (r"\b(scaffolder|tenaga kerja pada ketinggian)\b", "7119", {9: "9313"},
     "Pekerja kerangka bangunan YTDL."),
    (r"\b(tukang aluminium|fitter|jointer ftth)\b", "7126", {3: "3115"}, "Pekerja instalasi (pemasangan)."),
    (r"\b(potong kain|cutting garmen|potong pola)\b", "7532", {}, "Pemotong pola garmen."),
    (r"\b(soundman)\b", "3521", {}, "Teknisi audio-visual."),
    (r"\b(caddy|pramugolf)\b", "3422", {5: "5169"}, "Kru olahraga."),
    (r"\b(hostess|usher|vip service)\b", "5169", {}, "Tenaga usaha jasa perorangan YTDL."),
    (r"\b(sorter|sortir)\b", "9334", {}, "Buruh penata barang."),
    (r"\b(loper|riders|staff pengantaran|pengantaran)\b", "9621", {8: "8321"}, "Kurir."),
    (r"\b(tukang poles|detailing|body painting|body repair)\b", "7132", {}, "Pekerja cat semprot."),
    (r"\b(staff akademik|staf akademik)\b", "4110", {2: "2359"}, "Tenaga perkantoran (akademik)."),
    (r"\b(ehs|qms|quality management system)\b", "2263", {3: "3257"},
     "Ahli kesehatan dan keselamatan kerja / sistem mutu."),

    # =====================================================================
    # 1 MANAJER
    # =====================================================================
    (r"\b(general manager|direktur|director|ceo|coo|chief executive|"
     r"chief operating|presiden direktur|managing director|country manager)\b",
     "1120", {}, "Pimpinan eksekutif."),
    (r"\b(finance|keuangan|accounting|akuntansi|treasury|tax|pajak)\b.*\b(manager|manajer|head|kepala)\b|"
     r"\b(manager|manajer|head|kepala)\b.*\b(finance|keuangan|accounting|akuntansi|treasury|tax|pajak)\b|"
     r"\bfinance controller\b|\bcfo\b", "1211", {}, "Manajer keuangan."),
    (r"\b(hr|hrd|hrga|human resources?|sdm|personalia|people|talent)\b.*\b(manager|manajer|head|kepala|supervisor|spv|koordinator|coordinator|leader)\b|"
     r"\b(manager|manajer|head|kepala|supervisor|spv|koordinator)\b.*\b(hr|hrd|hrga|human resources?|sdm|personalia)\b",
     "1212", {}, "Manajer sumber daya manusia."),
    (r"\b(sales|penjualan|marketing|pemasaran|brand|business development|bisnis|"
     r"commercial|komersial|digital marketing|growth|e commerce|ecommerce|"
     r"account)\b.*\b(manager|manajer|head|kepala|direktur)\b|"
     r"\b(manager|manajer|head|kepala)\b.*\b(sales|penjualan|marketing|pemasaran|"
     r"brand|business development|commercial)\b|\barea sales manager\b|\basm\b|\brsm\b",
     "1221", {}, "Manajer penjualan dan pemasaran."),
    (r"\b(public relation|pr|humas|communication|komunikasi|advertising)\b.*\b(manager|manajer|head)\b",
     "1222", {}, "Manajer periklanan dan hubungan masyarakat."),
    (r"\b(r d|research|riset|penelitian|product development)\b.*\b(manager|manajer|head|kepala)\b",
     "1223", {}, "Manajer penelitian dan pengembangan."),
    (r"\b(produksi|production|plant|pabrik|factory|manufaktur|manufacturing)\b.*\b(manager|manajer|head|kepala)\b|"
     r"\b(kepala|manager|manajer|head)\b.*\b(produksi|production|pabrik|plant)\b",
     "1321", {3: "3122"}, "Manajer manufaktur."),
    (r"\b(site manager|construction manager|project manager konstruksi|"
     r"manajer proyek konstruksi|kepala proyek|pimpinan proyek|site engineer manager)\b",
     "1323", {}, "Manajer konstruksi."),
    (r"\b(gudang|warehouse|logistik|logistic|logistics|supply chain|purchasing|"
     r"procurement|pengadaan|distribusi|distribution|inventory|ppic|scm)\b.*\b(manager|manajer|head|kepala)\b|"
     r"\b(kepala|manager|manajer|head)\b.*\b(gudang|warehouse|logistik|logistic|"
     r"purchasing|procurement|pengadaan|distribusi|supply chain)\b",
     "1324", {}, "Manajer pengadaan, distribusi dan YBDI (termasuk manajer gudang)."),
    (r"\b(it|teknologi informasi|ict|technology|engineering manager|cto)\b.*\b(manager|manajer|head|kepala)\b",
     "1330", {}, "Manajer layanan teknologi informasi dan komunikasi."),
    (r"\b(klinik|clinic|rumah sakit|hospital|medical)\b.*\b(manager|manajer|kepala|head)\b",
     "1342", {}, "Manajer jasa kesehatan."),
    (r"\b(kepala sekolah|principal|school manager|academic manager|manajer akademik)\b",
     "1345", {}, "Manajer pendidikan."),
    (r"\b(hotel manager|manajer hotel|front office manager|resort manager)\b",
     "1411", {}, "Manajer hotel."),
    (r"\b(restaurant|restoran|resto|outlet|cafe|kafe|f b|kitchen|catering)\b.*\b(manager|manajer|kepala|head)\b|"
     r"\b(kepala|manager|manajer)\b.*\b(restoran|restaurant|resto|outlet|cafe|kafe)\b",
     "1412", {5: "5131"}, "Manajer penyediaan makanan dan minuman."),
    (r"\b(store manager|manajer toko|kepala toko|branch store manager|"
     r"retail manager|shop manager|kepala cabang toko)\b",
     "1420", {}, "Manajer perdagangan besar dan eceran."),
    (r"\b(project manager|manajer proyek|program manager|product manager|"
     r"operation manager|operations manager|operational manager|manager operasional|"
     r"manajer operasional|branch manager|kepala cabang|manager cabang|"
     r"area manager|regional manager|unit head|business unit head|"
     r"general affair manager|ga manager|office manager)\b",
     "1219", {}, "Manajer pelayanan bisnis dan administrasi YTDL."),

    # =====================================================================
    # Supervisor dan koordinator (sebelum aturan bidang)
    # =====================================================================
    (r"\b(supervisor|spv|koordinator|coordinator|leader|kepala regu|mandor|foreman)\b.*"
     r"\b(produksi|production|pabrik|factory|sewing|jahit|quality|qc|qa|maintenance|"
     r"mekanik|teknik|engineering|assembly|perakitan|finishing)\b|"
     r"\b(produksi|production|sewing|quality|qc|engineering|maintenance)\b.*\b(supervisor|spv|leader|koordinator)\b",
     "3122", {1: "1321"}, "Supervisor manufaktur."),
    (r"\b(supervisor|spv|koordinator|mandor|pengawas)\b.*\b(proyek|konstruksi|lapangan|"
     r"bangunan|sipil|site)\b|\bsite supervisor\b|\bpengawas lapangan\b",
     "3123", {1: "1323"}, "Supervisor konstruksi."),
    (r"\b(supervisor|spv|leader|koordinator|kepala)\b.*\b(toko|store|outlet|kasir|"
     r"retail|minimarket|supermarket|counter|showroom)\b|"
     r"\b(store|toko|outlet|retail)\b.*\b(supervisor|spv|leader|koordinator)\b",
     "5222", {1: "1420"}, "Supervisor toko."),
    (r"\b(supervisor|spv|leader|koordinator|captain)\b.*\b(restoran|restaurant|resto|"
     r"kitchen|dapur|cafe|f b|waiter|bar)\b|\bcaptain\b",
     "5131", {1: "1412"}, "Pengawas pelayanan makanan (pramusaji senior)."),
    (r"\b(supervisor|spv|koordinator|kepala)\b.*\b(housekeeping|kebersihan|cleaning)\b",
     "5151", {1: "1439"}, "Pengawas kebersihan dan kerumahtanggaan."),
    (r"\b(supervisor|spv|koordinator|leader|kepala)\b.*\b(admin|administrasi|kantor|office|"
     r"general affair|ga|finance|accounting|keuangan|collection|customer service|cs)\b",
     "3341", {1: "1219"}, "Supervisor kantor."),
    (r"\b(supervisor|spv|koordinator|coordinator|leader|lead|kepala|head|chief|manager|manajer)\b.*"
     r"\b(finance|keuangan|accounting|akuntansi|tax|pajak)\b|"
     r"\b(finance|accounting|keuangan|akuntansi)\b.*\b(supervisor|spv|koordinator|coordinator|leader)\b",
     "1211", {3: "3313", 4: "4311"}, "Manajer keuangan (penyelia bidang keuangan)."),
    (r"\b(supervisor|spv|koordinator|coordinator|leader|kepala|head|chief|manager|manajer)\b.*"
     r"\b(qc|qa|quality)\b|\b(qc|qa|quality)\b.*\b(manager|manajer|supervisor|spv|koordinator|"
     r"coordinator|head|leader)\b", "1321", {3: "3122", 7: "7543"},
     "Manajer manufaktur (penanggung jawab mutu)."),
    (r"\b(supervisor|spv|koordinator|coordinator|leader|kepala|chief)\b.*\b(teknisi|technician|"
     r"maintenance|mekanik|bengkel)\b|\b(maintenance|teknisi)\b.*\b(chief|supervisor|spv|leader|koordinator)\b",
     "3122", {1: "1321", 7: "7233"}, "Supervisor manufaktur (pemeliharaan)."),
    (r"\b(head kitchen|kitchen leader|kepala dapur|kitchen supervisor|kitchen manager|"
     r"head chef|chef de cuisine|executive chef|hub kitchen)\b", "3434",
     {1: "1412", 5: "5120"}, "Chef (kepala dapur)."),
    (r"\b(supervisor|spv|koordinator|coordinator|leader|lead|head|manager|manajer)\b.*"
     r"\b(kol|key opinion leader|community|affiliate|social media|content|creative|"
     r"digital|marketplace|e commerce|ecommerce|brand|branding|market research)\b|"
     r"\b(kol|community|social media|content|creative|marketplace|ecommerce|e commerce|brand)\b.*"
     r"\b(manager|supervisor|spv|leader|lead|koordinator|coordinator|head)\b",
     "1221", {2: "2431", 3: "3322"}, "Manajer penjualan dan pemasaran (bidang pemasaran digital)."),
    (r"\b(supervisor|spv|koordinator|leader)\b.*\b(gudang|warehouse|logistik|logistic|"
     r"delivery|distribusi|ekspedisi)\b|\b(warehouse|gudang)\b.*\b(supervisor|spv|leader|koordinator)\b",
     "4321", {1: "1324"}, "Penyelia pergudangan (KBJI tidak punya kode supervisor gudang; "
     "ditempatkan pada juru tata usaha pergudangan)."),
    (r"\b(supervisor|spv|koordinator|leader)\b.*\b(sales|penjualan|marketing|area|canvas)\b|"
     r"\b(sales|marketing)\b.*\b(supervisor|spv|leader|koordinator)\b",
     "3322", {1: "1221", 5: "5222"}, "Penyelia penjualan."),
    (r"\b(supervisor|spv|koordinator|leader)\b.*\b(security|keamanan|satpam)\b|\bdanru\b|\bchief security\b",
     "5414", {1: "1439"}, "Penjaga keamanan (kepala regu)."),

    # --- TIK khusus yang memuat kata "administrator", ditaruh sebelum blok admin
    (r"\b(system administrator|sysadmin|database administrator|network administrator|"
     r"server administrator|it administrator)\b", "2522", {3: "3513"},
     "Pengelola sistem."),
    # --- admin berdasarkan bidang (dipindah ke depan supaya "Admin HR", "Admin QC",
    #     "Admin Purchasing" dsb. tidak tertangkap aturan bidangnya lebih dulu)
    (r"\b(admin|administrasi|administration|administrator|staff administrasi|clerk)\b.*"
     r"\b(gudang|warehouse|logistik|logistic|logistics|stok|stock|inventory|inventori|"
     r"delivery|pengiriman|ekspedisi|expedisi|distribusi|timbangan|packing|"
     r"material|sparepart|spare part)\b|"
     r"\b(gudang|warehouse|logistik|logistic|stok|stock|inventory)\b.*\b(admin|administrasi)\b|"
     r"\b(checker|stock keeper|storekeeper|storeman|store keeper|stockist|"
     r"inventory control|inventory staff|stock opname|checker gudang)\b",
     "4321", {9: "9334"}, "Juru tata usaha pergudangan."),
    (r"\b(admin|administrasi|clerk)\b.*\b(produksi|production|ppic|pabrik|factory|"
     r"qc|quality|engineering|teknik|maintenance|project|proyek)\b",
     "4322", {3: "4322"}, "Juru tata usaha produksi."),
    (r"\b(admin|administrasi|clerk)\b.*\b(transport|transportasi|armada|fleet|"
     r"pool|dispatch|ekspedisi)\b|\b(dispatcher|dispatch)\b",
     "4323", {3: "4323"}, "Juru tata usaha transportasi."),
    (r"\b(admin|administrasi|clerk)\b.*\b(payroll|penggajian|gaji)\b|\bpayroll\b",
     "4313", {3: "3313"}, "Juru tata usaha penggajian."),
    (r"\b(admin|administrasi|clerk)\b.*\b(finance|keuangan|accounting|akuntansi|"
     r"fakturis|faktur|invoice|billing|tagihan|pajak|tax|kasir|ar|ap|piutang|hutang|"
     r"account payable|account receivable)\b|"
     r"\b(finance|keuangan|accounting|akuntansi|bookkeeper|pembukuan|"
     r"fakturis|billing|account payable|account receivable|accounts payable|"
     r"accounts receivable|ap staff|ar staff|tax|pajak|treasury|finance accounting)\b",
     "4311", {3: "3313", 2: "2411"}, "Juru tata usaha akuntansi dan pembukuan."),
    (r"\b(admin|administrasi|clerk)\b.*\b(hr|hrd|hrga|personalia|sdm|bpjs|"
     r"recruitment|karyawan|personnel)\b", "4416", {3: "3333"},
     "Juru tata usaha personalia."),
    (r"\b(general affair|ga|hrga|general affairs)\b", "4110", {3: "3341"},
     "Tenaga perkantoran umum (urusan umum)."),
    (r"\b(data entry|entri data|input data|pendataan|operator komputer|"
     r"admin data|data input|operator data)\b", "4132", {}, "Petugas entri data."),
    (r"\b(arsip|archive|filing|document control|dokumen control|doc control|"
     r"document controller|kearsipan)\b", "4415", {3: "3343"},
     "Juru tata usaha pengarsipan."),
    (r"\b(sekretaris|secretary)\b", "4120", {3: "3343"}, "Sekretaris."),
    (r"\b(admin|administrasi|administration|administrator|administratif|"
     r"office staff|staff kantor|staf kantor|clerical|tata usaha|tu|"
     r"admin staff|staff admin|back office|backoffice)\b",
     "4110", {}, "Tenaga perkantoran umum."),


    # =====================================================================
    # 2 PROFESIONAL
    # =====================================================================
    # --- TIK
    (r"\b(data scientist|data analyst|analis data|business intelligence|bi analyst|"
     r"data analytics|statistisi|statistician|actuary|aktuaris)\b",
     "2120", {3: "3314"}, "Ahli statistika; analis data menurut fungsi analisis kuantitatif."),
    (r"\b(data engineer|database|dba|etl)\b", "2521", {3: "3511"}, "Pengelola dan perancang database."),
    (r"\b(system analyst|systems analyst|analis sistem|it business analyst|"
     r"solution architect|it analyst|erp consultant|sap consultant|functional consultant)\b",
     "2511", {}, "Analis sistem."),
    (r"\b(devops|cloud engineer|system administrator|sysadmin|site reliability|sre|"
     r"infrastructure engineer|it infrastructure)\b", "2522", {3: "3513"}, "Pengelola sistem."),
    (r"\b(network engineer|jaringan engineer|network administrator|security engineer|"
     r"cyber security|keamanan siber|noc engineer)\b", "2523", {3: "3513"},
     "Profesional jaringan komputer."),
    (r"\b(front end|frontend|web developer|web programmer|wordpress|web designer|"
     r"pengembang web|shopify developer)\b", "2513", {3: "3514"}, "Pengembang web dan multimedia."),
    (r"\b(game developer|game programmer|animator|motion graphic|motion designer|3d artist|"
     r"3d modeller|3d modeler)\b", "2166", {3: "3435"}, "Perancang grafis dan multimedia."),
    (r"\b(mobile developer|android|ios developer|flutter|react native|"
     r"software engineer|software developer|programmer|backend|back end|full stack|"
     r"fullstack|developer|pengembang perangkat lunak|it programmer|ai engineer|"
     r"machine learning|ml engineer|embedded)\b", "2512", {3: "3512"},
     "Pengembang perangkat lunak."),
    (r"\b(qa engineer|software tester|qa tester|test engineer|quality assurance engineer)\b",
     "2519", {3: "3512"}, "Analis dan pengembang perangkat lunak YTDL (penguji perangkat lunak)."),
    (r"\b(ui ux|uiux|ui designer|ux designer|product designer digital|ux researcher)\b",
     "2166", {}, "Perancang grafis dan multimedia (desain antarmuka)."),
    (r"\b(it support|it helpdesk|helpdesk|help desk|technical support|tech support|"
     r"it staff|staff it|admin it|it officer|it technician|teknisi it)\b|^it$",
     "3512", {2: "2529", 4: "4110"}, "Teknisi pendukung pengguna TIK."),
    # --- desain, media, konten
    (r"^(?!.*\b(interior|fashion|busana|produk|product|pakaian|baju|furniture|landscape|"
     r"taman|ui|ux)\b).*\b(graphic designer|desain grafis|desainer grafis|design grafis|graphic design|"
     r"visual designer|designer grafis|layouter|illustrator|ilustrator|"
     r"desainer|designer|desain|design)\b", "2166", {3: "3435"},
     "Perancang grafis dan multimedia."),
    (r"\b(video editor|editor video|film editor|video producer|produser|producer|"
     r"sutradara|director of photography|creative director)\b", "2654", {3: "3521"},
     "Produser, sutradara dan penyunting film (ISCO 2654 mencakup film/video editor)."),
    (r"\b(videographer|videografer|camera person|cameraman|kameramen|"
     r"sound engineer|audio engineer|lighting|broadcast|multimedia staff|"
     r"operator multimedia|teknisi audio)\b", "3521", {2: "2654"},
     "Teknisi penyiaran dan audio-visual."),
    (r"\b(photographer|fotografer|fotografer fashion)\b", "3431", {2: "2651"}, "Fotografer."),
    (r"\b(copywriter|content writer|penulis|writer|script writer|scriptwriter|"
     r"technical writer|editor naskah|proofreader|editor)\b", "2641", {},
     "Pengarang dan penulis YBDI."),
    (r"\b(jurnalis|journalist|wartawan|reporter|redaktur)\b", "2642", {}, "Wartawan."),
    (r"\b(penerjemah|translator|interpreter|juru bahasa)\b", "2643", {3: "3435"},
     "Penerjemah dan profesional bahasa."),
    (r"\b(host live|live host|host live streaming|live streaming|live stream|"
     r"streamer|host tiktok|host shopee|host jualan|livestream)\b", "5242",
     {2: "2656", 3: "3435"},
     "Peraga penjualan: memperagakan dan menjual produk secara langsung. "
     "Bila fungsinya penyiar/pembawa acara murni, alternatifnya 2656."),
    (r"\b(mc|master of ceremony|pembawa acara|presenter|penyiar|announcer|news anchor|"
     r"host|talent|talent live)\b", "2656", {5: "5242", 3: "3435"},
     "Penyiar radio, televisi dan media lainnya."),
    (r"\b(content creator|kreator konten|konten kreator|creator|tiktok creator|"
     r"video content creator|ugc)\b", "2641", {5: "5242", 3: "3435"},
     "KBJI tidak memuat content creator. Ditempatkan pada pengarang dan penulis "
     "YBDI (2641) yang mencakup 'penulis media interaktif' (2641.04)."),
    # --- pemasaran & penjualan profesional
    (r"\b(kol|key opinion leader|affiliate|influencer|social media|sosial media|"
     r"sosmed|seo|sem|digital marketing|marketing digital|performance marketing|"
     r"ads specialist|advertiser|e commerce specialist|ecommerce specialist|"
     r"marketplace specialist|crm specialist|brand specialist|brand executive|"
     r"marketing specialist|marketing analyst|market research|marketing strategist|"
     r"growth|campaign|community specialist|community manager)\b",
     "2431", {},
     "Profesional periklanan dan pemasaran."),
    (r"\b(public relation|public relations|humas|pr officer|pr specialist|"
     r"corporate communication|marketing communication|marcomm|marcom)\b",
     "2432", {}, "Profesional hubungan masyarakat."),
    (r"\b(sales engineer|technical sales|medical representative|medrep|"
     r"product specialist|sales alat kesehatan|sales alkes|application specialist)\b",
     "2433", {3: "3322"}, "Profesional penjualan produk teknik dan kesehatan."),
    (r"\b(it sales|software sales|saas sales|sales it)\b", "2434", {3: "3322"},
     "Profesional penjualan produk TIK."),
    # --- bisnis & administrasi
    (r"\b(auditor|audit|internal audit)\b", "2411", {3: "3313", 4: "4311"}, "Akuntan (auditor)."),
    (r"\b(akuntan|accountant|tax consultant|konsultan pajak|tax specialist)\b",
     "2411", {3: "3313", 4: "4311"}, "Akuntan."),
    (r"\b(financial advisor|financial planner|perencana keuangan|investment|"
     r"wealth|konsultan keuangan|financial consultant)\b", "2412", {3: "3311"},
     "Konsultan keuangan dan investasi."),
    (r"\b(financial analyst|analis keuangan|credit analyst|analis kredit|"
     r"risk analyst|budget analyst|fp a)\b", "2413", {3: "3312"}, "Analis keuangan."),
    (r"\b(business analyst|analis bisnis|management consultant|business process|"
     r"process improvement|operational excellence|strategy analyst|corporate planning)\b",
     "2421", {3: "3339"}, "Analis manajemen dan organisasi."),
    (r"\b(business development|bizdev|biz dev|bisnis development|"
     r"pengembangan bisnis|partnership|kemitraan)\b", "2431",
     {3: "3322", 5: "5249", 1: "1221"},
     "Pengembangan bisnis menurut fungsinya mengidentifikasi peluang pasar "
     "(uraian 2431)."),
    (r"\b(recruiter|recruitment|rekrutmen|talent acquisition)\b",
     "2423", {3: "3333", 4: "4416"}, "Profesional personalia dan karir (rekrutmen)."),
    (r"\b(trainer|training|pelatihan|learning development|l d)\b(?!.*\b(gym|fitness|"
     r"personal|olahraga|renang)\b)", "2424", {3: "3423"},
     "Profesional pelatihan dan pengembangan staf."),
    (r"\b(hr|hrd|hrga|human resource|human resources|sdm|personalia|"
     r"people|hr generalist|hr business partner|compensation|payroll specialist)\b",
     "2423", {4: "4416"}, "Profesional personalia dan karir."),
    (r"\b(legal|hukum|lawyer|pengacara|advokat|corporate secretary|compliance|"
     r"kepatuhan|paralegal)\b", "2619", {3: "3411", 4: "4419"}, "Profesional hukum YTDL."),
    (r"\b(notaris|notary)\b", "2619", {3: "3411"}, "Profesional hukum (notaris)."),
    (r"\b(ekonom|economist)\b", "2631", {}, "Ahli ekonomi."),
    (r"\b(psikolog|psychologist)\b", "2634", {}, "Psikolog."),
    (r"\b(konselor|counselor|counsellor|pekerja sosial|social worker)\b",
     "2635", {3: "3412"}, "Profesional konseling dan pekerja sosial."),
    (r"\b(ustadz|ustadzah|ustad|guru ngaji|pengajar al quran|tahfidz|imam|pendeta)\b",
     "2636", {3: "3413", 2: "2636"}, "Profesional keagamaan."),
    # --- pendidikan
    (r"\b(dosen|lecturer)\b", "2310", {}, "Dosen."),
    (r"\b(guru|teacher|pengajar)\b.*\b(tk|paud|pg|preschool|kindergarten|"
     r"playgroup|anak usia dini)\b|\b(guru tk|guru paud)\b", "2342", {3: "5312"},
     "Guru anak usia dini."),
    (r"\b(guru|teacher|pengajar)\b.*\b(sd|sekolah dasar|elementary|primary|kelas)\b",
     "2341", {}, "Guru sekolah dasar."),
    (r"\b(guru|teacher|pengajar|tutor)\b.*\b(inggris|english|mandarin|bahasa|"
     r"jepang|korea|arab|language|bipa)\b|\b(english|mandarin|bahasa)\b.*\b(teacher|tutor|guru)\b",
     "2353", {}, "Guru kursus bahasa."),
    (r"\b(guru|teacher|pengajar|tutor)\b.*\b(musik|music|piano|gitar|vokal|drum)\b",
     "2354", {}, "Guru kursus musik."),
    (r"\b(guru|teacher|pengajar|tutor)\b.*\b(seni|art|lukis|tari|menggambar|drawing)\b",
     "2355", {}, "Guru kursus seni."),
    (r"\b(guru|teacher|pengajar|tutor|instruktur)\b.*\b(coding|programming|komputer|"
     r"computer|robotik|robotic|it)\b", "2356", {}, "Pengajar teknologi informasi."),
    (r"\b(shadow teacher|guru pendamping|guru pendamping khusus|gpk|"
     r"asisten guru|teacher assistant)\b", "5312", {2: "2352", 3: "5312"},
     "Guru pendamping."),
    (r"\b(guru slb|guru abk|special needs|terapis abk)\b", "2352", {}, "Guru siswa berkebutuhan khusus."),
    (r"\b(guru|teacher|wali kelas)\b", "2330", {}, "Guru pendidikan menengah."),
    (r"\b(tutor|pengajar|instruktur|instructor|mentor|les privat|tentor)\b",
     "2359", {3: "3423"}, "Profesional bidang pendidikan lainnya YTDL."),
    # --- kesehatan
    (r"\b(dokter gigi|dentist|drg)\b", "2261", {}, "Dokter gigi."),
    (r"\b(dokter spesialis|spesialis|sp a|sp og|sp pd|specialist doctor)\b(?!.*\b(marketing|sales))",
     "2212", {}, "Dokter spesialis."),
    (r"\b(dokter|doctor|physician|dokter umum|general practitioner)\b",
     "2211", {}, "Dokter umum."),
    (r"\b(dokter hewan|veterinarian|drh)\b", "2250", {}, "Dokter hewan."),
    (r"\b(asisten apoteker|tenaga teknis kefarmasian|ttk|teknisi farmasi|"
     r"pharmacy assistant|staff apotek|staf apotek)\b", "3213", {5: "5223"},
     "Teknisi farmasi dan asisten apoteker."),
    (r"\b(apoteker|pharmacist)\b", "2262", {3: "3213"}, "Apoteker."),
    (r"\b(bidan|midwife)\b", "2222", {3: "3222"}, "Profesional kebidanan."),
    (r"\b(perawat lansia|caregiver|care giver|pengasuh lansia|pendamping lansia)\b",
     "5322", {3: "3221", 5: "5321"}, "Pekerja perawatan pribadi di rumah."),
    (r"\b(perawat|nurse|ners)\b", "2221", {3: "3221"}, "Profesional keperawatan."),
    (r"\b(ahli gizi|nutritionist|dietitian|nutrisionis)\b", "2265", {}, "Ahli diet dan gizi."),
    (r"\b(fisioterapis|physiotherapist|fisioterapi)\b", "2264", {3: "3255"}, "Ahli fisioterapi."),
    (r"\b(okupasi|occupational therapist|terapis wicara|speech therapist|"
     r"terapis anak|terapis abk)\b", "2269", {3: "3259"}, "Ahli kesehatan YTDL (terapis)."),
    (r"\b(radiografer|radiographer|radiologi)\b", "3211", {}, "Teknisi peralatan perekam medis."),
    (r"\b(analis lab|analis laboratorium|analis kesehatan|medical laboratory|"
     r"atlm|lab medis)\b", "3212", {}, "Teknisi laboratorium medis."),
    (r"\b(rekam medis|medical record|perekam medis)\b", "3252", {4: "4415"},
     "Teknisi informasi kesehatan dan rekam medis."),
    (r"\b(optometris|refraksionis|optician|optisien|optik)\b", "3254", {2: "2267"}, "Optisien."),
    (r"\b(k3|hse|she|safety officer|safety|ahli k3|k3l|keselamatan)\b",
     "2263", {3: "3257"}, "Ahli kesehatan dan keselamatan kerja."),
    # --- teknik
    (r"\b(arsitek|architect)\b", "2161", {3: "3112"}, "Arsitek bangunan."),
    (r"\b(landscape architect|arsitek lanskap|landscape designer)\b", "2162", {}, "Arsitek lansekap."),
    (r"\b(interior designer|desainer interior|desain interior|interior design)\b",
     "3432", {2: "2161"}, "Desainer dan dekorator interior."),
    (r"\b(fashion designer|desainer fashion|desainer busana|fashion design|"
     r"product designer|desainer produk|desain produk|furniture designer|"
     r"pattern designer|textile designer|desainer baju|desain baju|desain pakaian)\b",
     "2163", {3: "3435", 7: "7532"}, "Perancang produk dan pakaian jadi."),
    (r"\b(drafter|draftman|draughtsman|autocad operator|cad operator|juru gambar)\b",
     "3118", {}, "Juru gambar teknik."),
    (r"\b(surveyor|juru ukur|quantity surveyor|estimator)\b", "2165", {3: "3112"},
     "Ahli pemetaan dan surveyor (termasuk estimator biaya)."),
    (r"\b(civil engineer|teknik sipil|structural engineer|site engineer|"
     r"engineer sipil|insinyur sipil)\b", "2142", {3: "3112"}, "Ahli teknik sipil."),
    (r"\b(environmental engineer|teknik lingkungan|ipal|waste water)\b", "2143", {3: "3132"},
     "Ahli teknik lingkungan."),
    (r"\b(mechanical engineer|teknik mesin|engineer mesin|mechanical)\b", "2144", {3: "3115"},
     "Ahli teknik mekanika."),
    (r"\b(chemical engineer|teknik kimia|process engineer kimia)\b", "2145", {3: "3116"},
     "Ahli teknik kimia."),
    (r"\b(electrical engineer|teknik elektro|engineer listrik|electrical)\b", "2151",
     {3: "3113", 7: "7411"}, "Ahli teknik listrik."),
    (r"\b(electronic engineer|elektronika engineer|hardware engineer)\b", "2152",
     {3: "3114"}, "Ahli teknik elektronik."),
    (r"\b(telecommunication|telekomunikasi|rf engineer|fiber optic engineer)\b", "2153",
     {3: "3522"}, "Ahli teknik telekomunikasi."),
    (r"\b(industrial engineer|teknik industri|process engineer|production engineer|"
     r"manufacturing engineer|ppic engineer|lean|continuous improvement|"
     r"quality engineer|qa engineer manufaktur)\b", "2141", {3: "3119"},
     "Ahli teknik industri dan produksi."),
    (r"\b(engineer|insinyur|engineering)\b", "2149", {3: "3119"}, "Ahli teknik lain YTDL."),
    (r"\b(chemist|ahli kimia|r d|research and development|riset dan pengembangan|"
     r"food technologist|formulator|peneliti|researcher|research)\b",
     "2113", {3: "3111", 2: "2113"},
     "Ahli kimia (riset dan pengembangan produk)."),
    (r"\b(geologist|geologi|geofisika)\b", "2114", {3: "3117"}, "Ahli geologi dan geofisika."),
    (r"\b(agronomis|agronomist|penyuluh pertanian|ahli pertanian)\b", "2132",
     {3: "3142"}, "Penasihat pertanian."),

    # =====================================================================
    # 3 TEKNISI DAN ASISTEN AHLI
    # =====================================================================
    (r"\b(analis kimia|analis laboratorium kimia|lab analyst|laboran|"
     r"laboratory analyst|analis lab|lab technician|teknisi laboratorium|qc lab)\b",
     "3111", {7: "7543"}, "Teknisi ilmu kimia dan fisika."),
    (r"\b(quality control|qc|quality assurance|qa|quality controller|inspector|"
     r"inspektor|pengendali mutu|penjamin mutu|qc inspector|checker qc)\b",
     "7543", {3: "3119", 2: "2141", 7: "7543"},
     "Penguji dan penilai kualitas produk (selain makanan dan minuman)."),
    (r"\b(teknisi listrik|electrician|tukang listrik|instalatir|teknisi elektrik)\b",
     "7411", {3: "3113"}, "Pekerja kelistrikan bangunan."),
    (r"\b(teknisi ac|ac technician|teknisi pendingin|refrigeration|hvac|mekanik ac)\b",
     "7127", {3: "3115"}, "Mekanik pendingin udara."),
    (r"\b(teknisi lift|lift technician|teknisi elevator|elevator)\b", "7412",
     {3: "3113"}, "Mekanik dan pemasang peralatan listrik."),
    (r"\b(teknisi elektronik|teknisi hp|service hp|teknisi handphone|"
     r"electronic technician|teknisi cctv|instalasi cctv|teknisi komputer)\b",
     "7421", {3: "3114"}, "Pekerja mekanik dan servis peralatan elektronik."),
    (r"\b(teknisi jaringan|teknisi wifi|teknisi internet|teknisi fiber|"
     r"fiber optic|fo technician|teknisi fo|installer internet|teknisi isp)\b",
     "7422", {3: "3513"}, "Pekerja instalasi dan servis peralatan TIK."),
    (r"\b(mekanik|mechanic|montir)\b.*\b(alat berat|heavy equipment|industri|mesin)\b",
     "7233", {3: "3115"}, "Mekanik dan tukang reparasi mesin industri."),
    (r"\b(mekanik|mechanic|montir|teknisi motor|teknisi mobil|service advisor)\b",
     "7231", {3: "3115", 2: "3115"}, "Mekanik dan tukang reparasi kendaraan bermotor."),
    (r"\b(maintenance|perawatan mesin|teknisi mesin|teknisi maintenance|"
     r"teknisi pabrik|utility|teknisi)\b", "7233", {3: "3115"},
     "Mekanik dan tukang reparasi mesin industri."),
    (r"\b(ppic|production planning|perencana produksi|production planner|demand planner|supply planner|material planner)\b", "4322",
     {}, "Juru tata usaha produksi."),
    (r"\b(nakhoda|nahkoda|captain kapal|mualim|perwira kapal|deck officer)\b",
     "3152", {}, "Nakhoda dan perwira geladak kapal."),
    (r"\b(masinis kapal|engineer kapal|marine engineer|juru mesin kapal)\b", "3151",
     {}, "Teknisi kapal."),
    (r"\b(pilot)\b", "3153", {}, "Pilot."),
    (r"\b(account officer|ao|loan officer|petugas kredit|marketing kredit|"
     r"credit officer|relationship officer|marketing funding|marketing lending)\b",
     "3312", {}, "Petugas kredit dan pinjaman."),
    (r"\b(asuransi|insurance|agen asuransi|financial consultant asuransi|unit link)\b",
     "3321", {}, "Perwakilan asuransi."),
    (r"\b(purchasing|procurement|pembelian|buyer|pengadaan)\b", "3323",
     {}, "Juru pembelian."),
    (r"\b(ekspor|export|impor|import|exim|forwarding|freight forwarder|customs|"
     r"clearance|ppjk|shipping)\b", "3331", {4: "4323"}, "Agen kliring dan pengiriman."),
    (r"\b(event planner|event organizer|event coordinator|wedding planner|"
     r"wedding organizer|mice|event)\b", "3332", {2: "2431"},
     "Perencana konferensi dan acara."),
    (r"\b(agen properti|property agent|marketing properti|property consultant|"
     r"real estate|marketing perumahan|sales properti|property)\b", "3334",
     {5: "5249"}, "Agen real estate dan manajer properti."),
    (r"\b(tenant relation|building manager|estate)\b", "3334", {5: "5153"},
     "Agen real estate dan manajer properti."),
    (r"\b(personal assistant|asisten pribadi|executive assistant|asisten eksekutif|"
     r"executive secretary|sekretaris direksi|sekretaris direktur|sekretaris eksekutif|"
     r"personal assitant|pa)\b", "3343", {4: "4120"}, "Sekretaris administrasi dan eksekutif."),
    (r"\b(medical secretary|sekretaris medis|admin klinik|admin rumah sakit)\b",
     "3344", {4: "4110"}, "Sekretaris medis."),
    (r"\b(personal trainer|fitness|gym|instruktur senam|yoga|pilates|zumba|"
     r"pelatih renang|swimming)\b", "3423", {2: "2359"},
     "Instruktur dan pelatih program kebugaran."),
    (r"\b(pelatih|coach|kru olahraga|wasit)\b", "3422", {}, "Pelatih olahraga."),
    (r"\b(head chef|chef de partie|chef|sous chef|kepala koki|cdp)\b",
     "3434", {5: "5120", 1: "1412"}, "Chef."),
    (r"\b(decorator|dekorator|florist|visual merchandiser|stylist|"
     r"wardrobe|make up artist pertunjukan|penata artistik)\b", "3432",
     {5: "5142", 2: "2163"}, "Desainer dan dekorator (display/visual)."),

    # =====================================================================
    # 4 TENAGA TATA USAHA
    # =====================================================================
    (r"\b(teller)\b", "4211", {}, "Teller bank."),
    (r"\b(desk collection|desk collector|field collection|field collector|"
     r"collection|collector|kolektor|penagih|telecollection|tele collection|"
     r"debt collector|remedial|recovery)\b", "4214", {}, "Penagih hutang."),
    (r"\b(ticketing|reservation|reservasi|travel consultant|travel agent|"
     r"tour consultant|booking)\b", "4221", {5: "5111"},
     "Tenaga tata usaha perjalanan."),
    (r"\b(call center|contact center|customer service online|cs online|"
     r"customer care|customer support|live chat|chat agent|admin chat|"
     r"customer service representative|csr|inbound)\b", "4222", {},
     "Tenaga tata usaha informasi pusat kontak."),
    (r"\b(front desk|front office|receptionist|resepsionis|frontliner|"
     r"guest service|guest relation)\b(?=.*\b(hotel|villa|resort|spa)\b)",
     "4224", {5: "5111"}, "Resepsionis hotel."),
    (r"\b(front desk|front office|receptionist|resepsionis|frontliner|"
     r"guest service|guest relation|operator telepon|telephone operator)\b",
     "4226", {5: "4226"}, "Resepsionis."),
    (r"\b(customer service|cs|layanan pelanggan|customer experience|"
     r"customer relation|after sales|aftersales|client service|"
     r"customer success|service advisor)\b", "4229", {},
     "Tenaga tata usaha informasi pelanggan YTDL. KBJI menempatkan layanan "
     "pelanggan pada golongan pokok 4 (subgolongan pokok 42)."),
    (r"\b(surveyor lapangan|enumerator|pewawancara|interviewer survei|"
     r"field survey|surveyor data)\b", "4227", {3: "3314"},
     "Pewawancara survei dan penelitian pasar."),
    # =====================================================================
    # 5 TENAGA USAHA JASA DAN TENAGA PENJUALAN
    # =====================================================================
    (r"\b(tour guide|pemandu wisata|tour leader|guide)\b", "5113", {}, "Pramuwisata."),
    (r"\b(pramugari|pramugara|flight attendant|cabin crew|ground staff|"
     r"ground handling)\b", "5111", {}, "Tenaga pelayanan perjalanan."),
    (r"^(?!.*\b(driver|supir|sopir)\b).*\b(asisten koki|assistant cook|asisten chef|cook helper|commis|cook|koki|"
     r"juru masak|tukang masak|kitchen staff|staff dapur|crew dapur|kitchen crew|"
     r"line cook|kitchen|dapur|masak|cooking|baker helper|pastry)\b(?!.*\bhelper dapur)",
     "5120", {9: "9411", 7: "7512"},
     "Juru masak. Asisten koki/chef/baker ke golongan pokok 5 sesuai keputusan pembimbing."),
    (r"\b(waiter|waitress|waiters|pramusaji|server|pelayan restoran|pelayan|"
     r"service crew|crew restoran|crew resto|food runner|runner|steward|"
     r"crew cafe|crew restaurant)\b", "5131", {}, "Pramusaji."),
    (r"\b(barista|bartender|mixologist|bar staff|bar crew)\b", "5132", {},
     "Pramutama bar/bartender (meracik dan melayani minuman)."),
    (r"\b(hair stylist|hairstylist|penata rambut|barber|kapster|hairdresser|"
     r"capster|stylist rambut)\b", "5141", {}, "Penata rambut."),
    (r"\b(beautician|beauty therapist|terapis kecantikan|therapist spa|spa therapist|"
     r"terapis spa|nail|eyelash|lash|makeup artist|mua|make up|waxing|facial|"
     r"skin care therapist|esthetician|terapis|therapist)\b", "5142", {2: "2269", 3: "3255"},
     "Perawat kecantikan/beautician dan YBDI."),
    (r"\b(housekeeping|room attendant|room boy|public area|pa)\b(?!.*\b(supervisor|spv|manager)\b)",
     "9112", {5: "5151"}, "Tenaga kebersihan di kantor, hotel dan tempat lainnya."),
    (r"\b(pet groomer|groomer|perawat hewan|animal keeper|zookeeper)\b", "5164",
     {}, "Pelatih dan pekerja perawatan hewan."),
    (r"\b(instruktur mengemudi|driving instructor|instruktur menyetir)\b", "5165",
     {}, "Instruktur mengemudi."),
    (r"\b(baby sitter|babysitter|baby sister|nanny|pengasuh|suster anak|"
     r"pengasuh anak|daycare|child care)\b", "5311", {9: "5311"},
     "Pekerja perawatan anak."),
    (r"\b(satpam|security|keamanan|penjaga keamanan|bodyguard|pengawal|patroli)\b",
     "5414", {8: "5414"}, "Penjaga keamanan."),
    (r"\b(pemadam|firefighter|fire fighter)\b", "5411", {}, "Petugas pemadam kebakaran."),
    (r"\b(kasir|cashier|petugas tiket|ticket seller|loket)\b", "5230",
     {}, "Kasir dan petugas tiket."),
    (r"\b(model|talent model|foto model|fitting model)\b", "5241", {2: "2655"},
     "Model fesyen dan model lainnya."),
    (r"\b(spg|spb|sales promotion|sales promotor|promotor|promoter|"
     r"usher|merchandiser|sales merchandiser|product demonstrator|"
     r"beauty advisor|beauty consultant|ba)\b", "5242", {},
     "Peraga penjualan (termasuk sales merchandiser)."),
    (r"\b(canvasser|canvas|kanvas|sales motoris|motoris|sales lapangan|"
     r"door to door|sales keliling|taking order|sales taking order)\b", "5243",
     {3: "3322"}, "Pedagang rumah ke rumah / kanvas."),
    (r"\b(telemarketing|telemarketer|telesales|tele sales|sales online|"
     r"admin sales online|chat sales|sales via telepon|telemarketing staff)\b",
     "5244", {4: "4222"}, "Pedagang melalui pusat informasi (telemarketing)."),
    (r"\b(operator spbu|petugas spbu|spbu|pom bensin|gas station)\b", "5245",
     {8: "5245"}, "Petugas stasiun pengisian bahan bakar."),
    (r"\b(crew outlet|crew store|crew toko|store crew|crew minimarket|"
     r"pramuniaga|shop assistant|store assistant|retail assistant|sales assistant|"
     r"asisten penjualan|pelayan toko|penjaga toko|staff toko|crew|"
     r"retail staff|staff retail|store staff|toko|showroom staff|crew booth|"
     r"sales counter|counter staff|sales toko|sales store|frontliner toko)\b",
     "5223", {9: "9334"},
     "Asisten penjualan toko."),
    (r"\b(petugas konter|crew counter|food counter|crew kantin|kantin)\b", "5246",
     {}, "Petugas konter layanan makanan."),
    (r"\b(pedagang|penjual makanan|pedagang kaki lima|jualan|reseller|dropshipper)\b",
     "5212", {9: "9510"},
     "Pedagang makanan kaki lima. Pedagang/penjual makanan ke golongan pokok 9 "
     "sesuai keputusan pembimbing (alternatif 9510)."),
    (r"\b(account executive|account manager|key account|sales executive|"
     r"sales representative|sales officer|sales consultant|salesman|sales person|"
     r"salesperson|sales engineer|sales b2b|b2b sales|corporate sales|"
     r"sales corporate|sales distributor|sales area|sales kanvas|"
     r"sales staff|staff sales|sales and marketing|sales marketing|"
     r"marketing executive|marketing officer|marketing staff|staff marketing|"
     r"marketing|pemasaran|penjualan|sales|bdr|sdr|business representative)\b",
     "3322", {5: "5249", 2: "2431", 1: "1221"},
     "Perwakilan penjualan komersial. Bila golongan pokoknya 5, ditempatkan pada "
     "pekerja penjualan YTDL (5249)."),

    # =====================================================================
    # 6 PERTANIAN, KEHUTANAN, PERIKANAN
    # =====================================================================
    (r"\b(petani|farmer|pekebun|perkebunan|kebun|plantation|sawit|hidroponik)\b",
     "6112", {9: "9211"}, "Pekerja pertanian tanaman tahunan."),
    (r"\b(peternak|kandang|unggas|ayam|sapi|livestock|peternakan)\b", "6121",
     {9: "9212"}, "Pekerja peternakan."),
    (r"\b(perikanan|tambak|budidaya ikan|aquaculture|nelayan)\b", "6221",
     {9: "9216"}, "Pekerja budidaya perikanan."),
    (r"\b(tukang kebun|gardener|landscape|landscaping|pertamanan|taman)\b",
     "6113", {9: "9214"}, "Pekerja tanaman taman."),

    # =====================================================================
    # 7 PEKERJA PENGOLAHAN DAN KERAJINAN
    # =====================================================================
    (r"\b(tukang batu|mason|tukang bangunan|kenek bangunan|kuli bangunan)\b",
     "7112", {9: "9313"}, "Tukang tembok dan YBDI."),
    (r"\b(tukang kayu|carpenter|kayu)\b", "7115", {}, "Tukang kayu bangunan."),
    (r"\b(plumber|plumbing|tukang pipa|pipa)\b", "7126", {}, "Pekerja perpipaan."),
    (r"\b(tukang cat|painter|pengecatan|cat duco|spray painter)\b", "7131", {},
     "Pekerja pengecatan."),
    (r"\b(welder|las|tukang las|pengelasan|welding|fabrikasi|fabrication)\b",
     "7212", {8: "7212"}, "Pekerja pengelasan."),
    (r"\b(cnc|bubut|lathe|milling|machinist|tool maker|toolmaker)\b", "7223",
     {8: "8121"}, "Operator dan penyetel mesin pengerjaan logam."),
    (r"\b(baker|pembuat roti|pembuat kue|cake|bakery|pastry chef|pastry cook|"
     r"cake decorator|roti)\b", "7512", {5: "5120"}, "Pembuat roti, kue dan kembang gula."),
    (r"\b(butcher|tukang daging|jagal|meat|fillet|potong ayam|pemotong)\b", "7511",
     {}, "Pemotong hewan dan pengolah makanan YBDI."),
    (r"\b(food tester|taster|qc makanan|qc food|food qc|quality control makanan)\b",
     "7515", {}, "Penilai kualitas makanan dan minuman."),
    (r"\b(furniture|mebel|meubel|upholstery|jok)\b", "7522", {}, "Pembuat furnitur."),
    (r"\b(pattern maker|pola|cutting garmen|cutter garment|pembuat pola)\b", "7532",
     {8: "7532"}, "Pembuat dan pemotong pola garmen."),
    (r"\b(penjahit|tailor|jahit|permak|sewing|operator jahit|operator sewing)\b",
     "8153", {7: "7533"}, "Operator mesin jahit."),
    (r"\b(printing|percetakan|sablon|screen printing|operator cetak|digital printing|"
     r"offset)\b", "7322", {8: "7322"}, "Pekerja pencetakan."),
    (r"\b(finishing|qc finishing|setrika|ironing)\b", "7549", {8: "8159"},
     "Pekerja pengolahan lainnya YTDL (penyelesaian)."),
    (r"\b(pest control|pembasmi hama|fumigasi)\b", "7544", {}, "Pengendali hama."),
    (r"\b(perhiasan|jewelry|emas|goldsmith)\b", "7313", {}, "Pembuat perhiasan."),

    # =====================================================================
    # 8 OPERATOR DAN PERAKIT MESIN
    # =====================================================================
    (r"\b(forklift|reach truck)\b", "8344", {}, "Operator forklift."),
    (r"\b(crane|derek|hoist)\b", "8343", {}, "Operator derek."),
    (r"\b(excavator|alat berat|heavy equipment|loader|dozer|grader)\b", "8342",
     {}, "Operator mesin pengeruk tanah."),
    (r"\b(batching plant|beton|ready mix)\b", "8114", {}, "Operator mesin pengolahan semen."),
    (r"\b(injection|plastik|plastic|blow molding|extrusion)\b", "8142", {},
     "Operator mesin pengolahan plastik."),
    (r"\b(operator mesin|machine operator|mesin)\b", "8189", {7: "7223"},
     "Operator mesin stasioner YTDL."),
    (r"\b(perakit|assembler|assembly|operator assembly)\b", "8219", {}, "Perakit YTDL."),
    (r"\b(helper produksi|helper pabrik|buruh pabrik|buruh produksi|helper)\b"
     r"(?=.*\b(produksi|pabrik|production|factory)\b)|\bhelper produksi\b",
     "9329", {8: "8189"}, "Buruh industri pengolahan YTDL."),
    (r"^(?!.*\b(video|film|konten|content|media|tv|musik|music)\b).*\b(operator produksi|production operator|staff produksi|production staff|"
     r"tenaga produksi|karyawan produksi|crew produksi|pekerja produksi|"
     r"operator pabrik|produksi|production|operator)\b", "8189",
     {9: "9329", 7: "7549", 5: "8189"},
     "Operator mesin stasioner YTDL. Jenis mesinnya tidak disebut di judul, "
     "sehingga belum bisa ditempatkan ke subgolongan yang lebih spesifik."),
    (r"\b(operator laundry|laundry)\b", "8157", {9: "9121"}, "Operator mesin binatu."),
    (r"\b(driver truk|driver truck|supir truk|sopir truk|truk|truck|trailer|"
     r"dump truck|tronton|wingbox)\b", "8332", {}, "Pengemudi truk berat."),
    (r"\b(driver bus|supir bus|sopir bus|bus)\b", "8331", {}, "Pengemudi bus."),
    (r"^(?!.*\boffice (boy|girl)\b).*\b(kurir|courier|delivery|pengantar|messenger|rider|kurir motor)\b",
     "9621", {8: "8321"}, "Kurir dan pengantar paket. Bila golongan pokoknya 8 "
     "(pengemudi), ditempatkan pada pengemudi sepeda motor (8321)."),
    (r"\b(driver|supir|sopir|pengemudi|chauffeur)\b", "8322", {}, "Pengemudi mobil, taksi dan van."),
    (r"\b(awak kapal|abk|anak buah kapal|deck crew|kelasi)\b", "8350", {}, "Awak geladak kapal."),

    # =====================================================================
    # 9 PEKERJA KASAR
    # =====================================================================
    (r"\b(asisten rumah tangga|art|pembantu rumah tangga|prt|maid|"
     r"housekeeper rumah)\b", "9111", {}, "Tenaga kebersihan dan juru bantu rumah tangga."),
    (r"\b(cleaning service|cleaner|petugas kebersihan|office boy|office girl|ob|og|"
     r"janitor|kebersihan|cleaning|pramubakti|pramu kantor)\b", "9112",
     {5: "9112", 3: "9112"}, "Tenaga kebersihan dan juru bantu di kantor/hotel."),
    (r"\b(car wash|cuci mobil|cuci motor|washer)\b", "9122", {}, "Tenaga cuci kendaraan."),
    (r"\b(pencuci piring|dishwasher|steward dapur|helper dapur|kitchen helper|"
     r"kitchen porter)\b", "9412", {5: "9412"}, "Juru bantu dapur."),
    (r"\b(packing|packer|pengemasan|packaging|pengepakan|staff packing|"
     r"admin packing)\b", "9321", {4: "4321"},
     "Buruh pengemasan. Bila golongan pokoknya 8, ditempatkan pada operator mesin "
     "pengemasan (8183)."),
    (r"\b(staff gudang|staf gudang|warehouse staff|warehouse crew|crew warehouse|"
     r"crew gudang|helper gudang|warehouse helper|gudang|warehouse|"
     r"operator gudang|operator warehouse|picker|picking|loader|bongkar muat|"
     r"kuli|porter|buruh angkut)\b", "9333", {4: "4321"},
     "Buruh angkat barang (pergudangan). KBJI tidak menempatkan pekerja gudang "
     "di golongan pokok 8 kecuali operator forklift."),
    (r"\b(parkir|parking|juru parkir|valet)\b", "9629", {}, "Pekerja kasar YTDL."),
    (r"\b(daily worker|pekerja harian|harian lepas|buruh harian|serabutan|"
     r"tenaga harian|helper|kenek|kernet)\b", "9622", {}, "Pekerja serabutan."),
]
