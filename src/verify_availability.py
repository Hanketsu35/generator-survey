# src/verify_availability.py
import subprocess
import sys
import os
sys.path.insert(0, ".")
from src.config import ALGORITHMS

SPMF_JAR = "spmf/spmf.jar"

def check_spmf_algorithm(spmf_name: str) -> bool:
    """SPMF'de algoritmanin kayitli olup olmadigini kontrol eder."""
    try:
        result = subprocess.run(
            ["java", "-jar", SPMF_JAR, "run", spmf_name,
             "datasets/raw/mushroom.txt", "results/raw/_test_avail.txt", "0.5"],
            capture_output=True, text=True, timeout=15
        )
        combined = (result.stdout + result.stderr).lower()
        # SPMF bilinmeyen algoritmada "unknown" veya "not found" yazar
        if "unknown" in combined or "not found" in combined or "error" in combined:
            # Ama bazi hatalar input file bulunamadigindan kaynaklanabilir - algorithm var ama dosya yok
            # Gercek "algorithm not found" mesajini yakala
            if "unknown algorithm" in combined or "algorithm not found" in combined:
                return False
            # Diger hatalar (dosya bulunamadi vb.) -> algoritma var
            return True
        return True
    except subprocess.TimeoutExpired:
        return True  # timeout -> algoritma calismayi basladi demektir
    except Exception:
        return False

def main():
    os.makedirs("datasets/raw", exist_ok=True)
    os.makedirs("results/raw", exist_ok=True)

    # Mushroom yoksa minimal test verisi olustur
    if not os.path.exists("datasets/raw/mushroom.txt"):
        with open("datasets/raw/mushroom.txt", "w") as f:
            f.write("1 2 3 4 5\n2 3 5 6\n1 3 5 7\n2 4 6 8\n1 2 5 9\n")
        print("[INFO] Test verisi olusturuldu (gercek dataset Task 3'te indirilecek)")

    results = {}
    print(f"{'Algoritma':<20} {'SPMF Adi':<25} {'Kat':<5} {'Durum'}")
    print("-" * 70)

    for name, cfg in ALGORITHMS.items():
        if cfg.get("available") is True:
            status = "MEVCUT (onceden bilinen)"
            results[name] = True
        elif cfg.get("available") is False:
            status = "YOK (SPMF disi)"
            results[name] = False
        elif cfg.get("spmf_name") is None:
            status = "SPMF ADI YOK"
            results[name] = False
        else:
            # available=None -> kontrol et
            available = check_spmf_algorithm(cfg["spmf_name"])
            status = "MEVCUT" if available else "YOK"
            results[name] = available

        print(f"{name:<20} {str(cfg.get('spmf_name', 'N/A')):<25} {cfg['category']:<5} {status}")

    return results

if __name__ == "__main__":
    results = main()
    available_count = sum(1 for v in results.values() if v)
    print(f"\nOzet: {available_count}/{len(results)} algoritma mevcut")
