# Plugin architecture guide (global-scale extensibility)

This document describes how to evolve Stewart into a plugin-first platform where nearly all product additions can be implemented as plugins without rewriting existing ones.

## 1) Contract-first architecture

A stable plugin contract is the single most important thing.

- **Manifest contract** (`manifest.yaml`) for metadata, compatibility, dependencies, permissions, and lifecycle settings.
- **Runtime contract** (`setup(plugin_context)`, optional `teardown()`) for initialization and shutdown.
- **Event contract** (named hooks + payload schemas) for integration with the assistant core.

Current manifest fields in this codebase:

```yaml
id: vendor/plugin
name: Human Readable Plugin
version: 0.1.0
assistant_api: "1.0"
description: What it does
entrypoints:
  - plugin.py
permissions:
  - assistant.events
depends_on:
  - vendor/other-plugin
enabled: true
```

## 2) Best practices for unlimited extensibility

### A. API versioning and compatibility

1. Keep a **host API major version** (breaking changes require a major bump).
2. Require plugin manifest to declare target API compatibility (`assistant_api`).
3. Never break existing public APIs in minor/patch releases.
4. Add new capabilities via optional methods/events instead of changing signatures.

### B. Dependency and load-order management

1. Support `depends_on` in manifests.
2. Build a topological load order.
3. Detect cycles and fail clearly.
4. Keep plugin IDs immutable once published.

### C. Capability-based security

1. Declare permissions in manifest (`assistant.events`, `assistant.audio`, `assistant.network`, etc.).
2. Route sensitive actions through `PluginContext` checks.
3. Add policy enforcement before exposing high-risk host APIs.
4. Add optional trust tiers (core, verified third-party, untrusted sandboxed).

### D. Event-driven extension surface

1. Expose named lifecycle events (`assistant.boot`, `plugin.loaded`, `assistant.shutdown`).
2. Define payload schemas and preserve backward compatibility.
3. Support handler priority and one-shot handlers.
4. Avoid hidden behavior; favor explicit events over monkey patches.

### E. Operational reliability

1. Plugin failures should not crash the assistant.
2. Keep plugin load logs and per-plugin diagnostics.
3. Add startup health checks and plugin status reporting.
4. Keep deterministic load order and deterministic event ordering.

### F. Lifecycle completeness

1. `setup` for bootstrapping.
2. `teardown` for cleanup.
3. Hook unregistering on shutdown/reload.
4. Optional hot-reload support later with state migration hooks.

### G. Marketplace-ready governance (future)

1. Signed plugin bundles.
2. Reproducible package format.
3. Provenance metadata (author, source repo, signatures).
4. Central compatibility index and automated checks.

## 3) Recommended long-term roadmap

1. **Now**: keep manifest + context + events stable.
2. **Next**: schema validation for manifests (JSON Schema or Pydantic), richer API semver ranges.
3. **Then**: plugin process isolation and capability sandboxing.
4. **Later**: remote plugin registry + signature verification + staged rollouts.

If you follow this roadmap, the core can stay small and stable while most innovation happens in plugins.
