"""Django decoupled-route provider (DEC-065, v0.6 Step 2 — research §5).

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

Method: a Django function/class view is **method-agnostic** → emitted at the
``http::*::<path>`` key (the Spring bare-``@RequestMapping`` precedent); a consumer
joins it via the DEC-047 method-wildcard fallback. DRF CRUD actions carry their
real verb. Confidence (DEC-065): a literal ``path()``/``as_view()`` with a resolved
view → EXTRACTED; a DRF default-router expansion → EXTRACTED-by-convention; a
``re_path`` regex path or an unknown router class → INFERRED; a view resolved only
by the cross-file same-name fallback → its resolver confidence (INFERRED/AMBIGUOUS).

No fabrication (DEC-065): a route whose view can't be resolved emits an Endpoint
with an empty ``symbol_id`` — the Endpoint is real (honest "we see the route, not
the handler"), but the HANDLES edge is filtered out at build (never a synthetic
handler symbol). Deferred: DRF ``@action`` detail/list routes; ``ROOT_URLCONF``
from settings (we treat any URLconf not targeted by an ``include`` as a root).
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
from forensic_deepdive.static.resolver import (
    _import_alias_matches,
    _resolve_import_to_file,
    _resolve_python_import,
    resolve_name_to_files,
)

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

_MARKERS = (b"urlpatterns",)

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
    module-qualified one (``views.owner_list``)."""

    module: str  # "" for a bare name
    member: str


class _Reg(NamedTuple):
    """One DRF ``router.register('prefix', ViewSet)`` registration."""

    prefix: str
    viewset: _ViewRef | None
    line: int


class _Entry(NamedTuple):
    """One ``urlpatterns`` element. ``kind`` discriminates the union."""

    kind: str  # 'route' | 'module_include' | 'router_include'
    prefix: str  # the path/prefix this entry contributes
    view: _ViewRef | None  # 'route'
    target_module: str  # 'module_include' — the dotted module path (e.g. app.urls)
    router_var: str  # 'router_include'
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


def _view_ref(node: Node, src: bytes) -> _ViewRef | None:
    """Read a view reference node. ``owner_list`` → bare; ``views.owner_list`` →
    module-qualified; ``OwnerList.as_view()`` → recurse on the class object."""
    if node.type == "identifier":
        return _ViewRef("", _text(node, src))
    if node.type == "attribute":
        obj = node.child_by_field_name("object")
        attr = node.child_by_field_name("attribute")
        if obj is None or attr is None:
            return None
        if obj.type == "identifier":
            return _ViewRef(_text(obj, src), _text(attr, src))
        # deeper (pkg.views.fn) — best-effort: use the object's trailing name.
        if obj.type == "attribute":
            inner = obj.child_by_field_name("attribute")
            if inner is not None:
                return _ViewRef(_text(inner, src), _text(attr, src))
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


def _include_target(arg: Node, src: bytes) -> tuple[str, str]:
    """Read an ``include(...)`` argument → ``(module_path, router_var)``; exactly
    one is non-empty. A string ``'app.urls'`` (or the first element of a tuple) →
    module; an attribute ``router.urls`` → the router var; else both empty."""
    if arg.type == "string":
        return py_string_literal(arg, src) or "", ""
    if arg.type == "tuple":
        first = next((c for c in arg.children if c.type == "string"), None)
        return (py_string_literal(first, src) or "", "") if first is not None else ("", "")
    if arg.type == "attribute":
        obj = arg.child_by_field_name("object")
        attr = arg.child_by_field_name("attribute")
        if (
            obj is not None
            and attr is not None
            and obj.type == "identifier"
            and _text(attr, src) == "urls"
        ):
            return "", _text(obj, src)
    return "", ""


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
        module_path, router_var = _include_target(inc[0], src)
        if module_path:
            return _Entry(
                "module_include", prefix, None, module_path, "", call.start_point[0], is_re
            )
        if router_var:
            return _Entry(
                "router_include", prefix, None, "", router_var, call.start_point[0], is_re
            )
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
            _mp, rv = _include_target(right, src)
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
# View resolution (cross-file)
# ---------------------------------------------------------------------------


def _resolve_module_member(
    module_name: str,
    member: str,
    rel_path: str,
    imports: list[Import],
    defs_top_by_file: dict[str, set[str]],
    source_files_by_path: dict[str, str],
) -> str | None:
    """Resolve ``<module_name>.<member>`` (e.g. ``views.owner_list``) to a file by
    finding the import that binds ``module_name`` as a Python submodule, then
    confirming ``member`` is a top-level def there. Import-backed → EXTRACTED."""
    for imp in imports:
        if imp.rel_path != rel_path or imp.language != "python":
            continue
        # from <pkg> import <module_name>  (submodule import)
        for ime in imp.imported_names:
            if (ime.alias or ime.name) != module_name:
                continue
            mp = imp.module_path
            if not mp:
                sub = ime.name
            elif mp.endswith("."):
                sub = mp + ime.name
            else:
                sub = mp + "." + ime.name
            tgt = _resolve_python_import(
                Import(rel_path=rel_path, module_path=sub, language="python", line=0),
                source_files_by_path,
            )
            if tgt is not None and member in defs_top_by_file.get(tgt, ()):
                return tgt
        # import <module_name> / import a.b as <module_name>
        if _import_alias_matches(imp, module_name):
            tgt = _resolve_import_to_file(imp, source_files_by_path)
            if tgt is not None and member in defs_top_by_file.get(tgt, ()):
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


def _join_path(prefix: str, suffix: str) -> str:
    """Concatenate two Django path fragments (neither carries a leading slash;
    ``normalize_provider_path`` adds it)."""
    return prefix + suffix


class _Emitter:
    """Accumulates provider Contracts while walking the URLconf include tree."""

    def __init__(self, ctx: ContractContext, urlconfs: dict[str, _UrlConf]) -> None:
        self.ctx = ctx
        self.urlconfs = urlconfs
        self.defs_top_by_file, self.defs_top_by_lang = _build_defs(ctx.tags)
        self.seen: set[tuple[str, str]] = set()
        self.contracts: list[Contract] = []

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


def _min_conf(a: Confidence, b: Confidence) -> Confidence:
    """The weaker (less certain) of two confidences (EXTRACTED > INFERRED > AMBIGUOUS)."""
    order = {Confidence.EXTRACTED: 2, Confidence.INFERRED: 1, Confidence.AMBIGUOUS: 0}
    return a if order[a] <= order[b] else b


def extract_django_providers(ctx: ContractContext) -> list[Contract]:
    """Scan every Django URLconf, resolve includes from each root URLconf, and emit
    ``http::<METHOD>::<path>`` providers bound to cross-file view handlers (DEC-065)."""
    urlconfs: dict[str, _UrlConf] = {}
    for rel_path, src, root in iter_candidate_files(ctx, languages=("python",), markers=_MARKERS):
        entries = _scan_urlpatterns(root, src)
        routers = _scan_routers(root, src)
        if entries or routers:
            urlconfs[rel_path] = _UrlConf(entries, routers)

    if not urlconfs:
        return []

    # A URLconf that is the target of some include() is a mounted module — its
    # routes are emitted with the parent prefix, not bare. Files not targeted by
    # any include are root URLconfs (we lack settings.ROOT_URLCONF — DEC-065).
    included: set[str] = set()
    for rel_path, urlconf in urlconfs.items():
        for entry in urlconf.entries:
            if entry.kind != "module_include":
                continue
            tgt = _resolve_python_import(
                Import(
                    rel_path=rel_path, module_path=entry.target_module, language="python", line=0
                ),
                ctx.source_files_by_path,
            )
            if tgt is not None:
                included.add(tgt)

    emitter = _Emitter(ctx, urlconfs)
    for rel_path in sorted(urlconfs):
        if rel_path in included:
            continue  # reached via its parent's include() instead
        emitter.walk(rel_path, "", set())
    return emitter.contracts
