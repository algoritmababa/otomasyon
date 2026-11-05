# otomasyon

`ref.txt` (adı/yolu değiştirilebilir) güncellenip yazma işlemi bittiğinde
(mtime_ns + boyut 5 sn boyunca sabit, 0.5 sn kontrol aralığı) tetiklenen iki bağımsız script.
İlk çalıştırmada mevcut dosya referans alınır, her güncellemede işlem yalnızca bir kez yapılır.
Python 3.10.6 / 3.10.12 uyumlu, harici Python bağımlılığı yoktur.

## 1) `vscode_chat_otomasyon.py` — Windows

VS Code'u öne getirir, Chat panelini kısayolla açar, mesajı yazar ve Enter'a basar.
Ayarlar dosyanın başında: `REF_FILE_PATH`, `CHAT_MESSAGE`, `CHAT_SHORTCUT`, `VSCODE_WINDOW_TITLE`.

Kurulum: yalnızca Python 3.10 (ek paket yok).

```bat
python vscode_chat_otomasyon.py
python vscode_chat_otomasyon.py "C:\proje\ref.txt"
```

## 2) `cmake_build_otomasyon.py` — Ubuntu

`ref.txt` güncellenince CMake ile configure + build yapar, başarılıysa executable'ı çalıştırır.
Derleme çıktısı gizlenir, yalnızca hata olursa gösterilir (`SHOW_BUILD_OUTPUT`).
Derleme başarısız olsa bile mevcut (eski) executable çalıştırılır (`RUN_EVEN_IF_BUILD_FAILS`).
Programın kendi çıktısı her zaman görünür.
Ayarlar dosyanın başında: `REF_FILE_PATH`, `BUILD_ENABLED`, `PROJECT_DIR`, `BUILD_DIR`, `BUILD_TYPE`,
`EXECUTABLE_PATH`, `EXECUTABLE_ARGS`, `WAIT_FOR_EXECUTABLE`, `SHOW_BUILD_OUTPUT`.

```bash
sudo apt update && sudo apt install -y cmake build-essential python3
python3 cmake_build_otomasyon.py
```
