# Security

Only the latest release is maintained. Use synthetic data in public issues.
For a vulnerability, use GitHub's private vulnerability reporting if enabled;
otherwise describe the affected component without an exploit or sensitive data
and ask for a private reporting channel. Do not post secrets, databases or
private source documents.

Local-only workflows still require care when exporting or sharing results.

The optional MCP server exposes the selected vault to its connected host. Use
an appropriate vault for that host. It opens SQLite read-only and has no
import, deletion or mark-reviewed tool. Source text remains untrusted data.
