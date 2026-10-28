# -*- coding: utf-8 -*-
"""Плеер: очередь, потоковая загрузка ссылок, QMediaPlayer."""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

import sc_api
from common import Track, run


class Player(QObject):
    trackChanged = Signal(object)      # Track | None
    playingChanged = Signal(bool)
    positionChanged = Signal("qlonglong")
    durationChanged = Signal("qlonglong")
    volumeChanged = Signal(int)        # 0..100
    error = Signal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._media = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._audio.setVolume(0.8)
        self._media.setAudioOutput(self._audio)

        self._media.positionChanged.connect(self.positionChanged)
        self._media.durationChanged.connect(self.durationChanged)
        self._media.playbackStateChanged.connect(self._on_playback_state)
        self._media.mediaStatusChanged.connect(self._on_media_status)
        self._media.errorOccurred.connect(self._on_media_error)

        self._queue: List[Track] = []
        self._idx = -1
        self._token = 0  # защита от устаревших ответов при быстрой переключке

    # ------------------------------------------------------------- stale

    def current(self) -> Optional[Track]:
        if 0 <= self._idx < len(self._queue):
            return self._queue[self._idx]
        return None

    def is_playing(self) -> bool:
        return self._media.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def position(self) -> int:
        return self._media.position()

    def duration(self) -> int:
        return self._media.duration()

    # --------------------------------------------------------- управление

    def play_queue(self, tracks: List[Track], index: int = 0) -> None:
        if not tracks:
            return
        self._queue = list(tracks)
        self._play_at(index)

    def _play_at(self, index: int) -> None:
        self._token += 1
        token = self._token
        if not 0 <= index < len(self._queue):
            self._media.stop()
            return
        self._idx = index
        track = self._queue[index]
        self.trackChanged.emit(track)
        self._media.setSource(QUrl())  # сброс предыдущего источника
        # Восстановленный из библиотеки/недавних трек почти голый — дозагружаем.
        if not (track.raw.get("media") or {}).get("transcodings"):
            def _fetch():
                return sc_api.api.get_track(track.id)

            def _got(full, tk=token):
                if tk != self._token:
                    return
                track.raw = full or {}
                self._load_and_play(track, tk)

            def _fail(msg, tk=token):
                if tk != self._token:
                    return
                self.error.emit(f"Не удалось загрузить трек: {msg}")
            run(_fetch, _got, _fail, parent=self)
        else:
            self._load_and_play(track, token)

    def _load_and_play(self, track: Track, token: int) -> None:
        def _get():
            return sc_api.api.stream_url(track.raw)

        def _got(url, tk=token):
            if tk != self._token:
                return
            self._media.setSource(QUrl(url))
            self._media.play()

        def _fail(msg, tk=token):
            if tk != self._token:
                return
            self.error.emit(f"Не удалось воспроизвести: {msg}")
        run(_get, _got, _fail, parent=self)

    def next(self) -> None:
        if self._idx + 1 < len(self._queue):
            self._play_at(self._idx + 1)
        else:
            self._media.stop()

    def prev(self) -> None:
        if self._media.position() > 3000 or self._idx == 0:
            self._media.setPosition(0)
            return
        self._play_at(self._idx - 1)

    def toggle(self) -> None:
        if self.is_playing():
            self._media.pause()
        elif self.current() is not None:
            self._media.play()

    def seek(self, ms: int) -> None:
        if self._media.duration() > 0:
            self._media.setPosition(max(0, int(ms)))

    def set_volume(self, v: int) -> None:
        v = max(0, min(100, int(v)))
        self._audio.setVolume(v / 100.0)
        self.volumeChanged.emit(v)

    def volume(self) -> float:
        """Текущая громкость 0..1 (для инициализации слайдеров)."""
        return self._audio.volume()

    # ----------------------------------------------------------- события

    def _on_playback_state(self, state) -> None:
        self.playingChanged.emit(state == QMediaPlayer.PlaybackState.PlayingState)

    def _on_media_status(self, status) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.next()

    def _on_media_error(self, err, msg) -> None:
        if self._media.source().isEmpty():
            return  # ошибка на пустом источнике после сброса
        self.error.emit(msg or f"Ошибка воспроизведения ({err})")
