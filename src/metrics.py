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
    """subprocess'in peak RSS memory'sini arka planda takip eder.

    A run shorter than the thread's own startup latency used to be recorded as
    0.0 MB: ``psutil.Process(pid)`` raised ``NoSuchProcess`` because the child
    had already exited, the outer handler swallowed it, and ``peak_mb`` kept its
    initial zero. Zero is not a measurement -- no process occupies no memory --
    and on the synthetic sweep, where the native miners finish in about 5 ms,
    every Borgelt run was reported that way.

    Two changes. ``sample()`` is callable synchronously, so a caller takes one
    reading immediately after spawning rather than waiting for the thread to be
    scheduled; and ``n_samples`` records whether anything was ever read, so a
    caller can report an honest missing value instead of a fabricated zero.
    Both only ever add samples, so no previously recorded peak can fall.
    """
    def __init__(self, pid: int, interval: float = 0.1):
        super().__init__(daemon=True)
        self.pid = pid
        self.interval = interval
        self.peak_mb: float = 0.0
        self.n_samples: int = 0
        self._stop_event = threading.Event()

    def sample(self) -> bool:
        """Read RSS of the process tree once. False once the process is gone."""
        try:
            proc = psutil.Process(self.pid)
            mem = proc.memory_info().rss
            for child in proc.children(recursive=True):
                try:
                    mem += child.memory_info().rss
                except psutil.NoSuchProcess:
                    pass
            self.peak_mb = max(self.peak_mb, mem / 1024 / 1024)
            self.n_samples += 1
            return True
        except psutil.NoSuchProcess:
            return False
        except Exception:
            return False

    @property
    def measured(self) -> bool:
        return self.n_samples > 0

    def run(self):
        while not self._stop_event.is_set():
            if not self.sample():
                break
            self._stop_event.wait(self.interval)

    def stop(self):
        self._stop_event.set()


#: Sampling interval of the peak-RSS monitor, in seconds. 0.1 is what
#: ``results/summary.csv`` was measured with, and it is the default so that new
#: runs stay comparable with the published table. The synthetic sweep lowers it,
#: because its native-miner runs last about 10 ms and a 0.1 s poll takes at most
#: one reading of them.
MONITOR_INTERVAL = 0.1

#: Address-space cap for NATIVE miners, in MB; None means no cap, which is how
#: results/summary.csv was measured. The JVM implementations have always been
#: capped -- the default heap is a quarter of physical RAM -- but a native
#: binary could take the whole machine: Borgelt's apriori on bms1 at a support
#: of 11 transactions grew to 28.9 GB resident and the kernel's OOM killer took
#: it and the benchmark with it. A cap equal to the JVM default gives every
#: implementation the same memory budget, and turns running out of it into a
#: recorded failure instead of a machine that stops. Set it only for runs that
#: are not compared against the uncapped published table.
NATIVE_MEM_LIMIT_MB = None


def _address_space_limiter(limit_mb):
    """preexec_fn setting RLIMIT_AS in the child, or None where unsupported."""
    if not limit_mb:
        return None
    try:
        import resource
    except ImportError:                                  # Windows
        return None
    lim = int(limit_mb) * 1024 * 1024

    def _set():
        resource.setrlimit(resource.RLIMIT_AS, (lim, lim))
    return _set


def _children_maxrss_mb():
    """Kernel peak RSS over reaped children, in MB -- NOT usable here.

    ``getrusage(RUSAGE_CHILDREN).ru_maxrss`` is measured by the kernel instead
    of sampled, so it looked like the right instrument for runs too short to
    poll. Measured, it is not: it reported about 42 MB for *every* miner on the
    synthetic pilot, including the native ones that use around 2 MB on real
    data, and it reported nearly the same number for all nine.

    The cause is ``fork``. ``subprocess.Popen`` with pipes forks before it
    execs, and between those two points the child shares the parent's address
    space, so the child's RSS high-water mark starts at the parent's footprint.
    The parent here is a Python worker with numpy and pandas imported -- about
    42 MB. The counter therefore measures the harness, not the miner, and no
    amount of per-child attribution fixes that.

    Kept, unused by the measurement path, so the finding is recorded where the
    next person will look for it rather than being rediscovered.
    """
    try:
        import resource
    except ImportError:
        return None
    try:
        ru = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    except (OSError, ValueError):
        return None
    if not ru:
        return 0.0
    import sys
    return ru / 1024.0 if sys.platform != "darwin" else ru / 1024.0 / 1024.0


def peak_rss_mb(monitor, rss_before=None):
    """Sampled peak RSS of the run just finished, or None if never sampled.

    None rather than 0.0 is the point. A run shorter than the sampler's startup
    latency yields no reading at all, and recording that as zero asserts that a
    process used no memory. Downstream analysis must treat these as missing --
    on the synthetic sweep the sub-10 ms native runs are the affected group, so
    any memory comparison there has to be restricted to runs long enough to
    have been observed.
    """
    if monitor.measured:
        return round(monitor.peak_mb, 2)
    return None



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

    monitor = MemoryMonitor(proc.pid, interval=MONITOR_INTERVAL)
    # One reading now: a run shorter than thread-startup latency would otherwise
    # never be sampled at all and be recorded as 0.0 MB.
    monitor.sample()
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
        "peak_memory_mb": peak_rss_mb(monitor),
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
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            preexec_fn=_address_space_limiter(NATIVE_MEM_LIMIT_MB))

    monitor = MemoryMonitor(proc.pid, interval=MONITOR_INTERVAL)
    # One reading now: a run shorter than thread-startup latency would otherwise
    # never be sampled at all and be recorded as 0.0 MB.
    monitor.sample()
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
        "peak_memory_mb": peak_rss_mb(monitor),
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
