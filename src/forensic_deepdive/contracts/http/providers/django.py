"""Django decoupled-route provider (DEC-065, v0.6 Step 2; DEC-072, v0.7 Step 1).

Unlike the decorator-on-handler frameworks (FastAPI/Flask/Spring/NestJS/JAX-RS),
a Django route and its view handler live in **different files**: a ``urls.py``
``urlpatterns`` table maps a path to a view reference (``views.owner_list`` /
``OwnerList.as_view()``), and the view is defined in ``views.py``. So this
provider is the first to do **cross-file view resolution** — it reuses the shared
``resolve_name_to_files`` ladder (DEC-059) plus Python submodule resolution to
bind ``http::<METHOD>::<path>`` Endpoints to the real handler Symbol across files.

Shapes handled:
- ``path('owners/', views.owner_list)`` / bare ``path('owners/', owner_list)``
- ``re_path(r'^vets/(?P<id>\\d+)/$', views.vet)`` — regex → ``{param}`` (INFERRED)
- ``path('users/<int:pk>/', UserDetail.as_view())`` — class-based view
- ``path('api/', include('app.urls'))`` — recurse into the included URLconf,
  concatenating the prefix (the GitNexus #1183 prefix-drop fix shape)
- DRF ``router.register(r'users', UserViewSet)`` + ``include(router.urls)`` —
  expand a ``SimpleRouter``/``DefaultRouter`` to the standard CRUD route set.

Method: a Django function view is **method-agnostic** → emitted at the
``http::*::<path>`` key (the Spring bare-``@RequestMapping`` precedent); a consumer
joins it via the DEC-047 method-wildcard fallback. DRF CRUD actions carry their
real verb. Confidence (DEC-065): a literal ``path()``/``as_view()`` with a resolved
view → EXTRACTED; a DRF default-router expansion → EXTRACTED-by-convention; a
``re_path`` regex path or an unknown router class → INFERRED; a view resolved only
by the cross-file same-name fallback → its resolver confidence (INFERRED/AMBIGUOUS).

**Completion (DEC-072, v0.7 Step 1):**
- ``include(<variable>)`` — a variable that aliases a sub-URLconf module
  (``from app import urls as api_urls; include(api_urls)``, the wagtail shape) is
  resolved to its file and recursed, so its routes carry the parent prefix (the
  wagtail prefix-collapse fix; the GitNexus #1183 last mile).
- **CBV per-method verbs** — a class-based view's ``get``/``post``/… method defs
  yield specific verbs instead of the method-agnostic ``http::*::<path>``.
- **DRF ``@action(detail=, methods=)``** — extra non-CRUD ViewSet routes
  (``detail=True`` → ``<prefix>/{param}/<action>/``; ``detail=False`` →
  ``<prefix>/<action>/``).
- **Deep dotted view paths** (``pkg.sub.views.fn``) — the full dotted module is
  resolved, not just the trailing name.

No fabrication (DEC-065): a route whose view can't be resolved emits an Endpoint
with an empty ``symbol_id`` — the Endpoint is real (honest "we see the route, not
the handler"), but the HANDLES edge is filtered out at build (never a synthetic
handler symbol). Deferred: ``ROOT_URLCONF`` from settings (we treat any URLconf not
targeted by an ``include`` as a root).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, NamedTuple

from tree_sitter import Node

from forensic_deepdive.contracts.base import Contract, ContractRole
from forensic_deepdive.contracts.http.normalize import (
    http_contract_id,
    is_noise_path,
    normalize_provider_path,
)
from forensic_deepdive.contracts.http.scan import iter_candidate_files, py_string_literal
from forensic_deepdive.graph.schema import Confidence
from forensic_deepdive.static.imports import Import
from forensic_deepdive.static.parse import parse_source
from forensic_deepdive.static.resolver import (
    _import_alias_matches,
    _resolve_import_to_file,
    _resolve_python_import,
    resolve_name_to_files,
)

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

_MARKERS = (b"urlpatterns",)

# Django class-based-view HTTP handler methods → the verb each emits (DEC-072).
_CBV_METHODS: tuple[str, ...] = ("get", "post", "put", "patch", "delete", "head", "options")

# DRF SimpleRouter/DefaultRouter standard route set for one registered ViewSet
# (verb, path-suffix-after-prefix). The detail routes share a single ``{param}``
# pk segment. ``DefaultRouter``'s API-root + ``.json`` format routes are skipped.
_DRF_ROUTERS = frozenset({"DefaultRouter", "SimpleRouter"})
_DRF_ROUTES: tuple[tuple[str, str], ...] = (
    ("get", ""),  # list
    ("post", ""),  # create
    ("get", "{param}/"),  # retrieve
    ("put", "{param}/"),  # update
    ("patch", "{param}/"),  # partial_update
    ("delete", "{param}/"),  # destroy
)

_RE_NAMED_GROUP = re.compile(r"\(\?P<[^>]+>[^)]*\)")
_RE_GROUP = re.compile(r"\([^)]*\)")
_RE_META = re.compile(r"[\\\[\]+*?^${}|]")  # leftover regex metachars → path unreliable


# ---------------------------------------------------------------------------
# View references + small AST helpers
# ---------------------------------------------------------------------------


class _ViewRef(NamedTuple):
    """A view reference in ``urls.py``: a bare name (``owner_list``) or a
    module-qualified one (``views.owner_list`` / ``pkg.sub.views.owner_list``)."""

    module: str  # "" for a bare name; the FULL dotted object path otherwise
    member: str


class _Reg(NamedTuple):
    """One DRF ``router.register('prefix', ViewSet)`` registration."""

    prefix: str
    viewset: _ViewRef | None
    line: int


class _Entry(NamedTuple):
    """One ``urlpatterns`` element. ``kind`` discriminates the union. ``router_var``
    holds the router variable (router_include) or the include variable (var_include)."""

    kind: str  # 'route' | 'module_include' | 'router_include' | 'var_include'
    prefix: str  # the path/prefix this entry contributes
    view: _ViewRef | None  # 'route'
    target_module: str  # 'module_include' — the dotted module path (e.g. app.urls)
    router_var: str  # 'router_include' / 'var_include' — the variable name
    line: int
    is_re_path: bool


class _UrlConf(NamedTuple):
    entries: list[_Entry]
    routers: dict[str, tuple[str, list[_Reg]]]  # var -> (router_class, registrations)


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _walk(node: Node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


def _rightmost_call_name(call: Node, src: bytes) -> str:
    """The trailing identifier of a call's function (``path`` / ``re_path`` /
    ``include`` / ``router.register`` → ``register``)."""
    fn = call.child_by_field_name("function")
    if fn is None:
        return ""
    if fn.type == "identifier":
        return _text(fn, src)
    if fn.type == "attribute":
        attr = fn.child_by_field_name("attribute")
        return _text(attr, src) if attr is not None else ""
    return ""


def _positional_args(call: Node) -> list[Node]:
    args = call.child_by_field_name("arguments")
    if args is None:
        return []
    return [
        c for c in args.children if c.type not in ("(", ")", ",", "comment", "keyword_argument")
    ]


def _keyword_arg(call: Node, name: str) -> Node | None:
    """The value node of keyword argument *name* in a call's ``argument_list``."""
    args = call.child_by_field_name("arguments")
    if args is None:
        return None
    for child in args.children:
        if child.type != "keyword_argument":
            continue
        key = child.child_by_field_name("name")
        val = child.child_by_field_name("value")
        if (
            key is not None
            and val is not None
            and key.type == "identifier"
            and key.text.decode("utf-8", "replace") == name
        ):
            return val
    return None


def _view_ref(node: Node, src: bytes) -> _ViewRef | None:
    """Read a view reference node. ``owner_list`` → bare; ``views.owner_list`` /
    ``pkg.sub.views.owner_list`` → module-qualified (full dotted object path, DEC-072);
    ``OwnerList.as_view()`` → recurse on the class object."""
    if node.type == "identifier":
        return _ViewRef("", _text(node, src))
    if node.type == "attribute":
        obj = node.child_by_field_name("object")
        attr = node.child_by_field_name("attribute")
        if obj is None or attr is None:
            return None
        # The full dotted object path is the module; ``attr`` is the member. Only a
        # plain dotted identifier chain qualifies (e.g. ``pkg.sub.views``).
        if obj.type in ("identifier", "attribute"):
            return _ViewRef(_text(obj, src), _text(attr, src))
        return None
    if node.type == "call":
        fn = node.child_by_field_name("function")
        if fn is not None and fn.type == "attribute":
            attr = fn.child_by_field_name("attribute")
            if attr is not None and _text(attr, src) == "as_view":
                obj = fn.child_by_field_name("object")
                return _view_ref(obj, src) if obj is not None else None
    return None


def _regex_to_path(rx: str) -> tuple[str, bool]:
    """Convert a Django ``re_path`` regex to a normalized-able path. Returns
    ``(path, clean)`` — ``clean`` is False when regex metachars survive (the path
    is then a best-effort INFERRED guess)."""
    rx = rx.strip().lstrip("^").rstrip("$")
    rx = _RE_NAMED_GROUP.sub("{param}", rx)
    rx = _RE_GROUP.sub("{param}", rx)
    # Clean = no regex metachars survive once the {param} placeholders are removed
    # (the placeholder's own braces must not count as leftover meta).
    residual = rx.replace("{param}", "")
    return rx, not bool(_RE_META.search(residual))


def _submodule(module_path: str, name: str) -> str:
    """Join an import's module path with an imported sub-name: ``from . import x`` →
    ``.x``; ``from pkg import x`` → ``pkg.x``; bare → ``x``."""
    if not module_path:
        return name
    return module_path + name if module_path.endswith(".") else f"{module_path}.{name}"


# ---------------------------------------------------------------------------
# Per-file scan (pass 1)
# ---------------------------------------------------------------------------


def _scan_routers(root: Node, src: bytes) -> dict[str, tuple[str, list[_Reg]]]:
    """Collect ``var = DefaultRouter()`` definitions + their ``.register`` calls."""
    routers: dict[str, tuple[str, list[_Reg]]] = {}
    for node in _walk(root):
        if node.type != "assignment":
            continue
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        if left is None or right is None or left.type != "identifier" or right.type != "call":
            continue
        cls = _rightmost_call_name(right, src)
        if cls.endswith("Router"):
            routers.setdefault(_text(left, src), (cls, []))
    if not routers:
        return routers
    for node in _walk(root):
        if node.type != "call":
            continue
        fn = node.child_by_field_name("function")
        if fn is None or fn.type != "attribute":
            continue
        attr = fn.child_by_field_name("attribute")
        obj = fn.child_by_field_name("object")
        if (
            attr is None
            or obj is None
            or _text(attr, src) != "register"
            or obj.type != "identifier"
        ):
            continue
        var = _text(obj, src)
        if var not in routers:
            continue
        pos = _positional_args(node)
        prefix = py_string_literal(pos[0], src) if pos else None
        viewset = _view_ref(pos[1], src) if len(pos) > 1 else None
        routers[var][1].append(_Reg(prefix or "", viewset, node.start_point[0]))
    return routers


def _include_target(arg: Node, src: bytes) -> tuple[str, str, str]:
    """Read an ``include(...)`` argument → ``(module_path, router_var, include_var)``;
    at most one is non-empty. A string ``'app.urls'`` (or the first tuple element) →
    module; an attribute ``router.urls`` → the router var; a bare identifier
    ``api_urls`` → the include variable (a module-alias / urlpatterns list, DEC-072);
    else all empty."""
    if arg.type == "string":
        return py_string_literal(arg, src) or "", "", ""
    if arg.type == "tuple":
        first = next((c for c in arg.children if c.type == "string"), None)
        return (py_string_literal(first, src) or "", "", "") if first is not None else ("", "", "")
    if arg.type == "attribute":
        obj = arg.child_by_field_name("object")
        attr = arg.child_by_field_name("attribute")
        if (
            obj is not None
            and attr is not None
            and obj.type == "identifier"
            and _text(attr, src) == "urls"
        ):
            return "", _text(obj, src), ""
    if arg.type == "identifier":
        return "", "", _text(arg, src)
    return "", "", ""


def _parse_route_call(call: Node, src: bytes) -> _Entry | None:
    """Turn one ``path()``/``re_path()`` call into a route or include entry."""
    name = _rightmost_call_name(call, src)
    if name not in ("path", "re_path", "url"):
        return None
    pos = _positional_args(call)
    if len(pos) < 2:
        return None
    is_re = name in ("re_path", "url")
    if is_re:
        raw = py_string_literal(pos[0], src)
        if raw is None:
            return None
        prefix, clean = _regex_to_path(raw)
        if not clean:
            return None  # regex metachars survive — can't form a stable path
    else:
        prefix = py_string_literal(pos[0], src)
        if prefix is None:
            return None

    second = pos[1]
    # An include() as the 2nd arg → a mount, not a leaf route.
    if second.type == "call" and _rightmost_call_name(second, src) == "include":
        inc = _positional_args(second)
        if not inc:
            return None
        module_path, router_var, include_var = _include_target(inc[0], src)
        if module_path:
            return _Entry(
                "module_include", prefix, None, module_path, "", call.start_point[0], is_re
            )
        if router_var:
            return _Entry(
                "router_include", prefix, None, "", router_var, call.start_point[0], is_re
            )
        if include_var:  # include(<variable>) — a module-alias / urlpatterns list (DEC-072)
            return _Entry("var_include", prefix, None, "", include_var, call.start_point[0], is_re)
        return None

    view = _view_ref(second, src)
    return _Entry("route", prefix, view, "", "", call.start_point[0], is_re)


def _scan_urlpatterns(root: Node, src: bytes) -> list[_Entry]:
    """Collect entries from every ``urlpatterns = [...]`` / ``urlpatterns += [...]``
    / ``urlpatterns = router.urls`` statement in the file."""
    entries: list[_Entry] = []
    for node in _walk(root):
        target = right = None
        if node.type == "assignment" or node.type == "augmented_assignment":
            target = node.child_by_field_name("left")
            right = node.child_by_field_name("right")
        if target is None or right is None or target.type != "identifier":
            continue
        if _text(target, src) != "urlpatterns":
            continue
        # urlpatterns = router.urls  →  a router include at the root prefix.
        if right.type == "attribute":
            _mp, rv, _iv = _include_target(right, src)
            if rv:
                entries.append(
                    _Entry("router_include", "", None, "", rv, right.start_point[0], False)
                )
            continue
        if right.type != "list":
            continue
        for el in right.children:
            if el.type != "call":
                continue
            entry = _parse_route_call(el, src)
            if entry is not None:
                entries.append(entry)
    return entries


# ---------------------------------------------------------------------------
# View / module resolution (cross-file)
# ---------------------------------------------------------------------------


def _resolve_module_member(
    module_name: str,
    member: str,
    rel_path: str,
    imports: list[Import],
    defs_top_by_file: dict[str, set[str]],
    source_files_by_path: dict[str, str],
) -> str | None:
    """Resolve ``<module_name>.<member>`` (``views.owner_list`` / deep
    ``pkg.sub.views.owner_list``, DEC-072) to a file. Tries the import that binds the
    first segment (appending any deeper segments), then a direct absolute-module
    resolution. Returns the file when ``member`` is a top-level def there."""
    segments = module_name.split(".")
    first, tail = segments[0], segments[1:]
    for imp in imports:
        if imp.rel_path != rel_path or imp.language != "python":
            continue
        # from <pkg> import <first> [as alias]  →  submodule <pkg>.<first>[.<tail>]
        for ime in imp.imported_names:
            if (ime.alias or ime.name) != first:
                continue
            sub = _submodule(imp.module_path, ime.name)
            for seg in tail:
                sub = f"{sub}.{seg}"
            tgt = _resolve_python_import(
                Import(rel_path=rel_path, module_path=sub, language="python", line=0),
                source_files_by_path,
            )
            if tgt is not None and member in defs_top_by_file.get(tgt, ()):
                return tgt
        # import <first> / import a.b as <first>  (only when there are no deeper segments)
        if not tail and _import_alias_matches(imp, first):
            tgt = _resolve_import_to_file(imp, source_files_by_path)
            if tgt is not None and member in defs_top_by_file.get(tgt, ()):
                return tgt
    # Direct absolute-module resolution (deep dotted paths, e.g. ``pkg.sub.views``).
    tgt = _resolve_python_import(
        Import(rel_path=rel_path, module_path=module_name, language="python", line=0),
        source_files_by_path,
    )
    if tgt is not None and member in defs_top_by_file.get(tgt, ()):
        return tgt
    return None


def _resolve_var_to_module_file(
    var: str,
    rel_path: str,
    imports: list[Import],
    source_files_by_path: dict[str, str],
) -> str | None:
    """Resolve an ``include(<var>)`` variable that aliases a sub-URLconf module
    (``from app import urls as api_urls`` → ``app/urls.py``, DEC-072) to its file."""
    for imp in imports:
        if imp.rel_path != rel_path or imp.language != "python":
            continue
        for ime in imp.imported_names:
            if (ime.alias or ime.name) != var:
                continue
            tgt = _resolve_python_import(
                Import(
                    rel_path=rel_path,
                    module_path=_submodule(imp.module_path, ime.name),
                    language="python",
                    line=0,
                ),
                source_files_by_path,
            )
            if tgt is not None:
                return tgt
        if _import_alias_matches(imp, var):
            tgt = _resolve_import_to_file(imp, source_files_by_path)
            if tgt is not None:
                return tgt
    return None


def _resolve_view(
    view: _ViewRef,
    rel_path: str,
    imports: list[Import],
    defs_top_by_file: dict[str, set[str]],
    defs_top_by_lang: dict[str, dict[str, list[str]]],
    source_files_by_path: dict[str, str],
) -> list[tuple[str, Confidence]]:
    """Resolve a view reference to ``(symbol_id, confidence)`` pairs. Bare names use
    the shared DEC-059 ladder; module-qualified names use submodule resolution.
    Empty list → unresolvable (the caller emits an honest unmatched Endpoint)."""
    if view.module:
        tgt = _resolve_module_member(
            view.module, view.member, rel_path, imports, defs_top_by_file, source_files_by_path
        )
        if tgt is not None:
            return [(f"{tgt}::{view.member}", Confidence.EXTRACTED)]
        return []
    resolved = resolve_name_to_files(
        view.member,
        rel_path,
        "python",
        imports,
        defs_top_by_file,
        defs_top_by_lang,
        source_files_by_path,
    )
    if resolved is None:
        return []
    files, conf = resolved
    return [(f"{f}::{view.member}", conf) for f in files]


# ---------------------------------------------------------------------------
# Resolution walk (pass 2) + extractor entry point
# ---------------------------------------------------------------------------


def _build_defs(tags) -> tuple[dict[str, set[str]], dict[str, dict[str, list[str]]]]:
    """Top-level def name indexes for the resolver, from the contract context tags."""
    defs_top_by_file: dict[str, set[str]] = {}
    defs_top_by_lang: dict[str, dict[str, list[str]]] = {}
    for t in tags:
        if t.kind != "def" or t.parent:  # top-level defs only
            continue
        defs_top_by_file.setdefault(t.rel_path, set()).add(t.name)
        defs_top_by_lang.setdefault(t.language, {}).setdefault(t.name, []).append(t.rel_path)
    return defs_top_by_file, defs_top_by_lang


def _build_cbv_verbs(tags) -> dict[str, list[str]]:
    """``<file>::<ClassName> -> [verb, …]`` for class-based views: the HTTP-handler
    method defs (``get``/``post``/…) on a top-level class (DEC-072). A function view has
    no such children → not in the map → stays method-agnostic ``*``."""
    by_symbol: dict[str, set[str]] = {}
    for t in tags:
        # A CBV method is a def whose parent is a single (top-level) class name.
        if t.kind != "def" or not t.parent or "." in t.parent or t.language != "python":
            continue
        if t.name in _CBV_METHODS:
            by_symbol.setdefault(f"{t.rel_path}::{t.parent}", set()).add(t.name)
    # Canonical verb order (deterministic) per the _CBV_METHODS sequence.
    return {sym: [v for v in _CBV_METHODS if v in verbs] for sym, verbs in by_symbol.items()}


def _join_path(prefix: str, suffix: str) -> str:
    """Concatenate two Django path fragments (neither carries a leading slash;
    ``normalize_provider_path`` adds it)."""
    return prefix + suffix


def _action_routes(file_src: bytes, root: Node, class_name: str) -> list[tuple[str, str, int]]:
    """DRF ``@action(detail=, methods=)`` routes for ViewSet ``class_name`` (DEC-072):
    ``(verb, path_suffix, line)`` per (method, verb). ``detail=True`` →
    ``{param}/<action>/``; else ``<action>/``."""
    out: list[tuple[str, str, int]] = []
    for node in _walk(root):
        if node.type != "class_definition":
            continue
        name_node = node.child_by_field_name("name")
        if name_node is None or _text(name_node, file_src) != class_name:
            continue
        body = node.child_by_field_name("body")
        if body is None:
            continue
        for member in body.children:
            if member.type != "decorated_definition":
                continue
            definition = member.child_by_field_name("definition")
            if definition is None or definition.type != "function_definition":
                continue
            mname_node = definition.child_by_field_name("name")
            if mname_node is None:
                continue
            action = _action_decorator(member, file_src)
            if action is None:
                continue
            detail, methods = action
            method_name = _text(mname_node, file_src)
            suffix = (f"{{param}}/{method_name}/") if detail else f"{method_name}/"
            for verb in methods:
                out.append((verb, suffix, mname_node.start_point[0]))
    return out


def _action_decorator(decorated: Node, src: bytes) -> tuple[bool, list[str]] | None:
    """If a method carries ``@action(detail=, methods=)``, return ``(detail, [verb,…])``
    (methods default ``['get']``); else ``None``."""
    for child in decorated.children:
        if child.type != "decorator":
            continue
        call = next((c for c in child.children if c.type == "call"), None)
        if call is None or _rightmost_call_name(call, src) != "action":
            continue
        detail_node = _keyword_arg(call, "detail")
        detail = detail_node is not None and _text(detail_node, src) == "True"
        methods_node = _keyword_arg(call, "methods")
        methods: list[str] = []
        if methods_node is not None and methods_node.type == "list":
            for el in methods_node.children:
                if el.type == "string":
                    val = py_string_literal(el, src)
                    if val and val.lower() in _CBV_METHODS:
                        methods.append(val.lower())
        return detail, (methods or ["get"])
    return None


class _Emitter:
    """Accumulates provider Contracts while walking the URLconf include tree."""

    def __init__(self, ctx: ContractContext, urlconfs: dict[str, _UrlConf]) -> None:
        self.ctx = ctx
        self.urlconfs = urlconfs
        self.defs_top_by_file, self.defs_top_by_lang = _build_defs(ctx.tags)
        self.cbv_verbs = _build_cbv_verbs(ctx.tags)
        self.seen: set[tuple[str, str]] = set()
        self.contracts: list[Contract] = []
        self._parsed: dict[str, tuple[bytes, Node] | None] = {}

    def _parse_file(self, rel_path: str) -> tuple[bytes, Node] | None:
        """Parse a (non-URLconf) Python file on demand — for reading ``@action``
        decorators in a ViewSet's file. Cached per file."""
        if rel_path not in self._parsed:
            try:
                data = (self.ctx.repo_path / rel_path).read_bytes()
                self._parsed[rel_path] = (data, parse_source(data, "python").root_node)
            except OSError:
                self._parsed[rel_path] = None
        return self._parsed[rel_path]

    def _emit(
        self,
        verb: str,
        raw: str,
        symbol_id: str,
        confidence: Confidence,
        rel_path: str,
        line: int,
        evidence: str,
    ) -> None:
        normalized = normalize_provider_path(raw)
        if is_noise_path(normalized):
            return
        contract_id = http_contract_id(verb, normalized)
        key = (contract_id, symbol_id)
        if key in self.seen:
            return
        self.seen.add(key)
        self.contracts.append(
            Contract(
                role=ContractRole.PROVIDER,
                contract_id=contract_id,
                symbol_id=symbol_id,
                confidence=confidence,
                evidence=evidence,
                protocol="http",
                method=verb.upper(),
                normalized_path=normalized,
                raw_path=raw,
                framework="django",
                rel_path=rel_path,
                line=line,
            )
        )

    def _emit_route(self, entry: _Entry, full_path: str, rel_path: str) -> None:
        views = (
            _resolve_view(
                entry.view,
                rel_path,
                self.ctx.imports,
                self.defs_top_by_file,
                self.defs_top_by_lang,
                self.ctx.source_files_by_path,
            )
            if entry.view is not None
            else []
        )
        route_conf = Confidence.INFERRED if entry.is_re_path else Confidence.EXTRACTED
        if not views:
            # Honest unmatched: the Endpoint is real, the handler isn't located.
            self._emit(
                "*",
                full_path,
                "",
                route_conf,
                rel_path,
                entry.line,
                "django route (unresolved view)",
            )
            return
        for symbol_id, res_conf in views:
            conf = _min_conf(route_conf, res_conf)
            # CBV per-method verbs (DEC-072): a class-based view's get/post/… → specific
            # verbs; a function view (no method children) stays method-agnostic ``*``.
            verbs = self.cbv_verbs.get(symbol_id)
            if verbs:
                for verb in verbs:
                    self._emit(verb, full_path, symbol_id, conf, rel_path, entry.line, "django CBV")
            else:
                self._emit("*", full_path, symbol_id, conf, rel_path, entry.line, "django path()")

    def _emit_router(self, router_var: str, prefix: str, rel_path: str) -> None:
        urlconf = self.urlconfs.get(rel_path)
        if urlconf is None or router_var not in urlconf.routers:
            return
        router_class, regs = urlconf.routers[router_var]
        by_convention = router_class in _DRF_ROUTERS
        base_conf = Confidence.EXTRACTED if by_convention else Confidence.INFERRED
        for reg in regs:
            if reg.viewset is None or not reg.prefix:
                continue
            views = _resolve_view(
                reg.viewset,
                rel_path,
                self.ctx.imports,
                self.defs_top_by_file,
                self.defs_top_by_lang,
                self.ctx.source_files_by_path,
            )
            reg_base = _join_path(prefix, reg.prefix.rstrip("/") + "/")
            targets = views or [("", base_conf)]
            for symbol_id, res_conf in targets:
                conf = base_conf if not symbol_id else _min_conf(base_conf, res_conf)
                for verb, suffix in _DRF_ROUTES:
                    self._emit(
                        verb,
                        reg_base + suffix,
                        symbol_id,
                        conf,
                        rel_path,
                        reg.line,
                        f"django drf {router_class}.register({reg.prefix!r})",
                    )
                # DRF @action extra routes (DEC-072), read from the ViewSet's file.
                if symbol_id and "::" in symbol_id:
                    vfile, vclass = symbol_id.split("::", 1)
                    parsed = self._parse_file(vfile)
                    if parsed is not None:
                        fsrc, froot = parsed
                        for verb, action_suffix, line in _action_routes(fsrc, froot, vclass):
                            self._emit(
                                verb,
                                reg_base + action_suffix,
                                symbol_id,
                                conf,
                                rel_path,
                                line,
                                f"django drf @action {vclass}",
                            )

    def walk(self, rel_path: str, prefix: str, visited: set[str]) -> None:
        urlconf = self.urlconfs.get(rel_path)
        if urlconf is None or rel_path in visited:
            return
        visited = visited | {rel_path}
        for entry in urlconf.entries:
            if entry.kind == "route" and entry.view is not None:
                self._emit_route(entry, _join_path(prefix, entry.prefix), rel_path)
            elif entry.kind == "router_include":
                self._emit_router(entry.router_var, _join_path(prefix, entry.prefix), rel_path)
            elif entry.kind == "module_include":
                tgt = _resolve_python_import(
                    Import(
                        rel_path=rel_path,
                        module_path=entry.target_module,
                        language="python",
                        line=0,
                    ),
                    self.ctx.source_files_by_path,
                )
                if tgt is not None:
                    self.walk(tgt, _join_path(prefix, entry.prefix), visited)
            elif entry.kind == "var_include":
                # include(<variable>): resolve the module-alias variable → recurse (DEC-072);
                # fall back to a local router of the same var name.
                tgt = _resolve_var_to_module_file(
                    entry.router_var, rel_path, self.ctx.imports, self.ctx.source_files_by_path
                )
                if tgt is not None:
                    self.walk(tgt, _join_path(prefix, entry.prefix), visited)
                elif urlconf is not None and entry.router_var in urlconf.routers:
                    self._emit_router(entry.router_var, _join_path(prefix, entry.prefix), rel_path)


def _min_conf(a: Confidence, b: Confidence) -> Confidence:
    """The weaker (less certain) of two confidences (EXTRACTED > INFERRED > AMBIGUOUS)."""
    order = {Confidence.EXTRACTED: 2, Confidence.INFERRED: 1, Confidence.AMBIGUOUS: 0}
    return a if order[a] <= order[b] else b


def _included_targets(urlconfs: dict[str, _UrlConf], ctx: ContractContext) -> set[str]:
    """Files reached by some ``include(...)`` (string OR variable, DEC-072) — they are
    mounted modules, not roots, so their routes carry the parent prefix."""
    included: set[str] = set()
    for rel_path, urlconf in urlconfs.items():
        for entry in urlconf.entries:
            if entry.kind == "module_include":
                tgt = _resolve_python_import(
                    Import(
                        rel_path=rel_path,
                        module_path=entry.target_module,
                        language="python",
                        line=0,
                    ),
                    ctx.source_files_by_path,
                )
            elif entry.kind == "var_include":
                tgt = _resolve_var_to_module_file(
                    entry.router_var, rel_path, ctx.imports, ctx.source_files_by_path
                )
            else:
                continue
            if tgt is not None:
                included.add(tgt)
    return included


def extract_django_providers(ctx: ContractContext) -> list[Contract]:
    """Scan every Django URLconf, resolve includes from each root URLconf, and emit
    ``http::<METHOD>::<path>`` providers bound to cross-file view handlers (DEC-065/072)."""
    urlconfs: dict[str, _UrlConf] = {}
    for rel_path, src, root in iter_candidate_files(ctx, languages=("python",), markers=_MARKERS):
        entries = _scan_urlpatterns(root, src)
        routers = _scan_routers(root, src)
        if entries or routers:
            urlconfs[rel_path] = _UrlConf(entries, routers)

    if not urlconfs:
        return []

    # A URLconf reached by some include() is a mounted module — its routes are emitted
    # with the parent prefix, not bare. Files not targeted by any include are roots (we
    # lack settings.ROOT_URLCONF — DEC-065). Variable-includes count too (DEC-072).
    included = _included_targets(urlconfs, ctx)

    emitter = _Emitter(ctx, urlconfs)
    for rel_path in sorted(urlconfs):
        if rel_path in included:
            continue  # reached via its parent's include() instead
        emitter.walk(rel_path, "", set())
    return emitter.contracts
