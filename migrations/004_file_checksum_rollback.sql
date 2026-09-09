-- Rollback for Migration 004
ALTER TABLE staff_document DROP COLUMN sha256;

DELETE FROM schema_version WHERE version = 4;
