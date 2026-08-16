# What's proven, and what isn't

Relocated from the README lead (2026-08-16, DEC-119) — a distribution/positioning pass,
not a content change. The honest framing itself is unchanged; it just no longer competes
with the pitch in the shop window. If you're deciding whether to trust this tool's
output, start here.

Deepdive is an **assisted-analysis** tool. A real fresh-agent onboarding test confirmed
it's **usable** and that an agent **auto-discovers** `AGENT_BRIEF.md` and routes to the
right skill unprompted, and a grounded [MCP tool review](v0.7/mcp-tool-review.md) found
the git-archaeology and curated briefs are the high-trust core. The **autonomous
end-to-end** question — whether deepdive-seeding makes an agent *resolve* real issues
measurably faster — is **still not proven**. A model-free localization **pilot** is
recorded in [`experiments/fastcontext/RESULTS.md`](../../experiments/fastcontext/RESULTS.md),
where the static seed turns out to be a *weak* prior, and the end-to-end measurement
remains blocked on hardware (it needs a GPU plus a frontier main-agent endpoint). No
autonomous-execution claims are made here.

Accepted across real repos including Apache Superset, wagtail (Django),
spring-petclinic, ripgrep, fastapi, and Iris-Nearby (Flutter/Dart). See the rest of
[`docs/findings/`](README.md) for the per-release detail behind that claim.
