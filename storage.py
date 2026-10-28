# -*- coding: utf-8 -*-
"""Локальная библиотека: лайки и недавние треки (JSON в %APPDATA%)."""

from __future__ import annotations

import json
from typing import Dict, List

import common
from common import Track
from sc_api import CONFIG_DIR

FILE = CONFIG_DIR / "library.json"


class Storage:
    def __init__(self) -> None:
        self._likes: Dict[int, dict] = {}
        self._recents: List[dict] = []
        self._settings: Dict[str, object] = {}
        self._load()

    # ------------------------------------------------------------ база

    def _load(self) -> None:
        try:
            data = json.loads(FILE.read_text("utf-8"))
        except Exception:
            data = {}
        self._likes = {}
        for k, v in (data.get("likes") or {}).items():
            try:
                self._likes[int(k)] = v
            except (TypeError, ValueError):
                continue
        self._recents = list(data.get("recents") or [])
        self._settings = dict(data.get("settings") or {})

    def save(self) -> None:
        data = {
            "likes": {str(k): v for k, v in self._likes.items()},
            "recents": self._recents[:200],
            "settings": self._settings,
        }
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            tmp = FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
            tmp.replace(FILE)
        except OSError:
            pass

    # ------------------------------------------------------------ лайки

    def is_liked(self, track_id: int) -> bool:
        return track_id in self._likes

    def toggle_like(self, track: Track) -> bool:
        if track.id in self._likes:
            del self._likes[track.id]
            self.save()
            return False
        self._likes[track.id] = track.to_brief()
        self.save()
        return True

    def likes(self) -> List[Track]:
        return [Track.from_brief(v) for v in reversed(list(self._likes.values()))]

    # ----------------------------------------------------------- recents

    def add_recent(self, track: Track) -> None:
        brief = track.to_brief()
        self._recents = [b for b in self._recents if b.get("id") != track.id]
        self._recents.insert(0, brief)
        self.save()

    def clear_recents(self) -> None:
        self._recents = []
        self.save()

    def clear_likes(self) -> None:
        self._likes = {}
        self.save()

    def recents(self) -> List[Track]:
        return [Track.from_brief(b) for b in self._recents]

    # ----------------------------------------------------------- настройки

    def setting(self, key: str, default=None):
        return self._settings.get(key, default)

    def set_setting(self, key: str, value) -> None:
        self._settings[key] = value
        self.save()
