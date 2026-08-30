# igniteiq-sdk-python — Agent Notes

> `CLAUDE.md` in this repo is a symlink to this file. Checked in — shared with cloud sessions, CI agents, and teammates.

## Overview

Python SDK — `igniteiq-vault` on PyPI. Wraps the Vault API (`igniteiq-vault`) so an LLM agent can query home-services business data in a few lines. Optional LangChain / LlamaIndex integrations.

Python ≥ 3.10, packaged with `hatchling`. Core dependency: `httpx`. Source in `igniteiq/`.

## ⚠️ This is published to PyPI

Anything merged and released is public and permanent — a bad release can't be unpublished, only superseded. **Publishing is manual and deliberately stays manual**: `.github/workflows/ci.yml` has no release job, so a merge cannot become a public release by accident. CI reports whether what we *would* publish is sound; it does not publish it.

The corollary bites: a fix merged here reaches nobody. Between 2026-08-30 and the next release, `master` is correct and PyPI still serves a 0.2.0 that fails to import on the floor it advertises.

## Common commands

```bash
pip install -e ".[langchain,llamaindex]"   # editable install with extras
python -m build                             # build sdist/wheel
```

## Conventions

- **Keep the core dependency-light — `httpx` only.** LangChain / LlamaIndex integrations stay behind optional extras. A heavy required dependency in a client library is a tax on every consumer.
- **Public API mirrors `igniteiq-sdk-typescript`** where reasonable — same Vault API, parallel SDKs. Divergence between the two is a bug unless deliberate, and a change to one should note whether the other needs it.
- Bump `version` in `pyproject.toml` on release-worthy changes.
- README code samples must stay in sync with the actual public API — they're the first thing consumers copy.

## Gotchas

- **Vault measures bind by name.** If a cube measure is renamed or redefined in `igniteiq-vault`, working SDK code breaks at runtime with no compile-time signal. When a Vault change lands, check whether documented examples still resolve.
- Auth is by API key against the Vault API. Never bake a key into examples, tests, or fixtures — use env vars and placeholders.

## Do not

- Don't add heavy or required dependencies to core `dependencies` — use `optional-dependencies`.
- Don't make a breaking API change without a version bump that reflects it.
- Don't let the two SDKs' public surfaces drift silently.
- Never commit a real API key or customer identifier.

## Python version support — the floor is 3.10, and it used to be a lie

`pyproject` declares `requires-python = ">=3.10"`, raised from `>=3.9` on 2026-08-30. The
old floor was never true, and not in a marginal way — **neither published release could be
imported on 3.9 at all**:

| release | `errors.py` has `from __future__ import annotations` | imports on 3.9 |
|---|---|---|
| 0.1.0 | no | no |
| 0.2.0 | no | no |

`errors.py` evaluates `int | None` at runtime, which is PEP 604 syntax that needs 3.10.
`client.py`, `langchain.py` and `llamaindex.py` all carried the `__future__` import, so
their unions were harmless; `errors.py` was the single module missing it, and `igniteiq`
imports it eagerly. Every 3.9 user got
`TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`.

**Why the floor was raised instead of the bug being patched forward.** Both were possible —
the one-line `__future__` import is already in `master`. But nothing else about `>=3.9`
survived contact:

- The `llamaindex` extra cannot work on 3.9 regardless. `llama-index-core` pulls in `banks`,
  whose `config.py` evaluates `Path | None` in a class body. That is upstream and unfixable
  from here — and `banks` advertises `requires-python >=3.9`, so pip installs it happily and
  the failure lands at import time.
- Current `llama-index-core` and `langchain-core` both declare `>=3.10` themselves. A 3.9
  user asking for either extra resolves to years-old versions.
- 3.9 reached end of life in October 2025.

So `>=3.9` promised a configuration that has never existed and has no upstream path back.
Raising the floor makes the metadata describe the package.

⚠️ **Raising the floor does not protect anyone already on 3.9.** PyPI still serves 0.2.0 and
0.1.0 with `requires-python >=3.9`; pip on 3.9 will keep resolving to them and keep failing
at import. The floor only governs versions published *after* it lands. Making 3.9 fail
cleanly — "no matching distribution" rather than a `TypeError` — means yanking both existing
releases, which is a separate decision and has not been taken.

🔑 **The low end of the CI matrix must equal `requires-python`, and that is now checked
rather than remembered.** `scripts/check_python_floor.py` compares the two and fails the
build when they disagree — including when it cannot compare them at all, since "no matrix
found" is the shape the original rot took. It ships with `--self-test`, so a clean run means
the rule ran and passed rather than quietly stopped working (ADR 0001).

`from __future__ import annotations` is no longer load-bearing at 3.10 — PEP 604 evaluates
natively — but it stays in every module for consistency, and its absence is the defect above.
