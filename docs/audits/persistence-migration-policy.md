# SQLite migration and recovery policy

Migrations are forward-only and run one version at a time inside a SQLite transaction. The application refuses to open a database whose recorded schema is newer than its bundled migrations. No destructive downgrade or automatic rollback script is provided.

Before applying a new migration to an existing database, create a SQLite online backup and confirm it opens with `PRAGMA integrity_check`. Use SQLite's backup API (`Connection.backup`) while connected; do not copy only the main database file while WAL mode may be active. Preserve the backup until the app has opened the migrated database and a follow-up integrity check succeeds.

If a migration fails, its transaction is rolled back. Keep the original database and backup, capture the migration version and safe error, then restore the backup with the SQLite backup API. Never drop or recreate the user's catalog as a recovery shortcut. For a fresh database, a failed migration may be retried after the code or migration is repaired.

The tests in `tests/data/test_security_boundaries.py` exercise failed-migration rollback, online backup/restore, and refusal of a future schema version. The current migration set is version 1; no upgrade path from a previously released application schema has been qualified.
