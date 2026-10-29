# -*- coding: utf-8 -*-
"""Главное окно: сайдбар, поиск, стек страниц, панель плеера."""

from __future__ import annotations

from typing import List

from PySide6.QtCore import QPropertyAnimation, Qt
from PySide6.QtCore import QEasingCurve, QAbstractAnimation
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import pages as pg
from common import Ctx
from player import Player
from storage import Storage
from widgets import PlayerBar


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DanyaCloud")
        self.setMinimumSize(940, 620)
        # прозрачное «стекло» (эффекты фона подключаются после show() в main.py)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.player = Player(self)
        self.storage = Storage()
        self.ctx = Ctx(self.player, self.storage, self.navigate, self.go_back)

        # режим повтора живёт в library.json между запусками
        self.player.set_repeat_mode(self.storage.setting("repeat", "off"))
        self.player.repeatChanged.connect(
            lambda m: self.storage.set_setting("repeat", m)
        )

        root = QWidget()
        root.setObjectName("Root")
        rv = QVBoxLayout(root)
        # отступ вокруг: сайдбар и панель плеера — плавающие скруглённые карточки
        rv.setContentsMargins(10, 10, 10, 10)
        rv.setSpacing(8)

        # ---- верхняя панель
        top = QWidget()
        t = QHBoxLayout(top)
        t.setContentsMargins(14, 12, 14, 8)
        t.setSpacing(4)
        self._back = QToolButton()
        self._back.setObjectName("BackBtn")
        self._back.setText("‹")
        self._back.setEnabled(False)
        self._back.setCursor(Qt.CursorShape.PointingHandCursor)
        self._back.clicked.connect(self.go_back)
        t.addWidget(self._back)
        self._search = QLineEdit()
        self._search.setObjectName("SearchEdit")
        self._search.setPlaceholderText("Поиск музыки, артистов, плейлистов…  (Ctrl+F)")
        self._search.returnPressed.connect(self._do_search)
        t.addWidget(self._search, 1)
        rv.addWidget(top)

        # ---- контент: сайдбар + страницы
        content = QWidget()
        ch = QHBoxLayout(content)
        ch.setContentsMargins(0, 0, 0, 0)
        ch.setSpacing(0)
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(230)
        sw = QVBoxLayout(sidebar)
        sw.setContentsMargins(10, 8, 10, 10)
        sw.setSpacing(2)
        logo = QLabel('<span style="color:#ff5500">danya</span>'
                      '<span style="color:#ffffff">cloud</span>')
        logo.setTextFormat(Qt.TextFormat.RichText)
        logo.setObjectName("Logo")
        sw.addWidget(logo)

        def nav(text: str, handler) -> None:
            b = QToolButton()
            b.setObjectName("NavButton")
            b.setText(text)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(handler)
            sw.addWidget(b)

        nav("⌂  Главная", lambda: self.navigate(pg.SearchPage(self.ctx)))
        nav("♥  Медиатека", lambda: self.navigate(pg.CollectionPage(self.ctx, "likes")))
        nav("↺  Недавно", lambda: self.navigate(pg.CollectionPage(self.ctx, "recents")))
        sw.addStretch()

        # --- настройка фона: мягкий (Mica) / сильный (акрил) блюр
        self._blur_btn = QToolButton()
        self._blur_btn.setObjectName("NavButton")
        self._blur_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_blur_btn()
        self._blur_btn.clicked.connect(self._cycle_blur)
        sw.addWidget(self._blur_btn)
        ch.addWidget(sidebar)

        self._stack = QStackedWidget()
        ch.addWidget(self._stack, 1)
        rv.addWidget(content, 1)

        # ---- нижняя панель плеера (прячется, когда открыт большой плеер)
        self._bar = PlayerBar(self.ctx)
        rv.addWidget(self._bar)
        self._stack.currentChanged.connect(self._sync_bar_visibility)
        self.setCentralWidget(root)

        # ---- навигация
        self._history: List[QWidget] = [pg.SearchPage(self.ctx)]
        self._stack.addWidget(self._history[0])

        # ---- горячие клавиши
        for seq in ("Ctrl+F", "Ctrl+K"):
            QShortcut(QKeySequence(seq), self, activated=self.focus_search)

    # ------------------------------------------------------------ действия

    def toggle_play(self) -> None:
        self.player.toggle()

    def focus_search(self) -> None:
        self._search.setFocus()
        self._search.selectAll()

    # ---------------------------------------------------------- фон окна

    def blur_setting(self) -> str:
        try:
            import storage
            return "light" if storage.read_setting("blur", "light") == "light" else "strong"
        except Exception:
            return "light"

    def _refresh_blur_btn(self) -> None:
        light = self.blur_setting() == "light"
        self._blur_btn.setText("🌾  Блюр: мягкий" if light else "🪟  Блюр: сильный")
        self._blur_btn.setToolTip(
            "Размытие фона окна (применится после перезапуска)")

    def _cycle_blur(self) -> None:
        new = "strong" if self.blur_setting() == "light" else "light"
        self.storage.set_setting("blur", new)
        self._refresh_blur_btn()

    def _do_search(self) -> None:
        q = self._search.text().strip()
        if not q:
            return
        self.navigate(pg.SearchPage(self.ctx, q))

    def _sync_bar_visibility(self) -> None:
        """В большом плеере нижняя панель не нужна — иконки не дублируются.
        Показ/скрытие анимированные (мягкое появление/растворение)."""
        cur = self._stack.currentWidget()
        full = cur is not None and isinstance(cur, pg.PlayerPage)
        self._animate_bar(not full)

    def _animate_bar(self, show: bool) -> None:
        bar = self._bar
        already = bar.isVisible() and bar.graphicsEffect() is None
        if already == show:
            return  # ничего менять не нужно
        old = getattr(self, "_bar_anim", None)
        if old is not None:
            old.stop()
        eff = bar.graphicsEffect()
        if not isinstance(eff, QGraphicsOpacityEffect):
            eff = QGraphicsOpacityEffect(bar)
            bar.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", bar)
        anim.setDuration(150)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        if show:
            bar.setVisible(True)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.finished.connect(lambda: bar.setGraphicsEffect(None))
        else:
            anim.setStartValue(1.0)
            anim.setEndValue(0.0)
            anim.finished.connect(
                lambda: (bar.setGraphicsEffect(None), bar.setVisible(False)))
        anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        self._bar_anim = anim

    # ------------------------------------------------- анимация появления

    def _fade_in(self, page: QWidget) -> None:
        """Мягкое появления страницы при переходе (170 мс, OutCubic)."""
        if page is None:
            return
        if page.graphicsEffect() is not None:
            return  # анимация ещё идёт
        eff = QGraphicsOpacityEffect(page)
        eff.setOpacity(0.0)
        page.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", page)
        anim.setDuration(170)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: page.setGraphicsEffect(None))
        anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    # ---------------------------------------------------------- навигация

    def navigate(self, page: QWidget) -> None:
        if page is None:
            return
        self._stack.addWidget(page)
        self._history.append(page)
        self._stack.setCurrentWidget(page)
        self._fade_in(page)
        self._back.setEnabled(True)
        # не даём стеку разрастаться (самая старая «верхняя» страница выкидывается)
        while len(self._history) > 15:
            old = self._history[1]
            if old is self._stack.currentWidget():
                break
            self._history.pop(1)
            self._stack.removeWidget(old)
            old.deleteLater()

    def go_back(self) -> None:
        if len(self._history) <= 1:
            return
        cur = self._history.pop()
        self._stack.removeWidget(cur)
        cur.deleteLater()
        self._stack.setCurrentWidget(self._history[-1])
        self._fade_in(self._history[-1])
        self._back.setEnabled(len(self._history) > 1)
