# HOTPATHS — omi

> The code most other code depends on, and the files that change most.
> **Confidence:** facts are `EXTRACTED` (deterministic from AST and git) unless a section / line says otherwise.

## Dependency hot spots

Symbols ranked by **distinct callers** — the count of distinct symbols with a `CALLS` edge into them (structural in-degree; the call-graph resolver). The load-bearing callees — signature changes touch every caller. The confidence mix is over the underlying call edges (a callee may have more edges than callers).

| Symbol | Defined in | Callers | Confidence mix |
| --- | --- | --- | --- |
| `Logger` | `app/lib/utils/logger.dart` | 778 | 4 `EXTRACTED`, 1458 `AMBIGUOUS` |
| `log` | `desktop/Desktop/Sources/Logger.swift` | 695 | 1580 `AMBIGUOUS` |
| `PlatformManager` | `app/lib/utils/platform/platform_manager.dart` | 302 | 5 `EXTRACTED`, 458 `AMBIGUOUS` |
| `AnalyticsManager.track` | `app/lib/utils/analytics/analytics_manager.dart` | 289 | 289 `EXTRACTED` |
| `logError` | `desktop/Desktop/Sources/Logger.swift` | 243 | 309 `AMBIGUOUS` |
| `SharedPreferencesUtil` | `app/lib/backend/preferences.dart` | 227 | 4 `EXTRACTED`, 442 `AMBIGUOUS` |
| `makeApiCall` | `app/lib/backend/http/shared.dart` | 200 | 200 `AMBIGUOUS` |
| `Wal` | `app/lib/services/wals/wal.dart` | 116 | 5 `EXTRACTED`, 159 `AMBIGUOUS` |
| `FirestoreService.build_request` | `desktop/Backend-Rust/src/services/firestore.rs` | 110 | 119 `INFERRED` |
| `ServerConversation` | `app/lib/backend/schema/conversation.dart` | 97 | 9 `EXTRACTED`, 126 `AMBIGUOUS` |
| `App` | `app/lib/backend/schema/app.dart` | 89 | 5 `EXTRACTED`, 126 `AMBIGUOUS` |
| `ServiceManager` | `app/lib/services/services.dart` | 87 | 6 `EXTRACTED`, 88 `AMBIGUOUS` |
| `BtDevice` | `app/lib/backend/schema/bt_device/bt_device.dart` | 79 | 17 `EXTRACTED`, 91 `AMBIGUOUS` |
| `get_llm` | `backend/utils/llm/clients.py` | 76 | 76 `EXTRACTED` |
| `PostHogManager.track` | `desktop/Desktop/Sources/PostHogManager.swift` | 74 | 74 `EXTRACTED` |

## Cross-file dependencies

File-to-file dependencies aggregated from symbol-level `CALLS` edges (the call-graph resolver). Self-edges (intra-file calls) excluded.

| From | To | Calls | Top callee |
| --- | --- | --- | --- |
| `desktop/Desktop/Sources/AppState.swift` | `desktop/Desktop/Sources/Logger.swift` | 205 | `log` |
| `desktop/Desktop/Sources/Providers/ChatProvider.swift` | `desktop/Desktop/Sources/Logger.swift` | 102 | `log` |
| `desktop/Desktop/Sources/Stores/TasksStore.swift` | `desktop/Desktop/Sources/Logger.swift` | 90 | `log` |
| `app/lib/services/devices/omi_connection.dart` | `app/lib/utils/logger.dart` | 86 | `Logger` |
| `desktop/Desktop/Sources/ProactiveAssistants/ProactiveAssistantsPlugin.swift` | `desktop/Desktop/Sources/Logger.swift` | 73 | `log` |
| `plugins/omi-twitter-chat-tools-app/main.py` | `plugins/omi-github-app/models.py` | 67 | `ChatToolResponse` |
| `plugins/omi-twitter-chat-tools-app/main.py` | `plugins/omi-google-calendar-app/models.py` | 67 | `ChatToolResponse` |
| `plugins/omi-twitter-chat-tools-app/main.py` | `plugins/omi-hive-app/models.py` | 67 | `ChatToolResponse` |
| `plugins/omi-twitter-chat-tools-app/main.py` | `plugins/omi-linear-app/models.py` | 67 | `ChatToolResponse` |
| `plugins/omi-twitter-chat-tools-app/main.py` | `plugins/omi-notion-app/models.py` | 67 | `ChatToolResponse` |
| `plugins/omi-twitter-chat-tools-app/main.py` | `plugins/omi-shipbob-app/models.py` | 67 | `ChatToolResponse` |
| `plugins/omi-twitter-chat-tools-app/main.py` | `plugins/omi-shopify-app/models.py` | 67 | `ChatToolResponse` |
| `plugins/omi-twitter-chat-tools-app/main.py` | `plugins/omi-twitter-chat-tools-app/models.py` | 67 | `ChatToolResponse` |
| `plugins/omi-twitter-chat-tools-app/main.py` | `plugins/omi-whoop-app/models.py` | 67 | `ChatToolResponse` |
| `plugins/omi-twitter-chat-tools-app/main.py` | `plugins/omi-zomato-app/models.py` | 67 | `ChatToolResponse` |

## Cross-stack routes

_Confidence: `INFERRED`._

Frontend/client call sites joined to the backend handler they hit, via a normalized HTTP contract (`ROUTES_TO`). `EXTRACTED` = spec-backed or unique literal path+method; `INFERRED` = a templated/normalized match; `AMBIGUOUS` = several candidate handlers (all surfaced, never one picked).

| Consumer | Handler | Endpoint | Confidence |
| --- | --- | --- | --- |
| `backend/utils/retrieval/tools/google_utils.py::refresh_google_token` | `backend/routers/mcp_sse.py::mcp_token` | `http::POST::/token` | `INFERRED` |
| `plugins/composio/src/notion.py::notion_callback` | `backend/routers/oauth.py::oauth_token` | `http::POST::/v1/oauth/token` | `INFERRED` |
| `plugins/oauth/client.py::NotionClient.get_access_token` | `backend/routers/oauth.py::oauth_token` | `http::POST::/v1/oauth/token` | `INFERRED` |

## Co-change clusters

_Confidence: `INFERRED`._

Files most frequently committed together. The shared-commit count is EXTRACTED from git; the implication 'these should change together' is the derivation.

| File A | File B | Shared commits |
| --- | --- | --- |
| `app/lib/l10n/app_localizations_de.dart` | `app/lib/l10n/app_localizations_es.dart` | 121 |
| `app/lib/l10n/app_localizations_de.dart` | `app/lib/l10n/app_localizations_ja.dart` | 121 |
| `app/lib/l10n/app_localizations_es.dart` | `app/lib/l10n/app_localizations_ja.dart` | 120 |
| `app/lib/l10n/app_localizations_es.dart` | `app/lib/l10n/app_localizations_zh.dart` | 120 |
| `app/lib/l10n/app_localizations_es.dart` | `app/lib/l10n/app_localizations_hi.dart` | 119 |
| `app/lib/l10n/app_localizations_es.dart` | `app/lib/l10n/app_localizations_pt.dart` | 119 |
| `app/lib/l10n/app_localizations_hi.dart` | `app/lib/l10n/app_localizations_ja.dart` | 119 |
| `app/lib/l10n/app_localizations_hi.dart` | `app/lib/l10n/app_localizations_zh.dart` | 119 |
| `app/lib/l10n/app_localizations_ja.dart` | `app/lib/l10n/app_localizations_zh.dart` | 119 |
| `app/lib/l10n/app_localizations_cs.dart` | `app/lib/l10n/app_localizations_de.dart` | 118 |

## Change hot spots

Files touched by the most commits (git churn).

| File | Commits |
| --- | --- |
| `desktop/CHANGELOG.json` | 421 |
| `backend/routers/transcribe.py` | 400 |
| `app/lib/pages/settings/developer.dart` | 381 |
| `app/lib/pages/home/page.dart` | 334 |
| `app/pubspec.yaml` | 315 |
| `app/lib/providers/capture_provider.dart` | 304 |
| `community-plugins.json` | 247 |
| `app/lib/main.dart` | 220 |
| `backend/utils/llm.py` | 208 |
| `backend/routers/apps.py` | 183 |
| `README.md` | 176 |
| `backend/routers/chat.py` | 168 |
| `app/lib/pages/chat/page.dart` | 164 |
| `codemagic.yaml` | 164 |
| `app/lib/backend/preferences.dart` | 161 |

## Churn × centrality

_Confidence: `INFERRED`._

Files that are **both** highly depended-on and frequently changed — the riskiest edits in the repo. Commit counts are EXTRACTED; the centrality column and the risk framing are the derivation.

| File | Centrality | Commits |
| --- | --- | --- |
| `app/lib/backend/preferences.dart` | 0.0085 | 161 |
| `app/lib/providers/capture_provider.dart` | 0.0033 | 304 |
| `app/lib/pages/apps/app_detail/app_detail.dart` | 0.0005 | 129 |
| `app/lib/pages/home/page.dart` | 0.0005 | 334 |
| `app/lib/l10n/app_localizations_ja.dart` | 0.0004 | 129 |
| `backend/routers/chat.py` | 0.0003 | 168 |
| `app/lib/pages/chat/page.dart` | 0.0003 | 164 |
| `backend/routers/memories.py` | 0.0003 | 155 |
| `app/lib/pages/settings/developer.dart` | 0.0002 | 381 |
| `backend/routers/transcribe.py` | 0.0002 | 400 |

---

*Generated by forensic-deepdive 0.9.0 on 2026-07-09. Regenerate with `forensic update` — do not hand-edit.*
