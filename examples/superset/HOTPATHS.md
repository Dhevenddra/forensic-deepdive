# HOTPATHS — superset

> The code most other code depends on, and the files that change most.
> **Confidence:** facts are `EXTRACTED` (deterministic from AST and git) unless a section / line says otherwise (DEC-015).

## Dependency hot spots

Symbols with the most inbound `CALLS` edges (DEC-025 resolver). The load-bearing callees — signature changes touch every caller.

| Symbol | Defined in | Callers | Confidence mix |
| --- | --- | --- | --- |
| `t` | `superset-frontend/packages/superset-core/src/translation/TranslatorSingleton.ts` | 1381 | 1381 `INFERRED` |
| `Pvm` | `superset/migrations/shared/security_converge.py` | 223 | 223 `EXTRACTED` |
| `useTheme` | `superset-frontend/packages/superset-core/src/theme/index.tsx` | 203 | 203 `INFERRED` |
| `ensureIsArray` | `superset-frontend/packages/superset-ui-core/src/utils/ensureIsArray.ts` | 142 | 142 `INFERRED` |
| `onChange` | `superset-frontend/src/explore/components/controls/DateFilterControl/components/CustomFrame.tsx` | 128 | 7 `EXTRACTED`, 121 `AMBIGUOUS` |
| `onChange` | `superset-frontend/src/explore/components/controls/DateFilterControl/components/AdvancedFrame.tsx` | 123 | 2 `EXTRACTED`, 121 `AMBIGUOUS` |
| `SupersetError` | `superset/errors.py` | 122 | 122 `EXTRACTED` |
| `onChange` | `superset-frontend/src/explore/components/controls/ColumnConfigControl/ControlForm/index.tsx` | 121 | 121 `AMBIGUOUS` |
| `deprecated` | `superset/views/base.py` | 121 | 8 `EXTRACTED`, 113 `INFERRED` |
| `ForeignKey` | `superset/migrations/shared/constraints.py` | 111 | 15 `EXTRACTED`, 96 `INFERRED` |
| `transaction` | `superset/utils/decorators.py` | 98 | 98 `EXTRACTED` |
| `ValidationError` | `superset/mcp_service/common/error_schemas.py` | 84 | 84 `INFERRED` |
| `getNumberFormatter` | `superset-frontend/packages/superset-ui-core/src/number-format/NumberFormatterRegistrySingleton.ts` | 82 | 82 `INFERRED` |
| `ChartError` | `superset/mcp_service/chart/schemas.py` | 81 | 81 `EXTRACTED` |
| `QueryResult` | `superset-core/src/superset_core/queries/types.py` | 70 | 70 `EXTRACTED` |

## Cross-file dependencies

File-to-file dependencies aggregated from symbol-level `CALLS` edges (DEC-025 resolver). Self-edges (intra-file calls) excluded.

| From | To | Calls | Top callee |
| --- | --- | --- | --- |
| `superset/sql/execution/executor.py` | `superset-core/src/superset_core/queries/types.py` | 114 | `QueryResult` |
| `superset/viz.py` | `superset/views/base.py` | 108 | `deprecated` |
| `superset-frontend/plugins/plugin-chart-point-cluster-map/src/controlPanel.ts` | `superset-frontend/packages/superset-core/src/translation/TranslatorSingleton.ts` | 67 | `t` |
| `superset/mcp_service/chart/tool/get_chart_data.py` | `superset/mcp_service/chart/schemas.py` | 62 | `ChartError` |
| `superset/migrations/shared/migrate_viz/processors.py` | `superset/migrations/shared/migrate_viz/query_functions.py` | 58 | `ensure_is_array` |
| `superset/migrations/versions/2020-12-10_15-05_45731db65d9c_security_converge_datasets.py` | `superset/migrations/shared/security_converge.py` | 44 | `Pvm` |
| `superset-frontend/plugins/preset-chart-deckgl/src/layers/Geojson/controlPanel.ts` | `superset-frontend/packages/superset-core/src/translation/TranslatorSingleton.ts` | 38 | `t` |
| `superset-frontend/plugins/legacy-plugin-chart-calendar/src/controlPanel.ts` | `superset-frontend/packages/superset-core/src/translation/TranslatorSingleton.ts` | 34 | `t` |
| `superset-frontend/src/explore/components/controls/DateFilterControl/utils/constants.ts` | `superset-frontend/packages/superset-core/src/translation/TranslatorSingleton.ts` | 34 | `t` |
| `superset/migrations/versions/2020-12-09_14-13_ccb74baaa89b_security_converge_charts.py` | `superset/migrations/shared/security_converge.py` | 34 | `Pvm` |
| `superset/migrations/versions/2020-12-11_11-45_1f6dca87d1a2_security_converge_dashboards.py` | `superset/migrations/shared/security_converge.py` | 34 | `Pvm` |
| `superset-frontend/src/SqlLab/actions/sqlLab.ts` | `superset-frontend/packages/superset-core/src/translation/TranslatorSingleton.ts` | 33 | `t` |
| `superset/migrations/versions/2025_12_18_0220_create_tasks_table.py` | `superset/migrations/shared/utils.py` | 33 | `create_index` |
| `superset-frontend/src/setup/setupFormatters.ts` | `superset-frontend/packages/superset-ui-core/src/number-format/NumberFormatterRegistrySingleton.ts` | 32 | `getNumberFormatter` |
| `superset/mcp_service/chart/validation/schema_validator.py` | `superset/mcp_service/common/error_schemas.py` | 31 | `ChartGenerationError` |

## Cross-stack routes

_Confidence: `INFERRED` (DEC-015)._

Frontend/client call sites joined to the backend handler they hit, via a normalized HTTP contract (DEC-043 `ROUTES_TO`). `EXTRACTED` = spec-backed or unique literal path+method; `INFERRED` = a templated/normalized match; `AMBIGUOUS` = several candidate handlers (all surfaced, never one picked).

| Consumer | Handler | Endpoint | Confidence |
| --- | --- | --- | --- |
| `superset-frontend/cypress-base/cypress/support/e2e.ts::<module>` | `superset/charts/api.py::ChartRestApi.bulk_delete` | `http::DELETE::/api/v1/chart` | `EXTRACTED` |
| `superset-frontend/src/pages/ChartList/index.tsx::handleBulkChartDelete` | `superset/charts/api.py::ChartRestApi.bulk_delete` | `http::DELETE::/api/v1/chart` | `EXTRACTED` |
| `superset-frontend/cypress-base/cypress/support/e2e.ts::<module>` | `superset/charts/api.py::ChartRestApi.delete` | `http::DELETE::/api/v1/chart/{param}` | `EXTRACTED` |
| `superset-frontend/src/views/CRUD/utils.tsx::handleChartDelete` | `superset/charts/api.py::ChartRestApi.delete` | `http::DELETE::/api/v1/chart/{param}` | `EXTRACTED` |
| `superset-frontend/cypress-base/cypress/support/e2e.ts::<module>` | `superset/dashboards/api.py::DashboardRestApi.bulk_delete` | `http::DELETE::/api/v1/dashboard` | `EXTRACTED` |
| `superset-frontend/src/pages/DashboardList/index.tsx::handleBulkDashboardDelete` | `superset/dashboards/api.py::DashboardRestApi.bulk_delete` | `http::DELETE::/api/v1/dashboard` | `EXTRACTED` |
| `superset-frontend/cypress-base/cypress/support/e2e.ts::<module>` | `superset/dashboards/api.py::DashboardRestApi.delete` | `http::DELETE::/api/v1/dashboard/{param}` | `EXTRACTED` |
| `superset-frontend/src/views/CRUD/utils.tsx::handleDashboardDelete` | `superset/dashboards/api.py::DashboardRestApi.delete` | `http::DELETE::/api/v1/dashboard/{param}` | `EXTRACTED` |
| `superset-frontend/src/pages/DatabaseList/index.tsx::handleDatabaseDelete` | `superset/databases/api.py::DatabaseRestApi.delete` | `http::DELETE::/api/v1/database/{param}` | `EXTRACTED` |
| `superset-frontend/src/pages/RowLevelSecurityList/index.tsx::handleBulkRulesDelete` | `superset/row_level_security/api.py::RLSRestApi.bulk_delete` | `http::DELETE::/api/v1/rowlevelsecurity` | `EXTRACTED` |
| `superset-frontend/src/features/tags/tags.ts::deleteTags` | `superset/tags/api.py::TagRestApi.bulk_delete` | `http::DELETE::/api/v1/tag` | `EXTRACTED` |
| `superset-frontend/src/features/tags/tags.ts::deleteTaggedObjects` | `superset/tags/api.py::TagRestApi.delete_object` | `http::DELETE::/api/v1/tag/{param}/{param}/{param}` | `EXTRACTED` |
| `superset-frontend/src/explore/actions/exploreActions.ts::fetchFaveStar` | `superset/charts/api.py::ChartRestApi.favorite_status` | `http::GET::/api/v1/chart/favorite_status` | `EXTRACTED` |
| `superset-frontend/src/explore/components/PropertiesModal/index.tsx::PropertiesModal` | `superset/charts/api.py::ChartRestApi.get` | `http::GET::/api/v1/chart/{param}` | `EXTRACTED` |
| `superset-frontend/src/explore/components/controls/AnnotationLayerControl/AnnotationLayer.tsx::<module>` | `superset/charts/api.py::ChartRestApi.get` | `http::GET::/api/v1/chart/{param}` | `EXTRACTED` |

## Co-change clusters

_Confidence: `INFERRED` (DEC-015)._

Files most frequently committed together (DEC-027). The shared-commit count is EXTRACTED from git; the implication 'these should change together' is the derivation.

| File A | File B | Shared commits |
| --- | --- | --- |
| `superset/config.py` | `superset/views/core.py` | 112 |
| `superset/models/core.py` | `superset/views/core.py` | 109 |
| `superset/views/base.py` | `superset/views/core.py` | 102 |
| `superset/config.py` | `superset/views/base.py` | 101 |
| `superset/db_engine_specs/base.py` | `superset/models/core.py` | 95 |
| `superset/connectors/sqla/models.py` | `superset/views/core.py` | 92 |
| `superset/db_engine_specs/base.py` | `superset/db_engine_specs/presto.py` | 91 |
| `superset/connectors/sqla/models.py` | `superset/models/helpers.py` | 87 |
| `superset/connectors/sqla/models.py` | `superset/viz.py` | 87 |
| `superset/views/core.py` | `superset/viz.py` | 87 |

## Change hot spots

Files touched by the most commits (git churn).

| File | Commits |
| --- | --- |
| `superset-frontend/package-lock.json` | 1,498 |
| `superset-frontend/package.json` | 1,078 |
| `superset/views/core.py` | 769 |
| `superset/config.py` | 675 |
| `superset/viz.py` | 488 |
| `setup.py` | 481 |
| `docs/yarn.lock` | 447 |
| `superset/connectors/sqla/models.py` | 443 |
| `requirements/base.txt` | 420 |
| `superset-websocket/package-lock.json` | 420 |
| `superset-websocket/package.json` | 404 |
| `docs/package.json` | 402 |
| `UPDATING.md` | 345 |
| `superset/models/core.py` | 329 |
| `superset/assets/package.json` | 300 |

## Churn × centrality

_Confidence: `INFERRED` (DEC-015)._

Files that are **both** highly depended-on and frequently changed — the riskiest edits in the repo. Commit counts are EXTRACTED; the centrality column and the risk framing are the derivation.

| File | Centrality | Commits |
| --- | --- | --- |
| `superset/utils/core.py` | 0.0130 | 286 |
| `superset/connectors/sqla/models.py` | 0.0022 | 443 |
| `superset/models/core.py` | 0.0011 | 329 |
| `superset/viz.py` | 0.0004 | 488 |
| `superset/config.py` | 0.0002 | 675 |
| `superset/views/core.py` | 0.0002 | 769 |
| `setup.py` | 0.0002 | 481 |

---

*Generated by forensic-deepdive 0.6.0 on 2026-06-13. Regenerate with `forensic update` — do not hand-edit.*
