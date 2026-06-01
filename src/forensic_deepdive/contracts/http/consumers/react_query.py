"""React Query / TanStack Query consumer extractor (DEC-046, v0.4 Item G).

Emits consumer ``CALLS_ENDPOINT`` records for the TanStack Query hooks
(``useQuery`` / ``useMutation`` / ``useInfiniteQuery`` / ``useSuspenseQuery``,
js/ts/tsx)::

    function UserProfile({ id }) {
      const { data } = useQuery({
        queryKey: ['user', id],
        queryFn: () => fetch(`/api/users/${id}`),
      });
      const add = useMutation({
        mutationFn: (body) => axios.post('/api/users', body),
      });
    }

The HTTP call lives inside the ``queryFn`` / ``mutationFn`` arrow. The bare
fetch/axios walker (``fetch_axios``) *would* see that inner call, but it attributes
to the nearest enclosing callable — the anonymous ``queryFn`` arrow, whose
pair-key name isn't a graph symbol, so that edge is filtered. **This extractor's
value-add is the attribution:** it digs the fetch/axios call out of the hook's
fn-prop (reusing ``fetch_axios._classify`` / ``_url_from``) but attributes it to
the enclosing **component/hook** — the real named callable around the
``useQuery(...)`` *call site* — so CALLS_ENDPOINT lands on a symbol the graph has.

Confidence mirrors fetch/axios: literal URL = EXTRACTED, template/numeric = INFERRED.
Only fetch/axios-backed query functions are handled; a custom-client fn is dropped
(honest — no resolvable URL).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tree_sitter import Node

from forensic_deepdive.contracts.base import Contract, ContractRole
from forensic_deepdive.contracts.http.consumers.fetch_axios import (
    _classify,
    _enclosing_symbol,
    _url_from,
    _walk,
)
from forensic_deepdive.contracts.http.normalize import (
    http_contract_id,
    is_noise_path,
    normalize_consumer_path,
)
from forensic_deepdive.contracts.http.scan import (
    iter_candidate_files,
    js_object_value,
)
from forensic_deepdive.graph.schema import Confidence

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

_MARKERS = (b"useQuery", b"useMutation", b"useInfiniteQuery", b"useSuspenseQuery")
_LANGS = ("javascript", "typescript", "tsx")
_HOOKS = frozenset({"useQuery", "useMutation", "useInfiniteQuery", "useSuspenseQuery"})
_FN_PROPS = ("queryFn", "mutationFn")


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _hook_config(call: Node) -> Node | None:
    """The first object-literal argument of a ``useQuery({...})`` hook call."""
    args = call.child_by_field_name("arguments")
    if args is None:
        return None
    for child in args.children:
        if child.type == "object":
            return child
    return None


def _query_fn(config: Node, src: bytes) -> Node | None:
    """The ``queryFn`` / ``mutationFn`` value (an arrow/function), or ``None``."""
    for prop in _FN_PROPS:
        value = js_object_value(config, prop, src)
        if value is not None and value.type in (
            "arrow_function",
            "function_expression",
            "function_declaration",
        ):
            return value
    return None


def _first_http_call(fn_node: Node, src: bytes) -> tuple[str, Node] | None:
    """The first fetch/axios call inside *fn_node*'s body, classified by the
    fetch/axios recognizer — ``(verb, url_node)`` or ``None``."""
    for node in _walk(fn_node):
        if node.type != "call_expression":
            continue
        classified = _classify(node, src)
        if classified is not None:
            return classified
    return None


def extract_react_query_consumers(ctx: ContractContext) -> list[Contract]:
    seen: set[tuple[str, str]] = set()
    contracts: list[Contract] = []
    for rel_path, src, root in iter_candidate_files(ctx, languages=_LANGS, markers=_MARKERS):
        for node in _walk(root):
            if node.type != "call_expression":
                continue
            fn = node.child_by_field_name("function")
            if fn is None or fn.type != "identifier" or _text(fn, src) not in _HOOKS:
                continue
            config = _hook_config(node)
            if config is None:
                continue
            query_fn = _query_fn(config, src)
            if query_fn is None:
                continue
            classified = _first_http_call(query_fn, src)
            if classified is None:
                continue
            verb, url_node = classified
            raw_url = _url_from(url_node, src)
            if raw_url is None:
                continue
            normalized = normalize_consumer_path(raw_url)
            if is_noise_path(normalized):
                continue
            contract_id = http_contract_id(verb, normalized)
            # Attribute to the component/hook around the *hook call*, not the
            # anonymous queryFn arrow (whose name isn't a graph symbol).
            symbol_id = _enclosing_symbol(node, src, rel_path)
            key = (contract_id, symbol_id)
            if key in seen:
                continue
            seen.add(key)
            confidence = (
                Confidence.EXTRACTED if "{param}" not in normalized else Confidence.INFERRED
            )
            contracts.append(
                Contract(
                    role=ContractRole.CONSUMER,
                    contract_id=contract_id,
                    symbol_id=symbol_id,
                    confidence=confidence,
                    evidence=f"react-query {verb}({raw_url!r})",
                    protocol="http",
                    method=verb.upper(),
                    normalized_path=normalized,
                    raw_path=raw_url,
                    framework="react-query",
                    rel_path=rel_path,
                    line=node.start_point[0],
                )
            )
    return contracts
