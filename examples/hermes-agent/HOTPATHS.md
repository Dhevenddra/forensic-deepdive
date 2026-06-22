# HOTPATHS — hermes-agent

> The code most other code depends on, and the files that change most.
> **Confidence:** facts are `EXTRACTED` (deterministic from AST and git) unless a section / line says otherwise (DEC-015).

## Dependency hot spots

Symbols ranked by **distinct callers** — the count of distinct symbols with a `CALLS` edge into them (structural in-degree; DEC-025 resolver). The load-bearing callees — signature changes touch every caller. The confidence mix is over the underlying call edges (a callee may have more edges than callers).

| Symbol | Defined in | Callers | Confidence mix |
| --- | --- | --- | --- |
| `load_config` | `hermes_cli/config.py` | 258 | 1508 `EXTRACTED` |
| `get_hermes_home` | `hermes_constants.py` | 237 | 294 `EXTRACTED`, 13 `INFERRED`, 55 `AMBIGUOUS` |
| `SendResult` | `gateway/platforms/base.py` | 126 | 378 `EXTRACTED` |
| `color` | `hermes_cli/colors.py` | 95 | 424 `EXTRACTED`, 13 `AMBIGUOUS` |
| `tool_error` | `tools/registry.py` | 95 | 311 `EXTRACTED` |
| `save_config` | `hermes_cli/config.py` | 81 | 495 `EXTRACTED` |
| `get_env_value` | `hermes_cli/config.py` | 77 | 521 `EXTRACTED`, 6 `AMBIGUOUS` |
| `_cprint` | `cli.py` | 66 | 329 `EXTRACTED` |
| `print_info` | `hermes_cli/cli_output.py` | 64 | 382 `EXTRACTED`, 194 `AMBIGUOUS` |
| `get_hermes_home` | `plugins/disk-cleanup/disk_cleanup.py` | 57 | 5 `EXTRACTED`, 55 `AMBIGUOUS` |
| `get_hermes_home` | `skills/productivity/google-workspace/scripts/_hermes_home.py` | 56 | 4 `EXTRACTED`, 55 `AMBIGUOUS` |
| `get_hermes_home` | `plugins/hermes-achievements/dashboard/plugin_api.py` | 55 | 3 `EXTRACTED`, 55 `AMBIGUOUS` |
| `cfg_get` | `hermes_cli/config.py` | 54 | 72 `EXTRACTED` |
| `get_hermes_home` | `plugins/platforms/google_chat/oauth.py` | 54 | 2 `EXTRACTED`, 55 `AMBIGUOUS` |
| `get_hermes_home` | `scripts/profile-tui.py` | 53 | 2 `EXTRACTED`, 55 `AMBIGUOUS` |

## Cross-file dependencies

File-to-file dependencies aggregated from symbol-level `CALLS` edges (DEC-025 resolver). Self-edges (intra-file calls) excluded.

| From | To | Calls | Top callee |
| --- | --- | --- | --- |
| `hermes_cli/main.py` | `hermes_cli/config.py` | 1768 | `load_config` |
| `hermes_cli/main.py` | `hermes_cli/auth.py` | 805 | `_save_model_choice` |
| `hermes_cli/setup.py` | `hermes_cli/cli_output.py` | 377 | `print_info` |
| `gateway/run.py` | `agent/i18n.py` | 274 | `t` |
| `hermes_cli/web_server.py` | `hermes_state.py` | 240 | `SessionDB` |
| `hermes_cli/gateway.py` | `hermes_cli/cli_output.py` | 221 | `print_info` |
| `hermes_cli/tools_config.py` | `hermes_cli/cli_output.py` | 191 | `print_info` |
| `hermes_cli/setup.py` | `hermes_cli/config.py` | 179 | `get_env_value` |
| `agent/lsp/servers.py` | `agent/lsp/install.py` | 169 | `try_install` |
| `cli.py` | `hermes_cli/config.py` | 159 | `load_config` |
| `cli.py` | `hermes_cli/skin_engine.py` | 153 | `get_active_skin` |
| `hermes_cli/skills_hub.py` | `tools/skills_hub.py` | 149 | `GitHubAuth` |
| `hermes_cli/gateway.py` | `gateway/status.py` | 146 | `get_running_pid` |
| `hermes_cli/main.py` | `hermes_constants.py` | 120 | `get_hermes_home` |
| `plugins/platforms/discord/adapter.py` | `gateway/platforms/base.py` | 116 | `SendResult` |

## Cross-stack routes

_Confidence: `INFERRED` (DEC-015)._

Frontend/client call sites joined to the backend handler they hit, via a normalized HTTP contract (DEC-043 `ROUTES_TO`). `EXTRACTED` = spec-backed or unique literal path+method; `INFERRED` = a templated/normalized match; `AMBIGUOUS` = several candidate handlers (all surfaced, never one picked).

| Consumer | Handler | Endpoint | Confidence |
| --- | --- | --- | --- |
| `tools/send_message_tool.py::_send_whatsapp` | `scripts/whatsapp-bridge/bridge.js::<module>` | `http::POST::/send` | `INFERRED` |
| `optional-skills/research/domain-intel/scripts/domain_intel.py::main` | `optional-skills/research/domain-intel/scripts/domain_intel.py::check_available` | `registry::COMMAND_MAP::*` | `AMBIGUOUS` |
| `optional-skills/research/domain-intel/scripts/domain_intel.py::main` | `optional-skills/research/domain-intel/scripts/domain_intel.py::check_ssl` | `registry::COMMAND_MAP::*` | `AMBIGUOUS` |
| `optional-skills/research/domain-intel/scripts/domain_intel.py::main` | `optional-skills/research/domain-intel/scripts/domain_intel.py::dns_records` | `registry::COMMAND_MAP::*` | `AMBIGUOUS` |
| `optional-skills/research/domain-intel/scripts/domain_intel.py::main` | `optional-skills/research/domain-intel/scripts/domain_intel.py::subdomains` | `registry::COMMAND_MAP::*` | `AMBIGUOUS` |
| `optional-skills/research/domain-intel/scripts/domain_intel.py::main` | `optional-skills/research/domain-intel/scripts/domain_intel.py::whois_lookup` | `registry::COMMAND_MAP::*` | `AMBIGUOUS` |
| `tools/mcp_tool.py::_register_server_tools` | `tools/mcp_tool.py::_make_get_prompt_handler` | `registry::_handler_factories::*` | `AMBIGUOUS` |
| `tools/mcp_tool.py::_register_server_tools` | `tools/mcp_tool.py::_make_list_prompts_handler` | `registry::_handler_factories::*` | `AMBIGUOUS` |
| `tools/mcp_tool.py::_register_server_tools` | `tools/mcp_tool.py::_make_list_resources_handler` | `registry::_handler_factories::*` | `AMBIGUOUS` |
| `tools/mcp_tool.py::_register_server_tools` | `tools/mcp_tool.py::_make_read_resource_handler` | `registry::_handler_factories::*` | `AMBIGUOUS` |
| `optional-skills/productivity/memento-flashcards/scripts/memento_cards.py::main` | `optional-skills/productivity/memento-flashcards/scripts/memento_cards.py::cmd_add` | `registry::cmd_map::*` | `AMBIGUOUS` |
| `optional-skills/productivity/memento-flashcards/scripts/memento_cards.py::main` | `optional-skills/productivity/memento-flashcards/scripts/memento_cards.py::cmd_add_quiz` | `registry::cmd_map::*` | `AMBIGUOUS` |
| `optional-skills/productivity/memento-flashcards/scripts/memento_cards.py::main` | `optional-skills/productivity/memento-flashcards/scripts/memento_cards.py::cmd_delete` | `registry::cmd_map::*` | `AMBIGUOUS` |
| `optional-skills/productivity/memento-flashcards/scripts/memento_cards.py::main` | `optional-skills/productivity/memento-flashcards/scripts/memento_cards.py::cmd_delete_collection` | `registry::cmd_map::*` | `AMBIGUOUS` |
| `optional-skills/productivity/memento-flashcards/scripts/memento_cards.py::main` | `optional-skills/productivity/memento-flashcards/scripts/memento_cards.py::cmd_due` | `registry::cmd_map::*` | `AMBIGUOUS` |

## Change hot spots

Files touched by the most commits (git churn).

| File | Commits |
| --- | --- |
| `.dockerignore` | 1 |
| `.env.example` | 1 |
| `.envrc` | 1 |
| `.gitattributes` | 1 |
| `.github/ISSUE_TEMPLATE/bug_report.yml` | 1 |
| `.github/ISSUE_TEMPLATE/config.yml` | 1 |
| `.github/ISSUE_TEMPLATE/feature_request.yml` | 1 |
| `.github/ISSUE_TEMPLATE/setup_help.yml` | 1 |
| `.github/PULL_REQUEST_TEMPLATE.md` | 1 |
| `.github/actions/hermes-smoke-test/action.yml` | 1 |
| `.github/actions/nix-setup/action.yml` | 1 |
| `.github/dependabot.yml` | 1 |
| `.github/pr-screenshots/39327/providers-collapsed.png` | 1 |
| `.github/pr-screenshots/39327/providers-expanded.png` | 1 |
| `.github/pr-screenshots/39327/tools-collapsed.png` | 1 |

## Churn × centrality

_Confidence: `INFERRED` (DEC-015)._

Files that are **both** highly depended-on and frequently changed — the riskiest edits in the repo. Commit counts are EXTRACTED; the centrality column and the risk framing are the derivation.

_None._

---

*Generated by forensic-deepdive 0.8.0 on 2026-06-22. Regenerate with `forensic update` — do not hand-edit.*
