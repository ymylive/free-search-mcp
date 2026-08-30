# Usage guide

A practical reference for the `free-search-mcp` tools, engine selection, and
filters. For install/deploy see the [Quick start](#quick-start) below or the
[README](../README.md).

---

## Quick start

```bash
# one-line setup for Claude Code
curl -LsSf https://raw.githubusercontent.com/sweetcornna/free-search-mcp/main/scripts/install.sh | bash -s -- --client claude-code

# one-line setup for Codex
curl -LsSf https://raw.githubusercontent.com/sweetcornna/free-search-mcp/main/scripts/install.sh | bash -s -- --client codex

# local checkout / install only
./scripts/install.sh --client none
```

For Codex, Cursor, Cline, Continue, Zed, and generic agent operating rules, see
[AGENT_USAGE.md](AGENT_USAGE.md).

Wire into **Claude Code**: this repo ships a `.mcp.json`, so running `claude`
inside the project auto-detects the `search` server. To register it globally:

```bash
claude mcp add search -s user -- uv --directory /absolute/path/to/free-search-mcp run search-mcp
```

Wire into **Codex**:

```bash
codex mcp add search -- uv --directory /absolute/path/to/free-search-mcp run search-mcp
codex mcp list
```

Wire into **Claude Desktop** — add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "search": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/free-search-mcp", "run", "search-mcp"]
    }
  }
}
```

**Docker** (containerized, stdio):

```bash
docker compose build
docker compose run --rm search-mcp
```

---

## Tools

| Tool | What it does |
|---|---|
| `search(query, engines?, max_results?, ...filters)` | Parallel multi-engine search, RRF-merged + deduped, optional `lead_snippet`. |
| `research(question, depth?, ...filters)` | search + fetch top N + return a Markdown brief in one call. |
| `paper_graph(paper, direction?, limit?)` | One paper's citation graph: what it cites, what cites it (ranked by influence), plus Crossref retraction / correction notices. |
| `compare(question, urls=[2..5])` | Concurrent fetch of 2–5 URLs, side-by-side excerpts. |
| `fetch(url, render?, inline?, ...)` | Fetch any resource: reader-mode Markdown for pages, parsed text for documents, or a description (type/size/dimensions/sha256) for images and binaries. `inline=True` returns the image itself for a vision model. |
| `fetch_batch(urls, ...)` | Concurrent multi-URL fetch (max 20 per call). |
| `read_doc(source, start?, length?, ...)` | Parse PDF / DOCX / XLSX / PPTX / EPUB / CSV / source code / zip-tar / HTML / TXT / MD with pagination. |
| `extract_structured(url, ...)` | JSON-LD / OpenGraph / Twitter cards / microdata. |
| `cache_search(query, limit?, ...)` | FTS5 search across previously fetched pages. |
| `engines(group?)` | The source tree — group → sub-group → engine, one line of description each. |
| `download(url, ...)` | Save a file to `${SEARCH_MCP_CACHE_DIR}/downloads` by default; files auto-delete after 24h. Set `SEARCH_MCP_DOWNLOAD_ENABLED=false` to disable it. |

All tools default to `format="markdown"`; pass `format="json"` for structured
output.

---

## Engines

`search` / `research` accept an `engines=[...]` list. Omit it to use the fast
default pool. Every engine here is **keyless** (no API key, no account).

The registry contains 49 engines in total; the default pool remains the four
all-HTTP engines below.

**Default pool** (all-HTTP, no browser):
`duckduckgo`, `mojeek`, `googlenews`, `bing`.

When the pool comes back empty (or nearly empty with gated/erroring engines),
the aggregator automatically runs one bounded rescue pass via `searx` and
reports it as `rescued_via`.

**Opt-in extras:**

| Engine | Source | Notes |
|---|---|---|
| `startpage` | Startpage | browser-rendered, ~5–10s |
| `brave` `bing` `baidu` | resp. engines | intermittently challenge headless clients |
| `searx` | public SearXNG instances | meta-search; public instances often slow |
| `google` | Google web SERP scrape | HTTP→browser fallback; Google **CAPTCHAs datacenter/headless IPs**, so expect gating off residential networks |
| `serpsearch` | alias of `google` | identical behavior (all real SERP APIs need a key) |
| `anysearch` | [AnySearch](https://github.com/anysearch-ai/anysearch-mcp-server) REST API | anonymous tier, IP rate-limited; one call returns fused/re-ranked results |
| `bilibili` | Bilibili (哔哩哔哩) JSON API | keyless video search (synthetic `buvid3` cookie); **video results only** |
| `zhihu` | Zhihu (知乎) search page | **best-effort**, browser-rendered; Zhihu hard-gates bots so a login wall / empty result is common and honest |
| `sogou` | 搜狗 HTML scrape | best-effort; returns **redirect URLs** (`sogou.com/link?url=…`), not target URLs |
| `so360` | 360搜索 HTML scrape | best-effort; returns direct URLs |
| `wikipedia` | MediaWiki API | language follows `SEARCH_MCP_REGION` |
| `openlibrary` | Open Library | book search |

The scholarly and financial sources (`arxiv`, `openalex`, `crossref`,
`pubmed`, `europepmc`, `dblp`, `doaj`, `clinicaltrials`, `zbmath`,
`sec_edgar`, `yahoofinance`, `cninfo`, `worldbank`, `imf`) are keyless too;
reach them with `category=` rather than by name. Dataset sources are `dryad`,
`dataverse`, `figshare`, `huggingface`, `dataeuropa`, and `zenodo`; image
sources are `openverse` and `wikimedia`.

### Vertical sources — selected automatically by `category=`

Not usually named directly. Sources are organised as **group → sub-group**: a
bare group widens (one specialist per sub-group joins the pool until the engine
cap), and a dotted sub-group narrows to that branch; the same cap still applies.

| `category` | Engines | Notes |
|---|---|---|
| `paper` | one per sub-group | real literature search, structured publication dates |
| `paper.index` | `openalex`, `crossref`, `semanticscholar` | cross-discipline DOI indexes with citation counts |
| `paper.preprint` | `arxiv`, `europepmc` | not peer reviewed, and labelled `PREPRINT` in the snippet |
| `paper.biomed` | `europepmc`, `pubmed` | MEDLINE plus its 40M-record superset |
| `paper.cs` | `dblp` | curated CS bibliography — exact venue, authors, DOI |
| `paper.openaccess` | `doaj`, `europepmc` | full text is free to read, so `read_doc` can open it |
| `paper.trial` | `clinicaltrials` | registered trials, with phase / status / sponsor |
| `paper.math` | `zbmath` | mathematics literature with reviews and classification |
| `finance` | one per sub-group | filings, market data and macro answer different questions |
| `finance.filings` | `sec_edgar`, `cninfo` | US regulatory filings; A-share / HK announcements |
| `finance.market` | `yahoofinance` | ticker resolution + news about the resolved instrument |
| `finance.macro` | `worldbank`, `imf` | World Bank documents; IMF series incl. WEO forecasts |
| `github` | `github`, `github_code` (keyed) | repos + issues/PRs; code search needs a token |
| `forum` | `stackexchange`, `hackernews` | accepted-answer / score signals |
| `news`, `news.world` | `googlenews`, `gdelt` | GDELT covers 100+ languages; strictly rate-limited, skipped rather than queued |
| `image` | `openverse`, `wikimedia` | CC-licensed/direct file results; Wikimedia also returns attribution and source metadata |
| `dataset` | one per sub-group | datasets, software, and open-data catalogues |
| `dataset.repository` | `dryad`, `dataverse`, `zenodo`, `figshare` | public research-dataset repositories with DOI or landing-page metadata |
| `dataset.ml` | `huggingface` | machine-learning dataset repositories and dataset cards |
| `dataset.gov` | `dataeuropa` | EU and member-state open-data catalogues in one index |

At the default category-engine limit, `category="dataset"` selects `dryad`,
`huggingface`, and `dataeuropa`—one source from each dataset sub-group. Use a
dotted token when the sub-group is known: `dataset.repository` for repository
catalogues, `dataset.ml` for Hugging Face, `dataset.gov` for data.europa.eu, or
`paper.math` for zbMATH. A bare group is broader and round-robins across its
sub-groups before the cap truncates; `category="paper"` remains `arxiv`,
`openalex`, and `europepmc`.

`image` and `dataset` **replace** the default pool; the rest augment it (capped
by `SEARCH_MCP_CATEGORY_ENGINE_LIMIT`, default 3). A web engine cannot return an
image file or a dataset record, so the exclusive categories keep only
specialist sources. Before 0.11.0 that meant one source each; they now have two
image sources and five dataset sources across three sub-groups, so one outage,
rate limit, or missed hit no longer exhausts specialist search. Passing
`engines=` disables the routing.

Results from an engine that natively indexes the requested category count
**double** in the rank fusion, so `category=` changes the ORDER too — not just
which engines run. A specialist is usually the only source returning a given
document, and without the weighting its hit lost to three general engines
agreeing on a blog post about the topic.

`engines()` prints this table live from the registry, so it cannot drift.

Enable globally via `SEARCH_MCP_DEFAULT_ENGINES` (JSON list) in `.env`.

**Keyed (API-key) engines** — dormant until a key is configured:

| Engine | Provider | Needs | Free tier |
|---|---|---|---|
| `brave_api` | Brave Search API | `brave_api_key` | 2,000/mo |
| `serper` | Serper (Google) | `serper_api_key` | 2,500 |
| `tavily` | Tavily (AI search) | `tavily_api_key` | 1,000/mo |
| `google_cse` | Google Custom Search | `google_cse_api_key` + `google_cse_cx` | 100/day |
| `github_code` | GitHub code search | `github_token` | keyless `github` covers repos/issues |
| `stackexchange` | Stack Exchange | `stackexchange_key` (optional) | 300/day keyless |
| `semanticscholar` | Semantic Scholar | `semanticscholar_api_key` (optional) | anonymous pool answers 429 in practice |

Add keys the simple way:

```bash
uv run search-mcp-admin     # http://127.0.0.1:8765 → paste keys → Save (applies live)
```

The admin page is **中英双语** and includes provider key fields, "How to get a
key / 如何获取密钥" steps, Save/Test/Clear buttons, and the Network / Proxy /
网络 / 代理 card. Or set `SEARCH_MCP_<FIELD>` env vars (e.g.
`SEARCH_MCP_SERPER_API_KEY`). An unconfigured keyed engine returns a clear
"not configured" hint instead of failing silently. Step-by-step key acquisition:
**[API_KEYS.md](API_KEYS.md)**.

### Examples

```text
# English web search, default pool
search("reciprocal rank fusion")

# One-call aggregator (anonymous AnySearch)
search("vector database benchmarks", engines=["anysearch"])

# Chinese video search on Bilibili
search("python 教程", engines=["bilibili"])

# Mix CJK verticals + general web
search("transformer 架构", engines=["bilibili", "zhihu", "duckduckgo"])

# Google SERP scrape (works best from a residential IP)
search("site:python.org asyncio", engines=["google"])
```

> **Real-tested status (June 2026):** `bilibili` and `anysearch` return live
> results out of the box. `google`/`serpsearch` work only when the source IP
> isn't CAPTCHA-gated by Google. `zhihu` frequently hits a login wall and
> returns empty — that's the honest no-key ceiling, by design.

**Gated engines** (Google/Bing CAPTCHA, Zhihu login) have three escape hatches:
a **proxy** (`SEARCH_MCP_PROXY` / admin "Network / Proxy"), an automatic
**SearXNG fallback** for `google`/`serpsearch`/`bing`, and a one-time
**`search-mcp-login zhihu`**. The response reports `gated_engines` + `gated_hint`
when an engine was gated. See **[PROXY_AND_GATES.md](PROXY_AND_GATES.md)**.

---

## Filters (search / research)

| Param | Values | Effect |
|---|---|---|
| `freshness` | `day` / `week` / `month` / `year` | only results from the last N |
| `include_domains` | `["python.org"]` | restrict to these domains |
| `exclude_domains` | `["pinterest.com"]` | remove these |
| `category` | a group (`news` / `pdf` / `github` / `paper` / `forum` / `blog` / `image` / `dataset` / `finance`) or a sub-group (`paper.biomed`, `paper.math`, `finance.filings`, `dataset.repository`, `dataset.ml`, `dataset.gov`, …) | content-type shortcut **and** routing signal — sends the query to sources that natively index it (see [Vertical sources](#vertical-sources--selected-automatically-by-category)) |
| `include_text` | `"async"` | substring required in title/snippet |
| `exclude_text` | `"beginner"` | substring forbidden |
| `max_age_hours` | `24` | override the 7-day cache TTL on this call |

```text
research("LLM eval frameworks", depth=3, freshness="month", category="paper")
search("kubernetes operators", include_domains=["github.com"], category="github")
search("CRISPR base editing", category="paper.preprint")
search("graph neural network datasets", category="dataset.ml")
search("Riemann hypothesis", category="paper.math")
search("NVDA 10-K risk factors", category="finance.filings")
paper_graph("10.1145/1571941.1572114")               # references + citing works
```

When filters drop results so aggressively that ≤3 remain, the response includes
`filter_diagnostics` telling you which knob to relax.

---

## Configuration

Copy `.env.example` → `.env` and edit. Every knob is an env var prefixed with
`SEARCH_MCP_` (see `.env.example` for the annotated full list). Common ones:

| Var | Default | Meaning |
|---|---|---|
| `SEARCH_MCP_DEFAULT_ENGINES` | `["duckduckgo","mojeek","googlenews","bing"]` | engine pool (JSON list) |
| `SEARCH_MCP_FETCH_STRATEGY` | `auto` | `auto` / `http` / `browser` |
| `SEARCH_MCP_SAFESEARCH` | `moderate` | `strict` / `moderate` / `off` |
| `SEARCH_MCP_REGION` | `us-en` | `cc-lang` token |
| `SEARCH_MCP_CACHE_TTL_SECONDS` | `604800` | 7 days |
| `SEARCH_MCP_CATEGORY_ENGINE_LIMIT` | `3` | how many category-native engines `category=` may add |
| `SEARCH_MCP_CONTACT_EMAIL` | *(empty)* | optional; OpenAlex/Crossref/NCBI route identified callers to a faster pool |
| `SEARCH_MCP_DOWNLOAD_ENABLED` | `true` | set `false` to disable local file downloads |
| `SEARCH_MCP_DOWNLOAD_DIR` | `${SEARCH_MCP_CACHE_DIR}/downloads` | optional directory override; unset or blank uses the dynamic default (`/data/downloads` in Docker) |
| `SEARCH_MCP_DOWNLOAD_TTL_HOURS` | `24` | downloaded files are deleted after this; `0` keeps them forever |
| `SEARCH_MCP_DOWNLOAD_MAX_MB` | `100` | second-layer save cap; effective remote cap is the smaller of this and `SEARCH_MCP_MAX_RESPONSE_BYTES` (25,000,000 bytes by default) |
| `SEARCH_MCP_TRANSPORT` | `stdio` | `stdio` / `streamable-http` |
| `SEARCH_MCP_HTTP_HOST` / `_PORT` / `_PATH` | `127.0.0.1` / `8000` / `/mcp` | streamable-http bind settings |

---

## Testing

```bash
# offline (no network) — default
uv run pytest -q

# live network tests (hit the real engines), gated behind an env var
SEARCH_MCP_TEST_NETWORK=1 uv run pytest tests/test_bilibili.py tests/test_anysearch.py -q
```
