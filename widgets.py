# -*- coding: utf-8 -*-
"""Переиспользуемые виджеты: обложки, строки, слайдер, панель плеера."""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSlider,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import appicons
import common
from common import Track, fmt_count, fmt_time
from theme import GLASS_COVER

ACCENT = "#ff5500"


# ------------------------------------------------------------------ обложка

class Cover(QLabel):
    def __init__(self, url: str = "", size: int = 48, radius: Optional[int] = None,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._radius = radius if radius is not None else size // 2
        self._size = size
        self._url = url or ""
        self.setFixedSize(size, size)
        self.setStyleSheet(f"background-color: {GLASS_COVER}; border-radius: {self._radius}px;")
        if self._url:
            common.fetch_image(self._url, self, self._apply)

    def _apply(self, url: str, img) -> None:
        if img is None or getattr(img, "isNull", lambda: True)():
            return
        pm = QPixmap.fromImage(img)
        s = self._size
        m = min(pm.width(), pm.height())
        pm = pm.copy((pm.width() - m) // 2, (pm.height() - m) // 2, m, m)
        pm = pm.scaled(s, s, Qt.AspectRatioMode.IgnoreAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
        out = QPixmap(s, s)
        out.fill(Qt.GlobalColor.transparent)
        p = QPainter(out)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        path = QPainterPath()
        path.addRoundedRect(0, 0, s, s, self._radius, self._radius)
        p.setClipPath(path)
        p.drawPixmap(0, 0, pm)
        p.end()
        self.setPixmap(out)


# ------------------------------------------------------------------ слайдер

class SeekSlider(QSlider):
    """Клик по треку перематывает сразу."""

    def __init__(self, parent=None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setObjectName("Seek")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setRange(0, 0)

    def mousePressEvent(self, ev) -> None:
        if ev.button() == Qt.MouseButton.LeftButton and self.maximum() > self.minimum():
            val = QStyle.sliderValueFromPosition(
                self.minimum(), self.maximum(), int(ev.position().x()), self.width()
            )
            self.setValue(val)
            self.sliderMoved.emit(val)
        super().mousePressEvent(ev)


# ------------------------------------------------------------- строки списков

class _Row(QWidget):
    """База для строк-плиток (трек, артист, плейлист)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TrackRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Двойной клик — воспроизведение")
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(10, 8, 12, 8)
        self._lay.setSpacing(12)

    def _texts(self, title: str, sub: str) -> None:
        mid = QVBoxLayout()
        mid.setSpacing(2)
        self._title = QLabel(title)
        self._title.setObjectName("TrackTitle")
        self._sub = QLabel(sub)
        self._sub.setObjectName("TrackSub")
        mid.addWidget(self._title)
        mid.addWidget(self._sub)
        self._lay.addLayout(mid, 1)
        self._dur = QLabel("")
        self._dur.setObjectName("TrackDur")
        self._lay.addWidget(self._dur)

    def enterEvent(self, ev):  # noqa: N802 — Qt-имя
        super().enterEvent(ev)

    def mouseDoubleClickEvent(self, ev) -> None:
        self._activate()


class TrackRow(_Row):
    def __init__(self, track: Track, queue: List[Track], index: int, ctx, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._track = track
        self._queue = queue
        self._index = index

        self._lay.addWidget(Cover(track.artwork, 46))
        self._texts(track.title, track.artist)
        self._dur.setText(fmt_time(track.duration))

        heart = QToolButton(self)
        heart.setObjectName("Heart")
        heart.setFixedSize(34, 30)
        heart.setCursor(Qt.CursorShape.PointingHandCursor)
        heart.clicked.connect(self._toggle_like)
        self._heart = heart
        self._refresh_heart()
        self._lay.addWidget(heart)

    def _refresh_heart(self) -> None:
        liked = self._ctx.storage.is_liked(self._track.id)
        self._heart.setText("♥" if liked else "♡")
        self._heart.setStyleSheet(f"color: {ACCENT};" if liked else "color: #9a9ba7;")

    def _toggle_like(self) -> None:
        self._ctx.storage.toggle_like(self._track)
        self._refresh_heart()

    def _activate(self) -> None:
        self._ctx.player.play_queue(list(self._queue), self._index)


class PersonRow(_Row):
    def __init__(self, user: dict, ctx, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._user = user
        self.setToolTip(None)
        self._lay.addWidget(Cover(user.get("avatar_url") or "", 46, radius=23))
        followers = user.get("followers_count") or 0
        sub = "смотровых нет :)" if not followers else f"{fmt_count(followers)} подписчиков"
        self._texts(user.get("username") or "Без имени", sub)
        self._dur.setText("")
        self._lay.addWidget(self._dur)

    def _activate(self) -> None:
        from pages import ArtistPage
        self._ctx.navigate(ArtistPage(self._ctx, self._user))


class PlaylistRow(_Row):
    def __init__(self, pl: dict, ctx, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._pl = pl
        self._lay.addWidget(Cover(pl.get("artwork_url") or "", 46))
        who = ((pl.get("user") or {}).get("username")) or ""
        tracks = pl.get("tracks") or []
        sub = f"плейлист · {len(tracks)} треков"
        if who:
            sub += f" · {who}"
        self._texts(pl.get("title") or "Без названия", sub)
        self._dur.setText("")
        self._lay.addWidget(self._dur)

    def _activate(self) -> None:
        from pages import PlaylistPage
        self._ctx.navigate(PlaylistPage(self._ctx, self._pl))


# ------------------------------------------------------------------ плеер

class PlayerBar(QWidget):
    def __init__(self, ctx, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("PlayerBar")
        self.setFixedHeight(84)
        self._ctx = ctx
        self._player = ctx.player
        self._storage = ctx.storage

        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 10, 18, 10)
        lay.setSpacing(14)

        # --- левая часть: обложка + название
        info = QWidget(self)
        il = QHBoxLayout(info)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(12)
        self._info_layout = il
        self._cover = Cover("", 56)
        il.addWidget(self._cover)
        self._title = QLabel("Ничего не играет")
        self._title.setObjectName("TrackTitle")
        il.addWidget(self._title, 1)
        expand = QToolButton(info)
        expand.setObjectName("PlayerBtn")
        expand.setToolTip("Открыть большой плеер")
        expand.setIcon(appicons.icon("expand", 16))
        expand.setFixedSize(38, 34)
        expand.setCursor(Qt.CursorShape.PointingHandCursor)
        expand.clicked.connect(self._open_full)
        il.addWidget(expand)
        self._heart = QToolButton(info)
        self._heart.setObjectName("Heart")
        self._heart.setFixedSize(34, 30)
        self._heart.setCursor(Qt.CursorShape.PointingHandCursor)
        self._heart.clicked.connect(self._toggle_like)
        il.addWidget(self._heart)
        info.setFixedWidth(330)
        lay.addWidget(info)

        # --- центральная часть: управление + перемотка
        mid = QVBoxLayout()
        mid.setSpacing(4)
        controls = QHBoxLayout()
        controls.setSpacing(4)
        self._status = QLabel("")
        self._status.setObjectName("ErrorLive")
        controls.addWidget(self._status)
        controls.addStretch()
        self._btn_prev = self._pbtn("prev", self._player.prev)
        self._btn_play = self._pbtn("play", self._player.toggle, big=True)
        self._btn_next = self._pbtn("next", self._player.next)
        for b in (self._btn_prev, self._btn_play, self._btn_next):
            controls.addWidget(b)
        controls.addStretch()
        mid.addLayout(controls)

        seek_row = QHBoxLayout()
        seek_row.setSpacing(8)
        self._t_cur = QLabel("00:00")
        self._t_cur.setObjectName("TimeLabel")
        self._seek = SeekSlider()
        self._t_total = QLabel("--:--")
        self._t_total.setObjectName("TimeLabel")
        seek_row.addWidget(self._t_cur)
        seek_row.addWidget(self._seek, 1)
        seek_row.addWidget(self._t_total)
        mid.addLayout(seek_row)
        lay.addLayout(mid, 1)

        # --- правая часть: громкость
        vol = QHBoxLayout()
        vol.setSpacing(8)
        vol_icon = QLabel()
        vol_icon.setPixmap(appicons.pixmap("volume", 12))
        vol_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._vol = QSlider(Qt.Orientation.Horizontal)
        self._vol.setObjectName("Vol")
        self._vol.setFixedWidth(96)
        self._vol.setRange(0, 100)
        self._vol.setValue(80)
        self._vol.valueChanged.connect(self._player.set_volume)
        vol.addWidget(vol_icon)
        vol.addWidget(self._vol)
        lay.addLayout(vol)

        # --- сигналы
        self._player.trackChanged.connect(self._on_track)
        self._player.playingChanged.connect(self._on_playing)
        self._player.positionChanged.connect(self._on_pos)
        self._player.durationChanged.connect(self._on_dur)
        self._player.error.connect(self._on_error)
        self._seek.sliderMoved.connect(self._on_seek_move)

    # helpers

    def _open_full(self) -> None:
        from pages import PlayerPage
        self._ctx.navigate(PlayerPage(self._ctx))

    def _pbtn(self, name: str, handler, big: bool = False) -> QToolButton:
        """Кнопка плеера с векторной иконкой из appicons."""
        b = QToolButton(self)
        b.setObjectName("PlayerBig" if big else "PlayerBtn")
        b.setIcon(appicons.icon(name, 20 if big else 14,
                                "#14161d" if big else appicons.DEFAULT))
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.clicked.connect(handler)
        if big:
            b.setFixedSize(46, 46)
            b.setIconSize(b.size() * 0.52)
        else:
            b.setFixedSize(38, 32)
        return b

    # слоты

    def _on_track(self, track: object) -> None:
        t: Optional[Track] = track
        if t is None:
            return
        self._title.setText(t.title)
        self._replace_cover(t.artwork)
        self._refresh_heart()
        self._status.setText("")
        self._storage.add_recent(t)

    def _replace_cover(self, url: str) -> None:
        old = self._cover
        c = Cover(url, 56)
        self._info_layout.replaceWidget(old, c)
        old.hide()
        old.deleteLater()
        self._cover = c

    def _refresh_heart(self) -> None:
        t = self._player.current()
        liked = t is not None and self._storage.is_liked(t.id)
        self._heart.setIcon(appicons.icon("heart_fill" if liked else "heart", 15,
                                          "#ff5500" if liked else "#a9aab6"))

    def _toggle_like(self) -> None:
        t = self._player.current()
        if t is not None:
            self._storage.toggle_like(t)
            self._refresh_heart()

    def _on_playing(self, playing: bool) -> None:
        self._btn_play.setIcon(appicons.icon("pause" if playing else "play", 20,
                                             "#14161d"))

    def _on_pos(self, pos: int) -> None:
        self._t_cur.setText(fmt_time(pos))
        if not self._seek.isSliderDown():
            self._seek.setValue(pos)

    def _on_dur(self, dur: int) -> None:
        self._t_total.setText(fmt_time(dur))
        self._seek.setRange(0, dur if dur > 0 else 0)

    def _on_seek_move(self, val: int) -> None:
        self._player.seek(val)

    def _on_error(self, msg: str) -> None:
        self._status.setText(msg)


# ---------------------------------------------------------------- кнопки

class AccentButton(QToolButton):
    def __init__(self, text: str, handler=None, enabled: bool = True,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("AccentBtn")
        self.setText(text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setEnabled(enabled)
        if handler is not None:
            self.clicked.connect(handler)
