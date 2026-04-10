from typing import List
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QFileDialog, QScrollArea,
                             QCheckBox, QComboBox, QLabel, QMessageBox,
                             QGroupBox, QFrame)
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal
from PyQt6.QtGui import QDrag, QPalette, QColor, QFont
from pyqt6_multiselect_combobox import MultiSelectComboBox

from src.export_image import ExportRule
from src.config_handler import ConfigHandler
from src.styling.style_manager import StyleManager
from src.styling.styling_utils import styled_information_box, styled_question_box, styled_warning_box

class RuleComponent(QWidget):
    """Widget for a single category-based export rule"""
    deleteRequested = pyqtSignal(object)
    dragStarted = pyqtSignal(object)

    def __init__(self, categories: List[str], rule: ExportRule, style_manager: StyleManager, editable: bool = True, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        self.rule = rule
        self.editable = editable
        self.style_manager = style_manager

        # Priority label
        self.priority_label = QLabel(str(self.rule.priority))
        self.priority_label.setStyleSheet(self.style_manager.get_stylesheet(QLabel, 'bold'))
        self.priority_label.setMinimumWidth(30)
        self.priority_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Category selector
        self.combo_box = MultiSelectComboBox()
        self.combo_box.setStyleSheet(self.style_manager.get_stylesheet(QComboBox))
        self.combo_box.addItems(categories)
        self.combo_box.setDisplayDelimiter(", ")
        if editable:
            self.combo_box.setPlaceholderText("Select categories...")
        if self.rule.categories and editable:
            self.combo_box.setCurrentOptions(list(self.rule.categories))
        else:
            self.combo_box.setCurrentText("DEFAULT")
        self.combo_box.setEnabled(editable)

        # File path
        self.file_path = QLineEdit(self.rule.destination)
        self.file_path.setStyleSheet(self.style_manager.get_stylesheet(QLineEdit))
        self.file_path.setPlaceholderText("Subdirectory path...")
        self.file_path.setEnabled(editable)

        layout.addWidget(self.priority_label, 0)
        layout.addWidget(self.combo_box, 6)
        layout.addWidget(self.file_path, 3)

        if editable:
            self.delete_button = QPushButton("✕")
            self.delete_button.setStyleSheet(self.style_manager.get_stylesheet(QPushButton, 'warning'))
            self.delete_button.setMaximumWidth(35)
            self.delete_button.clicked.connect(self.request_delete)
            layout.addWidget(self.delete_button, 0)

        self.setLayout(layout)
        self.setAcceptDrops(True)

    def get_data(self):
        return ExportRule(
            categories=set(self.combo_box.currentData()),
            destination=self.file_path.text(),
            priority=int(self.priority_label.text())
        )

    def request_delete(self):
        self.deleteRequested.emit(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.editable:
            self.dragStarted.emit(self)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self.editable:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(str(self.rule.priority))
            drag.setMimeData(mime_data)
            drag.exec(Qt.DropAction.MoveAction)

    def set_drag_highlight(self, highlight: bool):
        palette = self.palette()
        if highlight:
            palette.setColor(QPalette.ColorRole.Window, QColor(200, 200, 255))
        else:
            palette.setColor(QPalette.ColorRole.Window, self.parent().palette().color(QPalette.ColorRole.Window))
        self.setPalette(palette)
        self.setAutoFillBackground(highlight)


class ExportPopup(QWidget):
    """Redesigned export popup with better organization and tag rules support"""

    def __init__(self, export_callback: callable, categories, config: ConfigHandler,
                 style_manager: StyleManager, project_id: int = None):
        super().__init__()
        self.categories = categories
        self.export_callback = export_callback
        self.config = config
        self.style_manager = style_manager
        self.project_id = project_id

        self.setStyleSheet(self.style_manager.get_stylesheet(QWidget))
        self.setWindowTitle('Export Settings')
        self.setMinimumSize(800, 600)

        self.initUI()
        self.drag_component = None

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel("Export Configuration")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet(self.style_manager.get_stylesheet(QLabel))
        main_layout.addWidget(title_label)

        # Add a separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator)

        # Output directory section
        main_layout.addWidget(self._create_output_section())

        # Category rules section
        main_layout.addWidget(self._create_category_rules_section())

        # Score selection section
        main_layout.addWidget(self._create_score_section())

        # Export options section
        main_layout.addWidget(self._create_options_section())

        main_layout.addStretch()

        # Action buttons
        main_layout.addWidget(self._create_action_buttons())

        self.setLayout(main_layout)

    def _create_output_section(self) -> QGroupBox:
        """Create the output directory selection section"""
        group = QGroupBox("Output Directory")
        group.setStyleSheet(self.style_manager.get_stylesheet(QGroupBox))
        layout = QVBoxLayout()

        dir_layout = QHBoxLayout()
        self.dir_input = QLineEdit()
        self.dir_input.setStyleSheet(self.style_manager.get_stylesheet(QLineEdit))
        self.dir_input.setPlaceholderText("Select an output directory...")

        dir_button = QPushButton("Browse...")
        dir_button.setStyleSheet(self.style_manager.get_stylesheet(QPushButton, 'accent'))
        dir_button.clicked.connect(self.select_directory)

        dir_layout.addWidget(self.dir_input, 1)
        dir_layout.addWidget(dir_button)
        layout.addLayout(dir_layout)

        group.setLayout(layout)
        return group

    def _create_category_rules_section(self) -> QGroupBox:
        """Create the category-based export rules section"""
        group = QGroupBox("Category Rules (Drag to reorder by priority)")
        group.setStyleSheet(self.style_manager.get_stylesheet(QGroupBox))
        layout = QVBoxLayout()

        # Info label
        info_label = QLabel(
            "Define where images with specific categories should be exported. "
            "Higher priority rules are matched first."
        )
        info_label.setStyleSheet(self.style_manager.get_stylesheet(QLabel, 'subtext'))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Add rule button
        add_button = QPushButton("+ Add Category Rule")
        add_button.setStyleSheet(self.style_manager.get_stylesheet(QPushButton, 'function_accent'))
        add_button.clicked.connect(self.add_rule)
        layout.addWidget(add_button)

        # Scrollable area for rules
        self.scroll_area = QScrollArea()
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scroll_area.setContentsMargins(0, 0, 0, 0)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setSpacing(5)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.category_components = []

        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(150)
        layout.addWidget(self.scroll_area)

        # Default rule (non-editable)
        default_rule = ExportRule(categories=None, destination='.', priority=0)
        self.add_rule_component(default_rule, editable=False)

        # Enable drag and drop
        self.scroll_widget.setAcceptDrops(True)

        group.setLayout(layout)
        return group

    def _create_score_section(self) -> QGroupBox:
        """Create the score selection section"""
        group = QGroupBox("Score Filter")
        group.setStyleSheet(self.style_manager.get_stylesheet(QGroupBox))
        layout = QVBoxLayout()

        info_label = QLabel("Select which scores to include in the export:")
        info_label.setStyleSheet(self.style_manager.get_stylesheet(QLabel, 'subtext'))
        layout.addWidget(info_label)

        # Create checkboxes in a grid
        score_layout = QHBoxLayout()
        score_layout.setSpacing(10)

        self.checkboxes = {}
        preset, scores = self.config.get_scores()

        for name, label in scores.items():
            checkbox = QCheckBox(label)
            checkbox.setObjectName(name)
            checkbox.setStyleSheet(self.style_manager.get_stylesheet(QCheckBox))
            self.checkboxes[name] = checkbox
            score_layout.addWidget(checkbox)

        score_layout.addStretch()
        layout.addLayout(score_layout)

        group.setLayout(layout)
        return group

    def _create_options_section(self) -> QGroupBox:
        """Create the export options section"""
        group = QGroupBox("Export Options")
        group.setStyleSheet(self.style_manager.get_stylesheet(QGroupBox))
        layout = QVBoxLayout()
        layout.setSpacing(8)

        # Caption options
        self.export_captions = QCheckBox("Export caption files (.txt)")
        self.export_captions.setChecked(self.config.get_export_option('export_captions'))
        self.export_captions.setStyleSheet(self.style_manager.get_stylesheet(QCheckBox))
        layout.addWidget(self.export_captions)

        self.require_captions = QCheckBox("Require captions")
        self.require_captions.setChecked(True)
        self.require_captions.setStyleSheet(self.style_manager.get_stylesheet(QCheckBox))
        layout.addWidget(self.require_captions)

        # Separate by score
        self.seperate_by_score = QCheckBox("Separate images by score (create subdirectories)")
        self.seperate_by_score.setChecked(self.config.get_export_option('seperate_by_score'))
        self.seperate_by_score.setStyleSheet(self.style_manager.get_stylesheet(QCheckBox))
        layout.addWidget(self.seperate_by_score)

        # Apply tag rules
        self.apply_tag_rules = QCheckBox("Apply export tag rules (add tags based on conditions)")
        self.apply_tag_rules.setChecked(True)
        self.apply_tag_rules.setStyleSheet(self.style_manager.get_stylesheet(QCheckBox))

        # Add tooltip/info
        tag_rules_layout = QHBoxLayout()
        tag_rules_layout.addWidget(self.apply_tag_rules)

        info_btn = QPushButton(" ℹ ")
        info_btn.setMaximumWidth(25)
        info_btn.setStyleSheet(self.style_manager.get_stylesheet(QPushButton, 'function'))
        info_btn.clicked.connect(self._show_tag_rules_info)
        tag_rules_layout.addWidget(info_btn)
        tag_rules_layout.addStretch()

        layout.addLayout(tag_rules_layout)

        # Delete images warning
        self.delete_images = QCheckBox("⚠️ Delete source images after export")
        self.delete_images.setChecked(self.config.get_export_option('delete_images'))
        self.delete_images.setStyleSheet(self.style_manager.get_stylesheet(QCheckBox, 'warning'))
        layout.addWidget(self.delete_images)

        group.setLayout(layout)
        return group

    def _create_action_buttons(self) -> QWidget:
        """Create the action buttons section"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        export_button = QPushButton("Export Images")
        export_button.setStyleSheet(self.style_manager.get_stylesheet(QPushButton, 'accept'))
        export_button.setMinimumHeight(40)
        export_button.clicked.connect(self.export_data)

        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet(self.style_manager.get_stylesheet(QPushButton))
        cancel_button.setMinimumHeight(40)
        cancel_button.clicked.connect(self.close)

        layout.addStretch()
        layout.addWidget(cancel_button)
        layout.addWidget(export_button)

        widget.setLayout(layout)
        return widget

    def _show_tag_rules_info(self):
        """Show information about export tag rules"""
        styled_information_box(
            self,
            "Export Tag Rules",
            "Export tag rules allow you to automatically add tags during export based on conditions.\n\n"
            "For example, if an image has tags 'from above' AND 'from side', "
            "you can create a rule to automatically add the tag 'mixed perspectives'.\n\n"
            "Configure these rules in Settings → Export Conditions.",
            self.style_manager
        )

    def select_directory(self):
        """Open directory selection dialog"""
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.dir_input.setText(directory)

    def add_rule(self):
        """Add a new category rule"""
        new_rule = ExportRule(categories=set(), destination='', priority=len(self.category_components))
        self.add_rule_component(new_rule)

    def add_rule_component(self, rule: ExportRule, editable: bool = True):
        """Add a rule component to the list"""
        component = RuleComponent(self.categories, rule, self.style_manager, editable, parent=self.scroll_widget)
        component.deleteRequested.connect(self.delete_rule)
        component.dragStarted.connect(self.drag_started)
        self.category_components.insert(0, component)
        self.scroll_layout.insertWidget(0, component)
        self.update_priorities()

    def delete_rule(self, component):
        """Delete a category rule"""
        if component.rule.priority != 0:  # Prevent deleting the default rule
            self.scroll_layout.removeWidget(component)
            component.deleteLater()
            self.category_components.remove(component)
            self.update_priorities()

    def update_priorities(self):
        """Update priority labels after reordering"""
        for i, component in enumerate(reversed(self.category_components)):
            component.rule.priority = i
            component.priority_label.setText(str(i))

    def export_data(self):
        """Validate and export data"""
        data = {
            'output_directory': self.dir_input.text(),
            'rules': [component.get_data() for component in reversed(self.category_components)],
            'scores': [name for name, checkbox in self.checkboxes.items() if checkbox.isChecked()],
            'seperate_by_score': self.seperate_by_score.isChecked(),
            'export_captions': self.export_captions.isChecked(),
            'require_captions': self.require_captions.isChecked(),
            'delete_images': self.delete_images.isChecked(),
            'apply_tag_rules': self.apply_tag_rules.isChecked(),
            'project_id': self.project_id
        }

        # Validation
        if data['output_directory'] == '':
            styled_warning_box(self, 'Invalid Export', 'Please select an output directory.', self.style_manager)
            return

        if len(data['scores']) < 1:
            styled_warning_box(self, 'Invalid Export', 'Please select at least one score to export.', self.style_manager)
            return

        # Confirm if delete is enabled
        if data['delete_images']:
            reply = styled_question_box(
                self,
                'Confirm Deletion',
                '⚠️ You have selected to delete source images after export.\n\n'
                'This action cannot be undone. Are you sure you want to continue?',
                self.style_manager,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

        self.export_callback(data)

    # Drag and drop methods
    def drag_started(self, component):
        self.drag_component = component

    def dragEnterEvent(self, event):
        if event.mimeData().hasText() and self.drag_component and self.drag_component.editable:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText() and self.drag_component and self.drag_component.editable:
            event.accept()
            self.update_drag_highlight(event.position().toPoint())
        else:
            event.ignore()

    def update_drag_highlight(self, position):
        for component in self.category_components:
            if component.editable:
                highlight = component.geometry().contains(position) and component != self.drag_component
                component.set_drag_highlight(highlight)

    def dropEvent(self, event):
        if not (event.mimeData().hasText() and self.drag_component and self.drag_component.editable):
            event.ignore()
            return

        drop_position = event.position().toPoint()
        target_component = None

        for component in self.category_components:
            if component.editable and component.geometry().contains(drop_position):
                target_component = component
                break

        if target_component and target_component != self.drag_component:
            source_index = self.category_components.index(self.drag_component)
            target_index = self.category_components.index(target_component)

            # Reorder the components list
            self.category_components.insert(target_index, self.category_components.pop(source_index))

            # Clear layout and re-add components in new order
            for i in reversed(range(self.scroll_layout.count())):
                widget = self.scroll_layout.itemAt(i).widget()
                if widget is not None:
                    self.scroll_layout.removeWidget(widget)

            for component in self.category_components:
                self.scroll_layout.addWidget(component)

            self.update_priorities()

        # Reset drag highlight
        for component in self.category_components:
            component.set_drag_highlight(False)

        self.drag_component = None
        event.accept()

    def dragLeaveEvent(self, event):
        for component in self.category_components:
            component.set_drag_highlight(False)
