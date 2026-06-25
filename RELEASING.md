# Releasing OpenQuant India to PyPI

This monorepo publishes seven packages: `oq-core`, `oq-data`, `oq-backtest`,
`oq-broker`, `oq-mcp`, `oq-zoo`, and the `openquant-india` meta-package.

> **Naming note:** the bare `openquant` name on PyPI is held by an abandoned
> 2017 package, so the meta-package ships as `openquant-india`. The brand,
> GitHub org, and docs remain "OpenQuant India".

Publishing is **fully automated via GitHub Actions and PyPI Trusted
Publishing** — no API tokens are stored anywhere. Pushing a tag like
`oq-core-v0.1.0` triggers a build and publish of that one package.

---

## One-time PyPI setup

For **each** of the seven package names, configure a *pending trusted
publisher* on PyPI before the first release.

1. Log in to <https://pypi.org> with 2FA enabled.
2. Go to **Your account → Publishing → Add a new pending publisher**.
3. Fill in:
   - **PyPI Project Name:** `oq-core` (then repeat for the other six)
   - **Owner:** `revorhq`
   - **Repository name:** `openquant`
   - **Workflow name:** `publish.yml`
   - **Environment name:** `pypi`
4. Repeat for: `oq-data`, `oq-backtest`, `oq-broker`, `oq-mcp`, `oq-zoo`,
   `openquant-india`.

Then, in the GitHub repo:

1. **Settings → Environments → New environment** named `pypi`.
2. (Optional) Add required reviewers if you want a human approval gate
   before any publish.

---

## Reserve the names (one-time)

Reserve every name with a `0.0.0` placeholder release so nobody squats them.

```bash
# From the repo root, on main, with a clean tree.
for PKG in oq-core oq-data oq-backtest oq-broker oq-mcp oq-zoo openquant-india; do
  # Temporarily set version to 0.0.0 in that package's pyproject.toml,
  # tag, push, then revert.
  sed -i.bak -E "s/^version = \"[^\"]+\"/version = \"0.0.0\"/" packages/$PKG/pyproject.toml
  git add packages/$PKG/pyproject.toml
  git commit -s -m "chore($PKG): reserve PyPI name with 0.0.0 stub"
  git tag $PKG-v0.0.0
  git push origin main
  git push origin $PKG-v0.0.0
  mv packages/$PKG/pyproject.toml.bak packages/$PKG/pyproject.toml
  git add packages/$PKG/pyproject.toml
  git commit -s -m "chore($PKG): restore version after reservation"
  git push origin main
done
```

Easier alternative: bump versions in PRs and use the normal release flow
below — the very first publish of each name also reserves it.

---

## Releasing a single package

1. Bump the `version` in `packages/<pkg>/pyproject.toml`.
2. Commit and merge to `main`.
3. Tag and push:
   ```bash
   git tag oq-data-v0.2.0
   git push origin oq-data-v0.2.0
   ```
4. The `publish.yml` workflow:
   - parses the package and version from the tag,
   - verifies the tag version matches `pyproject.toml`,
   - builds with `uv build --package <pkg>`,
   - publishes to PyPI via trusted publishing.

---

## Releasing everything (dependency order)

Each package must exist on PyPI before any other package can depend on it.
Use this order:

```
oq-core   →   oq-data   →   oq-backtest   →   oq-broker   →   oq-mcp   →   oq-zoo   →   openquant-india
```

After each tag push, **wait for the publish workflow to finish** (and for
PyPI to make the version available — usually under a minute) before
tagging the next one.

---

## Tag naming convention

`<package>-v<MAJOR>.<MINOR>.<PATCH>` — e.g. `oq-backtest-v0.1.0`.

The workflow's tag pattern only matches the seven known package prefixes
(`oq-core-v*`, `oq-data-v*`, `oq-backtest-v*`, `oq-broker-v*`, `oq-mcp-v*`,
`oq-zoo-v*`, `openquant-india-v*`), so other tags are safe.

---

## Manual fallback (use only if CI is broken)

```bash
uv build --package oq-core
uv publish dist/*    # uses ~/.pypirc or env vars
```

This requires an API token. Prefer the automated path.
