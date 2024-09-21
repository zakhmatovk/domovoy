CREATE TABLE
    IF NOT EXISTS `test` (
        `name` Utf8,
        `applied_at` Datetime NOT NULL,
        `migration_code` Utf8 NOT NULL,
        `rollback_code` Utf8 NOT NULL,
        PRIMARY KEY (`name`)
    )