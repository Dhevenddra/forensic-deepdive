# HOTPATHS — omi

> The code most other code depends on, and the files that change most.
> **Confidence:** facts are `EXTRACTED` (deterministic from AST and git) unless a section / line says otherwise (DEC-015).

## Dependency hot spots

Symbols with the most inbound `CALLS` edges (DEC-025 resolver). The load-bearing callees — signature changes touch every caller.

| Symbol | Defined in | Callers | Confidence mix |
| --- | --- | --- | --- |
| `log` | `desktop/Desktop/Sources/Logger.swift` | 1580 | 1580 `INFERRED` |
| `Logger` | `app/lib/utils/logger.dart` | 1462 | 4 `EXTRACTED`, 1458 `INFERRED` |
| `PlatformManager` | `app/lib/utils/platform/platform_manager.dart` | 463 | 5 `EXTRACTED`, 458 `INFERRED` |
| `ChatToolResponse` | `plugins/omi-github-app/models.py` | 449 | 449 `AMBIGUOUS` |
| `ChatToolResponse` | `plugins/omi-google-calendar-app/models.py` | 449 | 449 `AMBIGUOUS` |
| `ChatToolResponse` | `plugins/omi-hive-app/models.py` | 449 | 449 `AMBIGUOUS` |
| `ChatToolResponse` | `plugins/omi-linear-app/models.py` | 449 | 449 `AMBIGUOUS` |
| `ChatToolResponse` | `plugins/omi-notion-app/models.py` | 449 | 449 `AMBIGUOUS` |
| `ChatToolResponse` | `plugins/omi-shipbob-app/models.py` | 449 | 449 `AMBIGUOUS` |
| `ChatToolResponse` | `plugins/omi-shopify-app/models.py` | 449 | 449 `AMBIGUOUS` |
| `ChatToolResponse` | `plugins/omi-twitter-chat-tools-app/models.py` | 449 | 449 `AMBIGUOUS` |
| `ChatToolResponse` | `plugins/omi-whoop-app/models.py` | 449 | 449 `AMBIGUOUS` |
| `ChatToolResponse` | `plugins/omi-zomato-app/models.py` | 449 | 449 `AMBIGUOUS` |
| `SharedPreferencesUtil` | `app/lib/backend/preferences.dart` | 446 | 4 `EXTRACTED`, 442 `INFERRED` |
| `logError` | `desktop/Desktop/Sources/Logger.swift` | 309 | 309 `INFERRED` |

## Cross-file dependencies

File-to-file dependencies aggregated from symbol-level `CALLS` edges (DEC-025 resolver). Self-edges (intra-file calls) excluded.

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

## Co-change clusters

_Confidence: `INFERRED` (DEC-015)._

Files most frequently committed together (DEC-027). The shared-commit count is EXTRACTED from git; the implication 'these should change together' is the derivation.

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

_Confidence: `INFERRED` (DEC-015)._

Files that are **both** highly depended-on and frequently changed — the riskiest edits in the repo. Commit counts are EXTRACTED; the centrality column and the risk framing are the derivation.

| File | Centrality | Commits |
| --- | --- | --- |
| `app/lib/backend/preferences.dart` | 0.0084 | 161 |
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

*Generated by forensic-deepdive 0.3.0 on 2026-05-30. Regenerate with `forensic update` — do not hand-edit.*
