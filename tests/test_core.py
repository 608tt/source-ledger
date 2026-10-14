import json
import tempfile
import unittest
from pathlib import Path
from source_ledger import core
from source_ledger.export import render
from source_ledger.__main__ import main


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = core.connect(self.root / "vault")

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def write(self, rows, name="input.jsonl"):
        path = self.root / name
        path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
        return path

    def record(self, **extra):
        return {"id": "1", "kind": "chat", "source": "demo", "text": "Hello 项目知识库", **extra}

    def test_repeat_import_and_move_are_idempotent(self):
        row = self.record()
        del row["id"]
        core.import_records(self.db, self.write([row]))
        result = core.import_records(self.db, self.write([row], "moved.jsonl"))
        self.assertEqual(result["unchanged"], 1)

    def test_repeated_messages_with_different_ids_are_preserved(self):
        core.import_records(self.db, self.write([self.record(id="1"), self.record(id="2")]))
        self.assertEqual(core.status(self.db)["documents"], 2)

    def test_update_invalidates_review(self):
        path = self.write([self.record()])
        core.import_records(self.db, path)
        chunk = core.search(self.db, "项目")[0]
        core.review(self.db, chunk["id"], "Read and checked")
        self.assertEqual(core.status(self.db)["reviewed_chunks"], 1)
        core.import_records(self.db, self.write([self.record(text="Changed 项目")]))
        self.assertEqual(core.status(self.db)["reviewed_chunks"], 0)
        self.assertNotEqual(core.search(self.db, "项目")[0]["sha256"], chunk["sha256"])

    def test_invalid_batch_is_atomic(self):
        with self.assertRaises(ValueError):
            core.import_records(self.db, self.write([self.record(), self.record(id="2", text=None)]))
        self.assertEqual(core.status(self.db)["documents"], 0)

    def test_search_is_literal_and_supports_chinese(self):
        core.import_records(self.db, self.write([self.record()]))
        self.assertEqual(len(core.search(self.db, "hello 项目")), 1)
        self.assertEqual(core.search(self.db, "' OR 1=1 --"), [])
        self.assertEqual(core.search(self.db, "项目", source="unknown"), [])
        with self.assertRaises(ValueError):
            core.search(self.db, " ")

    def test_chunk_offsets_and_overlap(self):
        text = "abcdefghij" * 30
        core.import_records(self.db, self.write([self.record(text=text)]), chunk_size=100, overlap=20)
        rows = core.search(self.db, "abc")
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertEqual(row["body"], text[row["start"]:row["end"]])

    def test_exports_escape_html_and_unsafe_links(self):
        core.import_records(self.db, self.write([self.record(text="<script>alert(1)</script>", url="javascript:alert(1)")]))
        result = core.search(self.db, "script")
        page = render(result, core.status(self.db), "html")
        self.assertNotIn("<script>", page)
        self.assertNotIn("javascript:", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn("<script>", render(result, core.status(self.db), "markdown"))
        self.assertNotIn(str(self.root), render(result, core.status(self.db), "json"))

    def test_review_requires_known_id_and_note(self):
        with self.assertRaises(ValueError):
            core.review(self.db, "missing", "reviewed")
        with self.assertRaises(ValueError):
            core.review(self.db, "missing", " ")

    def test_identity_components_cannot_collide(self):
        core.import_records(self.db, self.write([
            self.record(source="a:b", id="c"), self.record(source="a", id="b:c")]))
        self.assertEqual(core.status(self.db)["documents"], 2)

    def test_fallback_identity_does_not_join_ambiguous_metadata(self):
        rows = [self.record(title="a:b", date="c"), self.record(title="a", date="b:c")]
        for row in rows:
            del row["id"]
        core.import_records(self.db, self.write(rows))
        self.assertEqual(core.status(self.db)["documents"], 2)

    def test_stale_chunk_id_cannot_review_revised_content(self):
        core.import_records(self.db, self.write([self.record()]))
        old = core.search(self.db, "项目")[0]
        core.import_records(self.db, self.write([self.record(text="A revised 项目")]))
        new = core.search(self.db, "项目")[0]
        self.assertNotEqual(old["id"], new["id"])
        with self.assertRaises(ValueError):
            core.review(self.db, old["id"], "Review of old content")
        self.assertEqual(core.status(self.db)["reviewed_chunks"], 0)

    def test_metadata_update_preserves_body_review(self):
        core.import_records(self.db, self.write([self.record(title="Before")]))
        chunk = core.search(self.db, "项目")[0]
        core.review(self.db, chunk["id"], "Checked the body")
        result = core.import_records(self.db, self.write([self.record(title="After", date="2026-10-12")]))
        updated = core.search(self.db, "项目")[0]
        self.assertEqual(result["metadata_updated"], 1)
        self.assertEqual(updated["title"], "After")
        self.assertEqual(updated["date"], "2026-10-12")
        self.assertEqual(updated["id"], chunk["id"])
        self.assertEqual(core.status(self.db)["reviewed_chunks"], 1)

    def test_verification_page_and_unsupported_file(self):
        with self.assertRaises(ValueError):
            core.import_records(self.db, self.write([self.record(kind="article", text="环境异常，完成验证后即可继续访问")]))
        path = self.root / "unsupported.csv"
        path.write_text("content\nhello")
        with self.assertRaises(ValueError):
            core.import_records(self.db, path)

    def test_cli_errors_are_structured(self):
        self.assertEqual(main(["--root", str(self.root / "cli"), "search", " "]), 2)


if __name__ == "__main__":
    unittest.main()
