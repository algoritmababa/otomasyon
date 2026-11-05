# -*- coding: utf-8 -*-
"""
SCRIPT 2 - Ubuntu: ref.txt Guncellenince Shell Script Calistirma
=================================================================

ref.txt dosyasini izler. Dosya guncellenip yazma islemi tamamen bittiginde
(son degistirilme zamani ve boyutu STABLE_SECONDS boyunca degismezse)
SCRIPT_PATH ile verilen .sh dosyasini ./ornek.sh mantigiyla BIR KEZ calistirir.
Derleme gerekiyorsa bu islem .sh dosyasinin icinde yapilir.

Varsayilan olarak .sh dosyasinin ciktisi terminale yazdirilmaz;
yalnizca hata olursa (cikis kodu 0 degilse) cikti ve hata mesaji gosterilir.

Harici bagimlilik YOKTUR (sadece Python standart kutuphanesi).

Uyumluluk : Python 3.10.6 / 3.10.12 (Ubuntu)
Hazirlik  : chmod +x /home/kullanici/proje/ornek.sh   (ilk satir: #!/bin/bash)
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

# Calistirilacak shell script'in tam yolu.
# Ilk satirinda "#!/bin/bash" olmali ve "chmod +x" ile calistirma izni verilmeli.
SCRIPT_PATH = "/home/kullanici/proje/ornek.sh"

# Script'e verilecek argumanlar (ornek: ["Release"]).
SCRIPT_ARGS = []

# False: Script'in (derleme vb.) ciktisi gizlenir; sadece hata olursa gosterilir.
# True : Script'in tum ciktisi terminalde canli gorunur.
SHOW_SCRIPT_OUTPUT = False

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


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def error(msg):
    print("[%s] HATA: %s" % (time.strftime("%H:%M:%S"), msg), file=sys.stderr, flush=True)


def run_script():
    """Guncelleme tamamlandiginda yapilacak islem: .sh dosyasini calistir."""
    script = os.path.abspath(os.path.expanduser(SCRIPT_PATH))

    if not os.path.isfile(script):
        error("Script bulunamadi: %s (SCRIPT_PATH ayarini kontrol edin)" % script)
        return
    if not os.access(script, os.X_OK):
        error("Script calistirilabilir degil: %s (chmod +x %s)" % (script, script))
        return

    cmd = [script] + list(SCRIPT_ARGS)
    log("Calistiriliyor: %s" % " ".join(cmd))
    try:
        if SHOW_SCRIPT_OUTPUT:
            # Cikti dogrudan terminale akar.
            result = subprocess.run(cmd, cwd=os.path.dirname(script))
            output = ""
        else:
            # Cikti (stdout + stderr) yakalanir, sadece hata durumunda yazdirilir.
            result = subprocess.run(cmd, cwd=os.path.dirname(script),
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            output = result.stdout.decode("utf-8", errors="replace")
    except OSError as exc:
        # Ornek: ilk satirda #!/bin/bash yoksa "Exec format error"
        error("Script calistirilamadi: %s" % exc)
        return

    if result.returncode == 0:
        log("Script basariyla tamamlandi.")
    else:
        if output:
            print(output, file=sys.stderr, end="" if output.endswith("\n") else "\n")
        error("Script %d cikis koduyla sonlandi." % result.returncode)


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
            log("Guncelleme tamamlandi, script baslatiliyor...")
            try:
                on_update()
            except Exception as exc:  # izlemeyi durdurmadan hatayi raporla
                error(str(exc))
            processed = current           # bu guncelleme bir daha islenmez


def main():
    path = os.path.abspath(os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else REF_FILE_PATH))
    log("Script : %s" % os.path.abspath(os.path.expanduser(SCRIPT_PATH)))
    try:
        watch(path, run_script)
    except KeyboardInterrupt:
        print()
        log("Durduruldu.")


if __name__ == "__main__":
    main()
