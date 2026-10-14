# Validation — 2026-10-12

Python 3.14.7, macOS. `python -m unittest discover -s tests -v`: **14 passed**.
With the optional MCP extra installed: **20 passed**. Six adapter tests verify
read-only tool discovery, provenance, bounded excerpts, tool errors, write
rejection and a real stdio subprocess using official SDK 2.3.0.

Core tests include whole-file validation, moved-file deduplication, stable source
identity, content revision invalidation, stale chunk ID rejection, metadata-only
updates, chunk offsets, Chinese search, escaping and CLI errors.

Built a wheel and installed it into a fresh virtual environment. From a directory
outside the checkout, the installed `source-ledger` command imported synthetic
JSONL, searched Chinese text and exported a standalone HTML report successfully.
The browser screenshot was captured from the generated report. The installed
`source-ledger-mcp` executable also returned two excerpts and unchanged review
coverage over real stdio from outside the checkout.

The CI matrix targets Python 3.12/3.13; those runs are not yet verified. There is
no semantic search, encryption or corpus-scale performance claim in this release.
