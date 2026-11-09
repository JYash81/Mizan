# Identity database schema

Revision `20261108_0002` adds `users`, `auth_sessions`, `auth_tokens`, and `audit_events`. Public IDs are UUID strings (`String(36)`), portable across SQLite and MySQL/MariaDB. Timestamps use timezone-aware SQLAlchemy `DateTime`; SQLite stores them without native timezone semantics, while application code must use UTC.

`users.normalized_email`, `auth_sessions.session_token_hash`, and `auth_tokens.token_hash` are unique and indexed. Sessions and tokens reference users through foreign keys. Token purpose is a portable non-native enum with a check constraint. JSON audit metadata is portable to SQLite and MySQL JSON-capable versions; the model rejects credential-shaped top-level keys.

SQLite migration behavior has been verified. MySQL/MariaDB migration execution has not been tested because no test server is configured.
