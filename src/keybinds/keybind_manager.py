from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Union

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QPushButton, QWidget


@dataclass
class KeyBinding:
    """Represents a single key combination with optional modifiers"""

    key: int | str
    modifiers: List[Qt.KeyboardModifier] = None

    def __post_init__(self):
        if self.modifiers is None:
            self.modifiers = []


@dataclass
class ConfigBinding:
    """Represents a keybinding configuration with its config path"""

    config_key: str
    description: str
    default_value: KeyBinding | List[KeyBinding]


# Define a type for possible binding targets
BindTarget = Union[QPushButton, Callable[[], None]]


class KeybindHandler:
    def __init__(self, config_handler):
        self.config_handler = config_handler
        self.registered_pages: Dict[str, "KeybindPage"] = {}

        # Define all possible keybindings with their config paths and defaults
        self.binding_definitions = {
            "next_image": ConfigBinding(
                config_key="keybindings.next_image",
                description="Next image",
                default_value=KeyBinding(Qt.Key.Key_Right),
            ),
            "previous_image": ConfigBinding(
                config_key="keybindings.previous_image",
                description="Previous image",
                default_value=KeyBinding(Qt.Key.Key_Left),
            ),
            "discard": ConfigBinding(
                config_key="keybindings.discard",
                description="Discard image",
                default_value=KeyBinding(Qt.Key.Key_Backspace),
            ),
            "continue": ConfigBinding(
                config_key="keybindings.continue",
                description="Continue",
                default_value=KeyBinding(Qt.Key.Key_Return),
            ),
            "blur": ConfigBinding(
                config_key="keybindings.blur",
                description="Blur",
                default_value=KeyBinding(Qt.Key.Key_Space),
            ),
            **{
                f"key_{i}": ConfigBinding(
                    config_key=f"keybindings.key_{i}",
                    description=f"Score {i}",
                    default_value=[
                        KeyBinding(str(i)),  # Normal binding
                        KeyBinding(
                            str(i), [Qt.KeyboardModifier.AltModifier]
                        ),  # Alt+number binding
                    ],
                )
                for i in range(10)
            },
        }

        # In KeybindHandler.__init__
        self.binding_definitions.update(
            {
                f"category_{i}": ConfigBinding(
                    config_key=f"keybindings.category_{i}",
                    description=f"Category {i}",
                    default_value=KeyBinding(str(i), [Qt.KeyboardModifier.AltModifier]),
                )
                for i in range(10)
            }
        )

        # Current bindings cache
        self.current_bindings: Dict[str, List[KeyBinding]] = self._load_keybindings()

    def _load_keybindings(self) -> Dict[str, List[KeyBinding]]:
        """Load keybindings from config"""
        bindings = {}
        for action, binding_def in self.binding_definitions.items():
            value = self.config_handler.get_value(binding_def.config_key)
            if value is None:
                default = binding_def.default_value
                bindings[action] = (
                    [default] if isinstance(default, KeyBinding) else default
                )
            else:
                # Convert stored config value to KeyBinding objects
                # Implementation depends on how you store keybindings in config
                bindings[action] = self._parse_config_value(value)
        return bindings

    def _parse_config_value(self, value) -> List[KeyBinding]:
        """Convert stored config value to KeyBinding objects"""
        # Implement based on your config storage format
        # This is a placeholder implementation
        if isinstance(value, list):
            return [KeyBinding(v) for v in value]
        return [KeyBinding(value)]

    def register_page(self, page_id: str, page: "KeybindPage"):
        """Register a page to receive keybinding updates"""
        self.registered_pages[page_id] = page
        page.apply_keybindings(self.current_bindings)

    def unregister_page(self, page_id: str):
        """Unregister a page"""
        if page_id in self.registered_pages:
            del self.registered_pages[page_id]

    def update_keybinding(self, action: str, new_bindings: List[KeyBinding]):
        """Update a keybinding and propagate changes to all pages"""
        if action in self.binding_definitions:
            binding = self.binding_definitions[action]
            # Update config
            self.config_handler.set_value(binding.config_key, new_bindings)
            # Update cache
            self.current_bindings[action] = new_bindings
            # Update all registered pages
            for page in self.registered_pages.values():
                page.apply_keybindings({action: new_bindings})


class KeybindPage:
    def __init__(self, widget: QWidget):
        self.widget = widget
        self.shortcuts: Dict[str, List[QShortcut]] = {}
        self.bindings: Dict[str, Optional[BindTarget]] = {}

    def register_binding(
        self, action: str, target: Optional[BindTarget] = None, use_alt: bool = False
    ):
        """Register a button or function to be bound to a specific key action"""
        if use_alt:
            # For Alt-modified bindings, store with modifier flag
            self.bindings[f"{action}_alt"] = target
        else:
            self.bindings[action] = target

    def apply_keybindings(self, bindings: Dict[str, List[KeyBinding]]):
        """Apply keybindings to this page's buttons or functions"""
        # Clear existing shortcuts for the actions we're updating
        for action in bindings:
            if action in self.shortcuts:
                for shortcut in self.shortcuts[action]:
                    shortcut.setEnabled(False)
                    shortcut.deleteLater()
                del self.shortcuts[action]

        for action, key_bindings in bindings.items():
            if action not in self.bindings or self.bindings[action] is None:
                continue

            target = self.bindings[action]
            self.shortcuts[action] = []

            for binding in key_bindings:
                if binding.key is None:
                    continue

                def create_handler(target: BindTarget):
                    if isinstance(target, QPushButton):

                        def handler():
                            try:
                                if target.isEnabled():
                                    target.click()
                            except RuntimeError:
                                # Widget was deleted between shortcut creation and activation
                                pass
                    else:  # Callable
                        handler = target
                    return handler

                # Create key sequence with modifiers
                key_sequence = self._create_key_sequence(binding)
                shortcut = QShortcut(key_sequence, self.widget)
                shortcut.activated.connect(create_handler(target))
                self.shortcuts[action].append(shortcut)

    def _create_key_sequence(self, binding: KeyBinding) -> QKeySequence:
        """Create a QKeySequence from a KeyBinding"""
        # Combine modifiers with the key
        key = binding.key
        if binding.modifiers:
            modifier_str = "+".join(mod.name for mod in binding.modifiers)
            return QKeySequence(f"{modifier_str}+{key}")
        return QKeySequence(key)

    def remove_keybinding(self, action: str):
        """Remove a specific keybinding"""
        if action in self.shortcuts:
            for shortcut in self.shortcuts[action]:
                shortcut.setEnabled(False)
                shortcut.deleteLater()
            del self.shortcuts[action]
        # Also remove the stale target reference
        if action in self.bindings:
            del self.bindings[action]

    def _clear_shortcuts(self):
        """Clear all shortcuts"""
        for shortcuts in self.shortcuts.values():
            for shortcut in shortcuts:
                shortcut.setEnabled(False)
                shortcut.deleteLater()
        self.shortcuts.clear()
