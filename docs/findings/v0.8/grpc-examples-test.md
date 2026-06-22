# grpc-examples — v0.8 (gRPC protocol + the examples-demotion finding)

`forensic extract C:/Dev/scratch/grpc-examples --force` @ 0.8.0.

## What worked

gRPC client→server matching is strong. **94 ROUTES_TO** (`[E] 26 / [I] 0 / [A] 68`) across 15
distinct `grpc::…` service/method endpoints, e.g.
`examples/python/data_transmission/client.py::simple_method` →
`server.py::DemoServer.SimpleMethod` over `grpc::…demo_pb2_grpc::GRPCDemo/SimpleMethod`,
EXTRACTED. The 68 AMBIGUOUS are correct: many tutorials reuse `Greeter/SayHello`, so a single
client call has several candidate servers and all are surfaced (DEC-083), never guessed.

## The finding: "3 source files" on an examples-only repo

The extract summary and `MAP.md` both report **"Source files: 3 (swift 2, python 1)"** — while
the symbol graph is **117 files** and there are **94 routes** spanning dozens of Python files.
Not contradictory once you see why: `grpc-examples` is *entirely* under `examples/`, and
**DEC-049** assigns `ROLE_EXAMPLE` to files on an `examples`/`samples`/`demo` path segment —
they stay in the graph (so routes/PageRank still work) but are **not counted as "source."**
For a library that ships a few demos, demoting `examples/` is exactly right. For a repo that
*is* an examples collection, the headline "3 source files" reads as broken even though the
analysis underneath is complete and correct.

- **Root cause:** `inventory.py::_EXAMPLE_SEGMENTS` (DEC-049), behaving as designed.
- **Not a fix to the classification** — demotion is correct; the gap is *reporting*. Options
  for v0.9: show the graph file-count alongside ("3 source / 117 in graph"), or annotate
  "(N files demoted as examples/)" so the headline can't be misread.

**Verdict:** protocol matching passes; one reporting-clarity item filed for v0.9.
