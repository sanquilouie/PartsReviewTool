from __future__ import annotations

import subprocess
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSizePolicy,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.models.asset_record import AssetRecord
from app.models.project_state import ProjectState
from app.services.asset_service import AssetService
from app.services.config_service import ConfigService
from app.services.jpexs_service import JpexsService
from app.services.xml_structure_service import XmlStructureService
from app.ui.svg_gallery import SvgGallery
from app.utils.paths import (
    ORGANIZED_DIR,
    RAW_SVG_DIR,
    WORKSPACE_DIR,
    ensure_base_dirs,
    safe_stem,
)


class ExtractionWorker(QObject):
    finished = Signal(object, object)

    def __init__(self, config: dict, swf_path: Path, output_dir: Path) -> None:
        super().__init__()
        self.config = config
        self.swf_path = swf_path
        self.output_dir = output_dir

    @Slot()
    def run(self) -> None:
        try:
            result = JpexsService().extract_svgs(self.config, self.swf_path, self.output_dir)
            self.finished.emit(result, None)
        except Exception as error:
            self.finished.emit(None, error)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        ensure_base_dirs()

        self.setWindowTitle("Ninja Shibui Parts Review MVP")
        self.config_service = ConfigService()
        self.asset_service = AssetService()
        self.xml_structure_service = XmlStructureService()
        self.config = self.config_service.load()
        self.manifest = ProjectState(output_root=str(WORKSPACE_DIR))
        self.current_index = -1
        self.extraction_thread: QThread | None = None

        self._build_ui()
        self._load_config_into_fields()
        self._log("Ready.")

    def _build_ui(self) -> None:
        toolbar = QToolBar("Actions")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        new_action = toolbar.addAction("New")
        settings_action = toolbar.addAction("Settings")
        new_action.triggered.connect(self.new_session)
        settings_action.triggered.connect(self.open_settings)

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(8, 8, 8, 8)

        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.addWidget(self._build_source_panel())
        main_splitter.addWidget(self._build_gallery_panel())
        main_splitter.addWidget(self._build_review_panel())
        main_splitter.setSizes([250, 720, 360])

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(140)

        root_layout.addWidget(main_splitter, 1)
        root_layout.addWidget(self.log)
        self.setCentralWidget(root)

    def _build_source_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        panel.setMaximumWidth(280)
        layout = QVBoxLayout(panel)

        title = QLabel("Source")
        title.setStyleSheet("font-weight: 600;")
        layout.addWidget(title)

        form = QFormLayout()
        self.swf_field = QLineEdit()
        self.xml_field = QLineEdit()
        self.output_root_field = QLineEdit(str(self.config.get("output_root") or WORKSPACE_DIR))
        self.jpexs_field = QLineEdit()

        form.addRow("SWF", self._row_with_button(self.swf_field, "Choose", self.choose_swf))
        layout.addLayout(form)

        self.extract_button = QPushButton("Extract SVGs")
        self.extract_button.clicked.connect(self.extract_svgs)
        layout.addWidget(self.extract_button)

        self.choose_view_folder_button = QPushButton("Choose Folder to View")
        self.choose_view_folder_button.clicked.connect(self.choose_folder_to_view)
        layout.addWidget(self.choose_view_folder_button)

        layout.addStretch(1)
        return panel

    def _build_gallery_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)

        title = QLabel("Organized SVGs")
        title.setStyleSheet("font-weight: 600;")
        layout.addWidget(title)

        self.gallery = SvgGallery()
        self.gallery.setSelectionMode(QAbstractItemView.SingleSelection)
        self.gallery.assetSelected.connect(self.select_asset)
        layout.addWidget(self.gallery, 1)
        return panel

    def _build_review_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)

        title = QLabel("Preview / Organize")
        title.setStyleSheet("font-weight: 600;")
        layout.addWidget(title)

        self.current_file_label = QLabel("No SVG selected")
        self.current_file_label.setWordWrap(True)
        layout.addWidget(self.current_file_label)

        self.preview = QSvgWidget()
        self.preview.setMinimumHeight(260)
        self.preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.preview, 1)

        form = QFormLayout()
        self.new_name_field = QLineEdit()
        form.addRow("New filename", self.new_name_field)
        form.addRow("Quick rename", self._build_quick_rename_row())
        layout.addLayout(form)

        button_row = QHBoxLayout()
        self.save_move_button = QPushButton("Save / Move")
        self.save_move_button.clicked.connect(self.save_selected_asset)
        button_row.addWidget(self.save_move_button)
        layout.addLayout(button_row)

        folder_row = QHBoxLayout()
        self.open_source_button = QPushButton("Open Source Folder")
        self.open_source_button.clicked.connect(self.open_source_folder)
        folder_row.addWidget(self.open_source_button)
        layout.addLayout(folder_row)

        return panel

    def _row_with_button(self, field: QLineEdit, label: str, callback) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        button = QPushButton(label)
        button.clicked.connect(callback)
        layout.addWidget(field, 1)
        layout.addWidget(button)
        return row

    def _build_quick_rename_row(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        for name in ("skin", "layer_01", "layer_02"):
            button = QPushButton(name)
            button.clicked.connect(lambda checked=False, value=name: self.quick_save_filename(value))
            layout.addWidget(button)
        return row

    def quick_save_filename(self, name: str) -> None:
        self.new_name_field.setText(f"{name}.svg")
        self.save_selected_asset()

    def _load_config_into_fields(self) -> None:
        self.output_root_field.setText(str(self.config.get("output_root") or WORKSPACE_DIR))
        self.jpexs_field.setText(str(self.config.get("jpexs_path", "")))

    def open_settings(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        layout = QVBoxLayout(dialog)

        form = QFormLayout()
        output_root = QLineEdit(self.output_root_field.text())
        jpexs_path = QLineEdit(self.jpexs_field.text())
        form.addRow("Output root", self._row_with_button(output_root, "Choose", lambda: self._choose_folder_for_field(output_root)))
        form.addRow("JPEXS", self._row_with_button(jpexs_path, "Choose", lambda: self._choose_file_for_field(jpexs_path)))
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.Accepted:
            return

        self.output_root_field.setText(output_root.text().strip() or str(WORKSPACE_DIR))
        self.jpexs_field.setText(jpexs_path.text().strip())
        self.manifest.output_root = self.output_root_field.text().strip()
        self.manifest.jpexs_path = self.jpexs_field.text().strip()
        self._save_jpexs_config()
        self._set_session_paths()
        self._log("Settings updated.")

    def _choose_folder_for_field(self, field: QLineEdit) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose Output Root", field.text())
        if path:
            field.setText(path)

    def _choose_file_for_field(self, field: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose JPEXS executable or batch file",
            "",
            "Executable or Batch (*.exe *.bat *.cmd);;All Files (*)",
        )
        if path:
            field.setText(path)

    def choose_swf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose SWF", "", "SWF Files (*.swf)")
        if not path:
            return

        swf_path = Path(path)
        self.swf_field.setText(str(swf_path))
        self.manifest.session_name = safe_stem(swf_path)
        self.manifest.source_swf_path = str(swf_path)
        self._detect_xml_for_swf(swf_path)
        self._set_session_paths()
        self._log(f"Selected SWF: {swf_path}")

    def new_session(self) -> None:
        self.manifest = ProjectState(output_root=self.output_root_field.text().strip() or str(WORKSPACE_DIR))
        self.current_index = -1
        self.swf_field.clear()
        self.xml_field.clear()
        self.gallery.clear()
        self.current_file_label.setText("No SVG selected")
        self.new_name_field.clear()
        self.preview.load(bytes())
        self._log("Started a new session.")

    def extract_svgs(self) -> None:
        swf_path = Path(self.swf_field.text().strip())
        if not swf_path.exists():
            self._warn("Choose a valid SWF file first.")
            return

        self._save_jpexs_config()
        self.manifest.session_name = safe_stem(swf_path)
        self.manifest.source_swf_path = str(swf_path)
        self.manifest.source_xml_path = self.xml_field.text().strip()
        self.manifest.output_root = self.output_root_field.text().strip() or str(WORKSPACE_DIR)
        self.manifest.jpexs_path = self.jpexs_field.text().strip()
        self._set_session_paths()

        output_dir = Path(self.manifest.extracted_dir)
        self.extract_button.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self._log(f"Extracting SVGs to: {output_dir}")
        try:
            command = JpexsService().build_command(dict(self.config), swf_path, output_dir)
            self._log(f"JPEXS command: {subprocess.list2cmdline(command)}")
        except Exception:
            pass

        self.extraction_thread = QThread()
        self.extraction_worker = ExtractionWorker(dict(self.config), swf_path, output_dir)
        self.extraction_worker.moveToThread(self.extraction_thread)
        self.extraction_thread.started.connect(self.extraction_worker.run)
        self.extraction_worker.finished.connect(self._extraction_finished)
        self.extraction_worker.finished.connect(self.extraction_thread.quit)
        self.extraction_worker.finished.connect(self.extraction_worker.deleteLater)
        self.extraction_thread.finished.connect(self.extraction_thread.deleteLater)
        self.extraction_thread.start()

    def extract_or_load_xml(self) -> bool:
        swf_path = Path(self.swf_field.text().strip())
        if not swf_path.exists():
            self._warn("Choose a valid SWF file first.")
            return False

        if self._detect_xml_for_swf(swf_path):
            self._log("Loaded existing matching XML.")
            return True

        self._save_jpexs_config()
        self.manifest.session_name = safe_stem(swf_path)
        self.manifest.source_swf_path = str(swf_path)
        self.manifest.output_root = self.output_root_field.text().strip() or str(WORKSPACE_DIR)
        self.manifest.jpexs_path = self.jpexs_field.text().strip()
        self._set_session_paths()

        xml_path = Path(self.manifest.extracted_dir).parent / f"{self.manifest.session_name}.xml"
        try:
            command = JpexsService().build_xml_command(dict(self.config), swf_path, xml_path)
            self._log(f"JPEXS XML command: {subprocess.list2cmdline(command)}")
            result = JpexsService().swf_to_xml(dict(self.config), swf_path, xml_path)
        except Exception as error:
            self._warn(str(error))
            self._log(f"XML extraction failed: {error}")
            return False

        if result.returncode != 0:
            self._log("XML extraction command failed.")
            if result.stderr:
                self._log(result.stderr.strip())
            self._warn("JPEXS XML extraction failed. Check the log and config/jpexs_config.json.")
            return False

        if result.stdout:
            self._log(result.stdout.strip())

        self.xml_field.setText(str(xml_path))
        self.manifest.source_xml_path = str(xml_path)
        self._log(f"Loaded generated XML: {xml_path}")
        return True

    def reload_extracted_folder(self) -> None:
        self._set_session_paths()
        extracted_dir = Path(self.manifest.extracted_dir)
        self.manifest.assets = self.asset_service.scan_svgs(extracted_dir)
        self.gallery.set_assets(self.manifest.assets)
        self._log(f"Loaded {len(self.manifest.assets)} SVG files from {extracted_dir}")

    def choose_folder_to_view(self) -> None:
        self._set_session_paths()
        start_dir = self.manifest.organized_dir or str(ORGANIZED_DIR)
        folder = QFileDialog.getExistingDirectory(self, "Choose Folder to View", start_dir)
        if not folder:
            return

        self.load_view_folder(Path(folder))

    def load_view_folder(self, folder: Path) -> None:
        self.manifest.assets = self.asset_service.scan_svgs(folder)
        for asset in self.manifest.assets:
            relative = Path(asset.source_path).relative_to(folder)
            if len(relative.parts) > 1:
                asset.destination_slot = relative.parts[0]
            else:
                asset.destination_slot = folder.name
            asset.new_filename = Path(asset.source_path).name
            asset.destination_path = asset.source_path
            asset.status = "done"
        self.gallery.set_assets(self.manifest.assets)
        self._log(f"Loaded {len(self.manifest.assets)} SVG files from {folder}")

    def apply_xml_folders(self, show_warnings: bool = True) -> bool:
        xml_path = Path(self.xml_field.text().strip())
        if not xml_path.exists():
            if show_warnings:
                self._warn("Choose a valid XML file first.")
            return False

        if not self.manifest.assets:
            self.reload_extracted_folder()
        if not self.manifest.assets:
            if show_warnings:
                self._warn("No extracted SVGs are loaded.")
            return False

        self.manifest.source_xml_path = str(xml_path)
        self._set_session_paths()

        try:
            shape_slots = self.xml_structure_service.load_shape_slots(xml_path)
            count = self.xml_structure_service.apply_slots_to_assets(
                self.manifest.assets,
                shape_slots,
                Path(self.manifest.organized_dir),
                copy_files=True,
            )
        except Exception as error:
            if show_warnings:
                self._warn(str(error))
            self._log(f"Apply XML folders failed: {error}")
            return False

        self.gallery.set_assets(self.manifest.assets)
        self._log(f"Applied XML folders to {count} SVGs.")
        self.load_view_folder(Path(self.manifest.organized_dir))
        return True

    @Slot(object, object)
    def _extraction_finished(self, result, error) -> None:
        QApplication.restoreOverrideCursor()
        self.extract_button.setEnabled(True)

        if error is not None:
            self._log(f"Extraction failed: {error}")
            self._warn(str(error))
            return

        if result.returncode != 0:
            self._log("Extraction command failed.")
            if result.stderr:
                self._log(result.stderr.strip())
            self._warn("JPEXS extraction failed. Check the log and config/jpexs_config.json.")
            return

        if result.stdout:
            self._log(result.stdout.strip())
        self.reload_extracted_folder()
        if self.extract_or_load_xml():
            self.apply_xml_folders(show_warnings=False)
        else:
            self._log("XML was not loaded, so organized folder grouping was skipped.")
        self._log("Extraction complete.")

    @Slot(int)
    def select_asset(self, index: int) -> None:
        self.current_index = index
        if index < 0 or index >= len(self.manifest.assets):
            return

        asset = self.manifest.assets[index]
        self.current_file_label.setText(asset.original_filename)
        self.new_name_field.setText(asset.new_filename or asset.original_filename)

        path = Path(asset.source_path)
        if path.exists():
            self.preview.load(str(path))
            self._log(f"Selected: {path.name}")
        else:
            self._log(f"Missing source SVG: {path}")

    def save_selected_asset(self) -> None:
        asset = self._current_asset()
        if asset is None:
            return

        self._set_session_paths()
        try:
            destination = self.asset_service.save_to_organized(
                asset,
                Path(self.manifest.organized_dir),
                self._asset_slot(asset),
                self.new_name_field.text(),
            )
        except Exception as error:
            self._warn(str(error))
            self._log(f"Save / Move failed: {error}")
            return

        self.gallery.refresh_asset(self.current_index, asset)
        self._log(f"Saved organized SVG: {destination}")

    def open_source_folder(self) -> None:
        asset = self._current_asset()
        if asset is None:
            return
        self._open_folder(Path(asset.source_path).parent)

    def _current_asset(self) -> AssetRecord | None:
        if self.current_index < 0 or self.current_index >= len(self.manifest.assets):
            self._warn("Select an SVG first.")
            return None
        return self.manifest.assets[self.current_index]

    def _asset_slot(self, asset: AssetRecord) -> str:
        if asset.destination_slot:
            return asset.destination_slot

        organized_dir = Path(self.manifest.organized_dir)
        source_path = Path(asset.source_path)
        try:
            relative = source_path.relative_to(organized_dir)
        except ValueError:
            return ""

        if len(relative.parts) > 1:
            return relative.parts[0]
        return ""

    def _set_session_paths(self) -> None:
        output_root = Path(self.output_root_field.text().strip() or WORKSPACE_DIR)
        session_name = self.manifest.session_name or safe_stem(self.swf_field.text().strip())
        if not session_name:
            session_name = "session"

        self.manifest.session_name = session_name
        self.manifest.output_root = str(output_root)
        self.manifest.extracted_dir = str(output_root / "raw_svg" / session_name / "extracted")
        self.manifest.organized_dir = str(output_root / "organized" / session_name)

    def _save_jpexs_config(self) -> None:
        self.config["output_root"] = self.output_root_field.text().strip()
        self.config["jpexs_path"] = self.jpexs_field.text().strip()
        self.config_service.save(self.config)

    def _detect_xml_for_swf(self, swf_path: Path) -> bool:
        xml_path = swf_path.with_suffix(".xml")
        if xml_path.exists():
            self.xml_field.setText(str(xml_path))
            self.manifest.source_xml_path = str(xml_path)
            self._log(f"Detected matching XML: {xml_path}")
            return True
        return False

    def _open_folder(self, folder: Path) -> None:
        if not folder.exists():
            self._warn(f"Folder does not exist: {folder}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _log(self, message: str) -> None:
        self.log.appendPlainText(message)

    def _warn(self, message: str) -> None:
        QMessageBox.warning(self, "Parts Review", message)
