# -*- coding: utf-8 -*-
"""Точка входа: python main.py (или run.bat)."""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from PySide6.QtCore import QEvent, QObject, Qt
        from PySide6.QtWidgets import (
            QApplication,
            QAbstractSpinBox,
            QComboBox,
            QDateEdit,
            QDateTimeEdit,
            QLineEdit,
            QPlainTextEdit,
            QSpinBox,
            QTextEdit,
            QTimeEdit,
        )
    except ImportError:
        print("Не установлен PySide6. Выполни:  pip install -r requirements.txt")
        return 2

    import theme
    from mainwindow import MainWindow

    # Свой AppUserModelID: иначе панель задач показывает иконку python.exe
    # (как у IDLE), потому что процесс группируется по exe интерпретатора.
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "SoundCloudClient.Client.1"
            )
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(theme.QSS)
    app.setApplicationName("SoundCloud Client")

    from PySide6.QtGui import QIcon
    from pathlib import Path
    ico = Path(__file__).with_name("icon.png")
    if ico.exists():
        app.setWindowIcon(QIcon(str(ico)))

    win = MainWindow()
    win.resize(1200, 780)
    win.show()

    # Размытие + тёмная рамка (только Windows; иначе обычное окно).
    # Блюр всегда включён (BlurBehind) — настройка 'blur' в library.json
    # оставлена исторически и игнорируется.
    try:
        import window_effects
        mode = window_effects.apply_window_effects(win, blur="glass")
        if mode in ("none", "unsupported"):
            # убираем прозрачность, иначе было бы «чёрное окно-дырка»
            win.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        elif mode == "transparency_disabled":
            print("== Прозрачность окна отключена в Windows! ==\n"
                  "  Параметры → Персонализация → Цвета → «Эффекты прозрачности» → ВКЛ,\n"
                  "  затем перезапусти SoundCloud Client.")
            win.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        print(f"Режим фона окна: {mode}")
    except Exception as e:
        print(f"Эффекты окна недоступны ({e}) — работаем без блюра")

    # Пробел = пауза/плей (когда фокус не в поле ввода)
    editable_types = (QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox,
                      QAbstractSpinBox, QComboBox, QDateEdit, QTimeEdit,
                      QDateTimeEdit)

    class SpaceGrabber(QObject):
        def eventFilter(self, obj, ev) -> bool:
            if ev.type() == QEvent.Type.KeyPress and ev.key() == Qt.Key_Space:
                if not isinstance(QApplication.focusWidget(), editable_types):
                    win.toggle_play()
                    return True
            return False

    grabber = SpaceGrabber()
    app.installEventFilter(grabber)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
