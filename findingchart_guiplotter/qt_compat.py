from __future__ import annotations

"""Qt binding compatibility helpers.

The app prefers PySide6, but some astronomy conda environments already carry
PyQt6 and can fail if both bindings are imported in the same process. Importing
Qt before Matplotlib also lets Matplotlib select the same binding.
"""

import os
from datetime import datetime, timezone


QT_API = os.environ.get("FINDING_CHART_QT_API", "").strip().lower()

if QT_API == "pyqt6":
    from PyQt6.QtCore import QDateTime, QObject, QThread, Qt, pyqtSignal as Signal
    from PyQt6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QDateTimeEdit,
        QDoubleSpinBox,
        QFileDialog,
        QFormLayout,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSlider,
        QSpinBox,
        QTabWidget,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
    BINDING = "PyQt6"
else:
    try:
        from PySide6.QtCore import QDateTime, QObject, QThread, Qt, Signal
        from PySide6.QtWidgets import (
            QApplication,
            QCheckBox,
            QComboBox,
            QDateTimeEdit,
            QDoubleSpinBox,
            QFileDialog,
            QFormLayout,
            QGridLayout,
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QSlider,
            QSpinBox,
            QTabWidget,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
        BINDING = "PySide6"
    except ImportError:
        from PyQt6.QtCore import QDateTime, QObject, QThread, Qt, pyqtSignal as Signal
        from PyQt6.QtWidgets import (
            QApplication,
            QCheckBox,
            QComboBox,
            QDateTimeEdit,
            QDoubleSpinBox,
            QFileDialog,
            QFormLayout,
            QGridLayout,
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QSlider,
            QSpinBox,
            QTabWidget,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
        BINDING = "PyQt6"


def qdatetime_to_datetime(value) -> datetime:
    """Preserve the Qt instant and return an explicitly UTC Python datetime."""
    return datetime.fromtimestamp(value.toMSecsSinceEpoch() / 1000, tz=timezone.utc)
