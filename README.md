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
| [Selenga River Delta — Shoreline Mapping](shoreline/) | Extract delta shoreline from a binary land/water mask | Active |

## Philosophy

These benchmarks are not a competition. They are a shared resource for the
community to evaluate and compare methods on common problems. We encourage
contributions from any tool, language, or approach.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add a submission to an
existing benchmark, or how to propose a new benchmark problem.
