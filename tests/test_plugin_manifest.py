"""The Claude Code plugin is a third copy of the version number.

`pyproject.toml` says what gets published to PyPI, `plugin.json` says what a
user installed, and the plugin's `.mcp.json` pins which package that install
actually runs. If they drift, `/plugin install free-search` quietly starts a
different server than the one it advertises — so the drift is a test failure
here, not a support ticket later.
"""

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN_DIR = ROOT / "plugins" / "free-search"
PLUGIN_MANIFEST = PLUGIN_DIR / ".claude-plugin" / "plugin.json"
PLUGIN_MCP = PLUGIN_DIR / ".mcp.json"

DIST_NAME = "free-search-mcp"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def project_version() -> str:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]


def test_marketplace_entry_points_at_the_plugin():
    marketplace = read_json(MARKETPLACE)

    assert marketplace["name"] == DIST_NAME
    assert marketplace["owner"]["name"]

    entries = marketplace["plugins"]
    assert len(entries) == 1, "one repo, one plugin — a second entry needs its own test"
    entry = entries[0]
    assert entry["name"] == read_json(PLUGIN_MANIFEST)["name"]
    # Relative sources resolve against the marketplace root, i.e. the repo root.
    assert (ROOT / entry["source"]).resolve() == PLUGIN_DIR.resolve()
    assert PLUGIN_MANIFEST.is_file()


def test_plugin_version_tracks_the_package_version():
    assert read_json(PLUGIN_MANIFEST)["version"] == project_version()


def test_plugin_manifest_declares_an_existing_mcp_config():
    manifest = read_json(PLUGIN_MANIFEST)

    declared = manifest["mcpServers"]
    assert isinstance(declared, str), "keep the server config in .mcp.json, not inline"
    assert (PLUGIN_DIR / declared).resolve() == PLUGIN_MCP.resolve()


def test_plugin_runs_the_pinned_published_package():
    servers = read_json(PLUGIN_MCP)["mcpServers"]

    # The server name is what tool ids are built from, and what every other
    # install path in the docs uses; renaming it would silently break prompts.
    assert list(servers) == ["search"]
    search = servers["search"]
    assert search["command"] == "uvx"
    # Pinned, not floating: installing plugin X.Y.Z must run package X.Y.Z, and
    # `/plugin update` is what moves a user to a newer server.
    assert search["args"] == [f"{DIST_NAME}=={project_version()}"]


def test_docs_carry_the_plugin_install_commands():
    for path in (ROOT / "README.md", ROOT / "docs" / "AGENT_USAGE.md"):
        text = path.read_text(encoding="utf-8")
        assert f"/plugin marketplace add sweetcornna/{DIST_NAME}" in text, path
        assert f"/plugin install free-search@{DIST_NAME}" in text, path
