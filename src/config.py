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
    },
    "Zart": {
        "spmf_name": "Zart",
        "category": 1,
        "input_type": "transactional",
        "params": ["minsup"],
        "available": True,
    },
    "TalkyG_Diffset": {
        "spmf_name": "TalkyG_Diffset",
        "category": 1,
        "input_type": "transactional",
        "params": ["minsup"],
        "available": True,
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
MINSUP_VALUES = [0.2, 0.3, 0.5, 0.7]
MAXSUP_VALUES = [0.1, 0.2, 0.3]
# chainstore: max toplam utility ~ust sinir buyuk; foodmart: max toplam utility ~111
# Chainstore icin: 1000, 2000, 5000 uygundur
# Foodmart icin: 20, 50, 100 daha anlamlidir
MIN_UTILITY_VALUES = [1000, 2000, 5000]
MIN_UTILITY_FOODMART = [20, 50, 100]

DATASETS = {
    "transactional": ["mushroom", "connect", "chess", "t10i4d100k", "retail"],
    "sequential":    ["leviathan", "bible", "sign"],
    "utility":       ["chainstore", "foodmart"],
}

TIMEOUT_SECONDS = 3600  # Survey: 1 saat timeout, geçenler DNF olarak raporlanır
