# -*- coding: utf-8 -*-
"""
SCRIPT 2 - Ubuntu: CMake Build Otomasyonu
=========================================

ref.txt dosyasini izler. Dosya guncellenip yazma islemi tamamen bittiginde
(son degistirilme zamani ve boyutu STABLE_SECONDS boyunca degismezse):
  1. CMake projesini yapilandirir (configure) ve derler (build),
  2. Derleme basariliysa olusan executable dosyasini calistirir.

Harici Python bagimliligi YOKTUR (sadece standart kutuphane).

Uyumluluk : Python 3.10.6 / 3.10.12 (Ubuntu)
Kurulum   : sudo apt update && sudo apt install -y cmake build-essential python3
Calistirma: python3 cmake_build_otomasyon.py
            python3 cmake_build_otomasyon.py /yol/ref.txt   (opsiyonel yol)
Durdurma  : Ctrl+C
"""

# =============================================================================
# KONFIGURASYON - Sadece bu bolumu degistirmeniz yeterlidir
# =============================================================================

# Izlenecek dosyanin tam yolu (adi ve konumu serbestce degistirilebilir).
# Komut satirindan ilk arguman olarak verilirse o deger kullanilir.
REF_FILE_PATH = "/home/kullanici/proje/ref.txt"

# True : ref.txt guncellenince once CMake ile derlenir, basariliysa EXECUTABLE_PATH calistirilir.
# False: Derleme ATLANIR; EXECUTABLE_PATH (ornek: bir .sh scripti) dogrudan calistirilir.
BUILD_ENABLED = True

# CMake proje dizini (CMakeLists.txt bu dizinde aranir).
PROJECT_DIR = "/home/kullanici/proje"

# Build klasoru. Goreli yol verilirse PROJECT_DIR'e gore hesaplanir.
# Klasor yoksa otomatik olusturulur.
BUILD_DIR = "build"

# Build konfigurasyonu: "Release" veya "Debug" (RelWithDebInfo, MinSizeRel de olur).
BUILD_TYPE = "Release"

# Calistirilacak dosyanin yolu (derlenen program ya da ornek.sh gibi bir script).
# Tam yol onerilir: "/home/kullanici/proje/ornek.sh"
# Goreli yol verilirse: BUILD_ENABLED=True ise BUILD_DIR'e, False ise PROJECT_DIR'e gore hesaplanir.
# Shell script icin: ilk satirda "#!/bin/bash" olmali ve "chmod +x ornek.sh" yapilmali.
EXECUTABLE_PATH = "uygulama"

# Executable'a verilecek komut satiri argumanlari (ornek: ["--verbose", "girdi.txt"]).
EXECUTABLE_ARGS = []

# True : Program bitene kadar beklenir (cikti terminalde gorunur, sonra izlemeye donulur).
# False: Program arka planda baslatilir, izleme devam eder; yeni guncellemede
#        eski calisan program durdurulup yeniden derlenir/calistirilir.
WAIT_FOR_EXECUTABLE = True

# False: CMake configure/build ciktisi gizlenir; sadece hata olursa gosterilir.
# True : Tum derleme ciktisi terminalde gorunur.
# (Calistirilan programin kendi ciktisi her zaman gorunur.)
SHOW_BUILD_OUTPUT = False

# True : Derleme basarisiz olsa bile build klasorunde mevcut olan (bir onceki basarili
#        derlemeden kalan) executable yine de calistirilir.
# False: Derleme basarisizsa executable calistirilmaz.
RUN_EVEN_IF_BUILD_FAILS = True

# Paralel derleme is sayisi (None = CMake/derleyici varsayilani).
PARALLEL_JOBS = None

# Ek CMake configure argumanlari (ornek: ["-G", "Ninja"] veya ["-DOZELLIK=ON"]).
EXTRA_CMAKE_ARGS = []

# Dosya izleme ayarlari.
POLL_INTERVAL = 0.5     # Kontrol araligi (saniye)
STABLE_SECONDS = 5.0    # mtime + boyut bu sure boyunca degismezse yazma bitti kabul edilir

# =============================================================================
# KOD - Normalde degistirmeniz gerekmez
# =============================================================================

import os
import subprocess
import sys
import time

# Arka planda calisan executable (WAIT_FOR_EXECUTABLE = False iken kullanilir).
running_process = None


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def error(msg):
    print("[%s] HATA: %s" % (time.strftime("%H:%M:%S"), msg), file=sys.stderr, flush=True)


def resolve_paths():
    """Konfigurasyondaki yollari mutlak yola cevirir."""
    project_dir = os.path.abspath(os.path.expanduser(PROJECT_DIR))
    build_dir = os.path.join(project_dir, os.path.expanduser(BUILD_DIR))
    base_dir = build_dir if BUILD_ENABLED else project_dir
    exe_path = os.path.join(base_dir, os.path.expanduser(EXECUTABLE_PATH))
    return project_dir, os.path.abspath(build_dir), os.path.abspath(exe_path)


def run_command(cmd, cwd=None):
    """
    Derleme komutunu calistirir; basariliysa True dondurur.
    SHOW_BUILD_OUTPUT=False ise cikti yakalanir ve yalnizca hata olursa yazdirilir.
    """
    try:
        if SHOW_BUILD_OUTPUT:
            log("Komut: %s" % " ".join(cmd))
            result = subprocess.run(cmd, cwd=cwd)
        else:
            result = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
            if result.returncode != 0:
                output = result.stdout.decode("utf-8", errors="replace")
                print(output, file=sys.stderr, end="" if output.endswith("\n") else "\n")
    except FileNotFoundError:
        error("'%s' bulunamadi. Kurulu mu? (sudo apt install cmake build-essential)" % cmd[0])
        return False
    if result.returncode != 0:
        error("Komut basarisiz oldu (cikis kodu: %d)" % result.returncode)
        return False
    return True


def stop_running_process():
    """Arka planda calisan onceki executable varsa durdurur."""
    global running_process
    if running_process is not None and running_process.poll() is None:
        log("Onceki calisan program durduruluyor (PID %d)..." % running_process.pid)
        running_process.terminate()
        try:
            running_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            running_process.kill()
            running_process.wait()
    running_process = None


def build_project(project_dir, build_dir):
    """CMake configure + build yapar; basariliysa True dondurur."""
    # 1) CMakeLists.txt kontrolu
    if not os.path.isfile(os.path.join(project_dir, "CMakeLists.txt")):
        error("CMakeLists.txt bulunamadi: %s" % project_dir)
        return False

    # 2) Build klasoru yoksa olustur
    os.makedirs(build_dir, exist_ok=True)

    log("Derleniyor (%s)..." % BUILD_TYPE)

    # 3) Configure: cmake -S <proje> -B <build> -DCMAKE_BUILD_TYPE=<tip>
    configure_cmd = ["cmake", "-S", project_dir, "-B", build_dir,
                     "-DCMAKE_BUILD_TYPE=%s" % BUILD_TYPE] + list(EXTRA_CMAKE_ARGS)
    if not run_command(configure_cmd):
        error("CMake yapilandirmasi basarisiz.")
        return False

    # 4) Build: cmake --build <build> --config <tip> [--parallel N]
    build_cmd = ["cmake", "--build", build_dir, "--config", BUILD_TYPE]
    if PARALLEL_JOBS:
        build_cmd += ["--parallel", str(PARALLEL_JOBS)]
    if not run_command(build_cmd):
        error("Derleme basarisiz.")
        return False
    log("Derleme basarili.")
    return True


def build_and_run():
    """Guncelleme tamamlandiginda yapilacak islem: (istenirse) derle ve calistir."""
    global running_process
    project_dir, build_dir, exe_path = resolve_paths()

    stop_running_process()

    if BUILD_ENABLED and not build_project(project_dir, build_dir):
        if not RUN_EVEN_IF_BUILD_FAILS:
            error("Executable calistirilmayacak (RUN_EVEN_IF_BUILD_FAILS = False).")
            return
        # Derleme basarisiz: varsa onceki derlemeden kalan executable calistirilir.
        log("UYARI: Derleme basarisiz, mevcut (eski) executable calistirilacak.")

    # 5) Executable kontrolu ve calistirma (./executable mantigi)
    if not os.path.isfile(exe_path):
        error("Executable bulunamadi: %s (EXECUTABLE_PATH ayarini kontrol edin)" % exe_path)
        return
    if not os.access(exe_path, os.X_OK):
        error("Dosya calistirilabilir degil: %s (chmod +x gerekebilir)" % exe_path)
        return

    cmd = [exe_path] + list(EXECUTABLE_ARGS)
    exe_dir = os.path.dirname(exe_path)  # program kendi klasorunde calistirilir
    log("Calistiriliyor: %s" % " ".join(cmd))
    try:
        if WAIT_FOR_EXECUTABLE:
            result = subprocess.run(cmd, cwd=exe_dir)
            if result.returncode == 0:
                log("Program basariyla sonlandi.")
            else:
                error("Program %d cikis koduyla sonlandi." % result.returncode)
        else:
            running_process = subprocess.Popen(cmd, cwd=exe_dir)
            log("Program arka planda baslatildi (PID %d)." % running_process.pid)
    except OSError as exc:
        error("Program calistirilamadi: %s" % exc)


# ---- Dosya izleme --------------------------------------------------------------
def get_signature(path):
    """Dosyanin (st_mtime_ns, st_size) bilgisini dondurur; dosya yoksa None."""
    try:
        st = os.stat(path)
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return None


def watch(path, on_update):
    """
    Dosyayi izler. Mantik:
      - Baslangictaki durum 'islenmis' kabul edilir (ilk calismada tetiklenmez).
      - Imza (mtime_ns, boyut) islenmis imzadan farkliysa bekleyen guncelleme vardir.
      - Imza STABLE_SECONDS boyunca hic degismezse yazma bitmis sayilir,
        on_update() BIR KEZ cagrilir ve bu imza 'islenmis' olarak kaydedilir.
    """
    processed = get_signature(path)   # baslangic referansi
    last_seen = processed
    last_change = time.monotonic()

    log("Izleniyor: %s" % path)
    if processed is None:
        error("Dosya su an mevcut degil; olusturulmasi bekleniyor.")

    while True:
        time.sleep(POLL_INTERVAL)
        current = get_signature(path)
        now = time.monotonic()

        if current != last_seen:          # yeni bir degisiklik: sayaci sifirla
            last_seen = current
            last_change = now
            continue

        if (current is not None and current != processed
                and now - last_change >= STABLE_SECONDS):
            log("Guncelleme tamamlandi, islem baslatiliyor...")
            try:
                on_update()
            except Exception as exc:  # izlemeyi durdurmadan hatayi raporla
                error(str(exc))
            processed = current           # bu guncelleme bir daha islenmez


def main():
    path = os.path.abspath(os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else REF_FILE_PATH))
    project_dir, build_dir, exe_path = resolve_paths()
    log("Proje dizini : %s" % project_dir)
    if BUILD_ENABLED:
        log("Build dizini : %s (%s)" % (build_dir, BUILD_TYPE))
    else:
        log("Derleme      : KAPALI (dosya dogrudan calistirilacak)")
    log("Executable   : %s" % exe_path)
    try:
        watch(path, build_and_run)
    except KeyboardInterrupt:
        print()
        log("Durduruldu.")
    finally:
        stop_running_process()


if __name__ == "__main__":
    main()
