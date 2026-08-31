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

## Chrome DevTools MCP

Source: `ChromeDevTools/chrome-devtools-mcp`

The pinned upstream revision is recorded in `TOOLCHAIN_LOCK.json`.

Runtime policy:

- local built executable only
- preserve Apache-2.0 license/notices
- disable usage statistics
- disable CrUX lookups
- disable update checks
- redact sensitive network headers where supported
- no `npx ...@latest` or registry lookup at runtime

## VisiData

Source: `saulpw/visidata`

The pinned upstream revision is recorded in `TOOLCHAIN_LOCK.json`.

VisiData is GPL-3.0 software. Preserve its complete upstream source and license in the vendored tool and deployment. Invoke it as a separate local program/tool unless a separate licensing review supports tighter integration with proprietary modules.

## Release packaging

Vendored source plus all required local runtime dependencies/build output must be included so browser review, MCP tooling, and VisiData work with network access disabled.
