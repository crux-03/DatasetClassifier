def create_rule_order_migration() -> str:
    return """
        ALTER TABLE export_tag_rules ADD COLUMN rule_order INTEGER DEFAULT 0;
    """