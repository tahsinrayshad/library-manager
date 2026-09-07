# CR-01 — Book titles and author names are stored in lower case

| Field | Value |
|---|---|
| **Ticket** | CR-01 |
| **Category** | Corrective maintenance |
| **Severity** | High — silent, irreversible data corruption |
| **Reported** | 2026-09-07, during baseline verification |
| **Component** | `main.py`, command dispatch loop |
| **Branch** | `corrective/preserve-input-case` |

## Problem statement

Every book added through the CLI has its title and author permanently folded to
lower case before being written to SQLite. A user who enters

```
add "The Great Gatsby" "F. Scott Fitzgerald" 1925
```

sees the record stored and displayed as

```
'the great gatsby' by f. scott fitzgerald (1925)
```

The corruption occurs at the point of entry, so it is not a display fault. The
original capitalisation is destroyed before the value reaches the `Book`
constructor and cannot be recovered by re-reading the row.

Reproduced in `maintenance-lab/logs/step0-smoke.log`.

## Root cause

`main.py:55` normalises the command line for case-insensitive dispatch:

```python
command = input("\nEnter command (or 'help' for options): ").strip().lower()
```

The intent — making `SHOW` and `show` equivalent — is correct. The scope is
not. `.lower()` is applied to the entire input line, including operands that
are user data rather than command syntax.

## Rationale for classifying this as corrective

The change repairs a divergence between required and actual behaviour. The
requirement is established by the project's own `readme.md`, whose worked
example shows capitalisation preserved in stored output. The fault pre-existed
this work, is reproducible on demand, and its repair adds no capability and
accommodates no environmental change.

## Scope

**In scope**

- `main.py`: separate the string used for dispatch from the string used for
  operand extraction.
- Structured logging on the changed path so future regressions are observable.

**Out of scope**

- Repairing rows already stored in lower case. The fix is not retroactive; a
  data migration would be a separate change request.
- The two-word `help` sub-commands must continue to work unchanged.
- No change to `Library`, `Book`, `Connection`, or the schema.

## Constraints derived from impact analysis

`impact.py name command` reports 20 usages, all within `main`. Fifteen are
dispatch comparisons that require the lower-cased string; four (lines 58, 91,
98, 105) extract operands and must not see it.

Lower-casing only the first token is **rejected** as a fix: lines 114, 120, 125
and 130 dispatch on the two-word commands `help add`, `help remove`,
`help search` and `help edit`, which that approach would break.

## Acceptance criteria

1. `add "The Great Gatsby" "F. Scott Fitzgerald" 1925` stores and displays the
   title and author with original capitalisation.
2. `SHOW`, `Show` and `show` all continue to list books.
3. `HELP ADD`, `Help Add` and `help add` all continue to display the add help.
4. `search`, `remove` and `edit` continue to match case-insensitively.
5. No change to any file other than `main.py`.
