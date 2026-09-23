from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QSize, Qt, QThread, QStandardPaths, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
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

from duplicate_finder.actions import (
    list_quarantined_images,
    move_to_quarantine,
    quarantine_directory,
    restore_from_quarantine,
)
from duplicate_finder.duplicates import AnalysisResult, analyze_folder
from duplicate_finder.models import DuplicateGroup, ImageRecord
from duplicate_finder.quality import advise_group
from duplicate_finder.resources import resource_path


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


class PreviewDialog(QDialog):
    def __init__(self, record: ImageRecord, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(record.path.name)
        self.resize(1100, 800)

        layout = QVBoxLayout(self)

        preview = QLabel()
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pixmap = QPixmap(str(record.path))
        if pixmap.isNull():
            preview.setText("Preview unavailable")
        else:
            preview.setPixmap(
                pixmap.scaled(
                    QSize(1020, 700),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        details = QLabel(
            f"{record.path}\n"
            f"{record.width} × {record.height}   •   {record.size_bytes / 1024:.1f} KiB"
        )
        details.setObjectName("imagePath")
        details.setWordWrap(True)

        layout.addWidget(preview, 1)
        layout.addWidget(details)


class QuarantineDialog(QDialog):
    def __init__(self, scan_root: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.scan_root = scan_root
        self.changed = False

        self.setWindowTitle("Quarantine Manager")
        self.resize(760, 560)

        layout = QVBoxLayout(self)
        title = QLabel("Quarantine Manager")
        title.setObjectName("groupTitle")
        description = QLabel(
            "Files here are safe from normal scans. Restore anything you want back."
        )
        description.setObjectName("subtitle")

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.list_widget.setIconSize(QSize(120, 90))

        buttons = QHBoxLayout()
        self.open_button = QPushButton("Open Quarantine Folder")
        self.restore_selected_button = QPushButton("Restore Selected")
        self.restore_all_button = QPushButton("Restore All")

        self.open_button.clicked.connect(self.open_folder)
        self.restore_selected_button.clicked.connect(self.restore_selected)
        self.restore_all_button.clicked.connect(self.restore_all)

        buttons.addWidget(self.open_button)
        buttons.addStretch(1)
        buttons.addWidget(self.restore_selected_button)
        buttons.addWidget(self.restore_all_button)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(self.list_widget, 1)
        layout.addLayout(buttons)

        self.refresh()

    def refresh(self) -> None:
        self.list_widget.clear()
        files = list_quarantined_images(self.scan_root)

        for path in files:
            item = QListWidgetItem(path.name)
            item.setData(Qt.ItemDataRole.UserRole, str(path))

            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                item.setIcon(
                    QIcon(
                        pixmap.scaled(
                            QSize(120, 90),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
                )

            item.setToolTip(str(path))
            self.list_widget.addItem(item)

        has_files = bool(files)
        self.restore_selected_button.setEnabled(has_files)
        self.restore_all_button.setEnabled(has_files)

        if not has_files:
            empty = QListWidgetItem("Quarantine is empty.")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_widget.addItem(empty)

    def selected_paths(self) -> list[Path]:
        paths: list[Path] = []
        for item in self.list_widget.selectedItems():
            raw = item.data(Qt.ItemDataRole.UserRole)
            if raw:
                paths.append(Path(raw))
        return paths

    def open_folder(self) -> None:
        folder = quarantine_directory(self.scan_root)
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def restore_selected(self) -> None:
        paths = self.selected_paths()
        if not paths:
            QMessageBox.information(
                self,
                "Nothing selected",
                "Select one or more quarantined images to restore.",
            )
            return
        self._restore(paths)

    def restore_all(self) -> None:
        paths = list_quarantined_images(self.scan_root)
        if not paths:
            return

        answer = QMessageBox.question(
            self,
            "Restore all quarantined images?",
            f"Restore all {len(paths)} quarantined image(s) to the scanned folder?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._restore(paths, confirm=False)

    def _restore(self, paths: list[Path], *, confirm: bool = True) -> None:
        if confirm:
            answer = QMessageBox.question(
                self,
                "Restore selected images?",
                f"Restore {len(paths)} selected image(s) to the scanned folder?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        try:
            moves = restore_from_quarantine(paths, self.scan_root)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Restore failed",
                f"{type(exc).__name__}: {exc}",
            )
            return

        self.changed = self.changed or bool(moves)
        self.refresh()

        QMessageBox.information(
            self,
            "Images restored",
            f"Restored {len(moves)} image(s).",
        )


class ImageCard(QFrame):
    decision_changed = Signal(object, str)
    preview_requested = Signal(object)

    def __init__(
        self,
        record: ImageRecord,
        decision: str = "keep",
        notes: tuple[str, ...] = (),
        suggested: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.record = record
        self.decision = decision
        self.setObjectName("imageCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        preview = QLabel()
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setMinimumSize(220, 180)
        preview.setCursor(Qt.CursorShape.PointingHandCursor)
        preview.mousePressEvent = lambda _event: self.preview_requested.emit(self.record)

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

        if suggested:
            badge = QLabel("Suggested keep")
            badge.setObjectName("suggestedBadge")
            layout.addWidget(badge)

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

        comparison = QLabel("\n".join(f"• {note}" for note in notes))
        comparison.setObjectName("comparisonNotes")
        comparison.setWordWrap(True)
        comparison.setVisible(bool(notes))

        actions = QHBoxLayout()
        self.keep_button = QPushButton("Keep")
        self.ignore_button = QPushButton("Ignore")
        self.quarantine_button = QPushButton("Quarantine")
        self.quarantine_button.setObjectName("dangerButton")

        self.keep_button.clicked.connect(lambda: self.set_decision("keep", emit=True))
        self.ignore_button.clicked.connect(lambda: self.set_decision("ignore", emit=True))
        self.quarantine_button.clicked.connect(
            lambda: self.set_decision("quarantine", emit=True)
        )

        actions.addWidget(self.keep_button)
        actions.addWidget(self.ignore_button)
        actions.addWidget(self.quarantine_button)

        layout.addWidget(preview)
        layout.addWidget(name)
        layout.addWidget(details)
        layout.addWidget(path)
        layout.addWidget(comparison)
        layout.addLayout(actions)

        self.set_decision(decision, emit=False)

    def set_decision(self, decision: str, *, emit: bool) -> None:
        self.decision = decision
        self.setProperty("decision", decision)
        self.style().unpolish(self)
        self.style().polish(self)

        self.keep_button.setEnabled(decision != "keep")
        self.ignore_button.setEnabled(decision != "ignore")
        self.quarantine_button.setEnabled(decision != "quarantine")

        if emit:
            self.decision_changed.emit(self.record, decision)


class GroupPanel(QWidget):
    decision_changed = Signal(object, str)
    preview_requested = Signal(object)

    def __init__(
        self,
        group: DuplicateGroup,
        decisions: dict[Path, str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel(self._title_for(group))
        title.setObjectName("groupTitle")
        layout.addWidget(title)

        advice = advise_group(group)

        advice_box = QFrame()
        advice_box.setObjectName("adviceBox")
        advice_layout = QVBoxLayout(advice_box)
        advice_layout.setContentsMargins(14, 12, 14, 12)
        advice_layout.setSpacing(5)

        explanation = QLabel(advice.summary)
        explanation.setObjectName("adviceText")
        explanation.setWordWrap(True)
        advice_layout.addWidget(explanation)

        if advice.suggestion is not None and advice.suggestion_reason:
            suggestion = QLabel(
                f"Suggested keep: {advice.suggestion.name}\n{advice.suggestion_reason}."
            )
            suggestion.setObjectName("adviceSuggestion")
            suggestion.setWordWrap(True)
            advice_layout.addWidget(suggestion)

        layout.addWidget(advice_box)

        hint = QLabel("Click an image to preview it larger.")
        hint.setObjectName("imageDetails")
        layout.addWidget(hint)

        cards = QWidget()
        cards_layout = QHBoxLayout(cards)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(12)

        for record in group.files:
            card = ImageCard(
                record,
                decisions.get(record.path, "keep"),
                notes=advice.notes.get(record.path, ()),
                suggested=advice.suggestion == record.path,
            )
            card.decision_changed.connect(self.decision_changed.emit)
            card.preview_requested.connect(self.preview_requested.emit)
            cards_layout.addWidget(card)

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
        self.decisions: dict[Path, str] = {}
        self.record_lookup: dict[Path, ImageRecord] = {}

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

        subtitle = QLabel(
            "Find exact and visually similar images, then review them safely."
        )
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

        action_bar = QFrame()
        action_bar.setObjectName("controlBar")
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(14, 10, 14, 10)

        self.selection_summary = QLabel("0 selected for quarantine   •   0.0 B")
        self.selection_summary.setObjectName("summaryLabel")

        self.quarantine_button = QPushButton("Move Selected to Quarantine")
        self.quarantine_button.setObjectName("dangerButton")
        self.quarantine_button.setEnabled(False)
        self.quarantine_button.clicked.connect(self.apply_quarantine)

        self.manage_quarantine_button = QPushButton("Quarantine Manager")
        self.manage_quarantine_button.setEnabled(False)
        self.manage_quarantine_button.clicked.connect(self.open_quarantine_manager)

        action_layout.addWidget(self.selection_summary, 1)
        action_layout.addWidget(self.manage_quarantine_button)
        action_layout.addWidget(self.quarantine_button)
        outer.addWidget(action_bar)

        self.setCentralWidget(root)

        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage("Ready")

    def _load_styles(self) -> None:
        stylesheet = resource_path("duplicate_finder/ui/styles.qss")
        if stylesheet.exists():
            self.setStyleSheet(stylesheet.read_text(encoding="utf-8"))

    def choose_folder(self) -> None:
        pictures_folder = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.PicturesLocation
        )
        start_folder = str(self.folder) if self.folder else pictures_folder

        selected = QFileDialog.getExistingDirectory(
            self,
            "Choose image folder",
            start_folder,
        )
        if not selected:
            return

        self.folder = Path(selected)
        self.folder_label.setText(str(self.folder))
        self.folder_label.setToolTip(str(self.folder))
        self.scan_button.setEnabled(True)
        self.manage_quarantine_button.setEnabled(True)
        self.statusBar().showMessage("Folder selected")

    def start_scan(self) -> None:
        if self.folder is None or self.scan_thread is not None:
            return

        self.decisions.clear()
        self.record_lookup.clear()
        self._update_selection_summary()

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
        self._index_records(result)
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

    def _index_records(self, result: AnalysisResult) -> None:
        for groups in (
            result.exact_file_groups,
            result.exact_pixel_groups,
            result.near_duplicate_groups,
        ):
            for group in groups:
                for record in group.files:
                    self.record_lookup[record.path] = record
                    self.decisions.setdefault(record.path, "keep")

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
        panel = GroupPanel(group, self.decisions)
        panel.decision_changed.connect(self.set_decision)
        panel.preview_requested.connect(self.show_preview)
        self._replace_review_widget(panel)

    def set_decision(self, record: ImageRecord, decision: str) -> None:
        self.decisions[record.path] = decision
        self._update_selection_summary()

    def show_preview(self, record: ImageRecord) -> None:
        PreviewDialog(record, self).exec()

    def _selected_for_quarantine(self) -> list[ImageRecord]:
        return [
            self.record_lookup[path]
            for path, decision in self.decisions.items()
            if decision == "quarantine" and path in self.record_lookup
        ]

    def _update_selection_summary(self) -> None:
        selected = self._selected_for_quarantine()
        total_bytes = sum(record.size_bytes for record in selected)

        self.selection_summary.setText(
            f"{len(selected)} selected for quarantine"
            f"   •   {self._format_bytes(total_bytes)}"
        )

        self.quarantine_button.setEnabled(bool(selected) and self.folder is not None)

    @staticmethod
    def _format_bytes(size: int) -> str:
        value = float(size)
        for unit in ("B", "KiB", "MiB", "GiB"):
            if value < 1024 or unit == "GiB":
                return f"{value:.1f} {unit}"
            value /= 1024
        return f"{value:.1f} GiB"

    def open_quarantine_manager(self) -> None:
        if self.folder is None:
            return

        dialog = QuarantineDialog(self.folder, self)
        dialog.exec()

        if dialog.changed:
            self.start_scan()

    def apply_quarantine(self) -> None:
        if self.folder is None:
            return

        selected = self._selected_for_quarantine()
        if not selected:
            return

        destination = quarantine_directory(self.folder)

        answer = QMessageBox.question(
            self,
            "Move files to quarantine?",
            (
                f"Move {len(selected)} selected file(s) to:\n\n"
                f"{destination}\n\n"
                "The files will not be deleted."
            ),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            moves = move_to_quarantine(
                [record.path for record in selected],
                self.folder,
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Quarantine failed",
                f"{type(exc).__name__}: {exc}",
            )
            return

        QMessageBox.information(
            self,
            "Files quarantined",
            (
                f"Moved {len(moves)} file(s) to:\n\n"
                f"{destination}\n\n"
                "The folder will now be rescanned."
            ),
        )

        self.start_scan()

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

    icon_path = resource_path("assets/bills_duplicate_finder.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()
    return app.exec()
