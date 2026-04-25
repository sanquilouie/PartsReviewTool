from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QListWidget, QListWidgetItem

from app.models.asset_record import AssetRecord


class SvgGallery(QListWidget):
    assetSelected = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.setViewMode(QListWidget.IconMode)
        self.setResizeMode(QListWidget.Adjust)
        self.setMovement(QListWidget.Static)
        self.setIconSize(QSize(128, 128))
        self.setGridSize(QSize(168, 178))
        self.setSpacing(8)
        self.setUniformItemSizes(True)
        self.currentRowChanged.connect(self.assetSelected.emit)

    def set_assets(self, assets: list[AssetRecord]) -> None:
        self.clear()
        for index, asset in enumerate(assets):
            item = QListWidgetItem()
            item.setText(self._label(asset))
            item.setIcon(QIcon(self._thumbnail(Path(asset.source_path))))
            item.setData(32, index)
            self.addItem(item)

    def refresh_asset(self, index: int, asset: AssetRecord) -> None:
        item = self.item(index)
        if item is not None:
            item.setText(self._label(asset))

    def _label(self, asset: AssetRecord) -> str:
        prefix = asset.destination_slot or "unassigned"
        return f"{prefix}\n{asset.original_filename}"

    def _thumbnail(self, path: Path) -> QPixmap:
        pixmap = QPixmap(128, 128)
        pixmap.fill()

        renderer = QSvgRenderer(str(path))
        if not renderer.isValid():
            return pixmap

        painter = QPainter(pixmap)
        try:
            renderer.render(painter)
        finally:
            painter.end()

        return pixmap
