-- Migration 004: Add SHA-256 checksum column to staff_document
-- Apply:   sqlite3 org_directory.db < 004_file_checksum.sql
-- Rollback: see 004_file_checksum_rollback.sql

ALTER TABLE staff_document ADD COLUMN sha256 TEXT;

INSERT INTO schema_version (version, description) VALUES
    (4, 'File integrity: SHA-256 checksum on staff_document');
