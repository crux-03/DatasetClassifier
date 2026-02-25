from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QTransform, QKeySequence

from src.blur_manager import BlurManager
from src.keybinds.pages.scoring_keybind_page import ScoringKeybindPage
from src.keybinds.keybind_manager import KeyBinding, KeybindHandler
from src.project import Project
from src.config_handler import ConfigHandler
from src.database.database import Database
from src.image_handler import ImageHandler
from src.button_states import ButtonStateManager
from src.ui_components import UIComponents
from src.utils import key_to_unicode
from src.update_poller import UpdatePoller
from src.styling.style_manager import StyleManager
from src.widgets.category_button_widget import CategoryButtonWidget


class ScoringPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.button_states: ButtonStateManager = parent.button_states
        self.db: Database = parent.db
        self.style_manager: StyleManager = parent.style_manager
        self.config_handler: ConfigHandler = parent.config_handler
        self.update_poller: UpdatePoller = parent.update_poller
        self.active_project = None

        self.image_handler = ImageHandler(self.db, self.config_handler)
        self.default_scores = ['score_0', 'score_1', 'score_2', 'score_3', 'score_4', 'score_5', 'discard']
        self.category_buttons = []
        self.category_mapping = {}  # Maps category_name -> category_id

        self.page_active = True

        # Initialize keybind handler
        self.keybind_handler = KeybindHandler(self.config_handler)
        self.keybind_page = ScoringKeybindPage(self)

        # Initialize UI state variables
        self.alt_pressed = False
        self.ctrl_pressed = False

        # Cache for UI updates
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._delayed_ui_update)
        self._pending_updates = set()

        self.setup_ui()

        self.blur_manager: BlurManager = BlurManager(self.image_label, int(self.config_handler.get_value('privacy.blur_strength')))

        self.setup_keybinds()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(self.create_middle_row())
        main_layout.addLayout(self.create_scoring_buttons())

    def setup_keybinds(self):
        # Register score buttons (0-9)
        for i, button in enumerate(self.score_buttons[:-1]):
            self.keybind_page.register_binding(f'key_{i}', lambda s=button.objectName(): self.click_score_button(s))

        # Category buttons will be registered when created

        # Other bindings
        self.keybind_page.register_binding('discard', lambda: self.click_score_button('discard'))
        self.keybind_page.register_binding('next_image', self.next_button)
        self.keybind_page.register_binding('previous_image', self.prev_button)
        self.keybind_page.register_binding('blur', self.toggle_blur)

        # Register with handler
        self.keybind_handler.register_page("scoring", self.keybind_page)

    def click_score_button(self, object_name):
        self.score_image(object_name)

        if not self.config_handler.get_value('behaviour.auto_scroll_scores'):
            self.update_button_colors()

    def import_categories(self):
        """Load categories from database and create buttons"""
        categories = self.db.categories.get_project_categories(self.active_project.id)
        self.category_mapping.clear()

        for category_id, category_name, display_order in categories:
            self.category_mapping[category_name] = category_id
            self.add_category_button_from_import(category_name)

        # Update button states after importing
        self.update_button_colors()

    def update_score_button_labels(self):
        """Update button labels with their keybindings"""
        bindings = self.keybind_handler.current_bindings

        # Update score buttons
        for i, button in enumerate(self.score_buttons[:-1]):  # Exclude discard button
            key_bindings = bindings.get(f'key_{i}')
            if key_bindings:
                _, scores = self.config_handler.get_scores()
                # Get shortcuts for both normal and Alt versions
                shortcuts = []
                for binding in key_bindings:
                    key_sequence = self._create_key_sequence(binding)
                    unicode = key_to_unicode(key_sequence.toString())
                    shortcuts.append(unicode)

                # Join shortcuts with separator
                shortcut_text = " / ".join(shortcuts)
                score = button.objectName()
                button.setText(f"({shortcut_text})        {scores[score]}")

        # Update discard button
        key_bindings = bindings.get('discard')
        if key_bindings:
            discard_button = self.score_buttons[-1]
            shortcuts = []
            for binding in key_bindings:
                key_sequence = self._create_key_sequence(binding)
                unicode = key_to_unicode(key_sequence.toString())
                shortcuts.append(unicode)
            shortcut_text = " / ".join(shortcuts)
            if f"({shortcut_text})" not in discard_button.text():
                discard_button.setText(f"({shortcut_text})        discard")

    def update_category_button_labels(self):
        """Update category button labels with their keybindings"""
        bindings = self.keybind_handler.current_bindings

        for i, widget in enumerate(self.category_buttons):
            key_bindings = bindings.get(f'category_{i}')
            if key_bindings:
                shortcuts = []
                for binding in key_bindings:
                    key_sequence = self._create_key_sequence(binding)
                    unicode = key_to_unicode(key_sequence.toString())
                    shortcuts.append(unicode)
                shortcut_text = " / ".join(shortcuts)
                widget.set_keybind_text(f"({shortcut_text})")

    def set_active_project(self, project: Project):
        """Update the active project and refresh UI"""
        self.active_project = project
        self.load_images()
        self.import_categories()  # Import categories BEFORE updating colors
        self.display_image()
        self.update_button_colors()
        self.update_progress()

        # Enable relevant UI elements
        self.button_states.toggle_button_group(True, 'score')
        self.button_states.toggle_button_group(True, 'image')
        self.button_states.toggle_button_group(True, 'category')

    def _create_key_sequence(self, binding: KeyBinding) -> QKeySequence:
        """Create a QKeySequence from a KeyBinding"""
        key = binding.key
        if binding.modifiers:
            # Map Qt modifier enums to QKeySequence string format
            modifier_map = {
                Qt.KeyboardModifier.AltModifier: "Alt",
                Qt.KeyboardModifier.ControlModifier: "Ctrl",
                Qt.KeyboardModifier.ShiftModifier: "Shift",
                Qt.KeyboardModifier.MetaModifier: "Meta"
            }
            modifier_strs = [modifier_map.get(mod, mod.name) for mod in binding.modifiers]
            modifier_str = "+".join(modifier_strs)
            return QKeySequence(f"{modifier_str}+{key}")
        return QKeySequence(key)

    def score_image(self, score: str):
        """Optimized scoring with reduced UI updates"""
        if not self.active_project:
            return

        self.image_handler.score_image(score, None)

        # Auto-scroll to next image (if enabled)
        if self.config_handler.get_value('behaviour.auto_scroll_scores'):
            if self.image_handler.load_next_image():
                QTimer.singleShot(0, self.display_image)

        self.update_poller.poll_update('update_tagging_images')

    def categorize_image(self, category_name: str):
        """Toggle a category for the current image"""
        if not self.active_project or not self.image_handler.current_image_id:
            return

        category_id = self.category_mapping.get(category_name)
        if category_id is None:
            print(f"Warning: Category '{category_name}' not found in mapping")
            return

        image_id = self.image_handler.current_image_id

        # Toggle the category
        if self.db.categories.image_has_category(image_id, category_id):
            self.db.categories.remove_image_category(image_id, category_id)
        else:
            self.db.categories.add_image_category(image_id, category_id)

        # Update UI
        self.update_button_colors()

    def load_next_image(self):
        if self.image_handler.load_next_image():
            self.display_image()

    def load_previous_image(self):
        if self.image_handler.load_previous_image():
            self.display_image()

    def load_latest_image(self):
        """Load the latest scored image in the project"""
        latest_id = self.db.images.get_latest_image_id(self.active_project.id)
        if latest_id is not None and self.image_handler.image_ids:
            # Find the index of the latest image ID in our list
            try:
                latest_index = self.image_handler.image_ids.index(latest_id)
                self.image_handler.set_index(latest_index)
                self.display_image()

                # Update navigation button states
                self.button_states.toggle_button(False, 'to_latest_button_right', 'image')
                self.button_states.toggle_button(False, 'to_latest_button_left', 'image')
            except ValueError:
                print(f"Latest image ID {latest_id} not found in current image list")

    def display_image(self):
        """Optimized image display"""
        pixmap = self.image_handler.get_current_image()
        if not pixmap:
            return

        # Cache the orientation for the current image
        if not hasattr(self, '_cached_orientation'):
            self._cached_orientation = {}

        image_id = self.image_handler.current_image_id
        if image_id not in self._cached_orientation:
            self._cached_orientation[image_id] = self.image_handler.get_orientation()

        orientation = self._cached_orientation[image_id]

        # Only create transform if needed
        transform = None
        if orientation != "Normal":
            transform = QTransform()
            rotations = {
                "Rotate 90 CW": 90,
                "Rotate 180": 180,
                "Rotate 270 CW": 270,
                "Rotate 90 CCW": 270
            }
            if orientation in rotations:
                transform.rotate(rotations[orientation])

        # Apply transform if needed
        if transform:
            pixmap = pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)

        # Scale and display
        scaled_pixmap = pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)

        # Schedule UI updates
        self.schedule_ui_update('progress')
        self.schedule_ui_update('buttons')
        self.schedule_ui_update('latest')

    def load_images(self):
        """Load images for the active project"""
        if self.active_project:
            self.image_handler.load_images(self.active_project.id, False)
            self.update_progress()
            self.display_image()

    def update_progress(self):
        """Update the progress bar and label"""
        current, total = self.image_handler.get_progress()
        if total > 0:
            self.progress_bar.setValue(current * 100 // total)
            self.progress_label.setText(f"{current}/{total}")


    def manage_latest_button_state(self):
        """Update the state of Latest Image navigation buttons"""
        if not self.db or not self.active_project:
            return

        latest_id = self.db.images.get_latest_image_id(self.active_project.id)
        if latest_id is None or not self.image_handler.current_image_id:
            return

        # Get indices for comparison
        try:
            latest_index = self.image_handler.image_ids.index(latest_id)
            current_index = self.image_handler.image_ids.index(self.image_handler.current_image_id)

            # Update button states based on position
            if current_index == latest_index:
                self.button_states.toggle_button(False, 'to_latest_button_right', 'image')
                self.button_states.toggle_button(False, 'to_latest_button_left', 'image')
            elif current_index > latest_index:
                self.button_states.toggle_button(True, 'to_latest_button_left', 'image')
                self.button_states.toggle_button(False, 'to_latest_button_right', 'image')
            else:
                self.button_states.toggle_button(True, 'to_latest_button_right', 'image')
                self.button_states.toggle_button(False, 'to_latest_button_left', 'image')
        except ValueError:
            if not self.db.projects.has_scores(self.active_project.id):
                return

            print("Error: Could not determine image positions")

    def create_middle_row(self):
        layout = QHBoxLayout()

        image_viewer_layout, self.prev_button, self.image_label, self.next_button, self.to_latest_button_right, self.to_latest_button_left = UIComponents.create_image_viewer(self.button_states.image_enabled, self.style_manager)
        layout.addLayout(image_viewer_layout, 7)

        self.prev_button.clicked.connect(self.load_previous_image)
        self.next_button.clicked.connect(self.load_next_image)
        self.to_latest_button_right.clicked.connect(self.load_latest_image)
        self.to_latest_button_left.clicked.connect(self.load_latest_image)

        category_buttons_layout, self.category_input, self.category_add_button, self.category_button_layout = UIComponents.create_category_buttons(self.button_states.category_enabled, self.style_manager)
        layout.addLayout(category_buttons_layout, 3)

        self.category_input.textChanged.connect(self.check_category_button_name)
        self.category_add_button.clicked.connect(self.add_category_button)

        self.button_states.declare_button_group([self.prev_button, self.next_button, self.to_latest_button_right, self.to_latest_button_left], 'image')
        self.button_states.declare_button_group([self.category_input, self.category_add_button], 'category')

        return layout

    def create_scoring_buttons(self):
        layout, self.score_buttons, self.progress_bar, self.progress_label = UIComponents.create_scoring_buttons(self.default_scores, self.button_states.score_enabled, self.config_handler, self.style_manager)
        self.button_states.declare_button_group(self.score_buttons, 'score')
        self.score_layout = layout.itemAt(0).layout()  # Store the score_layout

        for btn in self.score_buttons:
            btn.clicked.connect(lambda _, s=btn.objectName(): self.click_score_button(s))

        return layout

    def check_category_button_name(self):
        name = self.category_input.text()
        enabled = not (name and any(widget.get_category_name() == name for widget in self.category_buttons))
        self.category_add_button.setEnabled(enabled)

    def add_category_button_from_import(self, name: str):
        """Add a category button from imported data"""
        self._create_category_button(name)
        self.update_category_button_labels()

    def add_category_button(self):
        """Add a new category button with keybinding support"""
        if len(self.category_buttons) < 10:
            name = self.category_input.text().strip()
            if name and not any(widget.get_category_name() == name for widget in self.category_buttons):
                # Add to database
                try:
                    category_id = self.db.categories.add_category(
                        self.active_project.id,
                        name,
                        len(self.category_buttons)
                    )
                    self.category_mapping[name] = category_id

                    # Create the UI button
                    self._create_category_button(name)
                    self.category_input.clear()
                    self.update_category_button_labels()
                except Exception as e:
                    print(f"Error adding category: {e}")

    def _create_category_button(self, name: str):
        """Create a new category button widget"""
        index = len(self.category_buttons)

        # Create the custom widget
        widget = CategoryButtonWidget(name, index, self.style_manager, self)

        # Connect signals
        widget.clicked.connect(self.categorize_image)
        widget.removeRequested.connect(self.remove_category_button)

        # Add to layout
        self.category_button_layout.addWidget(widget)
        self.category_buttons.append(widget)

        # Register keybinding - the widget's internal button will be triggered
        self.keybind_page.register_binding(f'category_{index}', widget.get_button())

        # Get the key from the corresponding score button (key_0, key_1, etc.)
        # and add Alt modifier to create the category keybind
        score_key_bindings = self.keybind_handler.current_bindings.get(f'key_{index}')
        if score_key_bindings and len(score_key_bindings) > 0:
            # Use the first score key binding and add Alt modifier
            base_key = score_key_bindings[0].key
            category_binding = KeyBinding(base_key, [Qt.KeyboardModifier.AltModifier])

            # Update in handler's cache
            self.keybind_handler.current_bindings[f'category_{index}'] = [category_binding]

            # Apply directly to this page
            self.keybind_page.apply_keybindings({f'category_{index}': [category_binding]})
        else:
            # Fallback to number keys if score keys aren't found
            fallback_binding = KeyBinding(str(index), [Qt.KeyboardModifier.AltModifier])
            self.keybind_handler.current_bindings[f'category_{index}'] = [fallback_binding]
            self.keybind_page.apply_keybindings({f'category_{index}': [fallback_binding]})

        # Update the label
        self.update_category_button_labels()

    def remove_category_button(self, widget: CategoryButtonWidget):
        """Remove a category button and its keybinding"""
        if widget in self.category_buttons:
            index = self.category_buttons.index(widget)
            category_name = widget.get_category_name()
            category_id = self.category_mapping.get(category_name)

            # Remove from database
            if category_id is not None:
                try:
                    self.db.categories.delete_category(category_id)
                    del self.category_mapping[category_name]
                except Exception as e:
                    print(f"Error deleting category: {e}")

            # Remove keybinding
            self.keybind_page.remove_keybinding(f'category_{index}')

            # Remove from list and layout
            self.category_buttons.remove(widget)
            self.category_button_layout.removeWidget(widget)
            widget.deleteLater()

            # Re-register remaining category buttons with updated indices
            self._reindex_category_bindings()

    def _reindex_category_bindings(self):
        """Update category button indices after removal"""
        # First, remove all old bindings
        for i in range(10):  # Max 10 categories
            self.keybind_page.remove_keybinding(f'category_{i}')

        # Re-register with correct indices
        for i, widget in enumerate(self.category_buttons):
            widget.index = i  # Update the widget's internal index
            self.keybind_page.register_binding(f'category_{i}', widget.get_button())

            # Get the key from the corresponding score button
            score_key_bindings = self.keybind_handler.current_bindings.get(f'key_{i}')
            if score_key_bindings and len(score_key_bindings) > 0:
                # Use the first score key binding and add Alt modifier
                base_key = score_key_bindings[0].key
                category_binding = KeyBinding(base_key, [Qt.KeyboardModifier.AltModifier])

                # Update in handler's cache
                self.keybind_handler.current_bindings[f'category_{i}'] = [category_binding]

                # Apply directly to this page
                self.keybind_page.apply_keybindings({f'category_{i}': [category_binding]})
            else:
                # Fallback to number keys
                fallback_binding = KeyBinding(str(i), [Qt.KeyboardModifier.AltModifier])
                self.keybind_handler.current_bindings[f'category_{i}'] = [fallback_binding]
                self.keybind_page.apply_keybindings({f'category_{i}': [fallback_binding]})

        self.update_category_button_labels()

    def update_button_colors(self):
        """Update score button colors based on the current image's score."""
        if not self.db or not self.image_handler.current_image_id:
            return

        current_image = self.image_handler.get_current_image_path()
        if not current_image:
            return

        # Get score from cache
        current_score, _ = self.image_handler.get_score(current_image)
        
        # Get categories directly from database (always fresh)
        image_id = self.image_handler.current_image_id
        current_categories = self.db.categories.get_image_category_names(image_id)

        # Update score buttons
        for i in range(self.score_layout.count()):
            button = self.score_layout.itemAt(i).widget()
            if not isinstance(button, QPushButton) or not button.isEnabled():
                continue

            button.setChecked(button.objectName() == current_score)

        # Update category buttons using the new widget
        for widget in self.category_buttons:
            category_name = widget.get_category_name()
            is_active = category_name in current_categories
            widget.set_active(is_active)

    def set_active(self, active: bool = True):
        self.page_active = active

    def schedule_ui_update(self, update_type):
        """Schedule a UI update to batch multiple updates together"""
        self._pending_updates.add(update_type)
        self._update_timer.start(50)  # 50ms delay

    def _delayed_ui_update(self):
        """Process all pending UI updates at once"""
        if 'progress' in self._pending_updates:
            self.update_progress()
        if 'buttons' in self._pending_updates:
            self.update_button_colors()
        if 'latest' in self._pending_updates:
            self.manage_latest_button_state()
        self._pending_updates.clear()

    def toggle_blur(self):
        self.blur_manager.toggle_blur()
