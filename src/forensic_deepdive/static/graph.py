"""NetworkX symbol-graph builder.

Builds the file-to-file dependency graph that ``pagerank.py`` ranks. Structure
ported from Aider's ``RepoMap.get_ranked_tags`` (Apache-2.0); the ``aider``
package is not a dependency. See DEC-003 and NOTICE.

The graph is a ``networkx.MultiDiGraph`` of repo-relative file paths. An edge
``A -> B`` means file ``A`` references an identifier that file ``B`` defines;
each shared identifier contributes one parallel edge so PageRank can weight
files by how heavily — and how diversely — they are depended upon.

Edges are scoped per DEC-012: only same-language file pairs are linked (no FFI
modeling), and a file that itself defines an identifier resolves references to
it locally rather than linking to other files' same-named definitions. The
pipeline feeds this builder production source tags only — test and fixture
files are excluded upstream.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import networkx as nx

from forensic_deepdive.static.tags import Tag

# Identifiers starting with "_" (private / dunder by convention) carry less
# architectural signal; their edges are down-weighted. Ported from Aider.
_PRIVATE_WEIGHT = 0.1
_PUBLIC_WEIGHT = 1.0


@dataclass
class SymbolGraph:
    """The symbol graph plus the indexes used to interpret PageRank output."""

    graph: nx.MultiDiGraph
    defines: dict[str, set[str]]  # identifier -> files that define it
    references: dict[str, list[str]]  # identifier -> files that reference it
    definitions: dict[tuple[str, str], list[Tag]]  # (file, identifier) -> defs
    files: set[str] = field(default_factory=set)


def build_symbol_graph(tags: list[Tag]) -> SymbolGraph:
    """Build a :class:`SymbolGraph` from a flat list of tags across all files.

    Mirrors Aider's algorithm: index definitions and references, intersect them
    to find cross-file identifiers, then add weighted referencer->definer edges
    (reference counts are sqrt-scaled so a few hot call sites do not dominate).
    """
    defines: dict[str, set[str]] = defaultdict(set)
    references: dict[str, list[str]] = defaultdict(list)
    definitions: dict[tuple[str, str], list[Tag]] = defaultdict(list)
    files: set[str] = set()
    file_language: dict[str, str] = {}

    for tag in tags:
        files.add(tag.rel_path)
        file_language.setdefault(tag.rel_path, tag.language)
        if tag.kind == "def":
            defines[tag.name].add(tag.rel_path)
            definitions[(tag.rel_path, tag.name)].append(tag)
        elif tag.kind == "ref":
            references[tag.name].append(tag.rel_path)

    # If a language yields no reference captures at all, fall back to treating
    # every definition as a reference so the graph is not empty (Aider does
    # the same). Only applies when references is globally empty.
    if not references:
        references = {name: list(file_set) for name, file_set in defines.items()}

    graph: nx.MultiDiGraph = nx.MultiDiGraph()
    graph.add_nodes_from(files)  # keep symbol-bearing files even if unconnected

    cross_file_idents = set(defines) & set(references)
    for ident in cross_file_idents:
        definers = defines[ident]
        weight_mult = _PRIVATE_WEIGHT if ident.startswith("_") else _PUBLIC_WEIGHT
        for referencer, num_refs in Counter(references[ident]).items():
            # DEC-012 (local shadowing): a file that itself defines this
            # identifier resolves the reference locally — no cross-file edge.
            if referencer in definers:
                continue
            referencer_language = file_language.get(referencer)
            scaled = math.sqrt(num_refs)
            for definer in definers:
                # DEC-012 (language scoping): no cross-language edges.
                if file_language.get(definer) != referencer_language:
                    continue
                graph.add_edge(
                    referencer,
                    definer,
                    weight=weight_mult * scaled,
                    ident=ident,
                )

    return SymbolGraph(
        graph=graph,
        defines={name: set(file_set) for name, file_set in defines.items()},
        references={name: list(refs) for name, refs in references.items()},
        definitions={key: list(val) for key, val in definitions.items()},
        files=files,
    )
