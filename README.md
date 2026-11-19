# sandpiper

**Benchmarks for geomorphology analysis tools.**

This repository hosts benchmark problems for evaluating geomorphology analysis
methods. Benchmarks use shared datasets and defined outputs; some include
reference solutions, while others support comparison between methods.

Browse the benchmarks, datasets, and results on the
[hosted site](http://sandpiper-toolchain.org/benchmarks/).

## Build the website locally

The site templates and assets are maintained in this repository. To build and
preview the site:

Linux, MacOS `bash`:
```bash
# Compile results for every benchmark (run from the repository root):
for bench in benchmarks/*/; do python score.py "$bench" --compile; done

# Build and preview:
python build_site.py --output-dir _site
python -m http.server 8000 --directory _site
```

Windows Command Prompt `cmd.exe`:
```DOS
:: Compile results for every benchmark (run from the repository root):
for /d %i in (benchmarks\*) do python score.py "%i" --compile

:: Build and preview:
python build_site.py --output-dir _site
    python -m http.server 8000 --directory _site
```


Then visit `http://localhost:8000`.

## Philosophy

This is a shared resource, not a competition. Contributions from any tool,
language, or workflow are welcome.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add a submission to an
existing benchmark, or how to propose a new benchmark problem.
