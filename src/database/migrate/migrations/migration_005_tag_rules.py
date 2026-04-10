"""
Migration 5: Extend export_tag_rules with operation_type and operation_data columns.

Adds support for: add, remove, replace, sort operations.
Migrates existing rules to explicitly have operation_type='add'.
"""


def create_export_rule_operations_migration() -> str:
    return """
        ALTER TABLE export_tag_rules ADD COLUMN operation_type TEXT NOT NULL DEFAULT 'add';
        ALTER TABLE export_tag_rules ADD COLUMN operation_data TEXT DEFAULT '{}';
    """