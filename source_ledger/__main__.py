import argparse
import json
import sqlite3
from pathlib import Path
from . import core
from .export import render


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline source search with explicit review coverage")
    parser.add_argument("--root", type=Path, default=Path(".source-ledger"))
    commands = parser.add_subparsers(dest="command", required=True)
    imp = commands.add_parser("import")
    imp.add_argument("path", type=Path)
    imp.add_argument("--kind", choices=sorted(core.KINDS))
    imp.add_argument("--source")
    imp.add_argument("--chunk-size", type=int, default=1600)
    imp.add_argument("--overlap", type=int, default=120)
    commands.add_parser("status")
    for cmd in ["search", "export"]:
        sub = commands.add_parser(cmd)
        sub.add_argument("query")
        sub.add_argument("--source")
        sub.add_argument("--limit", type=int, default=20)
        if cmd == "export":
            sub.add_argument("--format", choices=["markdown", "json", "html"], default="markdown")
            sub.add_argument("--output", type=Path)
    sub = commands.add_parser("pending")
    sub.add_argument("--limit", type=int, default=10)
    sub = commands.add_parser("read")
    sub.add_argument("chunk_id")
    sub = commands.add_parser("review")
    sub.add_argument("chunk_id")
    sub.add_argument("--note", required=True)
    args = parser.parse_args(argv)
    db = None
    try:
        db = core.connect(args.root)
        if args.command == "import":
            result = core.import_records(db, args.path, args.kind, args.source, args.chunk_size, args.overlap)
        elif args.command == "status":
            result = core.status(db)
        elif args.command in {"search", "export"}:
            result = core.search(db, args.query, args.source, args.limit)
            if args.command == "export":
                content = render(result, core.status(db), args.format)
                if args.output:
                    args.output.write_text(content, encoding="utf-8")
                    print(json.dumps({"exported": str(args.output), "excerpts": len(result)}))
                else:
                    print(content)
                return 0
        elif args.command == "pending":
            result = core.pending(db, args.limit)
        elif args.command == "read":
            result = core.read(db, args.chunk_id)
        else:
            result = core.review(db, args.chunk_id, args.note)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, sqlite3.Error) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 2
    finally:
        if db is not None:
            db.close()


if __name__ == "__main__":
    raise SystemExit(main())
