# Releasing claudecad

## One-time setup (Mike, on pypi.org — cannot be automated)

1. pypi.org → account → Publishing → "Add a new pending publisher":
   - PyPI project name: `claudecad` (verified available 2026-07-15)
   - Owner: `mdbritt`  ·  Repository: `claudecad`
   - Workflow: `release.yml`  ·  Environment: `pypi`
2. github.com/mdbritt/claudecad → Settings → Environments → create `pypi`
   (optionally add yourself as a required reviewer — that makes every
   publish a one-click manual approval).

## Each release

1. Bump `version` in BOTH `pyproject.toml` and `.claude-plugin/plugin.json`
   (keep them identical), commit, push, wait for CI green (the clean-room
   job is the release gate).
2. `git tag vX.Y.Z && git push origin vX.Y.Z`
3. `gh release create vX.Y.Z --generate-notes` — publishing the GitHub
   release triggers `release.yml`, which builds and uploads to PyPI via
   trusted publishing.
4. Verify: `uvx claudecad@X.Y.Z new smoke && cd smoke && uv sync &&
   uv run python -m designs.smoke.build` (fresh machine-equivalent).

## Plugin consumers

`/plugin marketplace add mdbritt/claudecad` then `/plugin install
claudecad` — the plugin version comes from `.claude-plugin/plugin.json`
at the repo's default branch; no separate publish step.
