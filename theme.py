# -*- coding: utf-8 -*-
"""Тема приложения (QSS) — стеклянная, под акриловое размытие окна.

Все фоны — полупрозрачные rgba (альфа 0–255), чтобы сквозь окно проступал
размытый «акриловый» фон рабочего стола.
"""

# стеклянные фоны (нейтральные — RGB-каналы равные, синевы нет)
GLASS_ROOT = "rgba(12, 12, 14, 64)"          # основное «стекло» окна: ~25% непрозрачности
GLASS_PANEL = "rgba(18, 18, 20, 130)"        # сайдбар / панель плеера (плотнее для читаемости)
GLASS_INPUT = "rgba(30, 30, 34, 150)"        # поля ввода, вкладки
GLASS_HOVER = "rgba(255, 255, 255, 26)"      # ховеры строк/кнопок
GLASS_ACCENT = "rgba(255, 85, 0, 40)"        # подсветка выбранных (оранжевая)
GLASS_COVER = "rgba(28, 28, 32, 170)"        # плейсхолдер обложки
LINE = "rgba(255, 255, 255, 28)"             # тонкие линии-разделители

FROSTED_QSS = f"""
* {{ font-family: "Segoe UI", "Segoe UI Emoji", sans-serif; outline: none; }}

/* Тёмное стекло красим ТОЛЬКО на корне: остальным виджетам — прозрачность.
   Общая краска на всех QWidget давала прямоугольные подложки под текстом
   и кнопками (логотип, сердечко, низ плеера). */
QMainWindow {{ background-color: {GLASS_ROOT}; }}
QWidget {{ background-color: transparent; }}
QWidget#Root {{ background-color: {GLASS_ROOT}; }}
QWidget#Root {{ background-color: {GLASS_ROOT}; }}
/* ------ панели: плавающие скруглённые карточки ------ */
QWidget#Sidebar {{
    background-color: {GLASS_PANEL}; border: 1px solid {LINE}; border-radius: 26px;
}}
QWidget#PageWidget {{ background-color: transparent; }}
QScrollArea {{ border: none; background-color: transparent; }}
QWidget#PlayerBar {{
    background-color: {GLASS_PANEL}; border: 1px solid {LINE}; border-radius: 26px;
}}
QWidget#BottomCard {{
    background-color: {GLASS_PANEL}; border: 1px solid {LINE}; border-radius: 26px;
}}

QLabel {{ color: #e9e9ee; }}
QLabel#Logo {{ font-size: 21px; font-weight: 700; padding: 4px 14px 14px 14px; color: #ffffff; }}
QLabel#SidebarNote {{ color: #a0a1ad; font-size: 11px; padding: 10px 14px; }}
QLabel#Big {{ font-size: 22px; font-weight: 700; color: #ffffff; }}
QLabel#Section {{ font-size: 15px; font-weight: 700; color: #ffffff; padding-top: 10px; }}
QLabel#Meta {{ color: #b3b4c0; font-size: 12px; }}
QLabel#Muted {{ color: #a5a6b2; font-size: 13px; }}
QLabel#PageStatus {{ color: #c3c4cf; font-size: 13px; }}
QLabel#ErrorText {{ color: #ff8080; font-size: 13px; }}
QLabel#Hint {{ color: #b9bac6; font-size: 14px; }}
QLabel#TrackTitle {{ font-size: 14px; font-weight: 600; color: #f2f2f6; }}
QLabel#TrackSub {{ font-size: 12px; color: #b3b4c0; }}
QLabel#TrackDur {{ font-size: 12px; color: #a8a9b5; }}

/* ------ сайдбар и верхняя панель ------ */
QToolButton#NavButton {{
    text-align: left; border: none; border-radius: 16px;
    padding: 10px 14px; font-size: 14px; color: #b4b5c1; background-color: transparent;
}}
QToolButton#NavButton:hover {{ background-color: {GLASS_HOVER}; color: #ffffff; }}
QToolButton#NavButton:checked {{ background-color: {GLASS_ACCENT}; color: #ff7d3b; font-weight: 600; }}

QLineEdit#SearchEdit {{
    background-color: {GLASS_INPUT}; border: 1px solid {LINE}; border-radius: 20px;
    padding: 7px 16px; color: #f0f0f4; font-size: 13px;
    selection-background-color: #ff5500;
}}
QLineEdit#SearchEdit:focus {{ border-color: #ff5500; }}

QToolButton#BackBtn {{
    background-color: transparent; border: none; color: #b4b5c1;
    border-radius: 12px;
    font-size: 20px; padding: 2px 12px 2px 2px;
}}
QToolButton#BackBtn:hover {{ color: #ffffff; }}
QToolButton#BackBtn:disabled {{ color: #5a5b66; }}

/* ------ вкладки поиска ------ */
QToolButton#Tab {{
    background-color: {GLASS_INPUT}; border: none; border-radius: 16px;
    padding: 6px 16px; font-size: 13px; color: #b4b5c1;
}}
QToolButton#Tab:hover {{ color: #ffffff; }}
QToolButton#Tab:checked {{ background-color: {GLASS_ACCENT}; color: #ff7d3b; font-weight: 600; }}

/* ------ строки ------ */
QWidget#TrackRow {{ background-color: transparent; border-radius: 20px; }}
QWidget#TrackRow:hover {{ background-color: {GLASS_HOVER}; }}
QToolButton#Heart {{
    background-color: transparent; border: none; font-size: 17px; padding: 2px;
}}

/* ------ крупные кнопки ------ */
QToolButton#GhostBtn {{
    background-color: rgba(255, 255, 255, 26); border: none; border-radius: 20px;
    padding: 7px 16px; font-size: 12px; color: #ffb0b0;
}}
QToolButton#GhostBtn:hover {{ background-color: rgba(255, 107, 107, 40); color: #ffd0d0; }}
QToolButton#AccentBtn, QPushButton#AccentBtn {{
    background-color: #ff5500; color: #ffffff; border: none; border-radius: 21px;
    padding: 9px 22px; font-size: 13px; font-weight: 600;
}}
QToolButton#AccentBtn:hover, QPushButton#AccentBtn:hover {{ background-color: #ff6a1f; }}
QToolButton#AccentBtn:disabled, QPushButton#AccentBtn:disabled {{
    background-color: rgba(255, 85, 0, 60); color: rgba(255, 255, 255, 110);
}}

/* ------ плеер ------ */
QToolButton#PlayerBtn {{
    background-color: transparent; border: none; color: #f0f0f4;
    font-size: 17px; padding: 6px 10px;
}}
QToolButton#PlayerBtn:hover {{ color: #ff7a33; }}
QToolButton#PlayerBig {{
    background-color: #f0f0f4; border: none; border-radius: 23px;
    color: #0f1014; font-size: 20px; padding: 8px;
}}
QToolButton#PlayerBig:hover {{ background-color: #ff5500; color: #ffffff; }}
QLabel#TimeLabel {{ color: #a8a9b5; font-size: 11px; }}
QLabel#ErrorLive {{ color: #ff8080; font-size: 11px; }}

/* ------ слайдеры ------ */
QSlider {{ background-color: transparent; }}
QSlider#Seek::groove:horizontal {{
    height: 5px; background-color: rgba(255, 255, 255, 36); border-radius: 3px;
}}
QSlider#Seek::sub-page:horizontal {{ background-color: #ff5500; border-radius: 2px; }}
QSlider#Seek::handle:horizontal {{
    width: 12px; margin: -4px 0; border-radius: 6px; background-color: #e9e9ee;
}}
QSlider#Vol::groove:horizontal {{
    height: 4px; background-color: rgba(255, 255, 255, 36); border-radius: 2px;
}}
QSlider#Vol::sub-page:horizontal {{ background-color: rgba(255, 255, 255, 110); border-radius: 2px; }}
QSlider#Vol::handle:horizontal {{
    width: 10px; margin: -3px 0; border-radius: 5px; background-color: #e9e9ee;
}}

/* ------ скроллбар ------ */
QScrollBar:vertical {{ background-color: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{
    background-color: rgba(255, 255, 255, 48); border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background-color: rgba(255, 255, 255, 80); }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background-color: transparent; }}
"""

# Совместимость: старое имя переменной, на которое могли ссылаться модули
QSS = FROSTED_QSS
