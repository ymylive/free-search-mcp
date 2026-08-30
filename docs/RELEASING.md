# Releasing

A version of this project is not one artifact but four, and a release is only
finished when all four agree:

| Where | What it is |
| --- | --- |
| PyPI | the `free-search-mcp` wheel + sdist every install path downloads |
| GitHub Release | the public record, with the same two files attached |
| CHANGELOG | the release notes — the workflow copies them verbatim |
| Plugin | `plugins/free-search` on `main`, which pins the PyPI version it runs |

A tag that reached PyPI without a GitHub Release, or a plugin still pinned to
the previous version, is an unfinished release.

## The version number lives in four files

| File | Why it has to change |
| --- | --- |
| `pyproject.toml` → `project.version` | the version PyPI publishes |
| `uv.lock` | records the workspace version; the release runs `uv lock --check` |
| `plugins/free-search/.claude-plugin/plugin.json` → `version` | what `/plugin install` reports and what `/plugin update` compares against |
| `plugins/free-search/.mcp.json` → `mcpServers.search.args` | the `free-search-mcp==X.Y.Z` pin the installed plugin actually runs |

Two gates keep them together, so a forgotten copy fails loudly rather than
shipping a plugin that advertises one version and starts another:

- `tests/test_plugin_manifest.py` — runs in CI on every PR, checks both plugin
  copies against `pyproject.toml`.
- **Validate release metadata** in `.github/workflows/release.yml` — re-checks
  all of them against the pushed tag, before anything is built or published.

## Checklist

1. Bump the version in the four files above (`uv lock` regenerates the lock).
2. Add a `## [X.Y.Z] - YYYY-MM-DD` section to `CHANGELOG.md`. Everything
   between it and the next `## [` becomes the GitHub Release body, so write it
   for readers, not for a diff.
3. `uv run ruff check . && uv run pytest -q`.
4. Optional, needs the Claude Code CLI (CI has none):
   `claude plugin validate . --strict && claude plugin validate ./plugins/free-search --strict`.
5. Commit to `main` and push.
6. Tag — **annotated**, and its subject becomes the GitHub Release title:
   ```bash
   git tag -a vX.Y.Z -m "short release title"
   git push origin vX.Y.Z
   ```
7. The `Release` workflow then runs the full `ci.yml` matrix, validates tag ↔
   version ↔ CHANGELOG ↔ plugin, builds, creates a draft GitHub Release with
   the artifacts, publishes to PyPI (`skip-existing`, token secret
   `PYPI_API_TOKEN`), and only then flips the release out of draft — marking it
   Latest only if no higher stable version exists.
8. Verify (below) before calling it done.

The workflow is idempotent: a failed run can be re-run on the same tag. It
reuses an existing draft when the assets match, deletes and rebuilds a draft
when they do not, and refuses to overwrite a published release whose assets
disagree with the tag.

## What the plugin release actually is

Nothing extra. There is no second repository, no marketplace registry to
notify, and no separate plugin tag: `/plugin marketplace add
sweetcornna/free-search-mcp` clones this repo's **default branch**, so the
plugin ships the moment the release commit lands on `main`. Existing users move
with `/plugin update free-search` (restart required).

That is also the one ordering constraint worth respecting. Between the release
commit landing on `main` and PyPI accepting the upload, the plugin on `main`
pins a version PyPI does not have yet, and a plugin installed in that window
cannot start its server. So:

- push the tag immediately after the release commit — do not let a bumped
  `main` sit untagged;
- if the workflow fails, either fix forward quickly or revert the bump commit
  on `main`, so the pin never points at a version that will never exist.

## Verify

```bash
uvx free-search-mcp==X.Y.Z --help          # PyPI has the new version
gh release view vX.Y.Z                     # exists, right assets, marked Latest
```

And the plugin path end to end, in a scratch scope you can throw away:

```bash
claude plugin marketplace add sweetcornna/free-search-mcp
claude plugin install free-search@free-search-mcp -s local
claude plugin details free-search@free-search-mcp   # version + 1 MCP server: search
claude plugin uninstall free-search@free-search-mcp -s local
```

## Notes

- The PyPI distribution name is `free-search-mcp`. The name `search-mcp`
  belongs to another account and uploads there return 403 — do not retry it.
  The import package, the console scripts, and the `SEARCH_MCP_*` env vars are
  all unaffected.
- The plugin, the `uvx` one-liner, `scripts/install.sh`, and Docker are four
  wrappers around the same server. A release changes the version they resolve
  to, never the contract between them.
