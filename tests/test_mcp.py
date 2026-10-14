import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from source_ledger import core
from source_ledger.mcp_server import readonly

HAS_MCP = importlib.util.find_spec("mcp") is not None


@unittest.skipUnless(HAS_MCP, 'Optional tests require pip install ".[mcp]"')
class MCPTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from source_ledger.mcp_server import create_server
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.vault = self.root / "vault"
        path = self.root / "demo.jsonl"
        path.write_text(json.dumps({"id": "one", "kind": "note", "source": "Synthetic journal",
                                   "title": "Demo", "text": "review 项目 " + "x" * 12000}), encoding="utf-8")
        with closing(core.connect(self.vault)) as db:
            core.import_records(db, path, chunk_size=15000)
        self.server = create_server(self.vault)

    def tearDown(self):
        self.temp.cleanup()

    async def test_only_three_readonly_tools_are_advertised(self):
        from mcp import Client
        async with Client(self.server) as client:
            tools = (await client.list_tools()).tools
            self.assertEqual({t.name for t in tools}, {"search_sources", "read_excerpt", "get_coverage"})
            self.assertTrue(all(t.annotations.read_only_hint for t in tools))

    async def test_search_and_read_keep_provenance_without_marking_review(self):
        from mcp import Client
        async with Client(self.server) as client:
            result = (await client.call_tool("search_sources", {"query": "项目"})).structured_content
            row = result["matches"][0]
            self.assertEqual(row["source"], "Synthetic journal")
            self.assertIn("sha256", row)
            self.assertNotIn(str(self.root), json.dumps(result))
            full = (await client.call_tool("read_excerpt", {"chunk_id": row["id"]})).structured_content
            self.assertEqual(full["id"], row["id"])
            coverage = (await client.call_tool("get_coverage", {})).structured_content
            self.assertEqual(coverage["reviewed_chunks"], 0)
            self.assertIsNone(coverage["source_history_complete"])

    async def test_results_are_bounded_and_offsets_describe_returned_text(self):
        from mcp import Client
        async with Client(self.server) as client:
            row = (await client.call_tool("search_sources", {"query": "review"})).structured_content["matches"][0]
            self.assertEqual(len(row["body"]), 2000)
            self.assertTrue(row["truncated"])
            self.assertEqual(row["excerpt_end"] - row["start"], len(row["body"]))
            full = (await client.call_tool("read_excerpt", {"chunk_id": row["id"]})).structured_content
            self.assertEqual(len(full["body"]), 8000)
            self.assertTrue(full["truncated"])

    async def test_bad_queries_limits_and_ids_return_tool_errors(self):
        from mcp import Client
        async with Client(self.server) as client:
            for name, args in [("search_sources", {"query": " "}),
                               ("search_sources", {"query": "review", "limit": 21}),
                               ("read_excerpt", {"chunk_id": "unknown"})]:
                result = await client.call_tool(name, args)
                self.assertTrue(result.is_error)
                self.assertNotIn(str(self.root), str(result.content))

    async def test_real_stdio_transport_can_search(self):
        from mcp import Client, StdioServerParameters
        transport = StdioServerParameters(command=sys.executable,
            args=["-m", "source_ledger.mcp_server", "--root", str(self.vault)],
            cwd=Path(__file__).resolve().parents[1])
        async with Client(transport, read_timeout_seconds=15) as client:
            result = await client.call_tool("search_sources", {"query": "项目"})
            self.assertEqual(len(result.structured_content["matches"]), 1)

    def test_database_rejects_writes_and_missing_vault_is_not_created(self):
        with closing(readonly(self.vault)) as db:
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("DELETE FROM chunks")
        missing = self.root / "missing"
        with self.assertRaises(ValueError):
            readonly(missing)
        self.assertFalse(missing.exists())
