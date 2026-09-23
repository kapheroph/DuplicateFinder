from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QSize, Qt, QThread, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from duplicate_finder.duplicates import AnalysisResult, analyze_folder
from duplicate_finder.models import DuplicateGroup, ImageRecord


class ScanWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, folder: Path, recursive: bool) -> None:
        super().__init__()
        self.folder = folder
        self.recursive = recursive

    def run(self) -> None:
        try:
            result = analyze_folder(self.folder, recursive=self.recursive)
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")
            return
        self.finished.emit(result)


class ImageCard(QFrame):
    def __init__(self, record: ImageRecord, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.record = record
        self.setObjectName("imageCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        preview = QLabel()
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setMinimumSize(220, 180)

        pixmap = QPixmap(str(record.path))
        if not pixmap.isNull():
            preview.setPixmap(
                pixmap.scaled(
                    QSize(360, 260),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            preview.setText("Preview unavailable")

        name = QLabel(record.path.name)
        name.setObjectName("imageName")
        name.setWordWrap(True)

        details = QLabel(
            f"{record.width} × {record.height}   •   {record.size_bytes / 1024:.1f} KiB"
        )
        details.setObjectName("imageDetails")

        path = QLabel(str(record.path.parent))
        path.setObjectName("imagePath")
        path.setWordWrap(True)

        layout.addWidget(preview)
        layout.addWidget(name)
        layout.addWidget(details)
        layout.addWidget(path)


class GroupPanel(QWidget):
    def __init__(self, group: DuplicateGroup, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel(self._title_for(group))
        title.setObjectName("groupTitle")
        layout.addWidget(title)

        cards = QWidget()
        cards_layout = QHBoxLayout(cards)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(12)

        for record in group.files:
            cards_layout.addWidget(ImageCard(record))

        cards_layout.addStretch(1)
        layout.addWidget(cards)
        layout.addStretch(1)

    @staticmethod
    def _title_for(group: DuplicateGroup) -> str:
        if group.kind == "exact_file":
            return f"Exact file duplicate • {len(group.files)} images"
        if group.kind == "exact_pixels":
            return f"Same pixels • {len(group.files)} images"
        distance = f" • max dHash distance {group.distance}" if group.distance is not None else ""
        return f"Similar images • {len(group.files)} images{distance}"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Bill's Duplicate Finder")
        self.resize(1280, 800)

        self.folder: Path | None = None
        self.result: AnalysisResult | None = None
        self.scan_thread: QThread | None = None
        self.scan_worker: ScanWorker | None = None
        self.group_lookup: list[DuplicateGroup] = []

        self._build_ui()
        self._load_styles()

    def _build_ui(self) -> None:
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(18, 18, 18, 12)
        outer.setSpacing(14)

        header = QHBoxLayout()
        title_block = QVBoxLayout()
        app_title = QLabel("Bill's Duplicate Finder")
        app_title.setObjectName("appTitle")
        subtitle = QLabel("Find exact and visually similar images without changing anything.")
        subtitle.setObjectName("subtitle")
        title_block.addWidget(app_title)
        title_block.addWidget(subtitle)

        self.choose_button = QPushButton("Choose Folder")
        self.choose_button.clicked.connect(self.choose_folder)

        self.scan_button = QPushButton("Scan")
        self.scan_button.setObjectName("primaryButton")
        self.scan_button.setEnabled(False)
        self.scan_button.clicked.connect(self.start_scan)

        header.addLayout(title_block, 1)
        header.addWidget(self.choose_button)
        header.addWidget(self.scan_button)
        outer.addLayout(header)

        control_bar = QFrame()
        control_bar.setObjectName("controlBar")
        control_layout = QHBoxLayout(control_bar)
        control_layout.setContentsMargins(14, 10, 14, 10)

        self.folder_label = QLabel("No folder selected")
        self.folder_label.setObjectName("folderLabel")

        self.recursive_checkbox = QCheckBox("Include subfolders")
        self.recursive_checkbox.setChecked(False)

        self.progress = QProgressBar()
        self.progress.setMaximumWidth(240)
        self.progress.setVisible(False)
        self.progress.setTextVisible(False)

        control_layout.addWidget(self.folder_label, 1)
        control_layout.addWidget(self.recursive_checkbox)
        control_layout.addWidget(self.progress)
        outer.addWidget(control_bar)

        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)

        sidebar = QWidget()
        sidebar.setMinimumWidth(250)
        sidebar.setMaximumWidth(320)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 10, 0)

        self.summary_label = QLabel("Choose a folder to begin.")
        self.summary_label.setObjectName("summaryLabel")
        self.summary_label.setWordWrap(True)

        self.group_list = QListWidget()
        self.group_list.currentRowChanged.connect(self.show_group)

        sidebar_layout.addWidget(self.summary_label)
        sidebar_layout.addWidget(self.group_list, 1)

        self.review_scroll = QScrollArea()
        self.review_scroll.setWidgetResizable(True)
        self.review_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.review_stack = QStackedWidget()
        empty = QLabel("Scan a folder, then choose a duplicate group to review.")
        empty.setObjectName("emptyState")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.setWordWrap(True)
        self.review_stack.addWidget(empty)
        self.review_scroll.setWidget(self.review_stack)

        splitter.addWidget(sidebar)
        splitter.addWidget(self.review_scroll)
        splitter.setStretchFactor(1, 1)
        outer.addWidget(splitter, 1)

        self.setCentralWidget(root)

        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage("Ready")

    def _load_styles(self) -> None:
        stylesheet = Path(__file__).with_name("styles.qss")
        if stylesheet.exists():
            self.setStyleSheet(stylesheet.read_text(encoding="utf-8"))

    def choose_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Choose image folder",
            str(self.folder) if self.folder else "",
        )
        if not selected:
            return

        self.folder = Path(selected)
        self.folder_label.setText(str(self.folder))
        self.folder_label.setToolTip(str(self.folder))
        self.scan_button.setEnabled(True)
        self.statusBar().showMessage("Folder selected")

    def start_scan(self) -> None:
        if self.folder is None or self.scan_thread is not None:
            return

        self._set_scanning(True)
        self.group_list.clear()
        self.group_lookup.clear()
        self._reset_review_stack()

        self.scan_thread = QThread(self)
        self.scan_worker = ScanWorker(
            self.folder,
            recursive=self.recursive_checkbox.isChecked(),
        )
        self.scan_worker.moveToThread(self.scan_thread)

        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.finished.connect(self.scan_finished)
        self.scan_worker.failed.connect(self.scan_failed)
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_worker.failed.connect(self.scan_thread.quit)
        self.scan_thread.finished.connect(self._cleanup_scan_thread)

        self.scan_thread.start()

    def scan_finished(self, result: AnalysisResult) -> None:
        self.result = result
        self._set_scanning(False)
        self._populate_groups(result)

        total_groups = (
            len(result.exact_file_groups)
            + len(result.exact_pixel_groups)
            + len(result.near_duplicate_groups)
        )
        self.summary_label.setText(
            f"{result.images_scanned} images scanned\n"
            f"{total_groups} groups to review\n"
            f"{len(result.unreadable)} skipped"
        )
        self.statusBar().showMessage(
            f"Scan complete — {result.images_scanned} images, {total_groups} groups"
        )

    def scan_failed(self, message: str) -> None:
        self._set_scanning(False)
        self.statusBar().showMessage("Scan failed")
        QMessageBox.critical(self, "Scan failed", message)

    def _cleanup_scan_thread(self) -> None:
        if self.scan_worker is not None:
            self.scan_worker.deleteLater()
        if self.scan_thread is not None:
            self.scan_thread.deleteLater()
        self.scan_worker = None
        self.scan_thread = None

    def _set_scanning(self, scanning: bool) -> None:
        self.choose_button.setEnabled(not scanning)
        self.scan_button.setEnabled(not scanning and self.folder is not None)
        self.recursive_checkbox.setEnabled(not scanning)
        self.progress.setVisible(scanning)
        if scanning:
            self.progress.setRange(0, 0)
            self.statusBar().showMessage("Scanning images…")
        else:
            self.progress.setRange(0, 1)
            self.progress.setValue(1)

    def _populate_groups(self, result: AnalysisResult) -> None:
        sections = (
            ("Exact", result.exact_file_groups),
            ("Same pixels", result.exact_pixel_groups),
            ("Similar", result.near_duplicate_groups),
        )

        for label, groups in sections:
            for number, group in enumerate(groups, 1):
                distance = (
                    f" • dHash ≤ {group.distance}"
                    if group.kind == "near" and group.distance is not None
                    else ""
                )
                item = QListWidgetItem(
                    f"{label} {number}   •   {len(group.files)} images{distance}"
                )
                self.group_list.addItem(item)
                self.group_lookup.append(group)

        if self.group_lookup:
            self.group_list.setCurrentRow(0)
        else:
            self._show_empty_message("No duplicate or similar-image groups found.")

    def show_group(self, row: int) -> None:
        if row < 0 or row >= len(self.group_lookup):
            return

        group = self.group_lookup[row]
        panel = GroupPanel(group)
        self._replace_review_widget(panel)

    def _reset_review_stack(self) -> None:
        self._show_empty_message("Scanning…")

    def _show_empty_message(self, text: str) -> None:
        label = QLabel(text)
        label.setObjectName("emptyState")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        self._replace_review_widget(label)

    def _replace_review_widget(self, widget: QWidget) -> None:
        while self.review_stack.count():
            old = self.review_stack.widget(0)
            self.review_stack.removeWidget(old)
            old.deleteLater()
        self.review_stack.addWidget(widget)
        self.review_stack.setCurrentWidget(widget)


def run_gui() -> int:
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("Bill's Duplicate Finder")
    window = MainWindow()
    window.show()
    return app.exec()
