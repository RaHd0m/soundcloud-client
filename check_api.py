# -*- coding: utf-8 -*-
"""Проверка доступа к SoundCloud без GUI:  python check_api.py"""

from __future__ import annotations

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from sc_api import api


def main() -> int:
    try:
        cid = api.client_id()
        print("[1] client_id:", cid)
    except Exception as e:
        print("[1] client_id: FAIL —", e)
        print("Проверь доступ к soundcloud.com (если он заблокирован в твоей сети — нужен VPN).")
        return 1

    try:
        res = api.search("lofi", "tracks", 5)
        print("[2] поиск: OK,", len(res), "треков")
    except Exception as e:
        print("[2] поиск: FAIL —", e)
        return 1

    if res:
        d = res[0]
        try:
            url = api.stream_url(d)
            kind = "HLS" if ".m3u8" in url or "/playlist" in url else "mp3"
            print(f"[3] поток «{d.get('title')}»: OK ({kind})")
        except Exception as e:
            print("[3] поток: FAIL —", e)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
