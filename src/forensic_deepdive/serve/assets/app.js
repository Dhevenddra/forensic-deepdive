/* forensic-deepdive graph explorer (DEC-053).
 *
 * Thin vanilla-JS client over the vendored Sigma.js (WebGL) + graphology stack.
 * The backend does all the level-of-detail bounding/filtering server-side
 * (`/api/graph` is never the whole graph); the client lays the bounded graph
 * out (ForceAtlas2), colours nodes by Louvain community, and shows a
 * context/trace panel on click. Globals: `graphology`, `graphologyLibrary`,
 * `Sigma` (loaded as UMD bundles by index.html).
 */
(function () {
  "use strict";

  var Graph = graphology.MultiDirectedGraph;
  var fa2 = graphologyLibrary.layoutForceAtlas2;
  var louvain = graphologyLibrary.communitiesLouvain;

  var sigma = null;
  var state = { edgeTypes: null, meta: null, lastGraph: null };

  var els = {
    repo: document.getElementById("repo-name"),
    edgeTypes: document.getElementById("edge-types"),
    minConfidence: document.getElementById("min-confidence"),
    language: document.getElementById("language"),
    directory: document.getElementById("directory"),
    maxNodes: document.getElementById("max-nodes"),
    maxEdges: document.getElementById("max-edges"),
    apply: document.getElementById("apply"),
    reset: document.getElementById("reset"),
    status: document.getElementById("status"),
    canvas: document.getElementById("canvas"),
    panel: document.getElementById("panel"),
  };

  // Louvain community → a stable, readable palette.
  var PALETTE = [
    "#4c6ef5", "#f06595", "#20c997", "#fab005", "#7950f2", "#ff922b",
    "#15aabf", "#e64980", "#82c91e", "#fd7e14", "#22b8cf", "#be4bdb",
  ];

  function setStatus(msg) { els.status.textContent = msg; }

  function getJSON(url) {
    return fetch(url).then(function (r) { return r.json(); });
  }

  function selectedEdgeTypes() {
    var boxes = els.edgeTypes.querySelectorAll("input[type=checkbox]");
    var on = [];
    boxes.forEach(function (b) { if (b.checked) on.push(b.value); });
    return on;
  }

  function buildEdgeTypeControls(meta) {
    els.edgeTypes.innerHTML = "";
    meta.edge_types.forEach(function (et) {
      var count = (meta.edge_type_counts && meta.edge_type_counts[et]) || 0;
      var on = meta.default_edge_types.indexOf(et) !== -1 && count > 0;
      var label = document.createElement("label");
      var cb = document.createElement("input");
      cb.type = "checkbox"; cb.value = et; cb.checked = on;
      cb.disabled = count === 0;
      label.appendChild(cb);
      var span = document.createElement("span");
      span.textContent = et + " (" + count + ")";
      label.appendChild(span);
      els.edgeTypes.appendChild(label);
    });
  }

  function fillSelect(sel, values) {
    values.forEach(function (v) {
      var o = document.createElement("option");
      o.value = v; o.textContent = v;
      sel.appendChild(o);
    });
  }

  function buildQuery() {
    var p = new URLSearchParams();
    p.set("edge_types", selectedEdgeTypes().join(","));
    p.set("min_confidence", els.minConfidence.value);
    if (els.language.value) p.set("language", els.language.value);
    if (els.directory.value) p.set("directory", els.directory.value);
    p.set("max_nodes", els.maxNodes.value || "300");
    p.set("max_edges", els.maxEdges.value || "1500");
    return p.toString();
  }

  function render(payload) {
    state.lastGraph = payload;
    var graph = new Graph();
    payload.nodes.forEach(function (n) {
      graph.addNode(n.key, Object.assign({}, n.attributes));
    });
    payload.edges.forEach(function (e) {
      // sigma's default edge program is "line"; drop the server "arrow" hint to
      // avoid requiring a registered arrow program in the vendored build.
      var a = Object.assign({}, e.attributes);
      delete a.type;
      if (!graph.hasEdge(e.source, e.target) || graph.multi) {
        try { graph.addEdgeWithKey(e.key, e.source, e.target, a); }
        catch (err) { /* duplicate key across reloads — ignore */ }
      }
    });

    if (graph.order > 0) {
      louvain.assign(graph, { nodeCommunityAttribute: "community" });
      graph.forEachNode(function (key, attr) {
        if (typeof attr.community === "number") {
          graph.setNodeAttribute(key, "color",
            attr.ntype === "endpoint" ? attr.color : PALETTE[attr.community % PALETTE.length]);
        }
      });
      var settings = fa2.inferSettings(graph);
      fa2.assign(graph, { iterations: graph.order > 600 ? 120 : 260, settings: settings });
    }

    if (sigma) { sigma.kill(); sigma = null; }
    sigma = new Sigma(graph, els.canvas, {
      defaultEdgeColor: "#3a4250",
      minCameraRatio: 0.05,
      maxCameraRatio: 12,
      labelRenderedSizeThreshold: 7,
      labelColor: { color: "#e9ecef" },
    });
    sigma.on("clickNode", function (e) { openPanel(e.node); });
    sigma.on("clickStage", function () { closePanel(); });

    var m = payload.meta;
    setStatus(
      m.node_count + " nodes · " + m.edge_count + " edges" +
      (m.truncated ? " · bounded (LOD)" : "")
    );
  }

  function tag(conf) {
    if (!conf) return "";
    return ' <span class="tag ' + conf + '">' + conf + "</span>";
  }

  function listFrom(items, fmt) {
    if (!items || !items.length) return '<li class="dim">—</li>';
    return items.map(fmt).join("");
  }

  function openPanel(key) {
    els.panel.classList.remove("hidden");
    els.panel.innerHTML = '<button class="close">×</button><div class="empty">loading…</div>';
    els.panel.querySelector(".close").onclick = closePanel;
    getJSON("/api/node?key=" + encodeURIComponent(key)).then(function (d) {
      els.panel.innerHTML = renderPanel(key, d) +
        '<button class="close" style="position:absolute;top:10px;right:14px">×</button>';
      var c = els.panel.querySelectorAll(".close");
      c.forEach(function (b) { b.onclick = closePanel; });
    });
  }

  function renderPanel(key, d) {
    if (d.endpoint !== undefined) return renderEndpointPanel(d);
    var ctx = d.context || {};
    var sym = ctx.symbol || {};
    var html = '<span class="kind">' + (sym.kind || "symbol") + "</span>";
    html += "<h3>" + (sym.qualified_name || key) + "</h3>";
    if (sym.file_path)
      html += '<p class="dim">' + sym.file_path + ":" + (sym.line_start || "?") + "</p>";

    if (d.trace_downstream) {
      html += "<h4>Cross-stack (downstream)</h4><ul>";
      html += listFrom(d.trace_downstream.chains, function (ch) {
        return "<li>" + ch.method + " " + ch.normalized_path +
          (ch.handler ? " → " + ch.handler : ' <em class="dim">(unlocated)</em>') +
          tag(ch.call_confidence) + "</li>";
      });
      html += "</ul>";
    }
    if (d.trace_upstream) {
      html += "<h4>Cross-stack (who calls this)</h4><ul>";
      html += listFrom(d.trace_upstream.chains, function (ch) {
        return "<li>" + ch.method + " " + ch.endpoint + " — " +
          (ch.callers || []).length + " caller(s)</li>";
      });
      html += "</ul>";
    }

    html += "<h4>Callers</h4><ul>" +
      listFrom(ctx.callers, function (c) {
        return "<li>" + c.qualified_name + tag(c.confidence) + "</li>";
      }) + "</ul>";
    html += "<h4>Callees</h4><ul>" +
      listFrom(ctx.callees, function (c) {
        return "<li>" + c.qualified_name + tag(c.confidence) + "</li>";
      }) + "</ul>";
    if (ctx.extends && ctx.extends.length)
      html += "<h4>Extends</h4><ul>" +
        listFrom(ctx.extends, function (x) { return "<li>" + x + "</li>"; }) + "</ul>";
    if (ctx.dominant_author)
      html += "<h4>Owner</h4><p>" + ctx.dominant_author.name + " (" +
        ctx.dominant_author.commits + " commits)</p>";
    return html;
  }

  function renderEndpointPanel(d) {
    if (!d.endpoint) return '<div class="empty">endpoint not found</div>';
    var e = d.endpoint;
    var html = '<span class="kind">endpoint' + (e.spec_backed ? " · spec-backed" : "") + "</span>";
    html += "<h3>" + e.method + " " + e.normalized_path + "</h3>";
    html += '<p class="dim">' + e.contract_id + " · " + (e.framework || e.protocol) + "</p>";
    html += "<h4>Handlers</h4><ul>" +
      listFrom(d.handlers, function (h) {
        return "<li>" + h.qualified_name + tag(h.confidence) + "</li>";
      }) + "</ul>";
    html += "<h4>Consumers</h4><ul>" +
      listFrom(d.consumers, function (c) {
        return "<li>" + c.qualified_name + tag(c.confidence) + "</li>";
      }) + "</ul>";
    if (d.unlocated)
      html += '<p class="dim">No located handler — documented but unlocated.</p>';
    return html;
  }

  function closePanel() { els.panel.classList.add("hidden"); }

  function loadGraph() {
    setStatus("querying graph…");
    getJSON("/api/graph?" + buildQuery()).then(render).catch(function (err) {
      setStatus("error: " + err);
    });
  }

  function init() {
    getJSON("/api/meta").then(function (meta) {
      state.meta = meta;
      els.repo.textContent = meta.name;
      buildEdgeTypeControls(meta);
      fillSelect(els.language, meta.languages);
      fillSelect(els.directory, meta.directories);
      els.apply.onclick = loadGraph;
      els.reset.onclick = function () {
        buildEdgeTypeControls(meta);
        els.minConfidence.value = "AMBIGUOUS";
        els.language.value = ""; els.directory.value = "";
        els.maxNodes.value = "300"; els.maxEdges.value = "1500";
        loadGraph();
      };
      loadGraph();
    }).catch(function (err) { setStatus("failed to load: " + err); });
  }

  init();
})();
