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

The repository includes a responsive website for browsing the benchmarks, comparing results, and previewing shoreline GeoJSON. The source templates and assets are maintained in this repository; CI generates the results tables, builds the complete site, and publishes it to the `gh-pages` branch. Generated HTML and results tables are not committed to `main`.

GitHub Pages should be configured to serve the root of the `gh-pages` branch.

- [templates/index.html](templates/index.html) — dashboard page template
- [templates/benchmark_page.html](templates/benchmark_page.html) — benchmark page template
- [assets/benchmark-dashboard.css](assets/benchmark-dashboard.css) — theme and responsive layout
- [assets/benchmark-dashboard.js](assets/benchmark-dashboard.js) — charts, results loading, and GeoJSON map preview

To build and preview the deployable site locally:

```bash
python run_all.py
python build_site.py --output-dir _site
python -m http.server 8000 --directory _site
```

Then visit `http://localhost:8000`. Shoreline geometry can be loaded from a local GeoJSON file.

## Philosophy

These benchmarks are not a competition. They are a shared resource for the
community to evaluate and compare methods on common problems. We encourage
contributions from any tool, language, or approach.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add a submission to an
existing benchmark, or how to propose a new benchmark problem.
