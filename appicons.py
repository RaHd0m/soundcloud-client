# -*- coding: utf-8 -*-
"""Векторные иконки приложения (рисуются QPainter'ом, кэшируются QIcon).

Использование: icon("play"), icon("heart_fill", color="#ff5500").
Формы рисуются в квадрате 0..100, масштабируются под размер кнопки.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF

_CACHE: dict = {}

DEFAULT = "#f0f0f4"


def icon(name: str, size: int = 20, color: str = DEFAULT) -> QIcon:
    key = (name, size, color)
    if key in _CACHE:
        return _CACHE[key]
    pm = QPixmap(size * 2, size * 2)  # ретина-запас
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size * 2
    p.scale(s / 100.0, s / 100.0)

    if name == "play":
        tri = QPolygonF([QPointF(30, 16), QPointF(88, 50), QPointF(30, 84)])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        p.drawPolygon(tri)
    elif name == "pause":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        p.drawRoundedRect(QRectF(24, 18, 18, 64), 6, 6)
        p.drawRoundedRect(QRectF(58, 18, 18, 64), 6, 6)
    elif name == "prev":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        bar = QPainterPath()
        bar.addRoundedRect(QRectF(18, 20, 10, 60), 4, 4)
        p.drawPath(bar)
        tri = QPolygonF([QPointF(82, 18), QPointF(32, 50), QPointF(82, 82)])
        p.drawPolygon(tri)
    elif name == "next":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        bar = QPainterPath()
        bar.addRoundedRect(QRectF(72, 20, 10, 60), 4, 4)
        p.drawPath(bar)
        tri = QPolygonF([QPointF(18, 18), QPointF(68, 50), QPointF(18, 82)])
        p.drawPolygon(tri)
    elif name in ("heart", "heart_fill"):
        path = QPainterPath()
        path.setFillRule(Qt.FillRule.WindingFill)
        path.addEllipse(QRectF(6, 14, 40, 40))
        path.addEllipse(QRectF(54, 14, 40, 40))
        tri = QPolygonF([QPointF(8, 44), QPointF(92, 44), QPointF(50, 88)])
        path.addPolygon(tri)
        path.closeSubpath()
        if name == "heart_fill":
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(color))
            p.drawPath(path)
        else:
            p.setPen(QPen(QColor(color), 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path.simplified())
    elif name == "expand":
        pen = QPen(QColor(color), 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        k = 26
        for x1, y1, x2, y2 in (
            (14, 14, 14, 14 + k), (14, 14, 14 + k, 14),
            (86, 14, 86, 14 + k), (86, 14, 86 - k, 14),
            (14, 86, 14, 86 - k), (14, 86, 14 + k, 86),
            (86, 86, 86, 86 - k), (86, 86, 86 - k, 86),
        ):
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
    elif name == "close":
        pen = QPen(QColor(color), 9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(24, 24), QPointF(76, 76))
        p.drawLine(QPointF(76, 24), QPointF(24, 76))
    elif name == "volume":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        spk = QPainterPath()
        spk.moveTo(12, 38)
        spk.lineTo(36, 38)
        spk.lineTo(58, 18)
        spk.lineTo(58, 82)
        spk.lineTo(36, 62)
        spk.lineTo(12, 62)
        spk.closeSubpath()
        p.drawPath(spk)
        pen = QPen(QColor(color), 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(56, 30, 24, 40), -55, 110)
        p.drawArc(QRectF(60, 20, 38, 60), -55, 110)
    elif name == "trash":
        p.setPen(QPen(QColor(color), 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(20, 30), QPointF(80, 30))
        body = QPainterPath()
        body.addRoundedRect(QRectF(30, 30, 40, 54), 8, 8)
        p.drawPath(body)
        p.drawLine(QPointF(40, 20), QPointF(60, 20))
        p.drawLine(QPointF(44, 44), QPointF(44, 68))
        p.drawLine(QPointF(56, 44), QPointF(56, 68))

    p.end()
    ic = QIcon(pm)
    _CACHE[key] = ic
    return ic


def pixmap(name: str, size: int = 20, color: str = DEFAULT) -> QPixmap:
    return icon(name, size, color).pixmap(size * 2, size * 2)
