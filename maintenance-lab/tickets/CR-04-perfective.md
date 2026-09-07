# CR-04 — Exact title lookup is a linear scan on every add, remove and edit

| Field | Value |
|---|---|
| **Ticket** | CR-04 |
| **Category** | Perfective maintenance |
| **Severity** | N/A — nothing is broken |
| **Reported** | 2026-09-08, from benchmarking |
| **Component** | `models/library.py` |
| **Branch** | `perfective/indexed-sql-search` |

## Problem statement

Nothing here is a defect. Three operations that already work correctly do more
work than they need to:

- `add_book` built a list of every lower-cased title, then searched that list,
  allocating N strings on every single add.
- `remove_book` and `edit_book` walked the whole list comparing lower-cased
  titles.
- `search_book` re-computed `name_book.lower()` on **every iteration**, twice
  per book, in addition to folding each title and author.

## Investigation

The original proposal was to replace the in-memory scan with an **indexed SQL
query**. That proposal was benchmarked before being implemented, and the
measurements rejected it.

Dataset: 50,001 books, best-of-5, wall clock.

| Strategy | Time | SQLite query plan |
|---|---:|---|
| `load_from_db` (startup) | 82.66 ms | 50,001 objects materialised |
| memory-scan substring (current) | 13.45 ms | — |
| SQL substring, no index | 10.70 ms | `SCAN books` |
| SQL substring, **with index** | 10.37 ms | `SCAN books` |
| SQL prefix, with index | 0.26 ms | `SEARCH books USING INDEX` |

**The index does nothing for the search we actually ship.** SQLite can only use
an index for a `LIKE` pattern anchored at the left; `'%term%'` forces a full
scan. Switching to prefix matching would be 40x faster but is a behaviour
regression: `search Orwell` must keep matching `George Orwell`, and
`LIKE 'Orwell%'` does not.

Exact lookup was then measured separately, because unlike substring search it
*can* use an index:

| Strategy | Time |
|---|---:|
| memory-scan exact | 4.11 ms |
| SQL exact, no index | 5.12 ms |
| SQL exact, with index | 0.23 ms |
| **in-memory dict index** | **0.0003 ms** |

An in-memory dict beats indexed SQL by roughly 770x, because it avoids the
round trip entirely.

## Decision

The originally proposed design was abandoned on the evidence:

- **No SQLite index.** It cannot serve the substring search, and the dict beats
  it for exact lookup. Adding it would be unused weight that still costs write
  time on every insert.
- **No DB-backed search.** A 13.45 → 10.70 ms gain does not justify making
  search results inconsistent with the in-memory list that `show` and `stats`
  read from.
- **Ship a dict index** keyed on the folded title, for the exact-lookup path.
- **Hoist the needle** out of the search loop — free, and changes nothing.

## Results

cProfile, 200 repetitions, 50,001 books. Absolute times are inflated by
profiler instrumentation; the ratios are the meaningful figures.

| Path | Before | After | Speedup |
|---|---:|---:|---:|
| duplicate check (`add_book`) | 19.87 ms | 0.0030 ms | **6,722x** |
| exact lookup (`remove`/`edit`) | 37.37 ms | 0.0030 ms | **12,445x** |
| substring search | 70.53 ms | 39.82 ms | 1.8x |

Wall clock without the profiler:

| Path | Before | After | Speedup |
|---|---:|---:|---:|
| substring search | 12.730 ms | 8.580 ms | 1.48x |
| exact lookup | 6.399 ms | 0.0003 ms | ~21,000x |

## Risk introduced

The dict is a cache, and a cache that drifts is worse than none. The dangerous
case is retitling: if the old key is left behind, a book stays findable under a
name it no longer has, and `remove_book` would then issue a `DELETE` whose
`WHERE title = ?` matches nothing — a silent no-op.

`tests/test_perfective_cr04.py` pins the invariant that `_by_title` always
agrees with `books`, after load, add, declined add, remove, declined remove,
retitle, and non-title edit.

## Acceptance criteria

1. All 25 characterisation tests pass unchanged. — **25 passed**
2. Index invariant holds after every mutation. — **11 new tests, all pass**
3. Substring search semantics unchanged. — **covered by both suites**
4. Measured improvement on the exact-lookup path. — **~21,000x wall clock**
