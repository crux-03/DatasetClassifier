from sqlite3 import Connection
from typing import List
import json

from src.tagging.export_tag_rule import ExportTagRule


class ExportTagRuleQueries:
    """Database queries for managing export tag rules"""

    def __init__(self, db: Connection):
        self.db = db

    def get_project_rules(self, project_id: int) -> List:
        """Get all export tag rules for a project, ordered by rule_order."""
        cursor = self.db.cursor()

        cursor.execute(
            """
            SELECT rule_id, project_id, rule_name, condition, tags_to_add,
                   enabled, operation_type, operation_data, rule_order
            FROM export_tag_rules
            WHERE project_id = ?
            ORDER BY rule_order, rule_id
            """,
            (project_id,),
        )

        rules = []
        for row in cursor.fetchall():
            (
                rule_id, proj_id, name, condition, tags_json,
                enabled, operation_type, operation_data_json, rule_order,
            ) = row

            tags_to_add = json.loads(tags_json)
            operation_data = json.loads(operation_data_json) if operation_data_json else {}

            rule = ExportTagRule(
                rule_id=rule_id,
                project_id=proj_id,
                name=name,
                condition=condition,
                tags_to_add=tags_to_add,
                enabled=bool(enabled),
                operation_type=operation_type or "add",
                operation_data=operation_data,
                order=rule_order or 0,
            )
            rules.append(rule)

        cursor.close()
        return rules

    def add_rule(self, rule) -> int:
        """Add a new export tag rule. Appends to end of order. Returns the new rule ID."""
        cursor = self.db.cursor()

        # Get the next order value
        cursor.execute(
            "SELECT COALESCE(MAX(rule_order), -1) + 1 FROM export_tag_rules WHERE project_id = ?",
            (rule.project_id,),
        )
        next_order = cursor.fetchone()[0]

        tags_json = json.dumps(rule.tags_to_add)
        operation_data_json = json.dumps(rule.operation_data)

        cursor.execute(
            """
            INSERT INTO export_tag_rules
                (project_id, rule_name, condition, tags_to_add, enabled,
                 operation_type, operation_data, rule_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rule.project_id, rule.name, rule.condition, tags_json,
                int(rule.enabled), rule.operation_type.value, operation_data_json,
                next_order,
            ),
        )

        self.db.commit()
        rule_id = cursor.lastrowid
        rule.order = next_order
        cursor.close()
        return rule_id # type: ignore

    def update_rule(self, rule):
        """Update an existing export tag rule."""
        cursor = self.db.cursor()

        tags_json = json.dumps(rule.tags_to_add)
        operation_data_json = json.dumps(rule.operation_data)

        cursor.execute(
            """
            UPDATE export_tag_rules
            SET rule_name = ?,
                condition = ?,
                tags_to_add = ?,
                enabled = ?,
                operation_type = ?,
                operation_data = ?,
                rule_order = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE rule_id = ?
            """,
            (
                rule.name, rule.condition, tags_json, int(rule.enabled),
                rule.operation_type.value, operation_data_json, rule.order, rule.id,
            ),
        )

        self.db.commit()
        cursor.close()

    def swap_rule_order(self, rule_a_id: int, rule_a_order: int, rule_b_id: int, rule_b_order: int):
        """Swap the order of two rules atomically."""
        cursor = self.db.cursor()

        cursor.execute(
            "UPDATE export_tag_rules SET rule_order = ?, updated_at = CURRENT_TIMESTAMP WHERE rule_id = ?",
            (rule_b_order, rule_a_id),
        )
        cursor.execute(
            "UPDATE export_tag_rules SET rule_order = ?, updated_at = CURRENT_TIMESTAMP WHERE rule_id = ?",
            (rule_a_order, rule_b_id),
        )

        self.db.commit()
        cursor.close()

    def delete_rule(self, rule_id: int):
        """Delete an export tag rule."""
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM export_tag_rules WHERE rule_id = ?", (rule_id,))
        self.db.commit()
        cursor.close()

    def toggle_rule(self, rule_id: int, enabled: bool):
        """Enable or disable a rule."""
        cursor = self.db.cursor()
        cursor.execute(
            """
            UPDATE export_tag_rules
            SET enabled = ?, updated_at = CURRENT_TIMESTAMP
            WHERE rule_id = ?
            """,
            (int(enabled), rule_id),
        )
        self.db.commit()
        cursor.close()