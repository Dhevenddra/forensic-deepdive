# Vendored client libraries (DEC-053)

These bundles are **vendored, pinned, and offline** (DEC-009 — local-only is
co-equal; a tool for proprietary code cannot fetch a CDN at view-time). All
three are MIT-licensed; their notices ship in the repository-root `NOTICE`.

| File | Package | Version | License | Source |
|---|---|---|---|---|
| `sigma.min.js` | sigma | 2.4.0 | MIT | https://cdn.jsdelivr.net/npm/sigma@2.4.0/build/sigma.min.js |
| `graphology.umd.min.js` | graphology | 0.25.4 | MIT | https://cdn.jsdelivr.net/npm/graphology@0.25.4/dist/graphology.umd.min.js |
| `graphology-library.min.js` | graphology-library | 0.8.0 | MIT | https://cdn.jsdelivr.net/npm/graphology-library@0.8.0/dist/graphology-library.min.js |

Globals exposed: `Sigma`, `graphology` (the `Graph` constructor), and
`graphologyLibrary` (`.layoutForceAtlas2`, `.communitiesLouvain`).

To refresh a pinned version: re-download from the URL above, bump the version
here, and re-verify the `NOTICE` attribution. There is intentionally **no npm /
Vite build step** — the UMD bundles are loaded directly via `<script>` tags so
the UI is fully offline.
