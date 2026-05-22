"""Personalized-PageRank ranking over the symbol graph.

Ported from Aider's ``RepoMap`` repo-map algorithm (Apache-2.0). This is the
*algorithm*, not the dependency: neither ``aider`` nor SciPy/NumPy is imported.
The power-iteration kernel below mirrors NetworkX's reference
``_pagerank_python`` implementation (with ``dangling`` weighted by the
personalization vector, as Aider configures it). See DEC-003, DEC-011, NOTICE.

Two outputs:
  * ``file_rank``  — PageRank score per file; how central each file is.
  * ``definitions`` — every cross-file definition, ranked by how much PageRank
    mass flows into it. This is what the MAP/HOTPATHS emitters consume.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import networkx as nx

from forensic_deepdive.static.graph import SymbolGraph
from forensic_deepdive.static.tags import Tag

_ALPHA = 0.85  # damping factor: probability of following an edge vs. teleporting
_MAX_ITER = 100
_TOL = 1.0e-6


@dataclass
class RankedDefinition:
    """A defined symbol with the PageRank mass that flows into it."""

    rel_path: str
    name: str
    rank: float
    tags: list[Tag]


@dataclass
class RankedRepo:
    """The result of ranking a :class:`SymbolGraph`."""

    file_rank: dict[str, float]  # file -> PageRank score, all graph nodes
    definitions: list[RankedDefinition]  # cross-file defs, highest rank first


def rank_files(
    symbol_graph: SymbolGraph,
    personalization: dict[str, float] | None = None,
) -> RankedRepo:
    """Run personalized PageRank over *symbol_graph* and rank its definitions.

    *personalization* optionally biases the walk toward seed files (e.g. files
    a developer is actively editing). Entries for unknown files are ignored; if
    nothing usable remains the walk is uniform (plain PageRank).
    """
    graph = symbol_graph.graph
    if graph.number_of_nodes() == 0:
        return RankedRepo(file_rank={}, definitions=[])

    teleport = _restrict_personalization(personalization, graph)
    file_rank = _power_iteration(graph, teleport)

    # Distribute each file's rank across its outgoing edges, proportional to
    # edge weight, and accumulate it onto the (definer_file, identifier) it
    # points at. This is Aider's rank-distribution step.
    definition_rank: dict[tuple[str, str], float] = defaultdict(float)
    for src in graph.nodes:
        src_rank = file_rank.get(src, 0.0)
        out_edges = list(graph.out_edges(src, data=True))
        total_weight = sum(data["weight"] for _, _, data in out_edges)
        if total_weight <= 0:
            continue
        for _src, dst, data in out_edges:
            contribution = src_rank * data["weight"] / total_weight
            definition_rank[(dst, data["ident"])] += contribution

    ranked = [
        RankedDefinition(
            rel_path=rel_path,
            name=name,
            rank=rank,
            tags=symbol_graph.definitions.get((rel_path, name), []),
        )
        for (rel_path, name), rank in sorted(
            definition_rank.items(), key=lambda item: item[1], reverse=True
        )
    ]
    return RankedRepo(file_rank=file_rank, definitions=ranked)


def _restrict_personalization(
    personalization: dict[str, float] | None,
    graph: nx.MultiDiGraph,
) -> dict[str, float] | None:
    """Keep only personalization entries for nodes present in *graph*."""
    if not personalization:
        return None
    restricted = {node: personalization.get(node, 0.0) for node in graph.nodes}
    return restricted if sum(restricted.values()) > 0 else None


def _power_iteration(
    graph: nx.MultiDiGraph,
    personalization: dict[str, float] | None,
) -> dict[str, float]:
    """Pure-Python personalized PageRank via power iteration.

    Equivalent to ``networkx.pagerank`` with ``weight="weight"`` and
    ``dangling`` set to the personalization vector, but without the SciPy/NumPy
    backend. Returns the last iterate if convergence is not reached within
    ``_MAX_ITER`` (approximate ranks are acceptable for repo mapping).
    """
    nodes = list(graph.nodes)
    node_count = len(nodes)
    if node_count == 0:
        return {}

    if personalization:
        total = sum(personalization.values())
        teleport = {n: personalization.get(n, 0.0) / total for n in nodes}
    else:
        teleport = {n: 1.0 / node_count for n in nodes}

    # Total outgoing weight per node; nodes with none are "dangling" and have
    # their rank redistributed via the teleport vector each iteration.
    out_weight: dict[str, float] = dict.fromkeys(nodes, 0.0)
    for src, _dst, data in graph.edges(data=True):
        out_weight[src] += data.get("weight", 1.0)
    dangling_nodes = [n for n in nodes if out_weight[n] == 0.0]

    rank = dict(teleport)
    for _ in range(_MAX_ITER):
        prev = rank
        rank = dict.fromkeys(nodes, 0.0)
        leaked = _ALPHA * sum(prev[n] for n in dangling_nodes)
        for src, dst, data in graph.edges(data=True):
            rank[dst] += _ALPHA * prev[src] * data.get("weight", 1.0) / out_weight[src]
        for node in nodes:
            rank[node] += (leaked + (1.0 - _ALPHA)) * teleport[node]
        if sum(abs(rank[n] - prev[n]) for n in nodes) < node_count * _TOL:
            break
    return rank
