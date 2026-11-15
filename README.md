# sandpiper

**Benchmarks for geomorphology analysis tools.**

This repository hosts standardised benchmark problems for geomorphology. 
Each benchmark provides:

- A real-world or synthetic input dataset
- A reference solution (ground truth)
- A scoring script that can be run locally or in CI
- A results table comparing different tools and methods

## Benchmarks

| Benchmark | Task | Status |
|-----------|------|--------|
| [Selenga River Delta — Shoreline Mapping](benchmarks/shoreline/) | Extract delta shoreline from a binary land/water mask | Active |
| [Paraná River — Bedform Geometry](benchmarks/river_dunes/) | Detect bedforms in 1-D bed profiles and extract height, wavelength, and asymmetry | Active |

## Website and interactive dashboard

The repository includes a responsive website for browsing the benchmarks, comparing results, and previewing shoreline GeoJSON. Its files live at the repository root:

- [index.html](index.html) — dashboard page structure and content
- [assets/benchmark-dashboard.css](assets/benchmark-dashboard.css) — theme and responsive layout
- [assets/benchmark-dashboard.js](assets/benchmark-dashboard.js) — charts, results loading, and GeoJSON map preview

The dashboard reads each benchmark's `results_table.json`. To preview it locally, start a web server from the repository root:

```bash
python -m http.server 8000
```

Then visit `http://localhost:8000`. Shoreline geometry can be loaded from a local GeoJSON file.

## Philosophy

These benchmarks are not a competition. They are a shared resource for the
community to evaluate and compare methods on common problems. We encourage
contributions from any tool, language, or approach.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add a submission to an
existing benchmark, or how to propose a new benchmark problem.
