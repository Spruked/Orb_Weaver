# Orb Weaver Local Toolchain

This directory is part of Orb Weaver itself and is shipped with every deployment that requires these capabilities.

Required layout:

```text
tools/
  mcp_server/
  chrome-devtools-mcp/
  visidata/
  TOOLCHAIN_LOCK.json
```

## Rule

All required tools are committed/vendored into this repository and included in the deployed system. Runtime operation must not download tools or dependencies from npm, PyPI, GitHub, hosted MCP services, CrUX, telemetry endpoints, or update services.

Do not use Git submodules for required deployment contents. Repository archives and release bundles must contain the actual tool files.

The first-party `mcp_server` coordinates the local tools. Chrome DevTools MCP provides local browser/DevTools truth for Browser Review and verification. VisiData provides local evidence/data inspection. They operate in unison as system tools rather than through a separate adapter hierarchy.

## Runtime rule

Required deployed tools must be executed from explicit local paths in this repository/install.

Forbidden during required runtime startup/execution:

- `npx`, whether `@latest`, version-pinned, or expected to be cached
- `npm install` / `npm ci`
- `pip install`
- runtime `git clone`, `git pull`, or submodule fetch
- any registry/package-index/update-server fallback if a local executable is absent

Pinning a version is provenance control only; it does not satisfy the offline-runtime requirement if runtime can still consult a registry.

## Controlled build/release carve-out

Development/release preparation may use networked source/dependency acquisition to construct and verify the vendored payload. Controlled build steps may therefore include `git clone`, `npm ci`, or Python dependency resolution.

That carve-out applies only before the release boundary. The produced repository/release/deployment must include the complete tool source/runtime, resolved dependencies/build output, licenses/notices, provenance, and hashes needed for offline operation.

## Chrome DevTools MCP

Source: `ChromeDevTools/chrome-devtools-mcp`

The pinned upstream revision is recorded in `TOOLCHAIN_LOCK.json`.

Runtime policy:

- execute the local built executable by explicit path
- preserve Apache-2.0 license/notices
- disable usage statistics
- disable CrUX lookups
- disable update checks
- redact sensitive network headers where supported
- no `npx` or registry lookup at deployed runtime

## VisiData

Source: `saulpw/visidata`

The pinned upstream revision is recorded in `TOOLCHAIN_LOCK.json`.

VisiData is GPL-3.0 software. Preserve its complete upstream source and license in the vendored tool and deployment. Invoke it as a separate local program/tool unless a separate licensing review supports tighter integration with proprietary modules.

## Release packaging

Vendored source plus all required local runtime dependencies/build output must be included so browser review, MCP tooling, and VisiData work with network access disabled.
