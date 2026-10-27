-- This migration runs once through Flyway, so MySQL does not need conditional
-- DDL.  MySQL 8.3 rejects the multi-clause ADD COLUMN IF NOT EXISTS form.
ALTER TABLE `alert`
    ADD COLUMN `device_id` BIGINT NULL,
    ADD COLUMN `alert_type` VARCHAR(64) NOT NULL DEFAULT 'THRESHOLD',
    ADD COLUMN `deduplication_key` VARCHAR(255) NULL;

CREATE INDEX `idx_alert_deduplication_created`
    ON `alert` (`deduplication_key`, `created_at`);
