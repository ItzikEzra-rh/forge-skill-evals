#!/usr/bin/env python3
"""
Load eval results into an MLflow instance.

Usage:
    # Load all v3 results
    python3 scripts/load-to-mlflow.py \
        --mlflow http://localhost:5000 \
        --results skills/generate-prd/results/v3

    # Re-evaluate and load with full traces (requires Anthropic API creds)
    python3 scripts/load-to-mlflow.py \
        --mlflow http://localhost:5000 \
        --results skills/generate-prd/results/v3 \
        --re-evaluate \
        --criteria skills/generate-prd/criteria/generate-prd.yaml \
        --dataset skills/generate-prd/dataset/cases \
        --forge-src /path/to/forge/src
"""

import argparse
import json
import sys
from pathlib import Path


def load_metrics_only(mlflow_uri: str, experiment: str, results_dir: Path):
    """Load pre-computed results as MLflow runs with metrics (no traces)."""
    import mlflow

    mlflow.set_tracking_uri(mlflow_uri)
    mlflow.set_experiment(experiment)

    for case_dir in sorted(results_dir.iterdir()):
        if not case_dir.is_dir():
            continue

        trace_path = case_dir / "trace.json"
        eval_path = case_dir / "eval-report" / "results.json"

        trace = json.load(open(trace_path)) if trace_path.exists() else {}
        if not eval_path.exists():
            print(f"  {case_dir.name}: SKIP (no eval report)")
            continue
        ev = json.load(open(eval_path))

        with mlflow.start_run(run_name=f"{case_dir.name}"):
            mlflow.set_tag("case", case_dir.name)
            mlflow.set_tag("skill", ev.get("skill", "generate-prd"))
            mlflow.set_tag("grade", ev.get("grade", "?"))
            mlflow.set_tag("type", "metrics-only")

            if trace:
                mlflow.log_metric("elapsed_seconds", trace.get("elapsed_seconds", 0))
                mlflow.log_metric("iterations", trace.get("iterations", 0))
                mlflow.log_metric("input_tokens", trace.get("total_input_tokens", 0))
                mlflow.log_metric("output_tokens", trace.get("total_output_tokens", 0))
                cost = (trace.get("total_input_tokens", 0) * 15
                        + trace.get("total_output_tokens", 0) * 75) / 1e6
                mlflow.log_metric("cost_usd", round(cost, 2))

            mlflow.log_metric("total_score", ev["total_score"])
            mlflow.log_metric("max_score", ev["max_score"])
            mlflow.log_metric("score_pct", round(ev["total_score"] / ev["max_score"] * 100, 1))
            mlflow.log_metric("criteria_passed", ev["total_passed"])

            for r in ev["results"]:
                mlflow.log_metric(f"c_{r['id']}", r["score"])

            try:
                if eval_path.exists():
                    mlflow.log_artifact(str(eval_path), "eval")
                gen = case_dir / "generated-prd.md"
                if gen.exists():
                    mlflow.log_artifact(str(gen), "generated")
            except Exception:
                pass

            print(f"  {case_dir.name}: {ev['total_score']}/{ev['max_score']} {ev.get('grade', '?')}")

    print("Done — metrics loaded")


def re_evaluate_with_traces(
    mlflow_uri: str,
    experiment: str,
    results_dir: Path,
    criteria_path: Path,
    dataset_dir: Path,
    forge_src: Path,
):
    """Re-run evaluation with MLflow tracing for full LLM call capture."""
    sys.path.insert(0, str(forge_src))

    import mlflow
    import mlflow.anthropic

    eval_script = forge_src.parent / "devtools" / "test-skill"
    sys.path.insert(0, str(eval_script))

    from evaluators.judge import evaluate
    from evaluators.reports import save_json

    mlflow.set_tracking_uri(mlflow_uri)
    mlflow.set_experiment(experiment)
    mlflow.anthropic.autolog()

    import logging
    logging.getLogger("mlflow.tracing.export").setLevel(logging.ERROR)

    for case_dir in sorted(results_dir.iterdir()):
        if not case_dir.is_dir():
            continue

        gen = case_dir / "generated-prd.md"
        gold = dataset_dir / case_dir.name / "gold-prd.md"

        if not gen.exists() or not gold.exists():
            print(f"  {case_dir.name}: SKIP (missing files)")
            continue

        with mlflow.start_run(run_name=f"eval — {case_dir.name}"):
            report = evaluate(criteria_path, gen, gold)

            output = case_dir / "eval-report"
            output.mkdir(parents=True, exist_ok=True)
            save_json(report, output)

            mlflow.set_tag("case", case_dir.name)
            mlflow.set_tag("skill", report.skill)
            mlflow.set_tag("grade", report.grade)
            mlflow.set_tag("type", "traced-eval")

            mlflow.log_metric("total_score", report.total_score)
            mlflow.log_metric("max_score", report.max_score)
            mlflow.log_metric("score_pct", round(report.total_score / report.max_score * 100, 1))
            mlflow.log_metric("criteria_passed", report.total_passed)

            for r in report.results:
                mlflow.log_metric(f"c_{r.id}", r.score)

            try:
                mlflow.log_artifact(str(output / "results.json"), "eval")
                mlflow.log_artifact(str(gen), "generated")
            except Exception:
                pass

            status = "PASS" if report.overall_pass else "FAIL"
            print(f"  {case_dir.name}: {report.total_score}/{report.max_score} "
                  f"{report.grade} {status}")

    print("Done — evaluated with traces")


def main():
    parser = argparse.ArgumentParser(
        description="Load forge-skill-evals results into MLflow"
    )
    parser.add_argument("--mlflow", required=True, help="MLflow tracking URI")
    parser.add_argument("--experiment", default="forge-generate-prd",
                        help="MLflow experiment name")
    parser.add_argument("--results", required=True,
                        help="Path to results directory (e.g., skills/generate-prd/results/v3)")
    parser.add_argument("--re-evaluate", action="store_true",
                        help="Re-run evaluation with tracing (requires API creds)")
    parser.add_argument("--criteria", help="Criteria YAML (required with --re-evaluate)")
    parser.add_argument("--dataset", help="Dataset cases dir (required with --re-evaluate)")
    parser.add_argument("--forge-src", help="Path to forge/src (required with --re-evaluate)")
    args = parser.parse_args()

    results_dir = Path(args.results)

    if args.re_evaluate:
        if not all([args.criteria, args.dataset, args.forge_src]):
            print("Error: --re-evaluate requires --criteria, --dataset, and --forge-src")
            sys.exit(1)
        re_evaluate_with_traces(
            args.mlflow, args.experiment, results_dir,
            Path(args.criteria), Path(args.dataset), Path(args.forge_src),
        )
    else:
        load_metrics_only(args.mlflow, args.experiment, results_dir)


if __name__ == "__main__":
    main()
