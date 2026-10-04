"""Small reusable widget helpers."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QColorDialog, QComboBox, QMenu, QWidget

from ..core.palette import JUMPER_PALETTE
from ..i18n import tr

ColorCallback = Callable[[str], None]


def color_icon(hex_color: str, size: int = 14) -> QIcon:
    """Rounded color swatch; an empty color is shown crossed out."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(QColor("#666666"))
    painter.setBrush(QColor(hex_color) if hex_color else Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(QRectF(0.5, 0.5, size - 1, size - 1), 3, 3)
    if not hex_color:
        painter.drawLine(QPointF(3, size - 3), QPointF(size - 3, 3))
    painter.end()
    return QIcon(pixmap)


def make_combo(items: Sequence[tuple[str, object]]) -> QComboBox:
    """Combo box from ``(text, data)`` pairs."""
    combo = QComboBox()
    for text, data in items:
        combo.addItem(text, data)
    return combo


def select_combo_data(combo: QComboBox, data: object) -> None:
    combo.setCurrentIndex(max(0, combo.findData(data)))


def populate_color_menu(menu: QMenu, parent: QWidget, callback: ColorCallback) -> None:
    """Fill ``menu`` with "no color", the jumper palette and a custom color entry."""
    menu.addAction(color_icon(""), tr("No color")).triggered.connect(lambda: callback(""))
    menu.addSeparator()
    for color in JUMPER_PALETTE:
        action = menu.addAction(color_icon(color.hex), tr(color.name))
        action.triggered.connect(lambda _checked=False, h=color.hex: callback(h))
    menu.addSeparator()

    def choose_custom() -> None:
        color = QColorDialog.getColor(QColor("#1565c0"), parent, tr("Choose color"))
        if color.isValid():
            callback(color.name())

    menu.addAction(tr("Other color…")).triggered.connect(choose_custom)
