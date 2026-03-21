# PEAT .NET 10 Migration Assessment

## Executive Summary

**Recommendation: Do not migrate.** The costs far outweigh the benefits. PEAT is a well-engineered, production-stable Python tool in a domain where Python's ecosystem is uniquely strong. Incremental Python improvements can achieve the desired benefits without a rewrite.

---

## Codebase Overview

- **Application:** Process Extraction and Analysis Tool (PEAT) — OT/ICS device interrogation
- **Developer:** Sandia National Labs
- **Size:** ~86,000 lines of Python across 167 files
- **Device Modules:** 19 (SEL, Rockwell, Siemens, Schneider, GE, Woodward, Fortinet, etc.)
- **Protocols:** 8+ (HTTP, FTP, SSH, SNMP, Serial, CIP/ENIP, Telnet, Modbus)
- **Tests:** 53 test files with comprehensive coverage
- **Maturity:** Production/Stable (PyPI classifier)

---

## What .NET 10 Would Provide

| Benefit | Impact for PEAT |
|---------|----------------|
| Stronger type system (records, interfaces) | **Moderate** — PEAT already uses Pydantic models + MyPy |
| Better runtime performance | **Low** — PEAT is I/O bound (network/serial), not CPU bound |
| Config validation via data annotations | **Low** — `SettingsManager` already validates YAML/ENV/CLI with ChainMap precedence |
| GUI via MAUI/Blazor/WPF | **Moderate** — Strongest argument, but primary audience uses CLI in field environments |
| Single-file deployment | **Low** — Already ships as PyInstaller binary and Docker container |
| Dependency injection | **Moderate** — Currently uses global singletons; DI would be cleaner |
| `IOptions<T>` pattern for config | **Low** — Current YAML + ChainMap system works well |

---

## What .NET 10 Would Cost

| Cost | Severity |
|------|----------|
| ~86K lines to rewrite | **Catastrophic** — Person-years of effort |
| 19 device modules to port | **Extreme** — Each has device-specific protocol logic hardened through real-world testing |
| Python library ecosystem loss | **Critical** — scapy, pysnmp, paramiko, pyserial, l5x, pyelftools have no mature .NET equivalents |
| scapy (packet crafting) specifically | **Critical** — No .NET equivalent; SharpPcap + PacketDotNet requires significantly more code |
| Re-testing against real OT hardware | **Extreme** — 19+ device types need physical re-validation |
| Team retraining | **High** — Existing contributors know Python |
| Linux-first deployment challenges | **Moderate** — .NET runs on Linux but ecosystem leans Windows |

---

## Estimated Migration Effort

- **Effort:** 2–4 person-years
- **Risk:** Very high (protocol library gaps, hardware re-validation)
- **Net benefit:** Negative

---

## Recommended Alternative: Incremental Python Improvements

| Goal | Python Solution | Effort |
|------|----------------|--------|
| Better config validation | Upgrade Pydantic v1 → v2 (pinned at 1.10.22). Pydantic v2 has massive validation improvements, JSON Schema generation, and 5–50x faster validation | 1–2 weeks |
| A real GUI/web interface | Add FastAPI + web UI on top of existing `peat.api.*` functions (`scan()`, `pull()`, `parse()`), or expand the existing Textual TUI | 2–4 weeks |
| Stricter typing | Enable stricter MyPy rules (`--strict`), add `runtime_checkable` Protocol classes | 1 week |
| Better dependency injection | Refactor `config`/`state`/`datastore` globals into a context object | 1–2 weeks |
| Interface contracts | Define Python `Protocol` (structural typing) classes for device modules | 1 week |
| Config schema validation | Generate JSON Schema from Pydantic v2 models, validate configs before execution | 1 week |

**Total incremental effort: ~2–3 months** vs. **2–4 years** for a .NET rewrite.

---

## When .NET Migration Would Make Sense

1. **Organizational mandate** to consolidate on .NET (budget 2–4 person-years)
2. **Windows-first deployment** becomes the primary target
3. **Rich desktop GUI** becomes a hard requirement (though a web UI via FastAPI achieves this too)
4. **The Python library ecosystem** for OT/network security significantly declines

---

## Conclusion

PEAT is doing exactly what it needs to do in the right language for its domain. The Python ecosystem for network security, protocol implementation, and OT device interrogation is unmatched. A .NET 10 migration would be a high-risk, high-cost endeavor delivering marginal improvements that are better achieved through incremental Python modernization.
