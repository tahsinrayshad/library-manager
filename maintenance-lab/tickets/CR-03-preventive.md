# CR-03 — Harden database access: unbound cursor, interpolated SQL column, duplicated boilerplate

| Field | Value |
|---|---|
| **Ticket** | CR-03 |
| **Category** | Preventive maintenance |
| **Severity** | Low today, high latent |
| **Reported** | 2026-09-08, from clone-detection output during CR-01 |
| **Component** | `db_connection.py`, `models/book.py`, `models/library.py` |
| **Branch** | `preventive/harden-db-access` |

## Problem statement

Three related weaknesses, none of which produces a wrong answer today.

### 1. `finally` dereferences an unbound local

`models/library.py:125` closed the cursor in a `finally` block, but `cursor`
was bound *inside* the `try`. If `conn.cursor()` itself raised, the `finally`
clause raised `UnboundLocalError`, which **replaced** the genuine database
error and escaped the method's own `except Exception` handler.

Demonstrated by `tests/test_regression_cr03.py`, which fails on the unmodified
code:

```
Error updating database: database is locked        <- the real error, reported
models/library.py:125: UnboundLocalError: cannot access local variable 'cursor'
```

The user sees a Python traceback instead of a handled error message, and the
true cause is buried.

### 2. SQL column name built by f-string interpolation

`models/library.py:114` built its statement as:

```python
query = f"UPDATE books SET {check} = ? WHERE title = ? AND author = ? AND year = ?"
```

The *values* are correctly parameterised; the *column* is not. This is **not
exploitable today**, because the prompt loop above constrains `check` to
`title`/`author`/`year`, and a test confirms that. The objection is that the
safety guarantee lives in a loop twenty lines away from the SQL, rather than at
the point the SQL is built. Any future change to how `check` is obtained
silently converts this into an injection.

### 3. The same connection boilerplate in four places

`connect / cursor / execute / commit / finally: close()` was copy-pasted into
`Connection.init_database`, `Book.save_to_db`, `Library.remove_book`,
`Library.edit_book` and `Library.load_from_db`. `jscpd` reported it as the
project's only clone:

```
db_connection.py [18:23 - 24:32] (7 lines, 25 tokens)
models\library.py [144:26 - 149:32]
Files 4 | Lines 415 | Clones 1 | Duplicated 6 (1.45%)
```

Duplicated cleanup logic is how the same bug comes to exist in several places
at once — which is exactly what happened with weakness 1.

## Rationale for classifying this as preventive

Preventive maintenance reduces the probability of future faults without
changing behaviour that users can observe. None of the three weaknesses
produces an incorrect result in normal operation: the `finally` bug needs a
database failure to trigger, the SQL is currently constrained, and duplication
is invisible at runtime. Nothing here responds to an environment change, and no
capability is added. The measure of success is that **behaviour is provably
unchanged**, which is why a characterisation suite was written first.

## Scope

**In scope**

- A `Connection.cursor()` context manager owning connect / commit / cleanup.
- Bind `cur = None` before the `try` so `finally` can never dereference it.
- Replace f-string column interpolation with a fixed statement per column.
- A pytest suite: characterisation tests plus regression tests for CR-03.
- Structured logging at the new single choke point.

**Out of scope**

- The unused `users` table and its plain-text `password` column.
- The bare `except:` at `main.py:84`.
- Any behavioural change whatsoever.

## Acceptance criteria

1. All characterisation tests pass **before** the change (proving they describe
   current behaviour) and **after** it (proving behaviour is preserved).
2. `test_edit_book_does_not_raise_nameerror_when_cursor_fails` fails before and
   passes after.
3. `jscpd` reports zero clones in application code after the change.
4. The end-to-end CLI session behaves identically.

## Result

| Criterion | Outcome |
|---|---|
| Characterisation tests | 25 passed before, 25 passed after |
| Regression tests | 2 failed before, 2 passed after |
| Clone detection | 1 clone / 6 lines / 1.45% → **0 clones / 0 lines / 0.00%** |
| End-to-end CLI | Identical behaviour |
