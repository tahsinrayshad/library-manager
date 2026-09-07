# CR-02 — Database location depends on the working directory

| Field | Value |
|---|---|
| **Ticket** | CR-02 |
| **Category** | Adaptive maintenance |
| **Severity** | Medium — silent data divergence, no error raised |
| **Reported** | 2026-09-08, during environment analysis |
| **Component** | `db_connection.py`; project dependency manifest |
| **Branch** | `adaptive/configurable-db-path` |

## Problem statement

`Connection.DB_NAME` was the bare relative string `"library.db"`. `sqlite3`
resolves a relative filename against the **process working directory**, not the
project. Launching the application from anywhere other than the repository root
therefore silently created and used a *different, empty* database.

Reproduced before the change:

```
=== A. launched from the repository root ===
Loaded 1 books from database.
=== B. launched from ...\scratchpad\dbdemo ===
Loaded 0 books from database.
=== files now present in the unrelated directory ===
library.db   24576 bytes
```

No error, no warning. The user's catalogue simply appears to be empty.

A second, related environment defect: `readme.md` instructs the user to run
`pip install python-dotenv` and `.gitignore` lists `.env`, but **no module
imported `dotenv`**. The only real third-party dependency, `colorama`, was
documented nowhere. Following the documented setup produced an application
that could not start. The project had no dependency manifest at all — partly
because the `*.txt` rule in `.gitignore` is broad enough to exclude
`requirements.txt`.

## Rationale for classifying this as adaptive

Adaptive maintenance adjusts a system to a change in its environment rather
than repairing a logic error. The code is internally consistent; what it gets
wrong is an assumption about the environment it runs in — namely that the
working directory always equals the project directory. That assumption holds
when the program is started by `cd`-ing into the repository and holds nowhere
else: not from a desktop shortcut, a scheduled task, a shell alias, an IDE run
configuration with a different working directory, or a packaged entry point.

The change makes the deployment environment configurable rather than assumed,
and brings the declared dependency environment into line with the actual one.
It repairs no incorrect computation, so it is not corrective.

## Scope

**In scope**

- Anchor the database path to the project root via `Path(__file__)`.
- Introduce the `python-dotenv` configuration layer the documentation already
  promised, reading an optional `LIBRARY_DB_PATH`.
- Add `requirements.txt` declaring the dependencies that actually exist.
- Add `.env.example` documenting the setting.
- Narrow `.gitignore` so the manifest is not excluded; ignore `.venv/`.

**Out of scope**

- Migrating or merging stray databases already created in other directories.
- Any change to `Library`, `Book`, `main.py`, or the schema.

## Constraints derived from impact analysis

`impact.py attr DB_NAME` reports exactly **one** read site,
`db_connection.py:11`. `impact.py attr get_connection` reports **six** call
sites across all four modules. Because every caller funnels through the single
`DB_NAME` read, changing that one expression fixes all six without touching
them.

## Acceptance criteria

1. Launching from the repository root loads the existing catalogue.
2. Launching from an unrelated directory loads the *same* catalogue.
3. No stray `library.db` is created in the unrelated directory.
4. `LIBRARY_DB_PATH` relative → resolved against the project root.
5. `LIBRARY_DB_PATH` absolute → used verbatim.
6. A `.env` file is honoured; with none present, behaviour is unchanged.
7. `requirements.txt` is tracked by git despite the `*.txt` ignore rule.
