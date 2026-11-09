# Password security

Mizan uses `argon2-cffi` Argon2id (`Type.ID`) with fresh library-generated salts. Defaults are time cost 2, memory cost 19,456 KiB, parallelism 1, hash length 32 bytes, and salt length 16 bytes. Backend-only settings can increase, but cannot reduce, those minimums.

Passwords must be 12–128 characters and at most 1,024 UTF-8 bytes. Unicode and whitespace are preserved. No composition rules or automatic trimming apply. Verification safely returns `False` for mismatches and malformed hashes. `needs_rehash` supports a future successful-login rehash flow; login and public APIs are deferred.
