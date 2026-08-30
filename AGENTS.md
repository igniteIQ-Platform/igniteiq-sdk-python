# igniteiq-sdk-python — Agent Notes

> `CLAUDE.md` in this repo is a symlink to this file. Checked in — shared with cloud sessions, CI agents, and teammates.

## Overview

Python SDK — `igniteiq-vault` on PyPI. Wraps the Vault API (`igniteiq-vault`) so an LLM agent can query home-services business data in a few lines. Optional LangChain / LlamaIndex integrations.

Python ≥ 3.9, packaged with `hatchling`. Core dependency: `httpx`. Source in `igniteiq/`.

## ⚠️ This is published to PyPI

Anything merged and released is public and permanent — a bad release can't be unpublished, only superseded. There is no CI in this repo, so there is **no automated gate between an edit and a release**; care substitutes for tooling here.

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

## Python version support — the base and the extras differ

`pyproject` declares `requires-python = ">=3.9"` and the base package honours it (CI tests
3.9 and 3.12). **The `llamaindex` extra does not work on 3.9**, and the cause is upstream:
`llama-index-core` pulls in `banks`, whose `config.py` evaluates `Path | None` in a class
body — PEP 604 syntax that only works from 3.10. `pyproject` cannot express a per-extra
Python floor, so CI tests the extras on 3.12 only and this note is the record.

🔑 **`from __future__ import annotations` is load-bearing in every module that uses
`X | None`.** It defers annotations to strings so PEP 604 unions are never evaluated at
runtime. `errors.py` was missing it, which made the PUBLISHED 0.2.0 fail on import for every
3.9 user with `TypeError: unsupported operand type(s) for |`. Eleven such unions in
`client.py` were harmless purely because that file had the import. Fixed 2026-08-30 — and it
needs a release to reach anyone.
