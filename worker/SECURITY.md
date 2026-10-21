# Legacy document proxy

The hosted editor removed Cloudflare document import in commit dc62018 (2026-04-29). Current hosted editing is local paste/format; the Python importer uses lark-cli directly.

The legacy Worker remains deployed for compatibility with health checks. Both /api/doc and /api/image require a server-side PROXY_KEY and an Authorization: Bearer header. With no PROXY_KEY configured, both fail closed. Do not put this key in public frontend code or URL query strings. The production deployment intentionally has no PROXY_KEY configured while this importer is retired.

Private document/image responses must not be publicly cached. Reintroducing browser import requires proper user authentication and authorized image delivery, not a shared key embedded in the page.
