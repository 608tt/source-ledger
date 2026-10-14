# Read-only MCP adapter

The optional adapter uses [the official Python SDK](https://github.com/modelcontextprotocol/python-sdk)
2.3.0. It provides three local tools and communicates over stdio, with no HTTP
listener. The dependency-free CLI remains available without this extra.

## Try it with synthetic sources

From a clone, use a dedicated environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install ".[mcp]"
source-ledger --root ./demo-vault import examples/demo.jsonl
source-ledger-mcp --root /absolute/path/to/source-ledger/demo-vault
```

The final command waits for an MCP host on stdin; silence is expected. It is
not an interactive text chat. Use the executable's full path in your host's
stdio-server configuration. For hosts that use an `mcpServers` JSON object:

```json
{
  "mcpServers": {
    "source-ledger": {
      "command": "/absolute/path/to/source-ledger/.venv/bin/source-ledger-mcp",
      "args": ["--root", "/absolute/path/to/source-ledger/demo-vault"]
    }
  }
}
```

Replace both paths with your own. On Windows the executable is under
`.venv/Scripts/source-ledger-mcp.exe`. Client configuration formats differ;
follow your host's stdio-server instructions rather than pasting this object
into every client. No client settings are modified by this repository.

Try asking the host: "Search my sources for review. Quote an excerpt with its
source and character range, then tell me what the coverage report can and
cannot establish."

## Tool contract

| Tool | Inputs | Output / boundary |
|---|---|---|
| `search_sources` | Literal query, optional exact source filter, limit 1–20 | Up to 2,000 characters per matching chunk, metadata, hash and ID |
| `read_excerpt` | Current chunk ID | Up to 8,000 characters; rejects unknown or stale IDs |
| `get_coverage` | None | Current import counts and human review marks; source completeness remains unknown |

`start` and `end` describe the full stored chunk. `excerpt_end` describes the
end of the returned text; `truncated` tells you whether text was omitted.
Offsets count Unicode code points in the trimmed document body. A result limit
can omit further matches and must not be presented as a full search census.

The server opens the chosen existing database in SQLite read-only mode. It does
not create a missing vault. Imports, edits and review notes stay in the CLI;
there is no model-call tool to mark material as reviewed. All three tools also
advertise read-only annotations, following [the SDK's tool interface](https://py.sdk.modelcontextprotocol.io/servers/tools/).

## Data handling

The server has no outbound requests, but the connected host can send returned
text to its model provider. Use a vault appropriate for that host. Source text
is untrusted quoted material, including any instructions embedded in it.
The adapter avoids returning local input paths and bounds responses; it does
not enforce an AI host's behavior or prove source truth.

Protocol tests use an in-memory client and an actual stdio child process.
SDK 2.3.0 was validated locally; individual desktop products and remote
transports have not been tested. See [validation](validation.md).
