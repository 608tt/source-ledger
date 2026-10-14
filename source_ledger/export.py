"""Portable evidence excerpts; no network requests or embedded scripts."""
import html
import json
from urllib.parse import urlsplit


def render(results, coverage, format="markdown"):
    if format == "json":
        return json.dumps({"coverage": coverage, "results": results}, ensure_ascii=False, indent=2)
    if format == "html":
        esc = html.escape
        cards = []
        for row in results:
            url = row["url"]
            link = f'<a href="{esc(url, quote=True)}" rel="noreferrer">Original source</a>' if urlsplit(url).scheme in {"http", "https"} else ""
            cards.append(f'<article><div class="meta">{esc(row["source"])} · {esc(row["date"])}</div>'
                         f'<h2>{esc(row["title"])}</h2><pre>{esc(row["body"])}</pre>'
                         f'<footer>{esc(row["id"])} · chars {row["start"]}–{row["end"]} · '
                         f'{"Reviewed" if row["reviewed_at"] else "Awaiting review"} {link}</footer></article>')
        return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Source Ledger · Evidence bundle</title><style>
body{background:#f5f4ef;color:#19352d;font:16px/1.65 system-ui;margin:0}main{max-width:1000px;margin:50px auto;padding:0 24px}
.eyebrow{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#648278}h1{font-size:56px;line-height:1.1;margin:18px 0}
.stats{display:flex;gap:18px;margin:32px 0}.stats div{background:#19352d;color:#e4f5da;padding:18px 25px;border-radius:14px;flex:1}.stats strong{font-size:30px;display:block}
article{background:white;border:1px solid #dee5df;border-radius:16px;margin:18px 0;padding:26px}.meta,footer{font-size:12px;color:#648278}
h2{margin:6px 0 18px;font-size:24px}pre{white-space:pre-wrap;font:inherit}a{color:#23694e;margin-left:14px}
@media(max-width:600px){h1{font-size:38px}.stats{flex-direction:column}main{margin:25px auto}}</style><main>
<p class="eyebrow">Offline · Traceable · Reviewable</p><h1>Your sources.<br>Your evidence.</h1>
<p>Search excerpts with stable IDs, original source metadata and explicit review coverage.</p>''' + (
            f'<div class="stats"><div><strong>{coverage["documents"]}</strong>documents</div>'
            f'<div><strong>{len(results)}</strong>matched excerpts</div>'
            f'<div><strong>{coverage["reviewed_percent"]}%</strong>chunks marked reviewed</div></div>'
            f'<p class="meta">{esc(coverage["coverage_note"])}</p>') + "".join(cards) + "</main></html>"
    parts = ["# Source Ledger — Evidence bundle", "", coverage["coverage_note"], ""]
    def safe_meta(text):
        return html.escape(" ".join(text.splitlines()))
    for row in results:
        parts.extend([f'## {safe_meta(row["title"] or row["source"])}',
                      f'Source: {safe_meta(row["source"])} | Date: {safe_meta(row["date"])} | ID: `{row["id"]}`',
                      f'Characters: {row["start"]}–{row["end"]} | SHA-256: `{row["sha256"]}`',
                      "", *["> " + html.escape(line) for line in row["body"].splitlines()], ""])
    return "\n".join(parts)
