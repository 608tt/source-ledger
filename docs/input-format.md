# Input format

JSONL accepts UTF-8 with an optional BOM and blank lines. Each non-empty line
must be a JSON object. A malformed record rejects the entire file before any
records are committed.

| Field | Required | Meaning |
|---|---|---|
| `kind` | Yes, or `--kind` | `article`, `chat`, `note`, `transcript` |
| `source` | Yes, or `--source` | Non-empty source name |
| `text` | Yes | Non-empty content string |
| `id` | Recommended | Stable original identifier, unique within kind + source |
| `title` | No | Display title |
| `date` | No | ISO-style string; sorting is lexical |
| `url` | No | Original source URL; may also identify an article |

All supplied fields in the table are strings. Preserve original chat message IDs
to keep repeated identical messages separate. Without `id` or `url`, identity
comes from title/date/content; identical records deduplicate across moved files,
but edited text becomes a new record rather than replacing the old one.

For an unchanged stable record, the import skips re-chunking. Changed title,
date or URL metadata is refreshed while existing body review marks are kept.
For a changed stable record, the import replaces its text and chunks,
invalidating all prior review marks. Chunk IDs include a content-hash prefix,
so a stale ID cannot mark a different version as reviewed.
Changing chunk-size options alone does not re-chunk unchanged records.

Markdown/TXT imports create one record per file and require kind/source flags.
Body text is trimmed before hashing and chunking; offsets refer to that trimmed
body, count Unicode code points and use a half-open range `[start, end)`.

Default chunk size: 1,600 characters, overlap: 120. Override with
`--chunk-size` and `--overlap` on import. A query's terms must appear in the same
chunk. Very distant terms or long boundary-spanning phrases may be missed.
