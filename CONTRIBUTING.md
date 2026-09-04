# Contributing

Keep Agent Footprint dependency-free and focused on deterministic filesystem before/after comparison.

1. Open an issue describing the missed or incorrect filesystem change.
2. Add one standard-library `unittest` that reproduces it.
3. Make the smallest fix and run:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
```

New agent integrations, dashboards, cloud uploads, content collection, and undo engines are intentionally out of scope.
