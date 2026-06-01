// Generated-style HTTP client for the OpenAPI codegen-shortcut fixture (DEC-048).
// Both URLs are template literals → INFERRED consumers; the committed openapi.json
// is what upgrades the joins/edges to EXTRACTED.

function loadItem(id) {
  // Joins the in-code FastAPI handler; spec-backed → ROUTES_TO EXTRACTED.
  return fetch(`/api/items/${id}`);
}

function loadOrphan(oid) {
  // Hits a spec-only endpoint (no handler); CALLS_ENDPOINT EXTRACTED, no ROUTES_TO.
  return fetch(`/api/orphan/${oid}`);
}
