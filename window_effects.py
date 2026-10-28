# -*- coding: utf-8 -*-
"""Эффекты окна под Windows.

Порядок попыток:
  1. Тёмная строка заголовка (всегда).
  2. DWM System Backdrop (Win11 22H2+): DWMSBT_TRANSIENTWINDOW (настоящий
     акриловый размыт) либо DWMSBT_MAINWINDOW (Mica). Это поддерживаемый
     Microsoft механизм — на Win11 24H2+ работает стабильно.
  3. Старый acrylic через SetWindowCompositionAttribute (Win10) — fallback.
  4. Если ничего не поддерживается — 'none' (после main.py вернёт
     непрозрачный фон, чтобы не было чёрного окна).
"""

from __future__ import annotations

import ctypes
import platform
import sys
from ctypes import wintypes

# --- атрибуты/константы DWM ---
# --- атрибуты/константы DWM ---
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19
DWMWA_SYSTEMBACKDROP_TYPE = 38
DWMSBT_AUTO = 0
DWMSBT_NONE = 1
DWMSBT_MAINWINDOW = 2       # Mica
DWMSBT_TRANSIENTWINDOW = 3  # Acrylic
DWMSBT_TABBEDWINDOW = 4     # Mica Alt

ACCENT_DISABLED = 0
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
WCA_ACCENT_POLICY = 19


class DWM_BLURBEHIND(ctypes.Structure):
    _fields_ = [
        ("dwFlags", wintypes.DWORD),
        ("fEnable", wintypes.BOOL),
        ("hRgnBlur", wintypes.HRGN),
        ("fTransitionOnMaximized", wintypes.BOOL),
    ]


DWM_BB_ENABLE = 0x1
DWM_BB_BLURREGION = 0x2


class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_int),
        ("AccentFlags", ctypes.c_int),
        ("GradientColor", ctypes.c_uint),  # ABGR: альфа — старший байт
        ("AnimationId", ctypes.c_int),
    ]


class WCA_DATA(ctypes.Structure):
    _fields_ = [
        ("attribute", ctypes.c_int),
        ("pData", ctypes.POINTER(ACCENT_POLICY)),
        ("dataSize", ctypes.c_size_t),
    ]


class MARGINS(ctypes.Structure):
    _fields_ = [
        ("cxLeftWidth", ctypes.c_int),
        ("cxRightWidth", ctypes.c_int),
        ("cyTopHeight", ctypes.c_int),
        ("cyBottomHeight", ctypes.c_int),
    ]


def windows_build() -> int:
    if sys.platform != "win32":
        return 0
    try:
        return int(platform.version().split(".")[2])
    except Exception:
        return 0


def _set_dark_titlebar(dwm, hwnd: int) -> None:
    val = ctypes.c_int(1)
    for attr in (DWMWA_USE_IMMERSIVE_DARK_MODE, DWMWA_USE_IMMERSIVE_DARK_MODE_OLD):
        try:
            if dwm.DwmSetWindowAttribute(
                wintypes.HWND(hwnd), wintypes.DWORD(attr),
                ctypes.byref(val), ctypes.sizeof(val)
            ) == 0:
                return
        except Exception:
            continue


def _try_system_backdrop(dwm, hwnd: int) -> str:
    """Акрил/Mica официально поддерживаются с Win11 22H2 (build 22621).
    Критично: DWA_SYSTEMBACKDROP_TYPE рисуется только там, куда «втянута»
    рамка окна — поэтому сначала DwmExtendFrameIntoClientArea(-1,-1,-1,-1)."""
    if windows_build() < 22621:
        return ""
    margins = MARGINS(-1, -1, -1, -1)
    extended = False
    try:
        extended = dwm.DwmExtendFrameIntoClientArea(
            wintypes.HWND(hwnd), ctypes.byref(margins)
        ) == 0
    except Exception:
        extended = False
    for bt, name in ((DWMSBT_TRANSIENTWINDOW, "acrylic"), (DWMSBT_MAINWINDOW, "mica")):
        val = ctypes.c_int(bt)
        try:
            if dwm.DwmSetWindowAttribute(
                wintypes.HWND(hwnd), wintypes.DWORD(DWMWA_SYSTEMBACKDROP_TYPE),
                ctypes.byref(val), ctypes.sizeof(val)
            ) == 0:
                return name
        except Exception:
            continue
    if extended:
        # откат: убираем растянутую рамку, чтобы не осталось стеклянной каёмки
        try:
            dwm.DwmExtendFrameIntoClientArea(
                wintypes.HWND(hwnd), ctypes.byref(MARGINS(0, 0, 0, 0))
            )
        except Exception:
            pass
    return ""


def _try_blur_behind(dwm, hwnd: int) -> str:
    """Классический BlurBehind: на Win11 24H2+ даёт нейтральное тёмное стекло
    БЕЗ синевы от системного акцента (проверено сэмплированием экрана).
    Требует translucent-фон: с ним и применяется. Работает и как обычный
    фолбэк на Win10."""
    gdi = ctypes.windll.gdi32
    dbb = DWM_BLURBEHIND()
    dbb.dwFlags = DWM_BB_ENABLE | DWM_BB_BLURREGION
    dbb.fEnable = True
    # регион (-1,-1,0,0) — стандартный трюк «размыть всё окно»
    dbb.hRgnBlur = gdi.CreateRectRgn(-1, -1, 0, 0)
    dbb.fTransitionOnMaximized = False
    try:
        if dwm.DwmEnableBlurBehindWindow(wt.HWND(hwnd), ctypes.byref(dbb)) == 0:
            return "glass"
    except Exception:
        pass
    return ""


def _try_wca_acrylic(user32, hwnd: int, tint_alpha: int, tint_color: int) -> str:
    """Легаси-акрил для Win10 (на Win11 24H2+ не работает — цвет заливки)."""
    accent = ACCENT_POLICY()
    accent.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
    accent.AccentFlags = 2
    accent.GradientColor = ((tint_alpha & 0xFF) << 24) | (tint_color & 0xFFFFFF)
    data = WCA_DATA()
    data.attribute = WCA_ACCENT_POLICY
    data.pData = ctypes.pointer(accent)
    data.dataSize = ctypes.sizeof(accent)
    try:
        if user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data)):
            return "acrylic_wca"
    except Exception:
        pass
    return ""


def transparency_enabled() -> bool:
    """Гоняет тумблер «Параметры → Персонализация → Цвета → Эффекты прозрачности».
    Когда он выключен, Windows рисует все acrylic/Mica непрозрачными."""
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as k:
            val, _ = winreg.QueryValueEx(k, "EnableTransparency")
            return bool(val)
    except Exception:
        return True


def apply_danya_window_effects(window, tint_alpha: int = 0x66,
                               tint_color: int = 0x000000) -> str:
    """Включает блюр/прозрачность. Возвращает применённый режим:
    'acrylic' | 'mica' | 'acrylic_wca' | 'transparency_disabled' |
    'none' (или 'unsupported' не-Windows)."""
    if sys.platform != "win32":
        return "unsupported"
    try:
        hwnd = int(window.winId())
    except Exception:
        return "none"
    if not hwnd:
        return "none"

    if not transparency_enabled():
        return "transparency_disabled"

    dwm = ctypes.windll.dwmapi
    user32 = ctypes.windll.user32

    _set_dark_titlebar(dwm, hwnd)

    # скругление углов самого окна (Win11): DWM обрезает контент по радиусу
    pref = ctypes.c_int(2)  # DWMWCP_ROUND
    try:
        dwm.DwmSetWindowAttribute(
            wintypes.HWND(hwnd), wintypes.DWORD(33),  # DWMWA_WINDOW_CORNER_PREFERENCE
            ctypes.byref(pref), ctypes.sizeof(pref)
        )
    except Exception:
        pass

    # 1) нейтральное стекло без системной синевы (уточнено сэмплами на 26300)
    mode = ""
    if windows_build() >= 22000:
        mode = _try_blur_behind(dwm, hwnd)
        if mode:
            return mode

    # 2) системный Backdrop (академический путь; на части билдов ничего не даёт)
    mode = _try_system_backdrop(dwm, hwnd)
    if mode:
        return mode

    # 3) легаси-акрил с настраиваемым цветом (Win10)
    mode = _try_wca_acrylic(user32, hwnd, tint_alpha, tint_color)
    if mode:
        return mode

    return "none"
