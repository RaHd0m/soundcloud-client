# -*- coding: utf-8 -*-
"""Общие модели и утилиты: фоновые задачи, картинки, нормализация данных."""

from __future__ import annotations

import html
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QImage

import sc_api

POOL = ThreadPoolExecutor(max_workers=6)


# --------------------------------------------------------------- форматы

def fmt_time(ms: Optional[int]) -> str:
    if not ms or ms <= 0:
        return "--:--"
    s = int(ms // 1000)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


def fmt_count(n: Optional[int]) -> str:
    if not n or n < 0:
        return ""
    if n >= 1_000_000:
        s = f"{n / 1_000_000:.1f}"
    elif n >= 1_000:
        v = n / 1_000
        s = f"{v:.1f}" if v < 100 else f"{v:.0f}"
    else:
        return str(n)
    s = s.rstrip("0").rstrip(".").replace(".", ",")
    return s + " млн" if n >= 1_000_000 else s + " тыс."


# ---------------------------------------------------------------- трек

@dataclass
class Track:
    id: int
    title: str
    artist: str
    duration: int  # мс
    artwork: str
    permalink: str
    plays: int = 0
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, d: dict) -> "Track":
        user = d.get("user") or {}
        art = d.get("artwork_url") or user.get("avatar_url") or ""
        art = art.replace("-large.", "-t500x500.")
        return cls(
            id=d.get("id") or 0,
            title=html.unescape(d.get("title") or "Без названия"),
            artist=html.unescape(user.get("username") or ""),
            duration=d.get("full_duration") or d.get("duration") or 0,
            artwork=art,
            permalink=d.get("permalink_url") or "",
            plays=d.get("playback_count") or 0,
            raw=d,
        )

    def to_brief(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "duration": self.duration,
            "artwork": self.artwork,
            "permalink": self.permalink,
            "plays": self.plays,
        }

    @classmethod
    def from_brief(cls, d: dict) -> "Track":
        return cls(
            id=d.get("id") or 0,
            title=d.get("title") or "Без названия",
            artist=d.get("artist") or "",
            duration=d.get("duration") or 0,
            artwork=d.get("artwork") or "",
            permalink=d.get("permalink") or "",
            plays=d.get("plays") or 0,
            raw={},
        )


# ------------------------------------------------------ контекст приложения

class Ctx:
    """Ссылки на общие сервисы: плеер, библиотека, навигация."""

    def __init__(self, player, storage, navigate: Callable, back: Callable) -> None:
        self.player = player
        self.storage = storage
        self.navigate = navigate
        self.back = back


# ---------------------------------------------------------- фоновые задачи

_JOBS: List["Job"] = []


class Job(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, fn: Callable, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._fn = fn

    def start(self) -> "Job":
        _JOBS.append(self)  # защита от сборки мусора
        QTimer.singleShot(0, lambda: POOL.submit(self._run))
        return self

    def _run(self) -> None:
        try:
            res = self._fn()
        except Exception as e:  # noqa: BLE001 — показываем текст пользователю
            self.failed.emit(str(e))
        else:
            self.finished.emit(res)
        finally:
            try:
                _JOBS.remove(self)
            except ValueError:
                pass


def run(fn: Callable, on_done: Callable, on_fail: Optional[Callable] = None,
        parent: Optional[QObject] = None) -> Job:
    """Выполнить fn в фоновом потоке, результат — в GUI-потоке получателя."""
    job = Job(fn, parent=parent)
    job.finished.connect(on_done)
    job.failed.connect(on_fail or (lambda *_: None))
    job.start()
    return job


# ---------------------------------------------------------------- картинки

_IMG_CACHE: dict[str, QImage] = {}


def fetch_image(url: str, receiver: QObject, on_ok: Callable[[str, QImage], None],
                on_fail: Optional[Callable] = None):
    cached = _IMG_CACHE.get(url)
    if cached is not None:
        on_ok(url, cached)
        return None

    def _do() -> QImage:
        data = sc_api.api.get_bytes(url, timeout=12)
        img = QImage.fromData(data)
        if img.isNull():
            raise sc_api.ImageError("Пустое изображение")
        return img

    def _ok(img: Any) -> None:
        if isinstance(img, QImage) and not img.isNull():
            _IMG_CACHE[url] = img
        on_ok(url, img)

    return run(_do, _ok, on_fail, parent=receiver)
