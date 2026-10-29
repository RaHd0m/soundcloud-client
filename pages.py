# -*- coding: utf-8 -*-
"""Страницы приложения: поиск, артист, плейлист, медиатека, недавние."""

from __future__ import annotations

import math
import random
from typing import Dict, List

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import sc_api
from common import Ctx, Track, fmt_count, fmt_time, run
from widgets import AccentButton, Cover, PersonRow, PlaylistRow, SeekSlider, TrackRow

TABS = [("tracks", "Треки"), ("users", "Артисты"), ("playlists", "Плейлисты")]


def clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        wdg = item.widget()
        if wdg is not None:
            wdg.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())


class ScrollPage(QWidget):
    """Вертикально скроллируемая страница с внутренним QVBox-контейнером."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(self)
        scroll.setObjectName("PageScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        body.setObjectName("PageWidget")
        self.lay = QVBoxLayout(body)
        self.lay.setContentsMargins(26, 22, 26, 26)
        self.lay.setSpacing(10)
        scroll.setWidget(body)
        outer.addWidget(scroll)


# ------------------------------------------------------------------- поиск

class SearchPage(ScrollPage):
    def __init__(self, ctx: Ctx, query: str = "", parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._q = query
        self._tab = "tracks"
        self._loaded: Dict[str, list] = {}
        self._errors: Dict[str, str] = {}
        self._pending: Dict[str, bool] = {}

        self._head = QLabel("")
        self._head.setObjectName("Big")
        self.lay.addWidget(self._head)

        chips = QHBoxLayout()
        chips.setContentsMargins(0, 0, 0, 0)
        chips.setSpacing(8)
        self._chips: Dict[str, QToolButton] = {}
        for kind, label in TABS:
            b = QToolButton()
            b.setObjectName("Tab")
            b.setText(label)
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=kind: self._pick(k))
            chips.addWidget(b)
            self._chips[kind] = b
        chips.addStretch()
        chips_new = QWidget()
        chips_new.setLayout(chips)
        self.lay.addWidget(chips_new)

        self._err = QLabel("")
        self._err.setObjectName("ErrorText")
        self._err.hide()
        self.lay.addWidget(self._err)

        self._box = QVBoxLayout()
        self._box.setSpacing(4)
        wrap = QWidget()
        wrap.setLayout(self._box)
        self.lay.addWidget(wrap)
        self.lay.addStretch()

        if query:
            self._start(query)
        else:
            self._home()

    # ---------------------------------------------------------------- home

    def _home(self) -> None:
        self._chips["tracks"].hide()
        self._chips["users"].hide()
        self._chips["playlists"].hide()
        self._head.setText("SoundCloud")
        box = QVBoxLayout()
        box.setContentsMargins(8, 120, 8, 0)
        box.setSpacing(10)
        hint = QLabel("Введи запрос в строке сверху и нажми Enter")
        hint.setObjectName("Hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        hint2 = QLabel("Поиск по трекам, артистам и плейлистам SoundCloud")
        hint2.setObjectName("Muted")
        hint2.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        box.addWidget(hint)
        box.addWidget(hint2)
        wrap = QWidget()
        wrap.setLayout(box)
        self._box.addWidget(wrap, 1)

    # ---------------------------------------------------------------- load

    def _start(self, q: str) -> None:
        self._q = q
        self._head.setText(f"Поиск: «{q}»")
        for kind, _ in TABS:
            self._pending[kind] = True
            self._loaded.pop(kind, None)
            self._errors.pop(kind, None)
        self._pick("tracks")
        for kind, _ in TABS:
            def call(kind=kind):
                return sc_api.api.search(q, kind)
            run(call, lambda res, k=kind: self._on(k, res),
                lambda msg, k=kind: self._on_err(k, msg), parent=self)

    def search_again(self, q: str) -> None:
        clear_layout(self._box)
        self._start(q)

    def _on(self, kind: str, res) -> None:
        self._pending.pop(kind, None)
        self._loaded[kind] = res or []
        if kind == self._tab:
            self._render()

    def _on_err(self, kind: str, msg: str) -> None:
        self._pending.pop(kind, None)
        self._errors[kind] = msg
        if kind == self._tab:
            self._render()

    def _pick(self, kind: str) -> None:
        self._tab = kind
        for k, b in self._chips.items():
            b.setChecked(k == kind)
        self._render()

    def _render(self) -> None:
        clear_layout(self._box)
        if not self._q:
            return
        status = QLabel("")
        status.setObjectName("PageStatus")
        if self._pending.get(self._tab):
            status.setText("Загрузка…")
            self._box.addWidget(status)
            self._err.hide()
            self._head.setText(f"Поиск: «{self._q}»")
            return
        err = self._errors.get(self._tab)
        if err:
            status.setText(err)
            status.setObjectName("ErrorText")
            status.style().unpolish(status)
            status.style().polish(status)
            self._box.addWidget(status)
            return
        items: list = self._loaded.get(self._tab) or []
        if not items:
            status.setText("Ничего не нашлось")
            self._box.addWidget(status)
            return
        extra = self._loaded.get("tracks")
        if self._tab == "tracks":
            tracks: List[Track] = [Track.from_api(d) for d in items]
            for i, t in enumerate(tracks):
                self._box.addWidget(TrackRow(t, tracks, i, self._ctx))
        elif self._tab == "users":
            for u in items:
                if u.get("kind") == "user":
                    self._box.addWidget(PersonRow(u, self._ctx))
        else:
            for p in items:
                if p.get("kind") == "playlist":
                    self._box.addWidget(PlaylistRow(p, self._ctx))


# ------------------------------------------------------------------ артист

class ArtistPage(ScrollPage):
    def __init__(self, ctx: Ctx, user: dict, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._uid = user.get("id")
        self._tracks: List[Track] = []

        header = QWidget()
        h = QHBoxLayout(header)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(20)
        self._avatar = Cover(user.get("avatar_url") or "", 128, radius=64)
        h.addWidget(self._avatar)
        right = QVBoxLayout()
        right.setSpacing(6)
        self._name = QLabel(user.get("username") or "Артист")
        self._name.setObjectName("Big")
        self._meta = QLabel("Загрузка…")
        self._meta.setObjectName("Meta")
        self._desc = QLabel("")
        self._desc.setObjectName("Muted")
        self._desc.setWordWrap(True)
        right.addWidget(self._name)
        right.addWidget(self._meta)
        right.addWidget(self._desc, 1)
        h.addLayout(right, 1)
        buttons = QVBoxLayout()
        self._play_all = AccentButton("▶  Слушать", handler=self._on_play_all, enabled=False)
        buttons.addWidget(self._play_all)
        h.addLayout(buttons)
        self.lay.addWidget(header)

        self._err = QLabel("")
        self._err.setObjectName("ErrorText")
        self._err.hide()
        self.lay.addWidget(self._err)

        self.lay.addWidget(self._section("Треки"))
        self._list = QVBoxLayout()
        self._list.setSpacing(4)
        lw = QWidget()
        lw.setLayout(self._list)
        self.lay.addWidget(lw)

        run(
            self._load,
            self._populate,
            self._on_err,
            parent=self,
        )

    def _load(self):
        u = sc_api.api.get_user(self._uid)
        tracks = sc_api.api.user_tracks(self._uid)
        playlists = sc_api.api.user_playlists(self._uid)
        return u, tracks, playlists

    def _populate(self, data) -> None:
        u, tracks, playlists = data
        self._name.setText(u.get("username") or "Артист")
        parts = []
        if u.get("followers_count"):
            parts.append(f"{fmt_count(u['followers_count'])} подписчиков")
        if u.get("track_count"):
            parts.append(f"{fmt_count(u['track_count'])} треков")
        self._meta.setText(" · ".join(parts))
        desc = (u.get("description") or "").strip()
        self._desc.setText(desc[:400])
        img = u.get("avatar_url") or ""
        if img and img != self._avatar._url:
            self._avatar = self._make_avatar(img)

        self._tracks = [Track.from_api(d) for d in tracks]
        if self._tracks:
            self._play_all.setEnabled(True)
            for i, t in enumerate(self._tracks):
                self._list.addWidget(TrackRow(t, self._tracks, i, self._ctx))
        else:
            note = QLabel("Публичных треков нет")
            note.setObjectName("PageStatus")
            self._list.addWidget(note)
        if playlists:
            self.lay.addWidget(self._section("Плейлисты"))
            for p in playlists:
                self.lay.addWidget(PlaylistRow(p, self._ctx))
        self.lay.addStretch()

    def _make_avatar(self, url: str) -> Cover:
        old = self._avatar
        c = Cover(url, 128, radius=64)
        old.parent().layout().replaceWidget(old, c)
        old.hide()
        old.deleteLater()
        return c

    def _on_play_all(self) -> None:
        if self._tracks:
            self._ctx.player.play_queue(list(self._tracks), 0)

    def _on_err(self, msg: str) -> None:
        self._meta.setText(msg)
        self._err.setText(msg)
        self._err.show()

    @staticmethod
    def _section(text: str) -> QLabel:
        lb = QLabel(text)
        lb.setObjectName("Section")
        return lb


# ---------------------------------------------------------------- плейлист

class PlaylistPage(ScrollPage):
    def __init__(self, ctx: Ctx, pl: dict, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._pid = pl.get("id")
        self._tracks: List[Track] = []

        header = QWidget()
        h = QHBoxLayout(header)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(20)
        self._cover = Cover(pl.get("artwork_url") or "", 128, radius=64)
        h.addWidget(self._cover)
        right = QVBoxLayout()
        right.setSpacing(6)
        self._title = QLabel(pl.get("title") or "Плейлист")
        self._title.setObjectName("Big")
        self._meta = QLabel("Загрузка…")
        self._meta.setObjectName("Meta")
        right.addWidget(self._title)
        right.addWidget(self._meta)
        h.addLayout(right, 1)
        buttons = QVBoxLayout()
        self._play_all = AccentButton("▶  Слушать", handler=self._on_play_all, enabled=False)
        buttons.addWidget(self._play_all)
        h.addLayout(buttons)
        self.lay.addWidget(header)

        self._err = QLabel("")
        self._err.setObjectName("ErrorText")
        self._err.hide()
        self.lay.addWidget(self._err)

        self._list = QVBoxLayout()
        self._list.setSpacing(4)
        lw = QWidget()
        lw.setLayout(self._list)
        self.lay.addWidget(lw)

        run(lambda: sc_api.api.get_playlist(self._pid),
            self._populate, self._on_err, parent=self)

    def _populate(self, data: dict) -> None:
        self._title.setText(data.get("title") or "Плейлист")
        raw = data.get("tracks") or []
        total = 0
        self._tracks = []
        for d in raw:
            t = Track.from_api(d)
            total += t.duration
            self._tracks.append(t)
        who = (data.get("user") or {}).get("username") or ""
        self._meta.setText(f"{who} · {len(self._tracks)} треков · {fmt_time(total)}")
        if self._tracks:
            self._play_all.setEnabled(True)
            for i, t in enumerate(self._tracks):
                self._list.addWidget(TrackRow(t, self._tracks, i, self._ctx))
        else:
            note = QLabel("Пусто")
            note.setObjectName("PageStatus")
            self._list.addWidget(note)
        self.lay.addStretch()

    def _on_play_all(self) -> None:
        if self._tracks:
            self._ctx.player.play_queue(list(self._tracks), 0)

    def _on_err(self, msg: str) -> None:
        self._meta.setText(msg)
        self._err.setText(msg)
        self._err.show()


# --------------------------------------------------------- медиатека/недавно

class CollectionPage(ScrollPage):
    def __init__(self, ctx: Ctx, kind: str, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._kind = kind
        title = "Медиатека" if kind == "likes" else "Недавно прослушанные"
        head = QLabel(title)
        head.setObjectName("Big")
        self.lay.addWidget(head)

        # строка действий (для «Недавно» — кнопка очистки истории)
        import appicons
        actions = QWidget()
        ah = QHBoxLayout(actions)
        ah.setContentsMargins(0, 0, 0, 0)
        ah.setSpacing(10)
        self._btn_play = AccentButton("▶  Слушать все")
        ah.addWidget(self._btn_play)
        if kind == "recents":
            clr = QToolButton()
            clr.setObjectName("GhostBtn")
            clr.setToolTip("Удалить всю историю прослушиваний")
            clr.setIcon(appicons.icon("trash", 14, "#ffb0b0"))
            clr.setText("Очистить историю")
            clr.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            clr.setCursor(Qt.CursorShape.PointingHandCursor)
            clr.clicked.connect(self._clear_history)
            ah.addWidget(clr)
        ah.addStretch()
        self.lay.addWidget(actions)

        self._rows = QVBoxLayout()
        self._rows.setSpacing(4)
        host = QWidget()
        host.setLayout(self._rows)
        self.lay.addWidget(host)
        self.lay.addStretch()

        self._rebuild()

    def _rebuild(self) -> None:
        clear_layout(self._rows)
        tracks = (self._ctx.storage.likes()
                  if self._kind == "likes" else self._ctx.storage.recents())
        if not tracks:
            note = QLabel(
                "Пока пусто. Понравившиеся треки сохраняются сердечком "
                "(в строке трека или внизу окна)." if self._kind == "likes"
                else "Пока пусто. Здесь появятся треки, которые ты слушал."
            )
            note.setObjectName("PageStatus")
            self._rows.addWidget(note)
            self._btn_play.setEnabled(False)
            return
        self._btn_play.setEnabled(True)
        self._btn_play.clicked.connect(
            lambda: self._ctx.player.play_queue(list(tracks), 0)
        )
        for i, t in enumerate(tracks):
            self._rows.addWidget(TrackRow(t, tracks, i, self._ctx))
        self._rows.addStretch()

    def _clear_history(self) -> None:
        self._ctx.storage.clear_recents()
        self._rebuild()


# ------------------------------------------------------------ большой плеер

class CavaBar(QWidget):
    """Визуализатор как в консольном cava: плавно «дышащие» столбики.

    Настоящий захват звука из QMediaPlayer недоступен, поэтому динамика —
    мягкая сумка синусоид + шум, синхронизированная с состоянием плеера:
    на паузе столбики плавно складываются. 60 FPS, ~1% CPU.
    """

    def __init__(self, player, bars: int = 64, parent=None) -> None:
        super().__init__(parent)
        self._n = bars
        self._amp = [0.0] * bars
        self._t = 0.0
        self._phases = [random.uniform(0.0, 6.28) for _ in range(bars)]
        self._speedd = [random.uniform(0.9, 1.35) for _ in range(bars)]
        self._timer = QTimer(self)
        self._timer.setInterval(33)  # ~30 FPS: глазу хватает, CPU щадим
        self._timer.timeout.connect(self._advance)
        self._playing = player.is_playing()
        player.playingChanged.connect(self._on_playing)

    def showEvent(self, ev):  # noqa: N802 — Qt-имя
        super().showEvent(ev)
        self._timer.start()

    def hideEvent(self, ev):  # noqa: N802
        self._timer.stop()
        super().hideEvent(ev)

    def _on_playing(self, playing: bool) -> None:
        self._playing = playing

    def _aim(self, i: int) -> float:
        t = self._t * self._speedd[i] + self._phases[i]
        env = 0.5 + 0.5 * math.sin(t * 0.6)
        wave = (
            0.62 * math.sin(t * 2.1)
            + 0.26 * math.sin(t * 0.9 + 1.7)
            + 0.12 * math.sin(t * 3.7 + 0.5)
        )
        n = self._n
        edge = math.sin(math.pi * (i + 0.5) / n) ** 0.8  # к центру выше
        center = 1.0 - 0.35 * abs((i - n / 2) / (n / 2))
        if self._playing:
            base = 0.10 + 0.90 * abs(wave * env)
        else:
            base = 0.04 + 0.03 * math.sin(t * 0.8)
        return max(0.0, min(1.0, base * (0.25 + 0.75 * edge * center)))

    def _advance(self) -> None:
        self._t += 0.05
        for i, a in enumerate(self._amp):
            aim = self._aim(i)
            rate = 0.45 if aim > a else 0.12  # резкий подъём, мягкий спад
            self._amp[i] = a + (aim - a) * rate
        self.update()

    def paintEvent(self, ev) -> None:  # noqa: N802
        from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath
        # from PySide6.QtCore нет нужды — Qt уже импортирован в модуле
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        gap = max(2.0, w * 0.006)
        bw = (w - gap * (self._n - 1)) / self._n
        grad = QLinearGradient(0, h, 0, 0)
        grad.setColorAt(0.0, QColor("#ff5500"))
        grad.setColorAt(1.0, QColor("#ffb367"))
        min_h = h * 0.06
        for i, a in enumerate(self._amp):
            bh = max(min_h, a * (h - 4))
            path = QPainterPath()
            path.addRoundedRect(
                i * (bw + gap), h - bh, bw, bh, bw / 2.6, bw / 2.6
            )
            p.fillPath(path, grad)
        p.end()


class PlayerPage(QWidget):
    """Плеер на все окно: большая обложка, крупный заголовок, управление."""

    def __init__(self, ctx: Ctx, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._player = ctx.player
        self._storage = ctx.storage
        self._cover_size = 340
        self._cover_radius = 170

        lay = QVBoxLayout(self)
        lay.setContentsMargins(34, 12, 34, 22)
        lay.setSpacing(10)

        # --- верхняя строка: ветка на весь экран + закрыть
        top = QHBoxLayout()
        top.setSpacing(6)
        import appicons
        btn_fs = QToolButton()
        btn_fs.setObjectName("BackBtn")
        btn_fs.setToolTip("Развернуть на весь экран")
        btn_fs.setIcon(appicons.icon("expand", 16))
        btn_fs.setFixedSize(40, 34)
        btn_fs.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_fs.clicked.connect(self._toggle_fullscreen)
        btn_close = QToolButton()
        btn_close.setObjectName("BackBtn")
        btn_close.setToolTip("Вернуться (Esc)")
        btn_close.setIcon(appicons.icon("close", 16))
        btn_close.setFixedSize(40, 34)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self._ctx.back)
        top.addStretch()
        top.addWidget(btn_fs)
        top.addWidget(btn_close)
        lay.addLayout(top)

        # --- центр: обложка + название
        center = QVBoxLayout()
        center.setSpacing(16)
        center.addStretch(1)
        cwrap = QHBoxLayout()
        self._cover = Cover(self._cover_url_hint() or "", self._cover_size,
                            radius=self._cover_radius)
        cwrap.addStretch()
        cwrap.addWidget(self._cover)
        cwrap.addStretch()
        center.addLayout(cwrap)

        self._title = QLabel(self._title_hint())
        self._title.setObjectName("PlayerTitle")
        self._title.setWordWrap(True)
        self._title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._title.setMaximumWidth(660)
        trow = QHBoxLayout()
        trow.addStretch()
        trow.addWidget(self._title)
        trow.addStretch()
        center.addLayout(trow)

        # анимация-визуализатор в стиле cava
        self._cava = CavaBar(self._player, bars=64)
        self._cava.setFixedHeight(86)
        self._cava.setMaximumWidth(660)
        crow = QHBoxLayout()
        crow.addStretch()
        crow.addWidget(self._cava, 1)
        crow.addStretch()
        center.addLayout(crow)

        center.addStretch(1)
        lay.addLayout(center, 1)

        # --- низ: перемотка, кнопки, громкость (отдельная скруглённая карточка)
        bottom = QWidget()
        bottom.setObjectName("BottomCard")
        bv = QVBoxLayout(bottom)
        bv.setContentsMargins(40, 16, 40, 18)
        bv.setSpacing(6)

        seek = QHBoxLayout()
        seek.setSpacing(10)
        self._t_cur = QLabel("00:00")
        self._t_cur.setObjectName("TimeLabel")
        self._resume = SeekSlider()
        self._t_total = QLabel("--:--")
        self._t_total.setObjectName("TimeLabel")
        seek.addWidget(self._t_cur)
        seek.addWidget(self._resume, 1)
        seek.addWidget(self._t_total)
        bv.addLayout(seek)

        controls = QHBoxLayout()
        controls.setSpacing(14)
        self._heart = QToolButton()
        self._heart.setObjectName("Heart")
        self._heart.setToolTip("В медиатеку")
        self._heart.setFixedSize(44, 40)
        self._heart.setCursor(Qt.CursorShape.PointingHandCursor)
        self._heart.clicked.connect(self._toggle_like)
        controls.addWidget(self._heart)
        controls.addStretch()
        self._btn_prev = self._pbtn("prev", self._player.prev)
        self._btn_play = self._pbtn("play", self._player.toggle, big=True)
        self._btn_next = self._pbtn("next", self._player.next)
        self._btn_repeat = self._pbtn("repeat", self._cycle_repeat)
        for b in (self._btn_prev, self._btn_play, self._btn_next, self._btn_repeat):
            controls.addWidget(b)
        # синхронизируем иконку/подсказку с режимом повтора
        self._player.repeatChanged.connect(self._on_repeat)
        self._on_repeat(self._player.repeat_mode())
        controls.addStretch()

        # громкость (справа, как в нижней панели)
        vol_icon = QLabel()
        vol_icon.setPixmap(appicons.pixmap("volume", 13))
        vol_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._vol = QSlider(Qt.Orientation.Horizontal)
        self._vol.setObjectName("Vol")
        self._vol.setFixedWidth(130)
        self._vol.setRange(0, 100)
        self._vol.setValue(int(self._player.volume() * 100))
        self._vol.valueChanged.connect(self._player.set_volume)
        controls.addSpacing(52)  # компенсация ширины сердечка для центра
        controls.addWidget(vol_icon)
        controls.addWidget(self._vol)
        bv.addLayout(controls)
        lay.addWidget(bottom)

        # --- начальное состояние и сигналы
        t = self._player.current()
        if t is not None:
            self._cover = self._make_cover(t.artwork)
            self._title.setText(t.title)
        self._t_cur.setText(fmt_time(self._player.position()))
        if self._player.duration() > 0:
            self._resume.setRange(0, self._player.duration())
            self._t_total.setText(fmt_time(self._player.duration()))
        self._resume.setValue(self._player.position())
        self._refresh_heart()

        self._player.trackChanged.connect(self._on_track)
        self._player.playingChanged.connect(self._on_playing)
        self._player.positionChanged.connect(self._on_pos)
        self._player.durationChanged.connect(self._on_dur)
        QShortcut(QKeySequence("Escape"), self, activated=self._ctx.back)

    # ------------------------------------------------------------------ ui

    def _pbtn(self, name: str, handler, big: bool = False) -> QToolButton:
        """Кнопка плеера с векторной иконкой из appicons."""
        import appicons
        b = QToolButton(self)
        b.setObjectName("PlayerBig" if big else "PlayerBtn")
        b.setIcon(appicons.icon(name, 24 if big else 16,
                                "#14161d" if big else appicons.DEFAULT))
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.clicked.connect(handler)
        if big:
            b.setFixedSize(54, 54)
            b.setIconSize(b.size() * 0.5)
        else:
            b.setFixedSize(44, 38)
        return b

    def _cover_url_hint(self) -> str:
        t = self._player.current()
        return t.artwork if t else ""

    def _title_hint(self) -> str:
        t = self._player.current()
        return t.title if t else "Ничего не играет"

    def _make_cover(self, url: str) -> Cover:
        old = self._cover
        c = Cover(url, self._cover_size, radius=self._cover_radius)
        old.parentWidget().layout().replaceWidget(old, c)
        old.hide()
        old.deleteLater()
        return c

    def _refresh_heart(self) -> None:
        import appicons
        t = self._player.current()
        liked = t is not None and self._storage.is_liked(t.id)
        self._heart.setIcon(appicons.icon("heart_fill" if liked else "heart", 17,
                                          "#ff5500" if liked else "#cfcfd8"))

    def _toggle_like(self) -> None:
        t = self._player.current()
        if t is not None:
            self._storage.toggle_like(t)
            self._refresh_heart()

    def _toggle_fullscreen(self) -> None:
        w = self.window()
        if w.isFullScreen():
            w.showNormal()
        else:
            w.showFullScreen()

    # ------------------------------------------------------------- слоты

    def _on_track(self, track: object) -> None:
        t: Track = track
        if t is None:
            return
        self._title.setText(t.title)
        self._cover = self._make_cover(t.artwork)
        self._refresh_heart()

    def _on_playing(self, playing: bool) -> None:
        import appicons
        self._btn_play.setIcon(appicons.icon("pause" if playing else "play", 24,
                                             "#14161d"))

    # ------------------------------------------------------------ повтор

    def _cycle_repeat(self) -> None:
        self._player.set_repeat_mode(
            {"off": "all", "all": "one", "one": "off"}[self._player.repeat_mode()]
        )

    def _on_repeat(self, mode: str) -> None:
        import appicons
        self._btn_repeat.setIcon(appicons.icon(
            "repeat_one" if mode == "one" else "repeat", 16,
            "#ff7a33" if mode != "off" else appicons.DEFAULT))
        self._btn_repeat.setToolTip({
            "off": "Повтор выключен (клик — повторять всю очередь)",
            "all": "Повтор: вся очередь (клик — повторять один трек)",
            "one": "Повтор: один трек (клик — выключить)",
        }[mode])

    def _on_pos(self, pos: int) -> None:
        self._t_cur.setText(fmt_time(pos))
        if not self._resume.isSliderDown():
            self._resume.setValue(pos)

    def _on_dur(self, dur: int) -> None:
        self._t_total.setText(fmt_time(dur))
        self._resume.setRange(0, dur if dur > 0 else 0)
