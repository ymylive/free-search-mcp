"""Keyless dataset, image and mathematics source enhancement (offline).

The fixtures are trimmed copies of real API responses received on 2026-08-29.
Tests exercise pure URL/body builders and mappers; the only network tests are
the explicitly gated live checks at the end.
"""

from __future__ import annotations

import os
from urllib.parse import parse_qs, urlparse

import certifi
import pytest

from search_mcp.aggregator import engines_for_category
from search_mcp.config import Settings
from search_mcp.engines import ENGINES, SearchFilters, get_engine
from search_mcp.engines.dataeuropa import DataEuropaEngine
from search_mcp.engines.dataverse import DataverseEngine
from search_mcp.engines.dryad import DryadEngine
from search_mcp.engines.figshare import FigshareEngine
from search_mcp.engines.huggingface import HuggingFaceEngine
from search_mcp.engines.wikimedia import WikimediaEngine
from search_mcp.engines.zbmath import ZbMathEngine

# pytest.ini sets `asyncio_mode = auto` so async tests are auto-marked.

NETWORK = os.environ.get("SEARCH_MCP_TEST_NETWORK") == "1"
skip_offline = pytest.mark.skipif(
    not NETWORK, reason="set SEARCH_MCP_TEST_NETWORK=1 to run"
)

NEW_SOURCES = {
    "dryad": {"dataset", "dataset.repository"},
    "dataverse": {"dataset", "dataset.repository"},
    "figshare": {"dataset", "dataset.repository"},
    "huggingface": {"dataset", "dataset.ml"},
    "dataeuropa": {"dataset", "dataset.gov"},
    "wikimedia": {"image"},
    "zbmath": {"paper", "paper.math"},
}


# ---------------------------------------------------------------------------
# Registry and routing contracts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("name", "categories"), NEW_SOURCES.items())
def test_new_source_is_registered_with_exact_categories(name, categories):
    assert name in ENGINES
    assert ENGINES[name].name == name
    assert ENGINES[name].categories == frozenset(categories)


@pytest.mark.parametrize("name", NEW_SOURCES)
def test_new_source_stays_out_of_the_default_pool(name):
    assert name not in Settings().default_engines


@pytest.mark.parametrize("name", NEW_SOURCES)
def test_new_source_never_uses_a_browser(name):
    engine = get_engine(name)
    assert engine.needs_browser is False
    assert engine.supports_browser_fallback is False


def test_zenodo_joins_the_repository_sub_group():
    assert ENGINES["zenodo"].categories == frozenset(
        {"dataset", "dataset.repository"}
    )


def test_bare_paper_keeps_its_deliberate_top_three():
    assert engines_for_category("paper") == ["arxiv", "openalex", "europepmc"]


def test_bare_dataset_spreads_across_repository_ml_and_government():
    assert engines_for_category("dataset") == ["dryad", "huggingface", "dataeuropa"]


def test_image_category_has_an_independent_commons_fallback():
    assert engines_for_category("image") == ["openverse", "wikimedia"]


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        ("paper.math", ["zbmath"]),
        ("dataset.ml", ["huggingface"]),
        ("dataset.gov", ["dataeuropa"]),
        ("dataset.repository", ["dryad", "dataverse", "zenodo"]),
    ],
)
def test_new_sub_groups_narrow_to_the_expected_sources(category, expected):
    assert engines_for_category(category) == expected


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        ("image", ["openverse", "wikimedia"]),
        ("dataset", ["dryad", "huggingface", "dataeuropa"]),
    ],
)
async def test_widened_exclusive_categories_do_not_re_admit_web_engines(
    monkeypatch, category, expected
):
    from search_mcp import aggregator as agg

    used: list[str] = []

    class _Stub:
        def __init__(self, name):
            self.name = name

        async def search(self, *args, **kwargs):
            used.append(self.name)
            return []

    monkeypatch.setattr(agg, "get_engine", lambda name: _Stub(name))

    async def _allow(name, max_wait=None):
        return True

    monkeypatch.setattr(agg.search_limiter, "acquire", _allow)
    monkeypatch.setattr(agg.settings, "rescue_enabled", False)
    await agg.aggregate_search(
        "traffic", category=category, max_results=3, use_cache=False
    )

    assert used == expected
    assert not (set(used) & set(Settings().default_engines))


# ---------------------------------------------------------------------------
# Dataset repositories
# ---------------------------------------------------------------------------


_DRYAD = {
    "count": 1,
    "total": 23,
    "_embedded": {
        "stash:datasets": [
            {
                "identifier": "doi:10.5061/dryad.7h44j1098",
                "title": (
                    "IoT network traffic flow datasets and encoder models for IoT "
                    "device behavioral representation learning"
                ),
                "authors": [
                    {"firstName": "Arunan", "lastName": "Sivanathan"},
                    {"firstName": "Hassan", "lastName": "Habibi Gharakheili"},
                ],
                "abstract": (
                    "<p>This repository accompanies the research paper, "
                    "<em>Generalizable IoT Traffic Representations for Cross-Network "
                    "Device Identification,</em> and contains two large-scale IoT "
                    "network traffic datasets, pretrained encoder models, and the "
                    "complete processing pipeline used to reproduce the traffic "
                    "representation learning methodology presented in the study.</p>\n"
                ),
                "publicationDate": "2026-07-13",
                "lastModificationDate": "2026-07-13",
                "license": "https://spdx.org/licenses/CC0-1.0.html",
            }
        ]
    },
}


def test_dryad_build_url_uses_page_size_and_native_freshness():
    url = DryadEngine().build_url(
        "traffic flow", 3, SearchFilters(freshness="month")
    )
    params = parse_qs(urlparse(url).query)
    assert params["q"] == ["traffic flow"]
    assert params["per_page"] == ["3"]
    assert params["page"] == ["1"]
    assert params["publishedSince"][0].count("-") == 2


def test_dryad_maps_doi_abstract_authors_and_publication_date():
    out = DryadEngine().map_results(_DRYAD)
    assert out[0].url == "https://doi.org/10.5061/dryad.7h44j1098"
    assert out[0].title.startswith("IoT network traffic flow datasets")
    assert out[0].snippet.startswith("Arunan Sivanathan, Hassan Habibi Gharakheili —")
    assert "<p>" not in out[0].snippet and len(out[0].snippet) <= 400
    assert out[0].published_age == "2026-07-13"
    assert out[0].published_age_confident is True


_DATAVERSE = {
    "status": "OK",
    "data": {
        "start": 0,
        "total_count": 5374,
        "items": [
            {
                "name": "Texas Traffic Accidents 2003-9 (CRIS)",
                "type": "dataset",
                "url": "https://doi.org/10.7910/DVN/GGLKEM",
                "global_id": "doi:10.7910/DVN/GGLKEM",
                "description": (
                    "Traffic accident (CRIS) files from 2003-2009 obtained from the "
                    "Center for Transportation Research at the University of Texas "
                    "at Austin that cover accidents across the state of Texas."
                ),
                "published_at": "2017-09-01T21:53:19Z",
                "authors": ["Fisher, Paul J.", "Gallagher, Justin"],
            }
        ],
    },
}


def test_dataverse_build_url_restricts_type_and_adds_a_date_range():
    url = DataverseEngine().build_url(
        "traffic flow", 3, SearchFilters(freshness="year")
    )
    params = parse_qs(urlparse(url).query)
    assert params["q"] == ["traffic flow"]
    assert params["type"] == ["dataset"]
    assert params["per_page"] == ["3"] and params["start"] == ["0"]
    assert params["fq"][0].startswith("publicationDate:[")
    assert params["sort"] == ["date"] and params["order"] == ["desc"]


def test_dataverse_maps_the_public_doi_record():
    out = DataverseEngine().map_results(_DATAVERSE)
    assert out[0].title == "Texas Traffic Accidents 2003-9 (CRIS)"
    assert out[0].url == "https://doi.org/10.7910/DVN/GGLKEM"
    assert "Center for Transportation Research" in out[0].snippet
    assert out[0].published_age == "2017-09-01"
    assert out[0].published_age_confident is True


_FIGSHARE = [
    {
        "id": 33324103,
        "title": "<p>Parameters of the models.</p>",
        "doi": "10.1371/journal.pcbi.1014646.t001",
        "url": "https://api.figshare.com/v2/articles/33324103",
        "url_public_html": (
            "https://plos.figshare.com/articles/dataset/"
            "_p_Parameters_of_the_models_p_/33324103"
        ),
        "published_date": "2026-08-24T17:37:18Z",
        "created_date": "2026-08-24T17:37:18Z",
        "modified_date": "2026-08-24T17:37:18Z",
        "defined_type": 3,
        "defined_type_name": "dataset",
    }
]


def test_figshare_uses_the_post_only_search_endpoint_and_dataset_filter():
    engine = FigshareEngine()
    assert engine.build_url("traffic flow", 3) == (
        "https://api.figshare.com/v2/articles/search"
    )
    body = engine._body("traffic flow", 3, SearchFilters(freshness="week"))
    assert body["search_for"] == "traffic flow"
    assert body["item_type"] == 3 and body["limit"] == 3
    assert body["published_since"].count("-") == 2
    assert body["order"] == "published_date" and body["order_direction"] == "desc"


async def test_figshare_fetches_with_a_json_post(monkeypatch):
    engine = FigshareEngine()
    seen: dict = {}

    async def fake(url, **kwargs):
        seen["url"] = url
        seen.update(kwargs)
        return _FIGSHARE

    monkeypatch.setattr(engine, "_get_json", fake)
    out = await engine.fetch_results("traffic flow", 3, None)
    assert seen["method"] == "POST"
    assert seen["json_body"]["item_type"] == 3
    assert out


def test_figshare_maps_the_human_page_and_strips_title_markup():
    out = FigshareEngine().map_results(_FIGSHARE)
    assert out[0].title == "Parameters of the models."
    assert out[0].url.startswith("https://plos.figshare.com/articles/dataset/")
    assert out[0].snippet == "dataset · DOI: 10.1371/journal.pcbi.1014646.t001"
    assert out[0].published_age == "2026-08-24"
    assert out[0].published_age_confident is True


# ---------------------------------------------------------------------------
# ML and government datasets
# ---------------------------------------------------------------------------


_HUGGINGFACE = [
    {
        "id": "fmops/ai-traffic-flows",
        "description": (
            '\n\t\n\t\t\n\t\tDataset Card for "ai-traffic-flows"\n\t\n\n'
            "More Information needed\n"
        ),
        "lastModified": "2023-09-05T23:01:22.000Z",
        "createdAt": "2023-09-05T23:01:18.000Z",
        "gated": False,
        "downloads": 19,
        "likes": 0,
    }
]


def test_huggingface_build_url_uses_repository_search():
    url = HuggingFaceEngine().build_url("traffic flow", 3)
    params = parse_qs(urlparse(url).query)
    assert params == {"search": ["traffic flow"], "limit": ["3"]}


def test_huggingface_derives_the_title_and_human_url_from_id():
    out = HuggingFaceEngine().map_results(_HUGGINGFACE)
    assert out[0].title == "fmops/ai-traffic-flows"
    assert out[0].url == "https://huggingface.co/datasets/fmops/ai-traffic-flows"
    assert out[0].snippet == 'Dataset Card for "ai-traffic-flows" More Information needed'
    assert out[0].published_age == "2023-09-05"
    assert out[0].published_age_confident is True


_DATAEUROPA = {
    "result": {
        "count": 34092,
        "results": [
            {
                "title": {
                    "de": "Verkehrsströme, Borough",
                    "en": "Traffic Flows, Borough",
                },
                "description": {
                    "en": (
                        "<p>Estimated traffic volume for cars and all vehicles by "
                        "local authority since 1993 (kilometres).</p>\r\n"
                        "<p>Million Vehicle Kilometres travelled by all motor vehicles "
                        "and all cars in London. Data comes from the Department for "
                        "Transport (DFT) National Road Traffic Survey.</p>\r\n"
                        "<p>Definitions can be found <a href=\"http://www.dft.gov.uk/"
                        "pgr/statistics/datatablespublications/roads/traffic/#technical\">"
                        "here</a>.</p>\r\n"
                        "<p><a href=\"https://www.gov.uk/government/collections/"
                        "road-traffic-statistics\" target=\"_blank\" rel=\"nofollow\">"
                        "https://www.gov.uk/government/collections/road-traffic-statistics"
                        "</a></p>\r\n"
                        "<p><a href=\"https://www.gov.uk/government/statistical-data-sets/"
                        "tra89-traffic-by-local-authority\" target=\"_blank\" "
                        "rel=\"nofollow\">https://www.gov.uk/government/statistical-data-"
                        "sets/tra89-traffic-by-local-authority</a></p>"
                    )
                },
                "resource": "http://data.europa.eu/88u/dataset/v8pow",
                "catalog_record": {
                    "issued": "2025-10-21T18:20:01Z",
                    "modified": "2026-06-16T05:56:58Z",
                },
            }
        ],
    }
}


def test_dataeuropa_build_url_uses_the_verified_get_pagination():
    url = DataEuropaEngine().build_url("traffic flow", 3)
    params = parse_qs(urlparse(url).query)
    assert params == {"q": ["traffic flow"], "limit": ["3"], "page": ["0"]}


def test_dataeuropa_maps_english_text_and_the_record_modification_date():
    out = DataEuropaEngine().map_results(_DATAEUROPA)
    assert out[0].title == "Traffic Flows, Borough"
    assert out[0].url == "http://data.europa.eu/88u/dataset/v8pow"
    assert out[0].snippet.startswith("Estimated traffic volume")
    assert "<p>" not in out[0].snippet
    assert out[0].published_age == "2026-06-16"
    assert out[0].published_age_confident is True


# ---------------------------------------------------------------------------
# Wikimedia Commons images
# ---------------------------------------------------------------------------


_WIKIMEDIA = {
    "continue": {"gsroffset": 2, "continue": "gsroffset||"},
    "query": {
        "pages": {
            "101799395": {
                "pageid": 101799395,
                "title": "File:Roscoe Wind Farm in West Texas.jpg",
                "imageinfo": [
                    {
                        "url": (
                            "https://upload.wikimedia.org/wikipedia/commons/d/d4/"
                            "Roscoe_Wind_Farm_in_West_Texas.jpg?utm_source="
                            "commons.wikimedia.org&utm_campaign=imageinfo&"
                            "utm_content=original"
                        ),
                        "timestamp": "2021-03-19T02:23:31Z",
                        "width": 2871,
                        "height": 1914,
                        "extmetadata": {
                            "ImageDescription": {
                                "value": (
                                    "Wind Turbines and an old windmill at the Roscoe "
                                    "Wind Farm in West Texas"
                                )
                            },
                            "LicenseShortName": {"value": "CC BY-SA 4.0"},
                            "Artist": {
                                "value": (
                                    '<a rel="nofollow" class="external text" '
                                    'href="https://matthewtrader.com">Matthew T Rader</a>'
                                )
                            },
                        },
                    }
                ],
            }
        }
    },
}


def test_wikimedia_build_url_requests_files_and_licence_metadata():
    url = WikimediaEngine().build_url("wind turbine", 3)
    params = parse_qs(urlparse(url).query)
    assert params["generator"] == ["search"]
    assert params["gsrsearch"] == ["wind turbine"]
    assert params["gsrnamespace"] == ["6"] and params["gsrlimit"] == ["3"]
    assert params["iiprop"] == ["url|extmetadata|size|mime|timestamp"]


def test_wikimedia_maps_page_object_values_to_direct_image_urls():
    out = WikimediaEngine().map_results(_WIKIMEDIA)
    assert out[0].title == "Roscoe Wind Farm in West Texas.jpg"
    assert out[0].url.startswith("https://upload.wikimedia.org/")
    assert out[0].snippet.startswith(
        "CC BY-SA 4.0 · by Matthew T Rader · 2871×1914px —"
    )
    assert "<a" not in out[0].snippet
    assert out[0].published_age == "2021-03-19"
    assert out[0].published_age_confident is True


def test_wikimedia_uses_the_honest_contactable_user_agent():
    assert WikimediaEngine().impersonate is None


# ---------------------------------------------------------------------------
# zbMATH Open
# ---------------------------------------------------------------------------


_ZBMATH = {
    "result": [
        {
            "id": 787736,
            "title": {
                "addition": None,
                "original": None,
                "subtitle": None,
                "title": "Numerical methods for engineers and scientists",
            },
            "zbmath_url": "https://zbmath.org/787736",
            "year": "1992",
            "datestamp": "0001-01-01T00:00:00Z",
            "editorial_contributions": [
                {
                    "language": "English",
                    "text": (
                        "zbMATH Open Web Interface contents unavailable due to "
                        "conflicting licenses."
                    ),
                    "contribution_type": "editorial",
                }
            ],
            "links": [],
        }
    ]
}


def test_zbmath_build_url_uses_the_https_document_search():
    url = ZbMathEngine().build_url("partial differential equation", 3)
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    assert parsed.scheme == "https" and parsed.netloc == "api.zbmath.org"
    assert params["search_string"] == ["partial differential equation"]
    assert params["results_per_page"] == ["3"] and params["page"] == ["0"]


def test_zbmath_does_not_present_a_browser_fingerprint():
    assert ZbMathEngine().impersonate is None


def test_zbmath_uses_certifis_maintained_trust_store():
    assert ZbMathEngine().verify == certifi.where()


def test_zbmath_uses_year_and_never_the_sentinel_datestamp():
    out = ZbMathEngine().map_results(_ZBMATH)
    assert out[0].title == "Numerical methods for engineers and scientists"
    assert out[0].url == "https://zbmath.org/787736"
    assert out[0].published_age == "1992"
    assert out[0].published_age != "0001-01-01"
    assert out[0].published_age_confident is False
    assert out[0].snippet.startswith("zbMATH Open Web Interface")


# ---------------------------------------------------------------------------
# Never-raise mapper boundaries
# ---------------------------------------------------------------------------


_ENGINE_CLASSES = [
    DryadEngine,
    DataverseEngine,
    FigshareEngine,
    HuggingFaceEngine,
    DataEuropaEngine,
    WikimediaEngine,
    ZbMathEngine,
]


@pytest.mark.parametrize("engine_cls", _ENGINE_CLASSES)
@pytest.mark.parametrize("payload", [{}, [], None])
def test_new_mappers_tolerate_structural_surprises(engine_cls, payload):
    assert engine_cls().map_results(payload) == []


def _wrap_hit(name: str, hit: dict) -> object:
    if name == "dryad":
        return {"_embedded": {"stash:datasets": [hit]}}
    if name == "dataverse":
        return {"data": {"items": [hit]}}
    if name in {"figshare", "huggingface"}:
        return [hit]
    if name == "dataeuropa":
        return {"result": {"results": [hit]}}
    if name == "wikimedia":
        return {"query": {"pages": {"1": hit}}}
    return {"result": [hit]}


_MISSING_FIELDS = {
    "dryad": (
        {"identifier": "doi:10.1/x"},
        {"title": "No URL"},
    ),
    "dataverse": (
        {"url": "https://doi.org/10.1/x"},
        {"name": "No URL"},
    ),
    "figshare": (
        {"url": "https://figshare.com/x"},
        {"title": "No URL"},
    ),
    # The Hub's repository ID is both its display title and the input to its
    # derived URL, so one missing field invalidates both.
    "huggingface": ({"description": "No repository ID"}, {"id": ""}),
    "dataeuropa": (
        {"resource": "http://data.europa.eu/x"},
        {"title": {"en": "No URL"}},
    ),
    "wikimedia": (
        {"imageinfo": [{"url": "https://upload.wikimedia.org/x.jpg"}]},
        {"title": "File:No URL.jpg", "imageinfo": [{}]},
    ),
    "zbmath": (
        {"zbmath_url": "https://zbmath.org/1"},
        {"title": {"title": "No URL"}},
    ),
}


@pytest.mark.parametrize("name", NEW_SOURCES)
def test_new_mappers_skip_hits_missing_a_title_or_url(name):
    engine = get_engine(name)
    missing_title, missing_url = _MISSING_FIELDS[name]
    assert engine.map_results(_wrap_hit(name, missing_title)) == []
    assert engine.map_results(_wrap_hit(name, missing_url)) == []


# ---------------------------------------------------------------------------
# Live network — opt-in
# ---------------------------------------------------------------------------


@skip_offline
@pytest.mark.parametrize(
    ("name", "query"),
    [
        ("dryad", "traffic flow"),
        ("dataverse", "traffic flow"),
        ("figshare", "traffic flow"),
        ("huggingface", "traffic flow"),
        ("dataeuropa", "traffic flow"),
        ("wikimedia", "wind turbine"),
        ("zbmath", "partial differential equation"),
    ],
)
async def test_live_source_enhancement_returns_results(name, query):
    out = await get_engine(name).search(query, 3)
    if not out:
        pytest.skip(f"{name} returned nothing (rate limit or outage)")
    assert out[0].url.startswith("http")
    assert out[0].title
    assert all(r.engine == name for r in out)


@skip_offline
async def test_live_zbmath_verifies_with_certifi():
    engine = ZbMathEngine()
    assert engine.verify == certifi.where()
    payload = await engine._get_json(
        engine.build_url("partial differential equation", 1)
    )
    if payload is None:
        pytest.skip("zbmath returned nothing (rate limit or outage)")
    assert engine.map_results(payload)
