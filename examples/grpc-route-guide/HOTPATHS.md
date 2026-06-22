# HOTPATHS — route_guide

> The code most other code depends on, and the files that change most.
> **Confidence:** facts are `EXTRACTED` (deterministic from AST and git) unless a section / line says otherwise (DEC-015).

## Dependency hot spots

Symbols ranked by **distinct callers** — the count of distinct symbols with a `CALLS` edge into them (structural in-degree; DEC-025 resolver). The load-bearing callees — signature changes touch every caller. The confidence mix is over the underlying call edges (a callee may have more edges than callers).

| Symbol | Defined in | Callers | Confidence mix |
| --- | --- | --- | --- |
| `format_point` | `route_guide_client.py` | 5 | 6 `EXTRACTED` |
| `read_route_guide_database` | `route_guide_resources.py` | 4 | 4 `INFERRED` |
| `get_feature` | `asyncio_route_guide_server.py` | 2 | 2 `EXTRACTED` |
| `get_feature` | `route_guide_server.py` | 2 | 2 `EXTRACTED` |
| `generate_messages` | `asyncio_route_guide_client.py` | 1 | 1 `EXTRACTED` |
| `generate_route` | `asyncio_route_guide_client.py` | 1 | 1 `EXTRACTED` |
| `guide_get_feature` | `asyncio_route_guide_client.py` | 1 | 1 `EXTRACTED` |
| `guide_get_one_feature` | `asyncio_route_guide_client.py` | 1 | 2 `EXTRACTED` |
| `guide_list_features` | `asyncio_route_guide_client.py` | 1 | 1 `EXTRACTED` |
| `guide_record_route` | `asyncio_route_guide_client.py` | 1 | 1 `EXTRACTED` |
| `guide_route_chat` | `asyncio_route_guide_client.py` | 1 | 1 `EXTRACTED` |
| `main` | `asyncio_route_guide_client.py` | 1 | 1 `EXTRACTED` |
| `make_route_note` | `asyncio_route_guide_client.py` | 1 | 5 `EXTRACTED` |
| `RouteGuideServicer` | `asyncio_route_guide_server.py` | 1 | 1 `EXTRACTED` |
| `get_distance` | `asyncio_route_guide_server.py` | 1 | 1 `EXTRACTED` |

## Cross-file dependencies

File-to-file dependencies aggregated from symbol-level `CALLS` edges (DEC-025 resolver). Self-edges (intra-file calls) excluded.

| From | To | Calls | Top callee |
| --- | --- | --- | --- |
| `asyncio_route_guide_client.py` | `route_guide_resources.py` | 1 | `read_route_guide_database` |
| `asyncio_route_guide_server.py` | `route_guide_resources.py` | 1 | `read_route_guide_database` |
| `route_guide_client.py` | `route_guide_resources.py` | 1 | `read_route_guide_database` |
| `route_guide_server.py` | `route_guide_resources.py` | 1 | `read_route_guide_database` |

## Cross-stack routes

_Confidence: `INFERRED` (DEC-015)._

Frontend/client call sites joined to the backend handler they hit, via a normalized HTTP contract (DEC-043 `ROUTES_TO`). `EXTRACTED` = spec-backed or unique literal path+method; `INFERRED` = a templated/normalized match; `AMBIGUOUS` = several candidate handlers (all surfaced, never one picked).

| Consumer | Handler | Endpoint | Confidence |
| --- | --- | --- | --- |
| `asyncio_route_guide_client.py::guide_get_one_feature` | `asyncio_route_guide_server.py::RouteGuideServicer.GetFeature` | `grpc::route_guide_pb2_grpc::RouteGuide/GetFeature` | `AMBIGUOUS` |
| `asyncio_route_guide_client.py::guide_get_one_feature` | `route_guide_server.py::RouteGuideServicer.GetFeature` | `grpc::route_guide_pb2_grpc::RouteGuide/GetFeature` | `AMBIGUOUS` |
| `route_guide_client.py::guide_get_one_feature` | `asyncio_route_guide_server.py::RouteGuideServicer.GetFeature` | `grpc::route_guide_pb2_grpc::RouteGuide/GetFeature` | `AMBIGUOUS` |
| `route_guide_client.py::guide_get_one_feature` | `route_guide_server.py::RouteGuideServicer.GetFeature` | `grpc::route_guide_pb2_grpc::RouteGuide/GetFeature` | `AMBIGUOUS` |
| `asyncio_route_guide_client.py::guide_list_features` | `asyncio_route_guide_server.py::RouteGuideServicer.ListFeatures` | `grpc::route_guide_pb2_grpc::RouteGuide/ListFeatures` | `AMBIGUOUS` |
| `asyncio_route_guide_client.py::guide_list_features` | `route_guide_server.py::RouteGuideServicer.ListFeatures` | `grpc::route_guide_pb2_grpc::RouteGuide/ListFeatures` | `AMBIGUOUS` |
| `route_guide_client.py::guide_list_features` | `asyncio_route_guide_server.py::RouteGuideServicer.ListFeatures` | `grpc::route_guide_pb2_grpc::RouteGuide/ListFeatures` | `AMBIGUOUS` |
| `route_guide_client.py::guide_list_features` | `route_guide_server.py::RouteGuideServicer.ListFeatures` | `grpc::route_guide_pb2_grpc::RouteGuide/ListFeatures` | `AMBIGUOUS` |
| `asyncio_route_guide_client.py::guide_record_route` | `asyncio_route_guide_server.py::RouteGuideServicer.RecordRoute` | `grpc::route_guide_pb2_grpc::RouteGuide/RecordRoute` | `AMBIGUOUS` |
| `asyncio_route_guide_client.py::guide_record_route` | `route_guide_server.py::RouteGuideServicer.RecordRoute` | `grpc::route_guide_pb2_grpc::RouteGuide/RecordRoute` | `AMBIGUOUS` |
| `route_guide_client.py::guide_record_route` | `asyncio_route_guide_server.py::RouteGuideServicer.RecordRoute` | `grpc::route_guide_pb2_grpc::RouteGuide/RecordRoute` | `AMBIGUOUS` |
| `route_guide_client.py::guide_record_route` | `route_guide_server.py::RouteGuideServicer.RecordRoute` | `grpc::route_guide_pb2_grpc::RouteGuide/RecordRoute` | `AMBIGUOUS` |
| `asyncio_route_guide_client.py::guide_route_chat` | `asyncio_route_guide_server.py::RouteGuideServicer.RouteChat` | `grpc::route_guide_pb2_grpc::RouteGuide/RouteChat` | `AMBIGUOUS` |
| `asyncio_route_guide_client.py::guide_route_chat` | `route_guide_server.py::RouteGuideServicer.RouteChat` | `grpc::route_guide_pb2_grpc::RouteGuide/RouteChat` | `AMBIGUOUS` |
| `route_guide_client.py::guide_route_chat` | `asyncio_route_guide_server.py::RouteGuideServicer.RouteChat` | `grpc::route_guide_pb2_grpc::RouteGuide/RouteChat` | `AMBIGUOUS` |

## Change hot spots

Files touched by the most commits (git churn).

| File | Commits |
| --- | --- |
| `.bazelci/presubmit.yml` | 1 |
| `.bazelignore` | 1 |
| `.bazelrc` | 1 |
| `.bazelversion` | 1 |
| `.bcr/metadata.template.json` | 1 |
| `.bcr/presubmit.yml` | 1 |
| `.bcr/source.template.json` | 1 |
| `.clang-format` | 1 |
| `.clang-tidy` | 1 |
| `.dockerignore` | 1 |
| `.editorconfig` | 1 |
| `.gemini/config.yaml` | 1 |
| `.git-blame-ignore-revs` | 1 |
| `.gitallowed` | 1 |
| `.gitattributes` | 1 |

## Churn × centrality

_Confidence: `INFERRED` (DEC-015)._

Files that are **both** highly depended-on and frequently changed — the riskiest edits in the repo. Commit counts are EXTRACTED; the centrality column and the risk framing are the derivation.

_None._

---

*Generated by forensic-deepdive 0.8.0 on 2026-06-22. Regenerate with `forensic update` — do not hand-edit.*
