# src/datasets.py
import os
import requests
from pathlib import Path

RAW_DIR = Path("datasets/raw")
FMT_DIR = Path("datasets/spmf_format")
RAW_DIR.mkdir(parents=True, exist_ok=True)
FMT_DIR.mkdir(parents=True, exist_ok=True)

DATASET_URLS = {
    "mushroom":   "http://www.philippe-fournier-viger.com/spmf/datasets/mushroom.txt",
    "connect":    "http://www.philippe-fournier-viger.com/spmf/datasets/connect.txt",
    "chess":      "http://www.philippe-fournier-viger.com/spmf/datasets/chess.txt",
    "t10i4d100k": "http://www.philippe-fournier-viger.com/spmf/datasets/T10I4D100K.txt",
    "retail":     "http://www.philippe-fournier-viger.com/spmf/datasets/retail.txt",
    "leviathan":  "http://www.philippe-fournier-viger.com/spmf/datasets/leviathan.txt",
    "bible":      "http://www.philippe-fournier-viger.com/spmf/datasets/Bible.txt",
    "sign":       "http://www.philippe-fournier-viger.com/spmf/datasets/sign.txt",
    "chainstore": "http://www.philippe-fournier-viger.com/spmf/datasets/chainstore.txt",
    "foodmart":   "http://www.philippe-fournier-viger.com/spmf/datasets/foodmart.txt",
}

def download_all():
    """
    SPMF resmi sitesinden dataset indirir. Site erisim sorunu oldugunda
    generate_synthetic_datasets() ile sentetik veriler olusturulabilir.
    Not: philippe-fournier-viger.com 300 HTTP yaniti donebilir; bu durumda
    sentetik dataset uretimi yapilir.
    """
    for name, url in DATASET_URLS.items():
        dest = RAW_DIR / f"{name}.txt"
        if dest.exists() and dest.stat().st_size > 1000:
            print(f"[SKIP] {name} zaten mevcut ({dest.stat().st_size // 1024} KB)")
            continue
        print(f"[DL]   {name} indiriliyor... {url}")
        try:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            # SPMF sitesi bazen 300 HTML donuyor - icerik kontrolu
            if r.content[:5] == b"<!DOC" or b"<html" in r.content[:100]:
                print(f"[WARN] {name}: Sunucu HTML donurdu (erisim sorunu) - sentetik veri kullan")
                continue
            dest.write_bytes(r.content)
            print(f"[OK]   {name}: {len(r.content)//1024} KB")
        except Exception as e:
            print(f"[ERR]  {name}: {e}")

def fix_utility_format(src: Path, dst: Path):
    """
    SPMF utility dataset format duzeltici.
    Kaynak format: 'items :total: utilities'  (':'dan sonra bosluk var)
    Hedef format:  'items :total:utilities'   (':'dan sonra bosluk yok)
    Java'da 'str.split(":")' sonrasi bas bosluk parseInt hatasina yol acar.
    """
    lines = src.read_text(encoding="utf-8", errors="ignore").splitlines()
    fixed = []
    for line in lines:
        parts = line.split(":")
        if len(parts) == 3:
            items = parts[0].rstrip()
            total = parts[1]
            utils = parts[2].strip()
            fixed.append(f"{items} :{total}:{utils}")
        else:
            fixed.append(line)
    dst.write_text("\n".join(fixed), encoding="ascii", errors="replace")


def get_utility_dataset_path(name: str) -> Path:
    """Utility dataset icin duzeltilmis format dosyasini dondurur."""
    raw = RAW_DIR / f"{name}.txt"
    if not raw.exists():
        raise FileNotFoundError(f"Dataset bulunamadi: {raw}. Once download_all() calistir.")
    fixed = FMT_DIR / f"{name}_utility_fixed.txt"
    if not fixed.exists() or fixed.stat().st_mtime < raw.stat().st_mtime:
        fix_utility_format(raw, fixed)
    return fixed


def get_dataset_path(name: str) -> Path:
    p = RAW_DIR / f"{name}.txt"
    if not p.exists():
        raise FileNotFoundError(f"Dataset bulunamadi: {p}. Once download_all() calistir.")
    return p

def get_dataset_stats(name: str) -> dict:
    path = get_dataset_path(name)
    lines = path.read_text(encoding="utf-8", errors="ignore").strip().splitlines()
    n_transactions = len(lines)
    all_items = set()
    for line in lines:
        all_items.update(line.split())
    return {
        "name": name,
        "transactions": n_transactions,
        "unique_items": len(all_items),
        "avg_length": sum(len(l.split()) for l in lines) / max(n_transactions, 1),
    }

if __name__ == "__main__":
    download_all()
    print("\n=== Dataset Istatistikleri ===")
    for name in DATASET_URLS:
        try:
            stats = get_dataset_stats(name)
            print(f"{name:15s}: {stats['transactions']:>7} islem, "
                  f"{stats['unique_items']:>5} oge, "
                  f"ort uzunluk={stats['avg_length']:.1f}")
        except Exception as e:
            print(f"{name}: {e}")
