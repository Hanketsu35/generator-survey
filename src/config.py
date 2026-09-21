# Algoritma konfigürasyon tablosu
# SPMF komut adı: http://www.philippe-fournier-viger.com/spmf/documentation.php

ALGORITHMS = {
    # ── Kategori 1: Temel Jeneratörler ──────────────────────────────
    "DefMe": {
        "spmf_name": "DefMe",
        "category": 1,
        "input_type": "transactional",
        "params": ["minsup"],
        "available": True,
    },
    "Gr_growth": {
        "spmf_name": None,
        "exe": "external_algos/Gr_growth/grgrowth-v1/GrGrowth-PBD-source/GrGrowth_PBd.exe",
        "exe_type": "grgrowth",
        "category": 1,
        "input_type": "transactional",
        "params": ["minsup"],
        "available": True,
    },
    "Talky_G": {
        "spmf_name": "TalkyG",
        "category": 1,
        "input_type": "transactional",
        "params": ["minsup"],
        "available": True,
    },
    "Touch": {
        "spmf_name": "TOUCH",
        "category": 1,
        "input_type": "transactional",
        "params": ["minsup"],
        "available": False,
        "note": "Bu SPMF versiyonunda mevcut değil",
    },
    "Prince": {
        "spmf_name": "Prince",
        "category": 1,
        "input_type": "transactional",
        "params": ["minsup"],
        "available": False,
        "note": "Bu SPMF versiyonunda mevcut değil",
    },
    "GrAFCI_plus": {
        "spmf_name": "GrAFCI+",
        "category": 1,
        "input_type": "transactional",
        "params": ["minsup"],
        "available": False,
        "note": "Bu SPMF versiyonunda mevcut değil",
    },
    "Pascal": {
        "spmf_name": "Pascal",
        "category": 1,
        "input_type": "transactional",
        "params": ["minsup"],
        "available": True,
        # Pascal tum frequent itemset'leri '#IS_GENERATOR: true|false' etiketiyle
        # yazar; duz satir sayimi jeneratör degil FI sayar.
        "count_fn": "pascal",
    },
    "Zart": {
        "spmf_name": "Zart",
        "category": 1,
        "input_type": "transactional",
        "params": ["minsup"],
        "available": True,
        # Zart kapali kumeler + jeneratörlerini insan-okunabilir rapor olarak
        # yazar; duz satir sayimi baslik satirlarini da sayar.
        "count_fn": "zart",
    },
    "TalkyG_Diffset": {
        "spmf_name": "TalkyG_Diffset",
        "category": 1,
        "input_type": "transactional",
        "params": ["minsup"],
        "available": True,
    },
    # ── Borgelt'in native C implementasyonlari (-tg = generator target) ──
    # borgelt.net/{apriori,eclat,fpgrowth}.html, v6.x, Windows x86-64 binary.
    #
    # ONEMLI ayrim: Apriori/Eclat/FP-growth *makaleleri* jeneratör algoritmasi
    # DEGILDIR; frequent itemset miner'dirlar.  Jeneratör hedefi Borgelt'in
    # IMPLEMENTASYONUNA ait bir ozelliktir ve POST-FILTER olarak calisir
    # ("filtering for generator item sets ... done" -- once tum FI'lar bulunur,
    # sonra jeneratör olmayanlar elenir).  Yani ozel bir jeneratör budamasi
    # yoktur.  Bu yuzden taksonomideki 25 algoritmaya EKLENMEZLER; ek
    # *implementasyon* olarak benchmark'a girerler.
    #
    # Borgelt'in tanimi Talky-G makalesi Definition 1 ile ayni:
    #   I jeneratördür  <=>  her J subset I icin supp(J) > supp(I)
    # Dogrulama (bkz. tools/validate_generators.py):
    #   - mushroom/0.4 (152 kume) ve chess/0.7 (23.892 kume): DefMe, Pascal,
    #     TalkyG ve ucu de BIREBIR ayni kume ailesini dondurdu.
    #   - ~27.000 kume uzerinde tanim kontrolu: 0 ihlal.
    "Apriori_Gen_Borgelt": {
        "spmf_name": None,
        "exe": "external_algos/borgelt/apriori.exe",
        "exe_type": "borgelt",
        "category": 1,
        "input_type": "transactional",
        "params": ["minsup"],
        "available": True,
        "count_fn": "borgelt",
    },
    "Eclat_Gen_Borgelt": {
        "spmf_name": None,
        "exe": "external_algos/borgelt/eclat.exe",
        "exe_type": "borgelt",
        "category": 1,
        "input_type": "transactional",
        "params": ["minsup"],
        "available": True,
        "count_fn": "borgelt",
    },
    "FPgrowth_Gen_Borgelt": {
        "spmf_name": None,
        "exe": "external_algos/borgelt/fpgrowth.exe",
        "exe_type": "borgelt",
        "category": 1,
        "input_type": "transactional",
        "params": ["minsup"],
        "available": True,
        "count_fn": "borgelt",
    },
    # ── Kategori 2: Sıralı Jeneratörler ─────────────────────────────
    "VGEN": {
        "spmf_name": "VGEN",
        "category": 2,
        "input_type": "sequential",
        "params": ["minsup"],
        "available": True,
    },
    "FEAT": {
        "spmf_name": "FEAT",
        "category": 2,
        "input_type": "sequential",
        "params": ["minsup"],
        "available": True,
    },
    "FGenSM": {
        "spmf_name": "FGenSM",
        "category": 2,
        "input_type": "sequential",
        "params": ["minsup"],
        "available": False,
        "note": "Bu SPMF versiyonunda mevcut değil",
    },
    "FCloSM": {
        "spmf_name": "FCloSM",
        "category": 2,
        "input_type": "sequential",
        "params": ["minsup"],
        "available": False,
        "note": "Bu SPMF versiyonunda mevcut değil",
    },
    "FSGP": {
        "spmf_name": "FSGP",
        "category": 2,
        "input_type": "sequential",
        "params": ["minsup"],
        "available": True,
    },
    # ── Kategori 3: High-Utility Jeneratörler ───────────────────────
    "HUG_Miner": {
        "spmf_name": "HUG-Miner",
        "category": 3,
        "input_type": "utility",
        "params": ["min_utility"],
        "available": True,
    },
    "GHUI_Miner": {
        "spmf_name": "GHUI-Miner",
        "category": 3,
        "input_type": "utility",
        "params": ["min_utility"],
        "available": True,
    },
    "HUCI_Miner": {
        "spmf_name": "HUCI_Miner",
        "category": 3,
        "input_type": "utility",
        "params": ["min_utility"],
        "available": False,
        "note": "Closed high-utility itemset miner — generator degil, survey kapsamı dışı",
    },
    "GFHUOI_Miner": {
        "spmf_name": "GFHUOI_Miner",
        "category": 3,
        "input_type": "utility",
        "params": ["min_utility"],
        "available": False,
        "note": "Bu SPMF versiyonunda mevcut değil",
    },
    "HUCI_Miner_Generators": {
        "spmf_name": "HUCI_Miner_Generators",
        "category": 3,
        "input_type": "utility",
        "params": ["min_utility"],
        "available": True,
    },
    # ── Kategori 4: Graf / Boolean / Disjunctive ─────────────────────
    "Fogger": {
        "spmf_name": None,
        "category": 4,
        "input_type": "graph",
        "params": [],
        "available": False,
        "note": "Graph generator - standalone impl araştırılacak",
    },
    "cgSpan": {
        "spmf_name": None,
        "category": 4,
        "input_type": "graph",
        "params": [],
        "available": False,
        "note": "gSpan variant - SPMF'de gSpan mevcut ama cgSpan ayrı",
    },
    "TitanicOR": {
        "spmf_name": None,
        "category": 4,
        "input_type": "transactional",
        "params": [],
        "available": False,
        "note": "Disjunctive generator - impl araştırılacak",
    },
    "BLOSOM": {
        "spmf_name": None,
        "category": 4,
        "input_type": "transactional",
        "params": [],
        "available": False,
        "note": "Boolean rule extractor - impl araştırılacak",
    },
    # ── Kategori 5: Stream / Nadir Jeneratörler ──────────────────────
    "FGC_Stream": {
        "spmf_name": None,
        "exe": "external_algos/FGC_Stream/FGC-Stream/FGC_Stream_release.exe",
        "exe_type": "fgcstream",
        "category": 5,
        "input_type": "transactional",
        "params": ["minsup"],
        "available": True,
    },
    "MINIT": {
        "spmf_name": "MINIT",
        "category": 5,
        "input_type": "transactional",
        "params": ["minsup"],
        "available": False,
        "note": "Bu SPMF versiyonunda mevcut değil",
    },
    "Arima": {
        "spmf_name": "AprioriRare",
        "category": 5,
        "input_type": "transactional",
        "params": ["maxsup"],
        "available": True,
    },
    "NOV_mGCFSI": {
        "spmf_name": None,
        "category": 5,
        "input_type": "transactional",
        "params": [],
        "available": False,
        "note": "SPMF'de adı bilinmiyor - standalone impl araştırılacak",
    },
}

# Benchmark parametreleri
#
# v1'de tum datasetler icin tek bir grid ([0.2, 0.3, 0.5, 0.7]) kullanilmisti.
# Bu, yogunluklari 3 buyukluk mertebesi farkeden datasetler icin uygun degil:
#   - retail (yogunluk 0.0006) ve t10i4d100k (0.011) bu esiklerde neredeyse
#     HIC jeneratör uretmiyor (olculen: t10i4d100k'da 0, retail'de 2-4).
#     Yani v1'deki bu 8 satir bilgi tasimiyor.
#   - chess (0.49) ve connect (0.33) ise 0.2'de patliyor ve DNF veriyor.
# v2'de her dataset kendi yogunluguna uygun bir grid aliyor; eski degerler
# korunuyor (resume sayesinde tamamlanmis kosular tekrar calismaz).
MINSUP_VALUES = [0.2, 0.3, 0.5, 0.7]          # geriye donuk varsayilan

MINSUP_BY_DATASET = {
    # yogun (dense) -- dusuk esikte kombinatorik patlama
    "chess":       [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
    "connect":     [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
    "pumsb":       [0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95],
    # orta
    "mushroom":    [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
    "accidents":   [0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
    # seyrek (sparse) -- anlamli cikti icin cok dusuk esik gerekiyor
    "t10i4d100k":  [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.2, 0.3, 0.5, 0.7],
    "retail":      [0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.2, 0.3, 0.5, 0.7],
}

# GrGrowth-PBd'nin ucuncu argumani (k), jeneratör testinde kac seviyeye kadar
# alt-kume kontrolu yapilacagini belirler (PatternSet.cpp:346,440).
#
# k=1  : yalnizca birebir alt kumeler kontrol edilir -> KLASIK minimal
#        jeneratör tanimi.  Destek anti-monoton oldugu icin bu YETERLIDIR.
# k>=2 : kod ayrica calc_subset_sum() ile icerme-dislama toplamlarini
#        karsilastirir; bu, minimalligin otesinde DAHA GUCLU bir kosuldur
#        (disjunction-free / turetilemez kumeler) ve cikti gercek jeneratör
#        kumesinin OZ ALT KUMESI olur.
#
# v2'ye kadar yanlislikla k=100 kullaniliyordu.  Olculen etki
# (mushroom, minsup=0.2, 8416 islem):
#     k=1   -> 1704 kume  (DefMe ciktisiyla BIREBIR ayni, bkz.
#                          tools/check_grgrowth.py)
#     k=2   ->  749 kume
#     k=100 ->  683 kume  (%60 eksik; 5-7 boyutlu jeneratörlerin tamami kayip)
# Yani eski kosular farkli ve cok daha kucuk bir problemi olcuyordu.
GRGROWTH_K = 1

# ---------------------------------------------------------------------------
# SIRALI (sequential) esikler -- dataset'e ozel.
#
# v2'ye kadar sirali aileye de [0.2, 0.3, 0.5, 0.7] uygulaniyordu.  Bu grid
# leviathan ve bible icin MATEMATIKSEL OLARAK IMKANSIZ: bu veri kumelerinde
# en sik gecen TEK oge bile esigin cok altinda kaliyor, dolayisiyla hicbir
# desen frequent olamaz.  Olculen tavan destekler:
#     leviathan : en sik oge 44/5834  = %0.8
#     bible     : en sik oge 100/36369 = %0.3
#     sign      : en sik oge 175/730   = %24.0
# Sonuc olarak 12 kosunun 11'i BOS cikti uretti; olculen sureler yalnizca JVM
# acilisi + dosya okumaydi ve "FEAT ~ FSGP" karsilastirmasi bir sey olcmuyordu.
#
# Asagidaki gridler her veri kumesinin gercek bilgilendirici araligini tarar
# (olculen desen sayilari FEAT ile):
#     leviathan 0.008 -> 36 ... 0.003 -> 8666
#     bible     0.0025 -> 0  ... 0.001 -> 13905
#     sign      0.24 -> ~146 ... 0.14 -> 267
# Not: cok dusuk esikte cikti tekil ogelerde doyuma ulasir (bible 0.001'de
# 13905 = ayrik oge sayisi), bu yuzden alt sinirlar orada birakildi.
# DAHA ONEMLI BIR BULGU: leviathan ve bible'da hicbir esikte COK OGELI
# sirali desen frequent olmuyor.  Olculen ust sinirlar:
#     leviathan: en sik OGE CIFTI yalnizca  3/5834  dizide birlikte geciyor
#     bible    : en sik OGE CIFTI yalnizca  3/36369 dizide birlikte geciyor
# Yani 2-uzunlugundaki bir desenin destegi 3'u asamaz; esik oraya indirildiginde
# ciktinin tamami zaten TEKIL ogelerden olusuyor (leviathan 9025 = ayrik oge
# sayisi, bible 13905 = ayrik oge sayisi).  Bu iki veri kumesinde gorev fiilen
# "frequent item" saymaya donusuyor; sirali yapi (alt-dizi iliskisi) HIC
# calistirilmiyor.  Bagimsiz dogrulama: PrefixSpan de ayni sonucu veriyor.
#
# sign ise gercek sirali madencilik yapiyor, ancak yalnizca minsup <= ~0.05'te:
#     0.05  -> 267 desen (hepsi tekil)
#     0.03  -> 13128  (267 tekil + 12861 ikili)
#     0.025 -> 30445  (~22 s)
#     0.02  -> 56952  (~42 s)
#     0.015 -> 69710  (267 tekil + 69415 ikili + 28 uclu, ~53 s)
# Bu yuzden sign gridi asagi cekildi; leviathan/bible kendi bilgilendirici
# (tekil-rejim) araliklarinda birakildi ve bu sinirlama makalede acikca
# raporlaniyor.
SEQ_MINSUP_BY_DATASET = {
    "sign":      [0.05, 0.04, 0.03, 0.025, 0.02, 0.015],
    "leviathan": [0.008, 0.006, 0.005, 0.004, 0.003],
    "bible":     [0.0025, 0.002, 0.0015, 0.00125, 0.001],
}
# Sirali yapinin gercekten calistirildigi (cok ogeli desen ureten) veri kumesi.
SEQ_STRUCTURE_DATASETS = {"sign"}
SEQ_MINSUP_VALUES = [0.2, 0.3, 0.5, 0.7]   # eski varsayilan (kullanilmiyor)

MAXSUP_VALUES = [0.1, 0.2, 0.3]

# Sayim yapildiktan sonra bu boyutun uzerindeki cikti dosyalari silinir.
# results/raw zaten 11 GB; genisletilmis grid ile yuzlerce GB olurdu.
# Sayimlar CSV/JSON'da kaldigi icin bilgi kaybi yok (dosya boyutu JSON'a yazilir).
MAX_KEEP_OUTPUT_MB = 20
# chainstore: max toplam utility ~ust sinir buyuk; foodmart: max toplam utility ~111
# Chainstore icin: 1000, 2000, 5000 uygundur
# Foodmart icin: 20, 50, 100 daha anlamlidir
MIN_UTILITY_VALUES = [1000, 2000, 5000]
MIN_UTILITY_FOODMART = [20, 50, 100]

DATASETS = {
    # accidents ve pumsb v2'de eklendi: iki ek yogun/buyuk standart benchmark.
    "transactional": ["mushroom", "connect", "chess", "t10i4d100k", "retail",
                      "accidents", "pumsb"],
    "sequential":    ["leviathan", "bible", "sign"],
    "utility":       ["chainstore", "foodmart"],
}

TIMEOUT_SECONDS = 3600  # Survey: 1 saat timeout, geçenler DNF olarak raporlanır
