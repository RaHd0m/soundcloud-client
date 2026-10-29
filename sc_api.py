# -*- coding: utf-8 -*-
"""Неофициальный web-API SoundCloud (api-v2.soundcloud.com).

SoundCloud закрыл публичный API для новых приложений, поэтому здесь
используется тот же приём, что и у известных опенсорсных клиентов:
берём публичный client_id фронтенда soundcloud.com и ходим в api-v2.
client_id кэшируется в %APPDATA%\\SCClient\\client_id.json.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

BASE_V2 = "https://api-v2.soundcloud.com"
WEB = "https://soundcloud.com"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

_appdata = os.environ.get("APPDATA")
if not _appdata:
    _appdata = str(Path.home() / "AppData" / "Roaming")
CONFIG_DIR = Path(_appdata) / "SCClient"
CACHE_FILE = CONFIG_DIR / "client_id.json"


class SoundCloudError(RuntimeError):
    """Ошибка обращения к SoundCloud."""


class ImageError(SoundCloudError):
    """Не удалось загрузить картинку."""


class SoundCloudAPI:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": UA, "Accept": "application/json, text/plain, */*"}
        )
        self._client_id: Optional[str] = None

    # ------------------------------------------------------------------ id

    def client_id(self) -> str:
        if self._client_id:
            return self._client_id
        cid = self._load_cached() or self._discover()
        self._client_id = cid
        return cid

    def refresh(self) -> str:
        self._client_id = self._discover()
        return self._client_id

    def _probe(self, cid: str) -> bool:
        try:
            r = self.session.get(
                BASE_V2 + "/search",
                params={"q": "test", "limit": 1, "client_id": cid},
                timeout=15,
            )
            return r.status_code == 200 and r.text.lstrip().startswith("{")
        except requests.RequestException:
            return False

    def _load_cached(self) -> Optional[str]:
        try:
            data = json.loads(CACHE_FILE.read_text("utf-8"))
            cid = data.get("client_id")
            ts = data.get("ts", 0)
            if cid and time.time() - ts < 30 * 24 * 3600 and self._probe(cid):
                return cid
        except Exception:
            return None
        return None

    def _discover(self) -> str:
        # Главная страница: находим скрипты фронтенда и ищем в них client_id.
        try:
            page = self.session.get(WEB + "/", timeout=15, headers={"Accept": "text/html"})
            scripts = re.findall(r'https://a-v2\.sndcdn\.com/assets/[^"\'<>\s]+\.js', page.text)
        except requests.RequestException as e:
            raise SoundCloudError(f"Нет доступа к soundcloud.com: {e}") from e
        if not scripts:
            raise SoundCloudError("soundcloud.com отдал страницу без скриптов (возможно, регион заблокирован)")
        for url in scripts[:10]:
            try:
                js = self.session.get(url, timeout=15)
                m = re.search(r'client_id[=:]\s*["\']([a-zA-Z0-9]{32})["\']', js.text)
            except requests.RequestException:
                continue
            if m and self._probe(m.group(1)):
                cid = m.group(1)
                self._save(cid)
                return cid
        raise SoundCloudError("Не удалось получить client_id SoundCloud")

    def _save(self, cid: str) -> None:
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(
                json.dumps({"client_id": cid, "ts": time.time()}), "utf-8"
            )
        except OSError:
            pass

    # ------------------------------------------------------------- запросы

    def _get(self, path: str, params: Optional[dict] = None, retry: bool = True) -> Any:
        full = dict(params or {})
        full["client_id"] = self.client_id()
        r = self.session.get(BASE_V2 + path, params=full, timeout=20)
        if r.status_code in (401, 403) and retry:
            self.refresh()
            return self._get(path, params, retry=False)
        if r.status_code == 404:
            raise SoundCloudError("Не найдено (404)")
        if r.status_code == 429:
            raise SoundCloudError("SoundCloud: слишком много запросов, подожди минуту")
        if not r.ok:
            raise SoundCloudError(f"SoundCloud API вернул {r.status_code}")
        try:
            return r.json()
        except ValueError as e:
            raise SoundCloudError("SoundCloud вернул не JSON") from e

    def _call_href(self, href: str) -> dict:
        base = BASE_V2
        if href.startswith(base):
            href = href[len(base):]
        elif not href.startswith("/"):
            href = "/" + href
        sep = "&" if "?" in href else "?"
        r = self.session.get(f"{base}{href}{sep}client_id={self.client_id()}", timeout=20)
        if not r.ok:
            raise SoundCloudError(f"SoundCloud API вернул {r.status_code}")
        return r.json()

    def _paged(self, path: str, params: dict, max_items: int = 200) -> list:
        items: List[Any] = []
        href: Optional[str] = None
        while len(items) < max_items:
            data = self._get(path, params) if href is None else self._call_href(href)
            if not isinstance(data, dict):
                break
            chunk = data.get("collection") or []
            items.extend(chunk)
            href = data.get("next_href")
            if not href:
                break
        return items

    # ------------------------------------------------------------- методы

    def search(self, q: str, kind: str = "tracks", limit: int = 40) -> list:
        return self._get(f"/search/{kind}", {"q": q, "limit": limit, "offset": 0}).get(
            "collection", []
        )

    def get_track(self, track_id: int) -> dict:
        return self._get(f"/tracks/{track_id}")

    def get_user(self, user_id: int) -> Dict[str, Any]:
        return self._get(f"/users/{user_id}")

    def user_tracks(self, user_id: int, limit: int = 60) -> list:
        return self._paged(
            f"/users/{user_id}/tracks", {"limit": limit, "linked_partitioning": 1}
        )

    def user_playlists(self, user_id: int, limit: int = 30) -> list:
        return self._paged(
            f"/users/{user_id}/playlists", {"limit": limit, "linked_partitioning": 1}
        )

    def get_playlist(self, playlist_id: int) -> dict:
        data = self._get(f"/playlists/{playlist_id}")
        tracks = data.get("tracks")
        # В search-результатах у плейлистов треки приходят как URI — разворачиваем.
        if tracks and any(isinstance(t, str) for t in tracks):
            ids = [t.split(":")[-1] for t in tracks if isinstance(t, str)]
            full = self._get("/tracks", {"ids": ",".join(ids[:80])})
            by_id = {t.get("id"): t for t in (full if isinstance(full, list) else [])}
            data["tracks"] = [by_id[int(i)] for i in map(int, ids) if int(i) in by_id]
        return data

    # ------------------------------------------------------------- радио

    def _expand_ids(self, ids: list) -> list:
        """Полные треки по списку id: `/tracks?ids=…` пачками по 80."""
        full: List[Any] = []
        for i in range(0, len(ids), 80):
            chunk = ids[i : i + 80]
            res = self._get("/tracks", {"ids": ",".join(map(str, chunk))})
            if isinstance(res, list):
                full.extend(res)
        by_id = {t.get("id"): t for t in full if isinstance(t, dict) and t.get("id")}
        return [by_id[i] for i in ids if i in by_id]

    def mixed_selections(self, limit: int = 20) -> List[dict]:
        """Селекции Discover'а SoundCloud: подборки-миксы + «Trending by genre».

        У каждой селекции items уже вшиты в ответ (items.collection).
        """
        data = self._get("/mixed-selections", {"limit": limit})
        return [s for s in (data.get("collection") or []) if isinstance(s, dict)]

    def system_playlist(self, urn: str) -> dict:
        """Жанровые подборки (system-playlist): например trending-by-genre:trap.

        Треки приходят заглушками {id, kind} — разворачиваем в полные.
        """
        data = self._get("/system-playlists/" + quote(urn, safe=""))
        stubs = data.get("tracks") or []
        ids = [t.get("id") for t in stubs if isinstance(t, dict) and t.get("id")]
        if ids:
            data["tracks"] = self._expand_ids(ids)
        return data

    def stream_url(self, track: dict) -> str:
        """Ссылка на аудиопоток: сначала прямой mp3 (progressive), потом HLS."""
        media = track.get("media") or {}
        prefs = media.get("transcodings") or []
        auth = media.get("track_authorization")
        prog = next(
            (p for p in prefs if (p.get("format") or {}).get("protocol") == "progressive"),
            None,
        )
        hls = next(
            (p for p in prefs if (p.get("format") or {}).get("protocol") == "hls"), None
        )
        pref = prog or hls
        if not pref:
            raise SoundCloudError("У трека нет доступных аудиопотоков")
        params: Dict[str, str] = {"client_id": self.client_id()}
        if auth:
            params["track_authorization"] = auth
        r = self.session.get(pref["url"], params=params, timeout=20)
        if not r.ok:
            raise SoundCloudError(f"Не удалось получить ссылку на поток ({r.status_code})")
        url = r.json().get("url")
        if not url:
            raise SoundCloudError("Пустая ссылка на поток (трек может требовать подписку go+)")
        return url

    def get_bytes(self, url: str, timeout: int = 15) -> bytes:
        r = self.session.get(url, timeout=timeout)
        if not r.ok:
            raise ImageError(f"Сеть: {r.status_code}")
        return r.content


# Глобальный экземпляр
api = SoundCloudAPI()
