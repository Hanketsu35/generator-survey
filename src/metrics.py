# src/metrics.py
import subprocess
import time
import threading
import psutil
import json
from pathlib import Path

SPMF_JAR = "spmf/spmf.jar"
RESULTS_RAW = Path("results/raw")
RESULTS_RAW.mkdir(parents=True, exist_ok=True)


class MemoryMonitor(threading.Thread):
    """subprocess'in peak RSS memory'sini arka planda takip eder."""
    def __init__(self, pid: int, interval: float = 0.1):
        super().__init__(daemon=True)
        self.pid = pid
        self.interval = interval
        self.peak_mb: float = 0.0
        self._stop_event = threading.Event()

    def run(self):
        try:
            proc = psutil.Process(self.pid)
            while not self._stop_event.is_set():
                try:
                    mem = proc.memory_info().rss
                    for child in proc.children(recursive=True):
                        try:
                            mem += child.memory_info().rss
                        except psutil.NoSuchProcess:
                            pass
                    self.peak_mb = max(self.peak_mb, mem / 1024 / 1024)
                except psutil.NoSuchProcess:
                    break
                self._stop_event.wait(self.interval)
        except Exception:
            pass

    def stop(self):
        self._stop_event.set()



def classify_failure(returncode, stdout, stderr, timed_out) -> str:
    """
    Bir kosunun sessizce bozulup bozulmadigini belirler.

    Timeout bir hata DEGILDIR: protokolun parcasi (DNF olarak raporlanir).
    Asil tehlike, sifir-disi cikis kodu ile biten ama arkasinda kismi cikti
    dosyasi birakan kosulardir -- bunlar duz satir sayimiyla "basarili" gibi
    gorunur.  Bulunan ornek: Arima/chess ve Arima/connect, varsayilan ~4 GB
    JVM heap'ini tuketip java.lang.OutOfMemoryError ile cikti.

    Dondurur: bos string (sorun yok) veya kisa hata etiketi.
    """
    if timed_out:
        return ""
    txt = (stdout or "") + (stderr or "")
    if "OutOfMemoryError" in txt:
        return "java.lang.OutOfMemoryError: Java heap space"
    if "StackOverflowError" in txt:
        return "java.lang.StackOverflowError"
    if returncode not in (0, None):
        return "non-zero exit code %s" % returncode
    return ""


def run_spmf(
    spmf_name: str,
    input_file: str,
    output_file: str,
    params: list,
    timeout: int = 300,
    count_fn=None,
    max_heap: str = None,
) -> dict:
    """
    SPMF algoritmasini calistirir.

    max_heap: None ise JVM varsayilan heap'i kullanilir (fiziksel RAM'in 1/4'u).
    Ana protokol BU varsayilani kullanir; boylece tum JVM algoritmalari ayni
    kosullarda olculur. "-Xmx12g" gibi bir deger yalnizca TANI amacli
    yeniden kosularda verilir (bkz. tools/rerun_arima_xmx.py): amac, bir
    OutOfMemoryError'un algoritmanin sinirindan mi yoksa yalnizca varsayilan
    heap tavanindan mi kaynaklandigini ayirt etmektir.

    Returns: runtime_s, peak_memory_mb, generator_count, returncode, timed_out
    """
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    heap_flags = [max_heap] if max_heap else []
    cmd = (["java"] + heap_flags + ["-jar", SPMF_JAR, "run", spmf_name,
            input_file, output_file] + [str(p) for p in params])

    t0 = time.perf_counter()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    monitor = MemoryMonitor(proc.pid)
    monitor.start()

    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        # Windows'ta proc.kill() sadece ana processi öldürür; Java child tree kalır.
        # psutil ile tüm process ağacını temizle.
        try:
            parent = psutil.Process(proc.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
        except psutil.NoSuchProcess:
            pass
        try:
            stdout, stderr = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            stdout, stderr = b"", b""
        timed_out = True

    monitor.stop()
    monitor.join()
    runtime_s = time.perf_counter() - t0

    generator_count = 0
    try:
        out_path = Path(output_file)
        if out_path.exists():
            if count_fn:
                generator_count = count_fn(out_path)
            else:
                generator_count = count_plain_lines(out_path)
    except Exception:
        pass

    # Cokme tespiti: JVM heap tukendiginde SPMF stderr'e OutOfMemoryError yazip
    # sifir-disi kodla cikar, ama kismi (truncated) bir cikti dosyasi birakir.
    # Bu dosya sayilirsa kosu "basarili" gorunur ve YANLIS sayim CSV'ye girer.
    # Bu yuzden sayimi gecersiz kilip hatayi acikca raporluyoruz.
    failure = classify_failure(proc.returncode, stdout, stderr, timed_out)
    if failure:
        generator_count = None

    return {
        "runtime_s": round(runtime_s, 4),
        "peak_memory_mb": round(monitor.peak_mb, 2),
        "returncode": proc.returncode,
        "stdout": stdout[:2000],
        "stderr": stderr[:2000],
        "generator_count": generator_count,
        "timed_out": timed_out,
        "failure": failure,
    }


def run_external(
    exe: str,
    cmd_args: list,
    output_file: str,
    timeout: int = 600,
    count_fn=None,
) -> dict:
    """
    SPMF olmayan bir executable calistirir.
    exe: path to executable
    cmd_args: list of string args (exe kendisi dahil degil)
    output_file: okunacak cikti dosyasi
    count_fn: output dosyasindan generator sayisini sayan fonksiyon (None = satir sayisi)
    """
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    exe_abs = str(Path(exe).resolve())
    cmd = [exe_abs] + [str(a) for a in cmd_args]

    t0 = time.perf_counter()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    monitor = MemoryMonitor(proc.pid)
    monitor.start()

    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            parent = psutil.Process(proc.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
        except psutil.NoSuchProcess:
            pass
        try:
            stdout, stderr = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            stdout, stderr = b"", b""
        timed_out = True

    monitor.stop()
    monitor.join()
    runtime_s = time.perf_counter() - t0

    generator_count = 0
    try:
        out_path = Path(output_file)
        if out_path.exists():
            if count_fn:
                generator_count = count_fn(out_path)
            else:
                lines = out_path.read_text(encoding="utf-8", errors="ignore").strip().splitlines()
                generator_count = len([l for l in lines if l.strip()])
    except Exception:
        pass

    return {
        "runtime_s": round(runtime_s, 4),
        "peak_memory_mb": round(monitor.peak_mb, 2),
        "returncode": proc.returncode,
        "stdout": (stdout or "")[:2000],
        "stderr": (stderr or "")[:2000],
        "generator_count": generator_count,
        "timed_out": timed_out,
    }


def count_transactions(input_file: str) -> int:
    """Dosyadaki transaction (satir) sayisini sayar."""
    count = 0
    with open(input_file, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def count_plain_lines(out_path: Path) -> int:
    """Bos olmayan satir sayisi. Ciktisi 'her satir bir pattern' olan
    algoritmalar icin dogru sayim (DefMe, TalkyG, TalkyG_Diffset, VGEN, ...)."""
    n = 0
    with open(out_path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def count_pascal_generators(out_path: Path) -> int:
    """Pascal (SPMF) TUM frequent itemset'leri yazar; her satir
    '#IS_GENERATOR: true|false' etiketi tasir.  Jeneratör sayisi = 'true' satirlari.

    Duz satir sayimi frequent itemset sayisini verir (connect/minsup=0.7'de
    80x fazla), bu yuzden etiket filtrelemesi zorunludur.
    """
    n = 0
    with open(out_path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "IS_GENERATOR: true" in line:
                n += 1
    return n


def count_zart_generators(out_path: Path) -> int:
    """Zart (SPMF) insan-okunabilir bir rapor yazar:

        ======= List of closed itemsets and their generators ============
         CLOSED :
           90  #SUP: 8416
           GENERATOR(S) :
             EMPTYSET

    Jeneratörler 'GENERATOR(S) :' satirindan sonra, bir sonraki ' CLOSED :'
    satirina kadar gelen satirlardir.  Duz satir sayimi baslik/bos satirlari
    da sayar (mushroom/minsup=0.2'de 34x fazla).
    """
    n = 0
    in_gen = False
    with open(out_path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            if s.startswith("====="):
                in_gen = False
            elif s.startswith("CLOSED"):
                in_gen = False
            elif s.startswith("GENERATOR(S)"):
                in_gen = True
            elif in_gen:
                n += 1
    return n


def count_borgelt_generators(out_path: Path) -> int:
    """Borgelt apriori/eclat/fpgrowth '-tg' ciktisi: her satir bir jeneratör,
    format 'item1 item2 ... (support%)'."""
    return count_plain_lines(out_path)


def count_grgrowth_generators(out_path: Path) -> int:
    """GrGrowth .txt dosyasindaki generator sayisini sayar (bos satirlar haric)."""
    lines = out_path.read_text(encoding="utf-8", errors="ignore").strip().splitlines()
    return len([l for l in lines if l.strip()])


def count_fgcstream_generators(out_path: Path) -> int:
    """FGC_Stream output dosyasindaki toplam generator sayisini sayar.
    Format: 's=X fermeture : A B generateurs : G1 G2  G3 G4'
    Generatorler 'generateurs :' sonrasinda iki boslukla ayrilir.
    """
    total = 0
    for line in out_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "generateurs :" not in line:
            continue
        gen_part = line.split("generateurs :", 1)[1].strip()
        if not gen_part:
            total += 1  # empty set generator
        else:
            # Generators separated by double spaces
            gens = [g.strip() for g in gen_part.split("  ") if g.strip()]
            total += len(gens)
    return total


def save_result(record: dict, filename: str):
    path = RESULTS_RAW / filename
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
