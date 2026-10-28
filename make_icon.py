# -*- coding: utf-8 -*-
"""Генерирует icon.ico/icon.png: тёмный скруглёный квадрат, оранжевое облако,
белая «D» слева. Запуск: python make_icon.py"""

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

    # оранжевое облако (справа): скруглёное основание + круглые бугры
    cloud = QPainterPath()
    body = QRect(104, 128, 122, 64)
    cloud.addRoundedRect(body, 32, 32)
    cloud.addEllipse(96, 96, 78, 78)
    cloud.addEllipse(148, 76, 100, 100)
    cloud.setFillRule(Qt.FillRule.WindingFill)  # объединяем фигуры без дыр
    cgrad = QLinearGradient(96, 80, 236, 190)
    cgrad.setColorAt(0.0, QColor("#ff7a1f"))
    cgrad.setColorAt(1.0, QColor("#e63c00"))
    p.fillPath(cloud.translated(24, 46), cgrad)

    # белая «D» слева — чистая геометрия (в offscreen нет шрифтов)
    left, top, bottom = 26, 58, 198
    right = left + 96  # 122
    outer = QPainterPath()
    outer.moveTo(left, top)
    outer.lineTo(right, top)
    # правая сторона — полный полукруг вниз (по часовой)
    outer.arcTo(QRectF(right - 70, top, 140, bottom - top), 90, -180)
    outer.lineTo(left, bottom)
    outer.closeSubpath()
    inner = QPainterPath()
    inner.addEllipse(60, 90, 46, 76)
    p.fillPath(outer.subtracted(inner), QColor("#f2f2f6"))

    p.end()
    ok = pm.save("icon.ico", "ICO")
    ok2 = pm.save("icon.png", "PNG")
    print("icon.ico:", "OK" if ok else "FAIL", "| icon.png:", "OK" if ok2 else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
