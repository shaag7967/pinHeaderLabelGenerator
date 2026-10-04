"""Zoomable preview of the label or the whole page."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QGraphicsItem, QGraphicsScene, QGraphicsView

from ..layout import PAGE_HEIGHT_MM, PAGE_WIDTH_MM, LabelLayout
from ..rendering import LabelPainter, PagePainter

ZOOM_STEP = 1.2


class PreviewItem(QGraphicsItem):
    """Scene item that paints the label sheet or the A4 page (scene units = mm)."""

    def __init__(self) -> None:
        super().__init__()
        self.sheet_layout: LabelLayout | None = None
        self.page_painter: PagePainter | None = None
        self.label_painter: LabelPainter | None = None

    def set_layout(self, layout: LabelLayout, page: bool) -> None:
        self.prepareGeometryChange()
        self.sheet_layout = layout
        self.page_painter = PagePainter(layout) if page else None
        self.label_painter = None if page else LabelPainter(layout)
        self.update()

    def paper_rect(self) -> QRectF:
        if self.page_painter is not None:
            return QRectF(0, 0, PAGE_WIDTH_MM, PAGE_HEIGHT_MM)
        if self.sheet_layout is None:
            return QRectF(0, 0, 10, 10)
        return QRectF(0, 0, self.sheet_layout.bbox.width, self.sheet_layout.bbox.height)

    def boundingRect(self) -> QRectF:
        return self.paper_rect().adjusted(-1, -1, 2, 2)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        if self.sheet_layout is None:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        paper = self.paper_rect()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 45))  # drop shadow
        painter.drawRect(paper.translated(0.5, 0.5))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRect(paper)
        if self.page_painter is not None:
            self.page_painter.paint(painter)
        elif self.label_painter is not None:
            self.label_painter.paint(painter, QPointF(0, 0))


class PreviewView(QGraphicsView):
    """Graphics view with mouse wheel zoom, drag panning and fit/1:1 modes."""

    def __init__(self) -> None:
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.item = PreviewItem()
        self.scene().addItem(self.item)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.TextAntialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QColor("#d6d8dd"))
        self.setMinimumWidth(320)

    def show_layout(self, layout: LabelLayout, page: bool, refit: bool) -> None:
        self.item.set_layout(layout, page)
        self.scene().setSceneRect(self.item.boundingRect().adjusted(-6, -6, 6, 6))
        if refit:
            self.fit()

    def fit(self) -> None:
        self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def real_size(self) -> None:
        """Approximately real size on screen."""
        screen = self.screen()
        dpi = screen.physicalDotsPerInch() if screen else 96.0
        self.resetTransform()
        self.scale(dpi / 25.4, dpi / 25.4)

    def wheelEvent(self, event) -> None:
        factor = ZOOM_STEP if event.angleDelta().y() > 0 else 1 / ZOOM_STEP
        self.scale(factor, factor)

    def mouseDoubleClickEvent(self, event) -> None:
        self.fit()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self.fit)
