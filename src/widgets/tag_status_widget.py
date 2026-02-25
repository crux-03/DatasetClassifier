from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.config_handler import ConfigHandler
from src.styling.style_manager import StyleManager
from src.styling.styling_utils import create_emoji_font
from src.tagging.tag_group import TagGroup

button_style = """
    QPushButton {
        background-color: #454545;
        color: white;
        padding: 5px 10px;
        border-radius: 3px;
    }
    QPushButton:hover {
        background-color: #555555;
    }
    QPushButton:pressed {
        background-color: #353535;
    }
    QPushButton:disabled {
        background-color: #353535;
        color: #545454;
    }
"""

tooltip_style = """
    QToolTip {
        background-color: #1e1e1e;
        color: white;
        border: 1px solid #3a3a3a;
        border-radius: 5px;
        padding: 2px;
    }
"""


class TagStatusWidget(QWidget):
    next_clicked: pyqtSignal = pyqtSignal()
    prev_clicked: pyqtSignal = pyqtSignal()
    latest_clicked: pyqtSignal = pyqtSignal()
    skip_clicked: pyqtSignal = pyqtSignal()
    auto_scroll_indicator_clicked: pyqtSignal = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.config_handler: ConfigHandler = self.parent.config_handler
        self.style_manager: StyleManager = self.parent.style_manager

        self.active_group: TagGroup = None
        self.is_valid = False

        self.auto_scroll_indicator_tooltip = "When the next tag is added, the next\nTagGroup will be selected automatically."

        self.initUI()

    def initUI(self):
        container = QFrame(self)
        container.setStyleSheet(self.style_manager.get_stylesheet(QWidget, "panel"))
        container.setFrameShadow(QFrame.Shadow.Raised)

        self.main_layout = QVBoxLayout(container)
        outer_layout = QVBoxLayout(self)
        outer_layout.addWidget(container)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        top_row_layout = QHBoxLayout()
        top_row_layout.setContentsMargins(0, 0, 0, 20)
        tag_group_layout = QVBoxLayout()

        ## Stats Layout
        # Tag group
        tag_group_stats_layout = QHBoxLayout()
        self.tag_group_status_label = QLabel("🔴")
        self.tag_group_status_label.setFont(create_emoji_font())
        self.tag_group_name_label = QLabel("GROUP_TITLE")
        self.tag_group_index_label = QLabel("(0/0)")

        self.tag_group_name_label.setStyleSheet(
            self.style_manager.get_stylesheet(QLabel, "bold")
        )
        self.tag_group_index_label.setStyleSheet(
            self.style_manager.get_stylesheet(QLabel, "subtext")
        )
        self.tag_group_status_label.setStyleSheet(tooltip_style)

        tag_group_stats_layout.addWidget(self.tag_group_status_label)
        tag_group_stats_layout.addWidget(self.tag_group_name_label)
        tag_group_stats_layout.addWidget(self.tag_group_index_label)

        # Selected tags
        tags_selected_layout = QHBoxLayout()
        self.seleted_tags_label = QLabel("0/0 selected")
        self.seleted_tags_label.setStyleSheet(
            self.style_manager.get_stylesheet(QLabel, "subtext")
        )
        self.auto_scroll_indicator = QLabel("⚡")
        self.auto_scroll_indicator.setFont(create_emoji_font())
        self.auto_scroll_indicator.setStyleSheet(tooltip_style)
        self.auto_scroll_indicator.setToolTip(self.auto_scroll_indicator_tooltip)
        self.auto_scroll_indicator.mousePressEvent = (
            self._auto_scroll_indicator_click_event
        )

        tags_selected_layout.addWidget(self.seleted_tags_label)
        tags_selected_layout.addWidget(self.auto_scroll_indicator)
        tags_selected_layout.addStretch(1)

        # Score
        self.score_label = QLabel("score_0")
        self.score_label.setStyleSheet(f"""
                                  background-color: {self.config_handler.get_color("accent_color")};
                                  color: white; padding:
                                  5px 10px; border-radius: 8px;
                                  """)

        bottom_row_layout = QHBoxLayout()
        bottom_row_layout.setContentsMargins(0, 0, 0, 0)

        ## Buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)

        # Add tag button
        skip_button = QPushButton("Skip")
        options_button = QPushButton("⚙️")
        options_button.setFont(create_emoji_font())

        self.prev_button = QPushButton("<")
        self.latest_button = QPushButton("🎯")
        self.latest_button.setFont(create_emoji_font())
        self.next_button = QPushButton(">")

        self.prev_button.setFixedWidth(35)
        self.latest_button.setFixedWidth(35)
        self.next_button.setFixedWidth(35)

        self.latest_button.setToolTip("Go to latest un-tagged group")

        self.prev_button.clicked.connect(self.prev_clicked)
        self.next_button.clicked.connect(self.next_clicked)
        self.latest_button.clicked.connect(self.latest_clicked)
        skip_button.clicked.connect(self.skip_clicked)

        self.prev_button.setEnabled(False)
        self.next_button.setEnabled(False)

        buttons_layout.addWidget(skip_button)
        buttons_layout.addWidget(options_button)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(self.prev_button)
        buttons_layout.addWidget(self.latest_button)
        buttons_layout.addWidget(self.next_button)

        for button in [
            skip_button,
            options_button,
            self.prev_button,
            self.latest_button,
            self.next_button,
        ]:
            button.setFixedHeight(30)
            button.setStyleSheet(button_style)

        bottom_row_layout.addLayout(buttons_layout)

        tag_group_layout.addLayout(tag_group_stats_layout)
        tag_group_layout.addLayout(tags_selected_layout)

        top_row_layout.addLayout(tag_group_layout)
        top_row_layout.addStretch(1)
        top_row_layout.addWidget(self.score_label)

        self.main_layout.addLayout(top_row_layout)
        self.main_layout.addLayout(bottom_row_layout)

        # Add click events
        options_button.clicked.connect(self.on_options_click)

    def set_tag_groups(self, tag_groups: list[TagGroup]):
        self.tag_groups = tag_groups

    def set_active_group(self, group: "TagGroup"):
        self.active_group = group
        self.update_group_ui()

    def update_group_ui(self):
        self.tag_group_name_label.setText(self.active_group.name)
        self.tag_group_index_label.setText(
            f"({self.active_group.order + 1}/{len(self.tag_groups)})"
        )

        if self.active_group.allow_multiple:
            self.seleted_tags_label.setText(f"0/{self.active_group.min_tags} selected")
        else:
            self.seleted_tags_label.setText("0/1 selected")

    def set_prev_button_enabled(self, enabled: bool):
        self.prev_button.setEnabled(enabled)

    def set_next_button_enabled(self, enabled: bool):
        self.next_button.setEnabled(enabled)

    def check_group_conditions(self, selected_tags: list[int]) -> bool:
        if self.active_group is None:
            return False

        count = self._get_applied_tags(selected_tags)

        if self.active_group.allow_multiple:
            condition_met = count >= self.active_group.min_tags
            self.seleted_tags_label.setText(
                f"{count}/{self.active_group.min_tags} selected"
            )
        else:
            condition_met = count == 1
            self.seleted_tags_label.setText(f"{count}/1 selected")
        self._set_status_label(condition_met)

        # Simplified — covers all four cases explicitly
        if self.active_group.is_required:
            self.is_valid = condition_met
        else:
            self.is_valid = True

        self._update_button_states()

        will_autoscroll = (
            self.is_valid
            and not condition_met
            and self._is_condition_met_on_next_add(selected_tags)
            and not self.active_group.prevent_auto_scroll
            and self.config_handler.get_value("behaviour.auto_scroll_on_tag_condition")
        )
        self._set_auto_scroll_indicator(will_autoscroll)

        return self.is_valid

    def can_add_tag(self, selected_tags: list[int]) -> bool:
        if self.active_group is None:
            return False

        count = self._get_applied_tags(selected_tags)
        limit = 1 if not self.active_group.allow_multiple else 9999

        return count + 1 <= limit

    def update_score(self, score: str):
        self.score_label.setText(score)

    def on_options_click(self):
        self.parent.show_configure_tag_groups()

    def _update_button_states(self):
        self.next_button.setEnabled(self.is_valid)

    def _get_applied_tags(self, selected_tags: list[int]) -> int:
        count = 0
        for group_tags in self.active_group.tags:
            count += 1 if group_tags.id in selected_tags else 0
        return count

    def _set_status_label(self, condition: bool):

        if (
            condition
            and self.active_group.is_required
            or condition
            and not self.active_group.is_required
        ):
            self.tag_group_status_label.setText("🟢")
            self.tag_group_status_label.setToolTip("Acceptable")
        if not condition and self.active_group.is_required:
            self.tag_group_status_label.setText("🔴")
            self.tag_group_status_label.setToolTip("Not acceptable")
        if not condition and not self.active_group.is_required:
            self.tag_group_status_label.setText("🟡")
            self.tag_group_status_label.setToolTip("Acceptable, not finished")

    def _set_auto_scroll_indicator(self, enabled: bool):
        self.auto_scroll_indicator.setVisible(enabled)

        temp_disabled = self.parent.auto_scroll_temp_disabled
        emoji = "⚡" if not temp_disabled else "🔅"
        self.auto_scroll_indicator.setText(emoji)
        if temp_disabled:
            self.auto_scroll_indicator.setToolTip(
                f"{self.auto_scroll_indicator_tooltip}\nTemporarily disabled. Click to Enable."
            )
        else:
            self.auto_scroll_indicator.setToolTip(self.auto_scroll_indicator_tooltip)

    def _is_condition_met_on_next_add(self, selected_tags: list[int]):
        """Checks whether the next tag added will meet (and not exceed) the conditions of the active group"""
        count = self._get_applied_tags(selected_tags)

        if self.active_group.allow_multiple:
            return count + 1 == self.active_group.min_tags
        else:
            return count + 1 == 1

    def _auto_scroll_indicator_click_event(self, event):
        temp_disabled = self.parent.auto_scroll_temp_disabled
        self.auto_scroll_indicator_clicked.emit(not temp_disabled)
