from enum import Enum
from typing import List, Optional
import json


class OperationType(str, Enum):
    ADD = "add"
    REMOVE = "remove"
    REPLACE = "replace"
    SORT = "sort"

    @classmethod
    def display_names(cls) -> dict:
        return {
            cls.ADD: "Add Tags",
            cls.REMOVE: "Remove Tags",
            cls.REPLACE: "Replace Tags (Regex)",
            cls.SORT: "Sort into Subdirectory",
        }

    @property
    def display_name(self) -> str:
        return self.display_names()[self]


class ExportTagRule:
    """Represents a rule for modifying tags or sorting during export based on conditions"""

    def __init__(
        self,
        rule_id: int = -1,
        project_id: int = -1,
        name: str = "",
        condition: str = "",
        tags_to_add: Optional[List[str]] = None,
        enabled: bool = True,
        operation_type: str = "add",
        operation_data: Optional[dict] = None,
        order: int = 0,
    ):
        self.id = rule_id
        self.project_id = project_id
        self.name = name
        self.condition = condition
        self.tags_to_add = tags_to_add or []
        self.enabled = enabled
        self.operation_type = OperationType(operation_type)
        self.operation_data = operation_data or {}
        self.order = order

    # --- Convenience accessors for operation_data fields ---

    @property
    def search_pattern(self) -> str:
        """Regex pattern for replace operations."""
        return self.operation_data.get("search_pattern", "")

    @search_pattern.setter
    def search_pattern(self, value: str):
        self.operation_data["search_pattern"] = value

    @property
    def subdirectory(self) -> str:
        """Target subdirectory for sort operations."""
        return self.operation_data.get("subdirectory", "")

    @subdirectory.setter
    def subdirectory(self, value: str):
        self.operation_data["subdirectory"] = value

    @property
    def position(self) -> str:
        """Tag insertion position for add operations: 'start' or 'end'."""
        return self.operation_data.get("position", "end")

    @position.setter
    def position(self, value: str):
        self.operation_data["position"] = value

    def __repr__(self):
        return (
            f"ExportTagRule(id={self.id}, name='{self.name}', "
            f"op={self.operation_type.value}, condition='{self.condition}', "
            f"tags={self.tags_to_add}, data={self.operation_data}, enabled={self.enabled})"
        )