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


def run_spmf(
    spmf_name: str,
    input_file: str,
    output_file: str,
    params: list,
    timeout: int = 300,
) -> dict:
    """
    SPMF algoritmasini calistirir.
    Returns: runtime_s, peak_memory_mb, generator_count, returncode, timed_out
    """
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    cmd = (["java", "-jar", SPMF_JAR, "run", spmf_name,
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
            lines = out_path.read_text(encoding="utf-8", errors="ignore").strip().splitlines()
            generator_count = len([l for l in lines if l.strip()])
    except Exception:
        pass

    return {
        "runtime_s": round(runtime_s, 4),
        "peak_memory_mb": round(monitor.peak_mb, 2),
        "returncode": proc.returncode,
        "stdout": stdout[:2000],
        "stderr": stderr[:2000],
        "generator_count": generator_count,
        "timed_out": timed_out,
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
