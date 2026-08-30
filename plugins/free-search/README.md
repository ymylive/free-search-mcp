# free-search — Claude Code plugin

The plugin packaging of [free-search-mcp](https://github.com/sweetcornna/free-search-mcp):
one `/plugin install` wires the `search` MCP server (11 tools — web search,
fetching, document reading) into Claude Code, with no API key and no manual
`claude mcp add`.

```
/plugin marketplace add sweetcornna/free-search-mcp
/plugin install free-search@free-search-mcp
```

## What it registers

`.mcp.json` declares a single stdio server named `search`, started with
`uvx free-search-mcp==<version>` — so [uv](https://docs.astral.sh/uv/) is the
only prerequisite, and the first launch downloads the package from PyPI.

The version is **pinned to this plugin's own version**: installing plugin
`0.10.0` always gets package `0.10.0`, and `/plugin update free-search` is what
moves you to a newer server. The three versions (plugin manifest, `.mcp.json`
pin, Python package) are kept in lockstep by `tests/test_plugin_manifest.py`
and re-checked against the tag in the release workflow.

## Configuration

Nothing is required — the keyless engines work on install. Optional settings
(engine pool, proxies, API keys for the opt-in engines) live in
`~/.config/search-mcp/.env`, exactly as for any other install method; the
plugin adds no separate config of its own. See
[Configuration](../../README.md#configuration) and
[docs/API_KEYS.md](../../docs/API_KEYS.md).

Browser-rendered engines (`startpage`, `zhihu`, …) and JS-heavy page fetches
need Chromium once:

```bash
uvx --from free-search-mcp playwright install chromium
```

Without it, HTTP search and fetch keep working and any call that needs the
browser returns that exact install command.

## Not using Claude Code?

The plugin is only a delivery wrapper. Every other client keeps its existing
path — `uvx free-search-mcp` over stdio; see the
[project README](../../README.md#install) and
[docs/AGENT_USAGE.md](../../docs/AGENT_USAGE.md).
