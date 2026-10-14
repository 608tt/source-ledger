"""Adapted from the author's original local article/chat library."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

KINDS = {"article", "chat", "note", "transcript"}


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def connect(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(root / "library.sqlite")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS documents(
        id TEXT PRIMARY KEY, kind TEXT NOT NULL, source TEXT NOT NULL,
        title TEXT, date TEXT, url TEXT, path TEXT, sha256 TEXT NOT NULL, body TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS chunks(
        id TEXT PRIMARY KEY, document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,
        ordinal INTEGER, start INTEGER, end INTEGER, body TEXT,
        reviewed_at TEXT, note TEXT);
    CREATE INDEX IF NOT EXISTS chunks_doc ON chunks(document_id);
    """)
    return db


def import_records(db, path, kind=None, source=None, chunk_size=1600, overlap=120):
    path = Path(path)
    if chunk_size < 100 or not 0 <= overlap < chunk_size:
        raise ValueError("chunk_size must be >=100 and 0 <= overlap < chunk_size")
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".jsonl":
        records = []
        for line_no, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Line {line_no}: invalid JSON") from error
            if not isinstance(record, dict):
                raise ValueError(f"Line {line_no}: expected object")
            records.append(record)
    elif path.suffix.lower() in {".md", ".txt"}:
        records = [{"kind": kind, "source": source, "title": path.stem, "text": text}]
    else:
        raise ValueError("Expected JSONL, Markdown or TXT")
    prepared = []
    for record in records:
        k, s, body = record.get("kind") or kind, record.get("source") or source, record.get("text")
        if not isinstance(k, str) or k not in KINDS:
            raise ValueError("kind must be article, chat, note or transcript")
        if not isinstance(s, str) or not s.strip() or not isinstance(body, str) or not body.strip():
            raise ValueError("source and text must be non-empty strings")
        for field in ["id", "title", "date", "url"]:
            if field in record and not isinstance(record[field], str):
                raise ValueError(f"{field} must be a string")
        if k == "article" and "环境异常，完成验证后即可继续访问" in body:
            raise ValueError("A verification page is not article content")
        body, s = body.strip(), s.strip()
        sha = digest(body)
        identity = record.get("id") or record.get("url") or digest(json.dumps(
            [record.get("title", ""), record.get("date", ""), body], ensure_ascii=False))
        docid = digest(json.dumps([k, s, identity], ensure_ascii=False))[:24]
        prepared.append((docid, k, s, record.get("title", ""), record.get("date", ""),
                         record.get("url", ""), str(path.resolve()), sha, body))
    inserted = skipped = metadata_updated = 0
    with db:
        for row in prepared:
            docid, *_, sha, body = row
            old = db.execute("SELECT * FROM documents WHERE id=?", (docid,)).fetchone()
            if old and old["sha256"] == sha:
                # Metadata can change while the reviewed body stays identical.
                if tuple(old[field] for field in ("title", "date", "url")) != row[3:6]:
                    db.execute("UPDATE documents SET title=?,date=?,url=?,path=? WHERE id=?",
                               (*row[3:7], docid))
                    metadata_updated += 1
                skipped += 1
                continue
            db.execute("DELETE FROM documents WHERE id=?", (docid,))
            db.execute("INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?)", row)
            start = ordinal = 0
            while start < len(body):
                end = min(start + chunk_size, len(body))
                db.execute("INSERT INTO chunks VALUES(?,?,?,?,?,?,NULL,NULL)",
                           (f"{docid}:{sha[:16]}:{ordinal}", docid, ordinal, start, end, body[start:end]))
                ordinal += 1
                if end == len(body):
                    break
                start = end - overlap
            inserted += 1
    return {"imported_or_updated": inserted, "unchanged": skipped,
            "metadata_updated": metadata_updated}


def status(db):
    chunks = db.execute("SELECT count(*) FROM chunks").fetchone()[0]
    reviewed = db.execute("SELECT count(*) FROM chunks WHERE reviewed_at IS NOT NULL").fetchone()[0]
    return {"documents": db.execute("SELECT count(*) FROM documents").fetchone()[0],
            "chunks": chunks, "reviewed_chunks": reviewed,
            "reviewed_percent": round(reviewed / chunks * 100, 1) if chunks else 0.0,
            "source_history_complete": None,
            "coverage_note": "Review markers are user declarations. Import counts do not prove complete source history.",
            "sources": [dict(row) for row in db.execute(
                "SELECT kind,source,count(*) records FROM documents GROUP BY kind,source ORDER BY source")]}


def search(db, query, source=None, limit=20):
    terms = query.split()
    if not terms:
        raise ValueError("Search query must not be empty")
    where = ["instr(lower(c.body),lower(?))>0" for _ in terms]
    params = list(terms)
    if source:
        where.append("d.source=?")
        params.append(source)
    params.append(max(1, min(limit, 100)))
    return [dict(row) for row in db.execute("""SELECT c.id,c.start,c.end,c.body,
        c.reviewed_at,c.note,d.source,d.title,d.kind,d.date,d.url,d.sha256
        FROM chunks c JOIN documents d ON d.id=c.document_id WHERE """ +
        " AND ".join(where) + " ORDER BY d.date DESC,d.id,c.ordinal LIMIT ?", params)]


def pending(db, limit=10):
    return [dict(row) for row in db.execute("""SELECT c.id,d.source,d.title,length(c.body) chars
        FROM chunks c JOIN documents d ON d.id=c.document_id WHERE c.reviewed_at IS NULL
        ORDER BY d.source,d.id,c.ordinal LIMIT ?""", (max(1, min(limit, 100)),))]


def read(db, chunk_id):
    row = db.execute("""SELECT c.*,d.source,d.title,d.date,d.url,d.sha256 FROM chunks c
        JOIN documents d ON d.id=c.document_id WHERE c.id=?""", (chunk_id,)).fetchone()
    if not row:
        raise ValueError("Unknown chunk id")
    return dict(row)


def review(db, chunk_id, note):
    if not note.strip():
        raise ValueError("Review note must not be empty")
    with db:
        result = db.execute("UPDATE chunks SET reviewed_at=?,note=? WHERE id=?",
                            (datetime.now(timezone.utc).isoformat(), note.strip(), chunk_id))
        if result.rowcount != 1:
            raise ValueError("Unknown chunk id")
    return {"reviewed": chunk_id}
