# -*- coding: utf-8 -*-
"""Генерирует icon.ico/icon.png: тёмный скруглёный квадрат + оранжевое облако.
Запуск: python make_icon.py"""

from __future__ import annotations

import os
import sys


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication([])  # QPixmap требует живого приложения

    from PySide6.QtCore import QRect, QRectF, Qt
    from PySide6.QtGui import (
        QColor,
        QLinearGradient,
        QPainter,
        QPainterPath,
        QPixmap,
    )

    size = 256
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # тёмный стеклянный фон
    bg = QPainterPath()
    bg.addRoundedRect(10, 10, size - 20, size - 20, 58, 58)
    grad = QLinearGradient(10, 10, size - 20, size - 20)
    grad.setColorAt(0.0, QColor("#1b1e28"))
    grad.setColorAt(1.0, QColor("#0d0e14"))
    p.setClipPath(bg)
    p.fillPath(bg, grad)

    # оранжевое облако (по центру): скруглёное основание + круглые бугры
    cloud = QPainterPath()
    body = QRect(56, 128, 144, 64)
    cloud.addRoundedRect(body, 32, 32)
    cloud.addEllipse(48, 96, 78, 78)
    cloud.addEllipse(104, 76, 100, 100)
    cloud.setFillRule(Qt.FillRule.WindingFill)  # объединяем фигуры без дыр
    cgrad = QLinearGradient(48, 80, 216, 190)
    cgrad.setColorAt(0.0, QColor("#ff7a1f"))
    cgrad.setColorAt(1.0, QColor("#e63c00"))
    p.fillPath(cloud.translated(4, 18), cgrad)

    p.end()
    ok = pm.save("icon.ico", "ICO")
    ok2 = pm.save("icon.png", "PNG")
    print("icon.ico:", "OK" if ok else "FAIL", "| icon.png:", "OK" if ok2 else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
