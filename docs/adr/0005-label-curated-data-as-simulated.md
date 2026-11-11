# 0005 — Curated sample sources are labelled simulated

## Context
Four adapters (AIS, Copernicus, DOT cameras, OSM) returned hardcoded records stamped `observedAt = now`, `dataStatus = actual` and `isSimulated = false`, and the registry advertised some of them as live. The specification's first rule is never to manufacture real-time updates or present speculation as fact.

## Decision
Until a real integration exists, those sources are registered with `status = simulated`, `isLive = false` and a `disabledReason`, and every record they emit carries `isSimulated = true` and `dataStatus = simulated`. A test enforces this for every non-live source. Retention never prunes simulated records, because they form a fixed, curated set.

## Consequences
- The UI's "actual vs simulated" filter now tells the truth.
- Replacing a sample with a live feed means changing that source's adapter and registry entry, after which the test no longer applies to it.
