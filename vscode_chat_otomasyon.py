# -*- coding: utf-8 -*-
"""
SCRIPT 1 - Windows: VS Code Chat Otomasyonu
============================================

ref.txt dosyasini izler. Dosya guncellenip yazma islemi tamamen bittiginde
(son degistirilme zamani ve boyutu STABLE_SECONDS boyunca degismezse):
  1. VS Code penceresini one getirir,
  2. Chat panelini acar / odaklar (CHAT_SHORTCUT),
  3. CHAT_MESSAGE metnini chat input alanina yazar,
  4. Enter ile gonderir.

Harici bagimlilik YOKTUR: sadece Python standart kutuphanesi (ctypes ile
Windows API) kullanilir.

Uyumluluk : Python 3.10.6 / 3.10.12 (Windows)
Calistirma: python vscode_chat_otomasyon.py
            python vscode_chat_otomasyon.py "C:\\proje\\ref.txt"   (opsiyonel yol)
Durdurma  : Ctrl+C
"""

# =============================================================================
# KONFIGURASYON - Sadece bu bolumu degistirmeniz yeterlidir
# =============================================================================

# Izlenecek dosyanin tam yolu (adi ve konumu serbestce degistirilebilir).
# Komut satirindan ilk arguman olarak verilirse o deger kullanilir.
REF_FILE_PATH = r"C:\proje\ref.txt"

# Chat'e gonderilecek mesaj.
CHAT_MESSAGE = "ref güncellendi sıradaki adıma geçilsin"

# Chat panelinin nasil acilacagi:
#   "shortcut" : CHAT_SHORTCUT kisayolu gonderilir.
#   "command"  : Komut paleti (Ctrl+Shift+P) acilir, CHAT_COMMAND yazilip Enter'a basilir.
#                Bir uzantinin (Claude Code, Cline, Continue vb.) chat'ini hedeflemek
#                icin en kolay yol budur; kisayol atamaniz gerekmez.
CHAT_OPEN_METHOD = "shortcut"

# "shortcut" modu: Chat panelini acan/odaklayan kisayol.
# Ornekler: "ctrl+alt+i" (VS Code varsayilani - Chat), "ctrl+shift+i",
#           "ctrl+i" (inline chat). Tuslar '+' ile ayrilir.
# Art arda basilmasi gereken birden fazla tus varsa liste olarak yazin;
# her biri sirayla, aralarinda SHORTCUT_STEP_DELAY beklenerek basilir:
#   CHAT_SHORTCUT = ["ctrl+alt+k", "enter"]
CHAT_SHORTCUT = "ctrl+alt+i"
SHORTCUT_STEP_DELAY = 0.5   # Liste halindeki tuslar arasi bekleme (saniye)

# "command" modu: Komut paletinde gorunen komut adi (birebir ayni yazilmali).
# Dogru adi bulmak icin VS Code'da Ctrl+Shift+P'ye basip uzantinin adini yazin
# ve chat'i acan/odaklayan komutu (genelde "... Focus ..." / "... Open ...") secin.
# NOT: VS Code arayuzu Turkce ise komut adlari da Turkce gorunur, o hali yazilmalidir.
CHAT_COMMAND = "Chat: Open Chat"
COMMAND_PALETTE_SHORTCUT = "ctrl+shift+p"
DELAY_IN_PALETTE = 0.8      # Komut adi yazildiktan sonra listenin filtrelenmesi icin

# VS Code penceresini bulmak icin pencere basliginda aranacak metin.
# Birden fazla VS Code penceresi varsa, ornegin proje adini yazabilirsiniz:
#   "proje_adi - Visual Studio Code"
VSCODE_WINDOW_TITLE = "Visual Studio Code"

# Dosya izleme ayarlari.
POLL_INTERVAL = 0.5     # Kontrol araligi (saniye)
STABLE_SECONDS = 5.0    # mtime + boyut bu sure boyunca degismezse yazma bitti kabul edilir

# Bekleme sureleri (saniye) - yavas sistemlerde artirilabilir.
DELAY_AFTER_FOCUS = 0.7     # Pencere one geldikten sonra
DELAY_AFTER_SHORTCUT = 1.0  # Chat paneli acildiktan sonra
DELAY_BEFORE_ENTER = 0.3    # Mesaj yazildiktan sonra, Enter'dan once
CHAR_DELAY = 0.005          # Her karakter arasi bekleme

# =============================================================================
# KOD - Normalde degistirmeniz gerekmez
# =============================================================================

import ctypes
import os
import sys
import time
from ctypes import wintypes

if sys.platform != "win32":
    print("HATA: Bu script yalnizca Windows uzerinde calisir.", file=sys.stderr)
    sys.exit(1)

user32 = ctypes.WinDLL("user32", use_last_error=True)

# ---- Windows API sabitleri ---------------------------------------------------
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
SW_RESTORE = 9
VK_MENU = 0x12  # Alt
VK_RETURN = 0x0D

# Kisayol metnindeki tus adlarinin sanal tus kodlari (Virtual-Key codes).
VK_CODES = {
    "ctrl": 0x11, "control": 0x11, "shift": 0x10, "alt": 0x12, "win": 0x5B,
    "enter": 0x0D, "esc": 0x1B, "escape": 0x1B, "tab": 0x09, "space": 0x20,
    "backspace": 0x08, "delete": 0x2E, "home": 0x24, "end": 0x23,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "`": 0xC0, ";": 0xBA, "=": 0xBB, ",": 0xBC, "-": 0xBD, ".": 0xBE,
    "/": 0xBF, "[": 0xDB, "\\": 0xDC, "]": 0xDD, "'": 0xDE,
}
for _i in range(1, 13):
    VK_CODES["f%d" % _i] = 0x6F + _i  # F1..F12


# ---- SendInput icin ctypes yapilari ------------------------------------------
# Union, 32/64 bit sistemlerde dogru INPUT boyutu icin tum uyeleri icermelidir.
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_size_t)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
user32.SendInput.restype = wintypes.UINT

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = (WNDENUMPROC, wintypes.LPARAM)
user32.GetWindowTextLengthW.argtypes = (wintypes.HWND,)
user32.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
user32.IsWindowVisible.argtypes = (wintypes.HWND,)
user32.IsIconic.argtypes = (wintypes.HWND,)
user32.ShowWindow.argtypes = (wintypes.HWND, ctypes.c_int)
user32.SetForegroundWindow.argtypes = (wintypes.HWND,)
user32.BringWindowToTop.argtypes = (wintypes.HWND,)
user32.GetForegroundWindow.restype = wintypes.HWND


def _send_inputs(inputs):
    """Hazirlanan INPUT listesini tek seferde isletim sistemine gonderir."""
    arr = (INPUT * len(inputs))(*inputs)
    sent = user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))
    if sent != len(inputs):
        raise OSError("SendInput basarisiz (hata kodu: %d)" % ctypes.get_last_error())


def _vk_input(vk, key_up=False):
    flags = KEYEVENTF_KEYUP if key_up else 0
    return INPUT(type=INPUT_KEYBOARD,
                 u=_INPUTUNION(ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=flags,
                                             time=0, dwExtraInfo=0)))


def _unicode_input(code_unit, key_up=False):
    flags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if key_up else 0)
    return INPUT(type=INPUT_KEYBOARD,
                 u=_INPUTUNION(ki=KEYBDINPUT(wVk=0, wScan=code_unit, dwFlags=flags,
                                             time=0, dwExtraInfo=0)))


def parse_shortcut(shortcut):
    """'ctrl+alt+i' gibi bir metni sanal tus kodu listesine cevirir."""
    codes = []
    for part in shortcut.lower().replace(" ", "").split("+"):
        if part in VK_CODES:
            codes.append(VK_CODES[part])
        elif len(part) == 1 and part.isalnum():
            codes.append(ord(part.upper()))  # A-Z ve 0-9 icin VK kodu = ASCII
        else:
            raise ValueError("Bilinmeyen tus: '%s' (kisayol: %s)" % (part, shortcut))
    return codes


def press_shortcut(shortcut):
    """Kisayolu basar: tuslari sirayla bas, ters sirayla birak."""
    codes = parse_shortcut(shortcut)
    inputs = [_vk_input(c) for c in codes] + [_vk_input(c, True) for c in reversed(codes)]
    _send_inputs(inputs)


def press_enter():
    _send_inputs([_vk_input(VK_RETURN), _vk_input(VK_RETURN, True)])


def type_text(text):
    """Metni Unicode olarak yazar (Turkce karakterler klavye duzeninden bagimsiz calisir)."""
    data = text.encode("utf-16-le")
    for i in range(0, len(data), 2):
        unit = int.from_bytes(data[i:i + 2], "little")
        _send_inputs([_unicode_input(unit), _unicode_input(unit, True)])
        if CHAR_DELAY:
            time.sleep(CHAR_DELAY)


def find_vscode_window(title_part):
    """Basliginda title_part gecen ilk gorunur pencerenin handle'ini dondurur."""
    found = []
    needle = title_part.lower()

    def callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        if needle in buf.value.lower():
            found.append(hwnd)
            return False  # bulundu, aramayi durdur
        return True

    user32.EnumWindows(WNDENUMPROC(callback), 0)
    return found[0] if found else None


def activate_window(hwnd):
    """Pencereyi (simge durumundaysa geri yukleyip) on plana getirir."""
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    # Windows, arka plandaki bir islemin pencere one getirmesini engelleyebilir.
    # Alt tusuna basip birakmak bu kisitlamayi asmanin yaygin ve guvenli yoludur.
    _send_inputs([_vk_input(VK_MENU), _vk_input(VK_MENU, True)])
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.2)
    return user32.GetForegroundWindow() == hwnd


def open_chat():
    """
    Chat panelini acar ve yazi kutusuna odaklanir.
    Uzanti panelleri (webview) Windows tarafinda ayri pencere olmadigi icin
    dogrudan bulunamaz; bunun yerine VS Code'un kendi komut sistemi kullanilir.
    """
    if CHAT_OPEN_METHOD == "command":
        press_shortcut(COMMAND_PALETTE_SHORTCUT)  # komut paletini ac (">" ile baslar)
        time.sleep(0.5)
        type_text(CHAT_COMMAND)                   # komut adini yaz -> liste filtrelenir
        time.sleep(DELAY_IN_PALETTE)
        press_enter()                             # ilk eslesen komutu calistir
    else:
        for i, step in enumerate(shortcut_steps()):
            if i > 0:
                time.sleep(SHORTCUT_STEP_DELAY)
            press_shortcut(step)


def shortcut_steps():
    """CHAT_SHORTCUT tek metin ya da metin listesi olabilir; her zaman liste dondurur."""
    if isinstance(CHAT_SHORTCUT, str):
        return [CHAT_SHORTCUT]
    return list(CHAT_SHORTCUT)


def send_chat_message():
    """Guncelleme tamamlandiginda yapilacak islem: VS Code Chat'e mesaj gonder."""
    hwnd = find_vscode_window(VSCODE_WINDOW_TITLE)
    if not hwnd:
        print("HATA: '%s' baslikli VS Code penceresi bulunamadi." % VSCODE_WINDOW_TITLE,
              file=sys.stderr)
        return
    if not activate_window(hwnd):
        print("UYARI: VS Code penceresi on plana alinamamis olabilir.", file=sys.stderr)
    time.sleep(DELAY_AFTER_FOCUS)

    open_chat()                         # Chat panelini ac / input'a odaklan
    time.sleep(DELAY_AFTER_SHORTCUT)

    type_text(CHAT_MESSAGE)             # Mesaji yaz
    time.sleep(DELAY_BEFORE_ENTER)
    press_enter()                       # Gonder
    print("[%s] Mesaj gonderildi: %s" % (time.strftime("%H:%M:%S"), CHAT_MESSAGE))


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

    print("Izleniyor: %s" % path)
    if processed is None:
        print("UYARI: Dosya su an mevcut degil; olusturulmasi bekleniyor.", file=sys.stderr)

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
            print("[%s] Guncelleme tamamlandi, islem baslatiliyor..." % time.strftime("%H:%M:%S"))
            try:
                on_update()
            except Exception as exc:  # izlemeyi durdurmadan hatayi raporla
                print("HATA: %s" % exc, file=sys.stderr)
            processed = current           # bu guncelleme bir daha islenmez


def main():
    path = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else REF_FILE_PATH)
    try:
        # ayar hatalarini erkenden yakala
        if CHAT_OPEN_METHOD not in ("shortcut", "command"):
            raise ValueError("CHAT_OPEN_METHOD 'shortcut' veya 'command' olmali.")
        for step in shortcut_steps():
            parse_shortcut(step)
        parse_shortcut(COMMAND_PALETTE_SHORTCUT)
    except ValueError as exc:
        print("HATA: %s" % exc, file=sys.stderr)
        sys.exit(1)
    try:
        watch(path, send_chat_message)
    except KeyboardInterrupt:
        print("\nDurduruldu.")


if __name__ == "__main__":
    main()
