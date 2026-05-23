# HOTPATHS — omi-test

> The code most other code depends on, and the files that change most.
> **Confidence:** every fact below is `EXTRACTED` — deterministic from Tree-sitter AST and git history (DEC-007).

## Dependency hot spots

Definitions with the widest blast radius — the most depended-on symbols.

| Symbol | Defined in | Rank |
| --- | --- | --- |
| `log` | `desktop/Desktop/Sources/Logger.swift` | 0.0203 |
| `Logger` | `app/lib/utils/logger.dart` | 0.0136 |
| `Button` | `desktop/Desktop/Sources/Bluetooth/DeviceUUIDs.swift` | 0.0133 |
| `debug` | `app/lib/utils/logger.dart` | 0.0123 |
| `set` | `backend/database/cache_manager.py` | 0.0123 |
| `error` | `app/lib/utils/logger.dart` | 0.0104 |
| `error` | `app/lib/services/custom_stt_log_service.dart` | 0.0104 |
| `instance` | `app/lib/services/services.dart` | 0.0099 |
| `fromJson` | `app/lib/backend/schema/bt_device/bt_device.dart` | 0.0075 |
| `fromJson` | `app/lib/backend/schema/geolocation.dart` | 0.0075 |
| `fromJson` | `app/lib/backend/schema/message.dart` | 0.0075 |
| `fromJson` | `app/lib/backend/schema/structured.dart` | 0.0075 |
| `of` | `app/lib/l10n/app_localizations.dart` | 0.0072 |
| `of` | `app/lib/main.dart` | 0.0072 |
| `isSupported` | `app/lib/l10n/app_localizations.dart` | 0.0068 |

## Cross-file dependencies

Which file leans on which (referencer → definer), by shared symbols.

| From | To | Shared symbols |
| --- | --- | --- |
| `backend/routers/apps.py` | `backend/utils/apps.py` | add_app_access_for_tester, add_tester, build_capability_category_groups_response, build_capability_groups_response, build_pagination_metadata… |
| `backend/routers/users.py` | `backend/database/users.py` | create_person, delete_person, delete_user_data, finalize_migration, get_conversation_summary_rating_score… |
| `backend/utils/apps.py` | `backend/database/redis_db.py` | can_update_persona, delete_generic_cache, get_app_cache_by_id, get_app_money_made_amount_cache, get_app_money_made_cache… |
| `backend/utils/apps.py` | `backend/database/apps.py` | add_app_access_for_tester_db, add_tester_db, can_tester_access_app_db, get_api_key_by_hash_db, get_app_by_id_db… |
| `app/lib/pages/chat/page.dart` | `app/lib/providers/message_provider.dart` | MessageProvider, addMessage, addMessageLocally, captureImage, clearChat… |
| `app/lib/pages/action_items/action_items_page.dart` | `app/lib/providers/action_items_provider.dart` | ActionItemsProvider, batchUpdateSortOrders, clearSearchQuery, clearSelection, createActionItem… |
| `app/lib/pages/conversation_detail/page.dart` | `app/lib/utils/analytics/analytics_manager.dart` | audioShareCompleted, audioShareFailed, audioShareStarted, checkedActionItem, conversationDetailSearchClicked… |
| `app/lib/models/announcement.dart` | `app/lib/models/announcement.g.dart` | _$AnnouncementCTAFromJson, _$AnnouncementCTAToJson, _$AnnouncementContentFromJson, _$AnnouncementContentToJson, _$AnnouncementFromJson… |
| `app/lib/utils/other/time_utils.dart` | `app/lib/l10n/app_localizations.dart` | AppLocalizations, of, timeCompactHours, timeCompactHoursAndMins, timeCompactMins… |
| `app/lib/utils/other/time_utils.dart` | `app/lib/l10n/app_localizations_ar.dart` | timeCompactHours, timeCompactHoursAndMins, timeCompactMins, timeCompactMinsAndSecs, timeCompactSecs… |
| `app/lib/utils/other/time_utils.dart` | `app/lib/l10n/app_localizations_be.dart` | timeCompactHours, timeCompactHoursAndMins, timeCompactMins, timeCompactMinsAndSecs, timeCompactSecs… |
| `app/lib/utils/other/time_utils.dart` | `app/lib/l10n/app_localizations_bg.dart` | timeCompactHours, timeCompactHoursAndMins, timeCompactMins, timeCompactMinsAndSecs, timeCompactSecs… |
| `app/lib/utils/other/time_utils.dart` | `app/lib/l10n/app_localizations_bn.dart` | timeCompactHours, timeCompactHoursAndMins, timeCompactMins, timeCompactMinsAndSecs, timeCompactSecs… |
| `app/lib/utils/other/time_utils.dart` | `app/lib/l10n/app_localizations_bs.dart` | timeCompactHours, timeCompactHoursAndMins, timeCompactMins, timeCompactMinsAndSecs, timeCompactSecs… |
| `app/lib/utils/other/time_utils.dart` | `app/lib/l10n/app_localizations_ca.dart` | timeCompactHours, timeCompactHoursAndMins, timeCompactMins, timeCompactMinsAndSecs, timeCompactSecs… |

## Change hot spots

Files touched by the most commits (git churn).

| File | Commits |
| --- | --- |
| `desktop/CHANGELOG.json` | 423 |
| `backend/routers/transcribe.py` | 217 |
| `app/lib/pages/settings/developer.dart` | 177 |
| `app/pubspec.yaml` | 156 |
| `app/lib/l10n/app_localizations_ja.dart` | 140 |
| `app/lib/l10n/app_localizations_de.dart` | 138 |
| `codemagic.yaml` | 138 |
| `app/lib/l10n/app_localizations_es.dart` | 136 |
| `app/lib/pages/home/page.dart` | 135 |
| `app/lib/l10n/app_localizations_hi.dart` | 134 |
| `app/lib/l10n/app_localizations_pt.dart` | 133 |
| `app/lib/l10n/app_localizations_zh.dart` | 133 |
| `app/lib/l10n/app_localizations_ar.dart` | 131 |
| `app/lib/l10n/app_localizations_cs.dart` | 131 |
| `app/lib/l10n/app_localizations_sk.dart` | 131 |

## Churn × centrality

Files that are **both** highly depended-on and frequently changed — the riskiest edits in the repo.

| File | Centrality | Commits |
| --- | --- | --- |
| `app/lib/l10n/app_localizations_ar.dart` | 0.0008 | 131 |
| `app/lib/l10n/app_localizations_bg.dart` | 0.0008 | 130 |
| `app/lib/l10n/app_localizations_cs.dart` | 0.0008 | 131 |
| `app/lib/l10n/app_localizations_de.dart` | 0.0008 | 138 |
| `app/lib/l10n/app_localizations_el.dart` | 0.0008 | 130 |
| `app/lib/l10n/app_localizations_es.dart` | 0.0008 | 136 |
| `app/lib/l10n/app_localizations_fi.dart` | 0.0008 | 130 |
| `app/lib/l10n/app_localizations_fr.dart` | 0.0008 | 130 |
| `app/lib/l10n/app_localizations_hi.dart` | 0.0008 | 134 |
| `app/lib/l10n/app_localizations_hu.dart` | 0.0008 | 130 |

---

*Generated by forensic-deepdive 0.1.0 on 2026-05-23. Regenerate with `forensic update` — do not hand-edit.*
