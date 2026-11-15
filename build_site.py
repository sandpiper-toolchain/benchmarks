#!/usr/bin/env python
"""
Build the sandpiper benchmarks website.

Discovers all benchmarks via benchmark.yaml files, reads their results_table.json,
and renders Jinja2 templates to produce per-benchmark index pages and the root
index.html.

Usage
-----
    python build_site.py               # rebuild all benchmark pages + root index.html
    python build_site.py shoreline     # rebuild one benchmark page + root index.html
    python build_site.py --no-index    # rebuild benchmark pages without touching index.html
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    import jinja2
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    import markupsafe
except ImportError:
    print(
        "ERROR: jinja2 is not installed.\n"
        "  Install it with:  pip install jinja2",
        file=sys.stderr,
    )
    sys.exit(1)

from scoring.benchmark import load_config, BenchmarkConfig


# ---------------------------------------------------------------------------
# Jinja2 environment
# ---------------------------------------------------------------------------

def make_env() -> Environment:
    templates_dir = HERE / "templates"
    if not templates_dir.is_dir():
        print(
            f"ERROR: templates directory not found: {templates_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    def tojson_filter(value, indent=None):
        dumped = json.dumps(value, indent=indent).replace("</", "<\\/")
        return markupsafe.Markup(dumped)

    env.filters["tojson"] = tojson_filter
    return env


# ---------------------------------------------------------------------------
# Config → plain dict (JSON-serialisable)
# ---------------------------------------------------------------------------

def config_to_dict(cfg: BenchmarkConfig) -> dict:
    """Convert a BenchmarkConfig to a plain dict safe for json.dumps."""
    return {
        "name": cfg.name,
        "slug": cfg.slug,
        "tagline": cfg.tagline,
        "domain": cfg.domain,
        "status": cfg.status,
        "reference_type": cfg.reference_type,
        "data_type": cfg.data_type,
        "submission_file_pattern": cfg.submission_file_pattern,
        "scoring": cfg.scoring,
        "datasets": cfg.datasets,
        # references_manifest and benchmark_dir are Path objects — omit them
        "website": cfg.website,
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_results(benchmark_dir: Path) -> list:
    results_path = benchmark_dir / "results_table.json"
    if not results_path.exists():
        return []
    try:
        with open(results_path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        print(f"  WARNING: could not read {results_path}: {exc}", file=sys.stderr)
        return []


def discover_benchmarks() -> list[Path]:
    """Return sorted list of benchmark directories that have a benchmark.yaml."""
    return sorted(
        p.parent for p in (HERE / "benchmarks").glob("*/benchmark.yaml")
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build the sandpiper benchmarks website from templates."
    )
    p.add_argument(
        "slug",
        nargs="?",
        default=None,
        help="Benchmark slug to (re)build (e.g. 'shoreline'). "
             "Omit to rebuild all benchmark pages.",
    )
    p.add_argument(
        "--no-index",
        action="store_true",
        help="Skip regenerating the root index.html.",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    env = make_env()

    all_benchmark_dirs = discover_benchmarks()
    if not all_benchmark_dirs:
        print("ERROR: no benchmarks/*/benchmark.yaml files found.", file=sys.stderr)
        sys.exit(1)

    # Determine which benchmarks to (re)build pages for.
    if args.slug is not None:
        target_dirs = [d for d in all_benchmark_dirs if d.name == args.slug]
        if not target_dirs:
            available = [d.name for d in all_benchmark_dirs]
            print(
                f"ERROR: no benchmark found for slug '{args.slug}'.\n"
                f"  Available: {available}",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        target_dirs = all_benchmark_dirs

    # Load config + results for every benchmark (needed for the index even when
    # only one slug is targeted for page rebuild).
    all_benchmarks: list[dict] = []
    for bdir in all_benchmark_dirs:
        try:
            cfg = load_config(bdir)
        except Exception as exc:
            print(f"ERROR: could not load config for {bdir.name}: {exc}", file=sys.stderr)
            sys.exit(1)
        results = load_results(bdir)
        all_benchmarks.append({
            "config": config_to_dict(cfg),
            "submission_count": len(results),
            "benchmark_dir": bdir,
            "_cfg": cfg,  # keep original for page rendering
        })

    # Render per-benchmark pages.
    page_tmpl = env.get_template("benchmark_page.html")
    for entry in all_benchmarks:
        if entry["benchmark_dir"] not in target_dirs:
            continue
        cfg_dict = entry["config"]
        submission_count = entry["submission_count"]
        benchmark_config_json = json.dumps(cfg_dict).replace("</", "<\\/")

        html = page_tmpl.render(
            config=cfg_dict,
            submission_count=submission_count,
            benchmark_config_json=benchmark_config_json,
            root_path="../../",
        )
        out_path = entry["benchmark_dir"] / "index.html"
        out_path.write_text(html, encoding="utf-8")
        print(f"  wrote {out_path.relative_to(HERE)}")

    # Render root index.html.
    if not args.no_index:
        active_benchmarks = [
            b for b in all_benchmarks if b["config"].get("status") == "active"
        ]
        benchmark_count = len(active_benchmarks)
        method_count = sum(b["submission_count"] for b in all_benchmarks)

        index_tmpl = env.get_template("index.html")
        index_html = index_tmpl.render(
            benchmarks=[
                {"config": b["config"], "submission_count": b["submission_count"]}
                for b in all_benchmarks
            ],
            benchmark_count=benchmark_count,
            method_count=method_count,
            root_path="./",
        )
        out_path = HERE / "index.html"
        out_path.write_text(index_html, encoding="utf-8")
        print(f"  wrote index.html")

    print("Done.")


if __name__ == "__main__":
    main()
