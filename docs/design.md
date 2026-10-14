# Design and limits

The store separates immutable source identity from content hashes and mutable
review markers. A changed stable record cannot silently keep a mark attached to
old text. Chunk IDs include the body hash; old IDs are rejected after a content
revision. Metadata-only changes preserve the reviewed body. Review coverage
describes only chunks currently present in the vault.

The core CLI uses no background service or outbound network requests.
The optional MCP adapter is a read-only local stdio process; the connected
AI host may transmit returned excerpts to its model provider. Search is literal,
parameterized and bounded to at most 100 result chunks. This choice keeps
installation small and makes behavior inspectable. It is a linear substring
scan rather than a semantic index or a benchmarked large-corpus search engine.

HTML exports escape titles and excerpts and only link HTTP(S) source URLs;
there are no embedded scripts. Exported snippets do not include local input
file paths. Markdown preserves source text in blockquotes; treat it as untrusted
content when sharing it with other tools. Every export may contain private
material if you imported it; synthetic examples are used in this repository.

Limits: no deletion synchronization, OCR, PDF extraction, website collection,
chat decryption, vector search or automatic answer generation. SQLite files are
not encrypted by the application. A review note is a user assertion, not proof
of comprehension, accuracy or complete historical coverage.

Future directions: explicit deletion/revision history, full-text indexing with
language-aware tokenization, optional retrieval adapters and import converters.
Each should preserve provenance and clear coverage accounting.
