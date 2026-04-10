from typing import List, Optional
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QWidget,
    QLineEdit, QTextEdit, QCheckBox, QComboBox,
)
from PyQt6.QtCore import Qt

from src.windows.settings_pages.settings_widget import SettingsWidget
from src.tagging.tag_group import TagGroup
from src.tagging.export_tag_rule import ExportTagRule, OperationType
from src.parser import parse_condition, validate_references
from src.styling.styling_utils import styled_information_box, styled_warning_box, styled_question_box


class ExportTagRuleWidget(QWidget):
    """Widget for displaying a single export tag rule in the list"""

    _OP_LABELS = {
        OperationType.ADD: "Adds",
        OperationType.REMOVE: "Removes",
        OperationType.REPLACE: "Replaces",
        OperationType.SORT: "Sorts into",
    }

    def __init__(self, rule: ExportTagRule, style_manager, settings_widget, parent=None):
        super().__init__(parent)
        self.rule = rule
        self.style_manager = style_manager
        self.settings_widget = settings_widget
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)

        # Order controls
        order_layout = QVBoxLayout()
        order_layout.setContentsMargins(0, 0, 5, 0)

        up_btn = QPushButton("▲")
        up_btn.setFixedSize(28, 28)
        up_btn.setStyleSheet(self.style_manager.get_stylesheet(QPushButton))
        up_btn.clicked.connect(lambda: self.settings_widget.move_rule_up(self.rule))

        down_btn = QPushButton("▼")
        down_btn.setFixedSize(28, 28)
        down_btn.setStyleSheet(self.style_manager.get_stylesheet(QPushButton))
        down_btn.clicked.connect(lambda: self.settings_widget.move_rule_down(self.rule))

        order_layout.addWidget(up_btn)
        order_layout.addWidget(down_btn)

        layout.addLayout(order_layout)

        # Rule name and info
        info_layout = QVBoxLayout()

        name_label = QLabel(f"{self.rule.order + 1}. {self.rule.name or 'Unnamed Rule'}")
        name_label.setStyleSheet(self.style_manager.get_stylesheet(QLabel, 'bold'))

        op_display = self.rule.operation_type.display_name
        condition_label = QLabel(f"[{op_display}] Condition: {self.rule.condition or 'None'}")
        condition_label.setStyleSheet(self.style_manager.get_stylesheet(QLabel, 'subtext'))

        detail_text = self._build_detail_text()
        detail_label = QLabel(detail_text)
        detail_label.setStyleSheet(self.style_manager.get_stylesheet(QLabel, 'subtext'))

        info_layout.addWidget(name_label)
        info_layout.addWidget(condition_label)
        info_layout.addWidget(detail_label)

        layout.addLayout(info_layout, 1)

        # Action buttons
        btn_layout = QHBoxLayout()

        edit_btn = QPushButton("Edit")
        edit_btn.setStyleSheet(self.style_manager.get_stylesheet(QPushButton, 'accent'))
        edit_btn.clicked.connect(lambda: self.settings_widget.edit_rule(self.rule))

        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet(self.style_manager.get_stylesheet(QPushButton, 'warning'))
        delete_btn.clicked.connect(lambda: self.settings_widget.delete_rule(self.rule))

        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _build_detail_text(self) -> str:
        op = self.rule.operation_type
        label = self._OP_LABELS.get(op, "???")

        if op == OperationType.ADD:
            tags = ', '.join(self.rule.tags_to_add) if self.rule.tags_to_add else 'None'
            pos = "start" if self.rule.position == "start" else "end"
            return f"{label} ({pos}): {tags}"
        elif op == OperationType.REMOVE:
            tags = ', '.join(self.rule.tags_to_add) if self.rule.tags_to_add else 'None'
            return f"{label}: {tags}"
        elif op == OperationType.REPLACE:
            pattern = self.rule.search_pattern or '(none)'
            replacement = self.rule.tags_to_add[0] if self.rule.tags_to_add else '(empty)'
            return f"{label}: /{pattern}/ → {replacement}"
        elif op == OperationType.SORT:
            subdir = self.rule.subdirectory or '(none)'
            return f"{label}: {subdir}"
        return ""


class ExportTagRulesSettings(SettingsWidget):
    """Settings page for managing export tag rules"""

    def __init__(self, parent=None):
        self._pages = {}
        self._page_creators = {
            "rules_list": self.create_rules_list_page,
            "rule_editor": lambda **kwargs: self.create_rule_editor_page(**kwargs),
        }

        super().__init__(parent)

        self.rules: List[ExportTagRule] = []
        self.current_rule: Optional[ExportTagRule] = None
        self.tag_groups: List[TagGroup] = []

        self.load_data()
        self.switch_page("rules_list")

    def navigate_path(self, path: str):
        pass

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)

    def load_data(self):
        self.tag_groups = self.db.tags.get_project_tags(self.active_project.id)
        self.rules = self.db.export_rules.get_project_rules(self.active_project.id)

    # ------------------------------------------------------------------ #
    #  Rules list page
    # ------------------------------------------------------------------ #

    def create_rules_list_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        header_layout = QHBoxLayout()
        header_layout.addLayout(self._create_header("Export Tag Rules", font_size=14))
        header_layout.addStretch(1)

        new_btn = self._create_button("New Rule", "Create a new export tag rule")
        new_btn.clicked.connect(self.create_new_rule)
        header_layout.addWidget(new_btn)

        layout.addLayout(header_layout)

        info_label = QLabel(
            "Define rules to automatically modify tags or sort images during export.\n"
            "Operations: Add tags, Remove tags, Replace tags (regex), Sort into subdirectories."
        )
        info_label.setStyleSheet(self.style_manager.get_stylesheet(QLabel, 'subtext'))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        self.rules_list = QListWidget()
        self.rules_list.setStyleSheet(self.style_manager.get_stylesheet(QListWidget))
        layout.addWidget(self.rules_list)

        self.refresh_rules_list()
        return widget

    # ------------------------------------------------------------------ #
    #  Rule editor page
    # ------------------------------------------------------------------ #

    def create_rule_editor_page(self, rule: Optional[ExportTagRule] = None) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        title = "Edit Rule" if rule else "New Rule"
        layout.addLayout(self._create_header(title, font_size=14))

        # --- Rule name ---
        name_layout = QHBoxLayout()
        name_label = QLabel("Rule Name:")
        name_label.setStyleSheet(self.style_manager.get_stylesheet(QLabel))
        self.rule_name_input = QLineEdit()
        self.rule_name_input.setStyleSheet(self.style_manager.get_stylesheet(QLineEdit))
        self.rule_name_input.setPlaceholderText("e.g., 'Add trigger word'")
        if rule:
            self.rule_name_input.setText(rule.name)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.rule_name_input, 1)
        layout.addLayout(name_layout)

        # --- Operation type ---
        op_layout = QHBoxLayout()
        op_label = QLabel("Operation:")
        op_label.setStyleSheet(self.style_manager.get_stylesheet(QLabel))
        self.operation_combo = QComboBox()
        self.operation_combo.setStyleSheet(self.style_manager.get_stylesheet(QComboBox))

        display_names = OperationType.display_names()
        for op_type in OperationType:
            self.operation_combo.addItem(display_names[op_type], op_type.value)

        if rule:
            idx = self.operation_combo.findData(rule.operation_type.value)
            if idx >= 0:
                self.operation_combo.setCurrentIndex(idx)

        self.operation_combo.currentIndexChanged.connect(self._on_operation_changed)

        op_layout.addWidget(op_label)
        op_layout.addWidget(self.operation_combo, 1)
        layout.addLayout(op_layout)

        # --- Condition ---
        condition_label = QLabel("Condition (using tag group syntax):")
        condition_label.setStyleSheet(self.style_manager.get_stylesheet(QLabel))
        layout.addWidget(condition_label)

        self.condition_input = QTextEdit()
        self.condition_input.setStyleSheet(self.style_manager.get_stylesheet(QTextEdit))
        self.condition_input.setPlaceholderText(
            "Examples:\n"
            "  Composition[has:from above] AND BodyFeatures[has:long ears]\n"
            "  Composition[completed]\n"
            "  BodyFeatures[count>=3]"
        )
        self.condition_input.setMaximumHeight(100)
        if rule:
            self.condition_input.setPlainText(rule.condition)
        layout.addWidget(self.condition_input)

        validate_btn = QPushButton("Validate Condition")
        validate_btn.setStyleSheet(self.style_manager.get_stylesheet(QPushButton, 'function'))
        validate_btn.clicked.connect(self.validate_condition)
        layout.addWidget(validate_btn)

        # --- Dynamic fields container ---
        self.dynamic_container = QWidget()
        self.dynamic_layout = QVBoxLayout()
        self.dynamic_layout.setContentsMargins(0, 0, 0, 0)
        self.dynamic_container.setLayout(self.dynamic_layout)
        layout.addWidget(self.dynamic_container)

        # Build the dynamic fields for the current operation type
        self._build_dynamic_fields(rule)

        # --- Enabled checkbox ---
        self.enabled_checkbox = QCheckBox("Rule Enabled")
        self.enabled_checkbox.setStyleSheet(self.style_manager.get_stylesheet(QCheckBox))
        self.enabled_checkbox.setChecked(rule.enabled if rule else True)
        layout.addWidget(self.enabled_checkbox)

        layout.addStretch(1)

        # --- Action buttons ---
        btn_layout = QHBoxLayout()

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(self.style_manager.get_stylesheet(QPushButton, 'accept'))
        save_btn.clicked.connect(lambda: self.save_rule(rule))

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(self.style_manager.get_stylesheet(QPushButton))
        cancel_btn.clicked.connect(lambda: self.switch_page("rules_list"))

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        return widget

    # ------------------------------------------------------------------ #
    #  Dynamic fields per operation type
    # ------------------------------------------------------------------ #

    def _get_current_operation(self) -> OperationType:
        return OperationType(self.operation_combo.currentData())

    def _on_operation_changed(self, _index: int):
        self._build_dynamic_fields(rule=None)

    def _clear_dynamic_layout(self):
        while self.dynamic_layout.count():
            item = self.dynamic_layout.takeAt(0)
            if item.widget(): # type: ignore
                item.widget().deleteLater() # type: ignore
            elif item.layout(): # type: ignore
                # Recursively clear nested layouts
                sub = item.layout() # type: ignore
                while sub.count(): # type: ignore
                    sub_item = sub.takeAt(0) # type: ignore
                    if sub_item.widget(): # type: ignore
                        sub_item.widget().deleteLater() # type: ignore

    def _build_dynamic_fields(self, rule: Optional[ExportTagRule]):
        self._clear_dynamic_layout()
        op = self._get_current_operation()

        if op == OperationType.ADD:
            self._build_add_fields(rule)
        elif op == OperationType.REMOVE:
            self._build_remove_fields(rule)
        elif op == OperationType.REPLACE:
            self._build_replace_fields(rule)
        elif op == OperationType.SORT:
            self._build_sort_fields(rule)

    def _build_add_fields(self, rule: Optional[ExportTagRule]):
        label = QLabel("Tags to Add (comma-separated):")
        label.setStyleSheet(self.style_manager.get_stylesheet(QLabel))
        self.dynamic_layout.addWidget(label)

        self.tags_input = QLineEdit()
        self.tags_input.setStyleSheet(self.style_manager.get_stylesheet(QLineEdit))
        self.tags_input.setPlaceholderText("e.g., 'slime girl, transparent'")
        if rule and rule.operation_type == OperationType.ADD and rule.tags_to_add:
            self.tags_input.setText(", ".join(rule.tags_to_add))
        self.dynamic_layout.addWidget(self.tags_input)

        # Position selector
        pos_layout = QHBoxLayout()
        pos_label = QLabel("Insert at:")
        pos_label.setStyleSheet(self.style_manager.get_stylesheet(QLabel))

        self.position_combo = QComboBox()
        self.position_combo.setStyleSheet(self.style_manager.get_stylesheet(QComboBox))
        self.position_combo.addItem("End of caption", "end")
        self.position_combo.addItem("Start of caption (e.g. trigger words)", "start")

        if rule and rule.operation_type == OperationType.ADD:
            idx = self.position_combo.findData(rule.position)
            if idx >= 0:
                self.position_combo.setCurrentIndex(idx)

        pos_layout.addWidget(pos_label)
        pos_layout.addWidget(self.position_combo, 1)
        self.dynamic_layout.addLayout(pos_layout)

    def _build_remove_fields(self, rule: Optional[ExportTagRule]):
        label = QLabel("Tags to Remove (comma-separated, exact match):")
        label.setStyleSheet(self.style_manager.get_stylesheet(QLabel))
        self.dynamic_layout.addWidget(label)

        self.tags_input = QLineEdit()
        self.tags_input.setStyleSheet(self.style_manager.get_stylesheet(QLineEdit))
        self.tags_input.setPlaceholderText("e.g., 'low quality, blurry'")
        if rule and rule.operation_type == OperationType.REMOVE and rule.tags_to_add:
            self.tags_input.setText(", ".join(rule.tags_to_add))
        self.dynamic_layout.addWidget(self.tags_input)

    def _build_replace_fields(self, rule: Optional[ExportTagRule]):
        pattern_label = QLabel("Search Pattern (regex):")
        pattern_label.setStyleSheet(self.style_manager.get_stylesheet(QLabel))
        self.dynamic_layout.addWidget(pattern_label)

        self.search_pattern_input = QLineEdit()
        self.search_pattern_input.setStyleSheet(self.style_manager.get_stylesheet(QLineEdit))
        self.search_pattern_input.setPlaceholderText(r"e.g., 'transparent\s*body' or 'see-through'")
        if rule and rule.operation_type == OperationType.REPLACE:
            self.search_pattern_input.setText(rule.search_pattern)
        self.dynamic_layout.addWidget(self.search_pattern_input)

        replacement_label = QLabel("Replacement (leave empty to delete matched text):")
        replacement_label.setStyleSheet(self.style_manager.get_stylesheet(QLabel))
        self.dynamic_layout.addWidget(replacement_label)

        self.tags_input = QLineEdit()
        self.tags_input.setStyleSheet(self.style_manager.get_stylesheet(QLineEdit))
        self.tags_input.setPlaceholderText("e.g., 'translucent body'")
        if rule and rule.operation_type == OperationType.REPLACE and rule.tags_to_add:
            self.tags_input.setText(rule.tags_to_add[0])
        self.dynamic_layout.addWidget(self.tags_input)

    def _build_sort_fields(self, rule: Optional[ExportTagRule]):
        label = QLabel("Subdirectory name (relative to current export directory):")
        label.setStyleSheet(self.style_manager.get_stylesheet(QLabel))
        self.dynamic_layout.addWidget(label)

        self.subdirectory_input = QLineEdit()
        self.subdirectory_input.setStyleSheet(self.style_manager.get_stylesheet(QLineEdit))
        self.subdirectory_input.setPlaceholderText("e.g., 'transparent' or 'high_drip'")
        if rule and rule.operation_type == OperationType.SORT:
            self.subdirectory_input.setText(rule.subdirectory)
        self.dynamic_layout.addWidget(self.subdirectory_input)

    # ------------------------------------------------------------------ #
    #  Actions
    # ------------------------------------------------------------------ #

    def refresh_rules_list(self):
        self.rules_list.clear()
        for rule in self.rules:
            item = QListWidgetItem()
            widget = ExportTagRuleWidget(rule, self.style_manager, self, self.rules_list)
            self.rules_list.addItem(item)
            self.rules_list.setItemWidget(item, widget)
            item.setSizeHint(widget.sizeHint())

    def create_new_rule(self):
        self.current_rule = None
        self.switch_page("rule_editor")

    def edit_rule(self, rule: ExportTagRule):
        self.current_rule = rule
        self.switch_page("rule_editor", rule=rule)

    def move_rule_up(self, rule: ExportTagRule):
        """Swap this rule with the one above it."""
        idx = self.rules.index(rule)
        if idx <= 0:
            return
        other = self.rules[idx - 1]

        # Swap orders in DB
        self.db.export_rules.swap_rule_order(rule.id, rule.order, other.id, other.order)

        # Swap in memory
        rule.order, other.order = other.order, rule.order
        self.rules[idx], self.rules[idx - 1] = self.rules[idx - 1], self.rules[idx]

        self.refresh_rules_list()

    def move_rule_down(self, rule: ExportTagRule):
        """Swap this rule with the one below it."""
        idx = self.rules.index(rule)
        if idx >= len(self.rules) - 1:
            return
        other = self.rules[idx + 1]

        # Swap orders in DB
        self.db.export_rules.swap_rule_order(rule.id, rule.order, other.id, other.order)

        # Swap in memory
        rule.order, other.order = other.order, rule.order
        self.rules[idx], self.rules[idx + 1] = self.rules[idx + 1], self.rules[idx]

        self.refresh_rules_list()

    def validate_condition(self):
        condition_text = self.condition_input.toPlainText().strip()

        if not condition_text:
            styled_information_box(self, "Validation", "Condition is empty", self.style_manager)
            return

        try:
            parsed = parse_condition(condition_text)

            if parsed is None:
                styled_information_box(self, "Validation", "Condition is empty", self.style_manager)
                return

            dummy_group = TagGroup(
                id=-1,
                project_id=self.active_project.id,
                name="__validation__",
                order=len(self.tag_groups),
                condition=condition_text,
            )

            validate_references(parsed, dummy_group, self.tag_groups)

            styled_information_box(
                self,
                "Validation Successful",
                "The condition syntax is valid and all referenced groups/tags exist!",
                self.style_manager,
            )
        except ValueError as e:
            styled_warning_box(self, "Validation Error", f"Invalid condition:\n{e}", self.style_manager)
        except Exception as e:
            styled_warning_box(self, "Validation Error", f"Error validating condition:\n{e}", self.style_manager)

    def save_rule(self, existing_rule: Optional[ExportTagRule]):
        name = self.rule_name_input.text().strip()
        condition = self.condition_input.toPlainText().strip()
        enabled = self.enabled_checkbox.isChecked()
        op = self._get_current_operation()

        # --- Validate common fields ---
        if not name:
            styled_warning_box(self, "Validation Error", "Please enter a rule name", self.style_manager)
            return
        if not condition:
            styled_warning_box(self, "Validation Error", "Please enter a condition", self.style_manager)
            return

        # --- Validate condition syntax ---
        try:
            parsed = parse_condition(condition)
            if parsed is None:
                styled_warning_box(self, "Validation Error", "Condition cannot be empty", self.style_manager)
                return
            dummy_group = TagGroup(
                id=-1,
                project_id=self.active_project.id,
                name="__validation__",
                order=len(self.tag_groups),
                condition=condition,
            )
            validate_references(parsed, dummy_group, self.tag_groups)
        except ValueError as e:
            styled_warning_box(self, "Validation Error", f"Invalid condition:\n{e}", self.style_manager)
            return

        # --- Collect operation-specific data ---
        tags_to_add: List[str] = []
        operation_data: dict = {}

        if op == OperationType.ADD:
            tags_text = self.tags_input.text().strip()
            tags_to_add = [t.strip() for t in tags_text.split(',') if t.strip()]
            if not tags_to_add:
                styled_warning_box(self, "Validation Error", "Please enter at least one tag to add", self.style_manager)
                return
            position = self.position_combo.currentData()
            if position != "end":
                operation_data["position"] = position

        elif op == OperationType.REMOVE:
            tags_text = self.tags_input.text().strip()
            tags_to_add = [t.strip() for t in tags_text.split(',') if t.strip()]
            if not tags_to_add:
                styled_warning_box(self, "Validation Error", "Please enter at least one tag to remove", self.style_manager)
                return

        elif op == OperationType.REPLACE:
            pattern = self.search_pattern_input.text().strip()
            replacement = self.tags_input.text().strip()
            if not pattern:
                styled_warning_box(self, "Validation Error", "Please enter a search pattern", self.style_manager)
                return
            # Validate regex
            import re
            try:
                re.compile(pattern)
            except re.error as e:
                styled_warning_box(self, "Validation Error", f"Invalid regex pattern:\n{e}", self.style_manager)
                return
            operation_data["search_pattern"] = pattern
            tags_to_add = [replacement]  # Store replacement in tags_to_add

        elif op == OperationType.SORT:
            subdir = self.subdirectory_input.text().strip()
            if not subdir:
                styled_warning_box(self, "Validation Error", "Please enter a subdirectory name", self.style_manager)
                return
            # Basic path safety
            if '..' in subdir or subdir.startswith('/'):
                styled_warning_box(
                    self, "Validation Error",
                    "Subdirectory must be a relative path without '..'",
                    self.style_manager,
                )
                return
            operation_data["subdirectory"] = subdir

        # --- Save ---
        if existing_rule:
            existing_rule.name = name
            existing_rule.condition = condition
            existing_rule.tags_to_add = tags_to_add
            existing_rule.enabled = enabled
            existing_rule.operation_type = op
            existing_rule.operation_data = operation_data
            self.db.export_rules.update_rule(existing_rule)
        else:
            new_rule = ExportTagRule(
                project_id=self.active_project.id,
                name=name,
                condition=condition,
                tags_to_add=tags_to_add,
                enabled=enabled,
                operation_type=op.value,
                operation_data=operation_data,
            )
            rule_id = self.db.export_rules.add_rule(new_rule)
            new_rule.id = rule_id
            self.rules.append(new_rule)

        self.refresh_rules_list()
        self.switch_page("rules_list")

    def delete_rule(self, rule: ExportTagRule):
        reply = styled_question_box(
            self,
            "Delete Rule",
            f"Are you sure you want to delete the rule '{rule.name}'?",
            self.style_manager,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.db.export_rules.delete_rule(rule.id)
            self.rules.remove(rule)
            self.refresh_rules_list()

    # ------------------------------------------------------------------ #
    #  Page management
    # ------------------------------------------------------------------ #

    def get_page(self, page_name: str, **kwargs):
        if page_name == "rule_editor":
            return self._page_creators[page_name](**kwargs)
        if page_name not in self._pages:
            creator = self._page_creators.get(page_name)
            if creator:
                page = creator(**kwargs)
                self._pages[page_name] = page
                self.main_layout.addWidget(page)
        return self._pages.get(page_name)

    def switch_page(self, page_name: str, **kwargs):
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget(): # type: ignore
                item.widget().setParent(None) # type: ignore

        page = self.get_page(page_name, **kwargs)
        if page:
            self.main_layout.addWidget(page)