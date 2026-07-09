# HOTPATHS — rabbitmq-tutorials

> The code most other code depends on, and the files that change most.
> **Confidence:** facts are `EXTRACTED` (deterministic from AST and git) unless a section / line says otherwise.

## Dependency hot spots

Symbols ranked by **distinct callers** — the count of distinct symbols with a `CALLS` edge into them (structural in-degree; the call-graph resolver). The load-bearing callees — signature changes touch every caller. The confidence mix is over the underlying call edges (a callee may have more edges than callers).

| Symbol | Defined in | Callers | Confidence mix |
| --- | --- | --- | --- |
| `TutorialSupport.newEnvironment` | `java-amqp/src/main/java/TutorialSupport.java` | 15 | 15 `INFERRED` |
| `failOnError` | `go/publisher_confirms.go` | 5 | 8 `EXTRACTED` |
| `PublisherConfirms.createConnection` | `java/PublisherConfirms.java` | 5 | 5 `EXTRACTED` |
| `openConfirmChannel` | `go/publisher_confirms.go` | 3 | 3 `EXTRACTED` |
| `failOnError` | `go/rpc_client.go` | 3 | 8 `EXTRACTED` |
| `RPCClient` | `dart/rpc_client.dart` | 2 | 3 `EXTRACTED` |
| `fib` | `dart/rpc_server.dart` | 2 | 3 `EXTRACTED` |
| `fib` | `go-amqp/rpc_server.go` | 2 | 3 `EXTRACTED` |
| `fib` | `go/rpc_server.go` | 2 | 3 `EXTRACTED` |
| `RPCServer.fib` | `java-amqp/src/main/java/RPCServer.java` | 2 | 3 `EXTRACTED` |
| `RPCServer.fib` | `java/RPCServer.java` | 2 | 3 `EXTRACTED` |
| `fibonacci` | `javascript-nodejs/src/rpc_server.js` | 2 | 3 `EXTRACTED` |
| `fib` | `python/rpc_server.py` | 2 | 3 `EXTRACTED` |
| `fib` | `rust-lapin/src/bin/rpc_server.rs` | 2 | 3 `EXTRACTED` |
| `RabbitAmqpTutorialsRunner` | `spring-amqp-stream/src/main/java/org/springframework/amqp/tutorials/RabbitAmqpTutorialsRunner.java` | 2 | 2 `AMBIGUOUS` |

## Cross-file dependencies

File-to-file dependencies aggregated from symbol-level `CALLS` edges (the call-graph resolver). Self-edges (intra-file calls) excluded.

| From | To | Calls | Top callee |
| --- | --- | --- | --- |
| `java-amqp/src/main/java/PublisherConfirms.java` | `java-amqp/src/main/java/TutorialSupport.java` | 3 | `TutorialSupport.newEnvironment` |
| `spring-amqp/src/main/java/org/springframework/amqp/tutorials/tut2/Tut2Config.java` | `spring-amqp/src/main/java/org/springframework/amqp/tutorials/tut2/Tut2Receiver.java` | 2 | `Tut2Receiver` |
| `java-amqp/src/main/java/EmitLog.java` | `java-amqp/src/main/java/TutorialSupport.java` | 1 | `TutorialSupport.newEnvironment` |
| `java-amqp/src/main/java/EmitLogDirect.java` | `java-amqp/src/main/java/TutorialSupport.java` | 1 | `TutorialSupport.newEnvironment` |
| `java-amqp/src/main/java/EmitLogTopic.java` | `java-amqp/src/main/java/TutorialSupport.java` | 1 | `TutorialSupport.newEnvironment` |
| `java-amqp/src/main/java/NewTask.java` | `java-amqp/src/main/java/TutorialSupport.java` | 1 | `TutorialSupport.newEnvironment` |
| `java-amqp/src/main/java/RPCClient.java` | `java-amqp/src/main/java/TutorialSupport.java` | 1 | `TutorialSupport.newEnvironment` |
| `java-amqp/src/main/java/RPCServer.java` | `java-amqp/src/main/java/TutorialSupport.java` | 1 | `TutorialSupport.newEnvironment` |
| `java-amqp/src/main/java/ReceiveLogs.java` | `java-amqp/src/main/java/TutorialSupport.java` | 1 | `TutorialSupport.newEnvironment` |
| `java-amqp/src/main/java/ReceiveLogsDirect.java` | `java-amqp/src/main/java/TutorialSupport.java` | 1 | `TutorialSupport.newEnvironment` |
| `java-amqp/src/main/java/ReceiveLogsTopic.java` | `java-amqp/src/main/java/TutorialSupport.java` | 1 | `TutorialSupport.newEnvironment` |
| `java-amqp/src/main/java/Recv.java` | `java-amqp/src/main/java/TutorialSupport.java` | 1 | `TutorialSupport.newEnvironment` |
| `java-amqp/src/main/java/Send.java` | `java-amqp/src/main/java/TutorialSupport.java` | 1 | `TutorialSupport.newEnvironment` |
| `java-amqp/src/main/java/Worker.java` | `java-amqp/src/main/java/TutorialSupport.java` | 1 | `TutorialSupport.newEnvironment` |
| `spring-amqp-stream/src/main/java/org/springframework/amqp/tutorials/RabbitAmqpTutorialsApplication.java` | `spring-amqp-stream/src/main/java/org/springframework/amqp/tutorials/RabbitAmqpTutorialsRunner.java` | 1 | `RabbitAmqpTutorialsRunner` |

## Cross-stack routes

_Confidence: `INFERRED`._

Frontend/client call sites joined to the backend handler they hit, via a normalized HTTP contract (`ROUTES_TO`). `EXTRACTED` = spec-backed or unique literal path+method; `INFERRED` = a templated/normalized match; `AMBIGUOUS` = several candidate handlers (all surfaced, never one picked).

| Consumer | Handler | Endpoint | Confidence |
| --- | --- | --- | --- |
| `python/rpc_client.py::FibonacciRpcClient.call` | `python.rpc_server` | `queue::rpc_queue` | `EXTRACTED` |
| `python.emit_log_direct` | `python/receive_logs_direct.py::main` | `amqp::direct_logs` | `INFERRED` |
| `python.emit_log` | `python/receive_logs.py::main` | `amqp::logs` | `INFERRED` |
| `python.emit_log_topic` | `python/receive_logs_topic.py::main` | `amqp::topic_logs` | `INFERRED` |
| `python.send` | `python/receive.py::main` | `queue::hello` | `AMBIGUOUS` |
| `python.send` | `python.send` | `queue::hello` | `AMBIGUOUS` |
| `python.new_task` | `python.new_task` | `queue::task_queue` | `AMBIGUOUS` |
| `python.new_task` | `python.worker` | `queue::task_queue` | `AMBIGUOUS` |

## Change hot spots

Files touched by the most commits (git churn).

| File | Commits |
| --- | --- |
| `.devcontainer/Dockerfile` | 1 |
| `.devcontainer/devcontainer.json` | 1 |
| `.devcontainer/library-scripts/node-debian.sh` | 1 |
| `.github/dependabot.yml` | 1 |
| `.gitignore` | 1 |
| `AGENTS.md` | 1 |
| `LICENSE.txt` | 1 |
| `README.md` | 1 |
| `clojure/.gitignore` | 1 |
| `clojure/README.md` | 1 |
| `clojure/project.clj` | 1 |
| `clojure/src/rabbitmq/tutorials/emit_log.clj` | 1 |
| `clojure/src/rabbitmq/tutorials/emit_log_direct.clj` | 1 |
| `clojure/src/rabbitmq/tutorials/emit_log_topic.clj` | 1 |
| `clojure/src/rabbitmq/tutorials/new_task.clj` | 1 |

## Churn × centrality

_Confidence: `INFERRED`._

Files that are **both** highly depended-on and frequently changed — the riskiest edits in the repo. Commit counts are EXTRACTED; the centrality column and the risk framing are the derivation.

_None._

---

*Generated by forensic-deepdive 0.9.0 on 2026-07-09. Regenerate with `forensic update` — do not hand-edit.*
