#!/usr/bin/env python3
"""
Run LTE, NR, and Wi-Fi comparison scenarios across seeds, traffic scales, and node counts.

Example usage:

    python3 scripts/run_comparison_matrix.py --dry-run
    python3 scripts/run_comparison_matrix.py -j 4
    python3 scripts/run_comparison_matrix.py --tech wifi nr
"""

from __future__ import annotations

import argparse
import concurrent.futures
import itertools
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_STAMP = datetime.now().strftime("%Y-%m-%d")
RESULTS_ROOT = REPO_ROOT / "results" / RUN_STAMP

FLOW_SCALES = {
    "0p1": 0.1,
    "0p5": 0.5,
    "1p0": 1.0,
}

RNG_SEEDS = [5, 6, 7]
NODE_COUNTS = [5, 10, 15]
WIFI_BANDS = ["5g", "2g"]


@dataclass(frozen=True)
class ScenarioCommand:
    label: str
    command: List[str]
    metrics_src: Path
    metrics_dst: Path
    temp_output_dir: Path

    def describe(self) -> str:
        return f"{self.label} -> {' '.join(self.command)}"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def run_command(cmd: Sequence[str]) -> None:
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def build_wifi_commands() -> Iterable[ScenarioCommand]:
    for band, seed, sta_count, (flow_tag, flow_scale) in itertools.product(
        WIFI_BANDS, RNG_SEEDS, NODE_COUNTS, FLOW_SCALES.items()
    ):
        temp_dir = RESULTS_ROOT / "_tmp" / "wifi" / band / f"seed_{seed}" / f"sta{sta_count}" / flow_tag
        metrics_src = temp_dir / "wifi-test-2-adhoc-grid-six-metrics.md"
        metrics_dst = (
            RESULTS_ROOT
            / "wifi"
            / band
            / f"seed_{seed}"
            / f"sta{sta_count}"
            / flow_tag
            / "metrics.md"
        )
        cmd = [
            "./ns3",
            "run",
            (
                "scratch/wifi-test-2-adhoc-grid-six "
                f"--numStaNodes={sta_count} "
                f"--staHeight=0 "
                f"--hotspotBand={band} "
                f"--flowScale={flow_scale} "
                f"--rngSeed={seed} "
                f"--outputDir={temp_dir.as_posix()}"
            ),
        ]
        label = f"[wifi band={band} seed={seed} sta={sta_count} flow={flow_tag}]"
        yield ScenarioCommand(label, cmd, metrics_src, metrics_dst, temp_dir)


def build_nr_commands() -> Iterable[ScenarioCommand]:
    for seed, ue_count, (flow_tag, flow_scale) in itertools.product(
        RNG_SEEDS, NODE_COUNTS, FLOW_SCALES.items()
    ):
        temp_dir = RESULTS_ROOT / "_tmp" / "nr" / f"seed_{seed}" / f"ue{ue_count}" / flow_tag
        metrics_src = temp_dir / "nr-playfield-metrics.md"
        metrics_dst = (
            RESULTS_ROOT
            / "nr"
            / f"seed_{seed}"
            / f"ue{ue_count}"
            / flow_tag
            / "metrics.md"
        )
        cmd = [
            "./ns3",
            "run",
            (
                "scratch/nr_playfield_traces "
                f"--nUes={ue_count} "
                f"--flowScale={flow_scale} "
                f"--rngSeed={seed} "
                f"--outputDir={temp_dir.as_posix()}"
            ),
        ]
        label = f"[nr seed={seed} ue={ue_count} flow={flow_tag}]"
        yield ScenarioCommand(label, cmd, metrics_src, metrics_dst, temp_dir)


def build_lte_commands() -> Iterable[ScenarioCommand]:
    for seed, ue_count, (flow_tag, flow_scale) in itertools.product(
        RNG_SEEDS, NODE_COUNTS, FLOW_SCALES.items()
    ):
        temp_dir = RESULTS_ROOT / "_tmp" / "lte" / f"seed_{seed}" / f"ue{ue_count}" / flow_tag
        metrics_src = temp_dir / "lte-playfield-metrics.md"
        metrics_dst = (
            RESULTS_ROOT
            / "lte"
            / f"seed_{seed}"
            / f"ue{ue_count}"
            / flow_tag
            / "metrics.md"
        )
        cmd = [
            "./ns3",
            "run",
            (
                "scratch/lte_playfield_traces "
                f"--nUes={ue_count} "
                f"--flowScale={flow_scale} "
                f"--rngSeed={seed} "
                f"--outputDir={temp_dir.as_posix()}"
            ),
        ]
        label = f"[lte seed={seed} ue={ue_count} flow={flow_tag}]"
        yield ScenarioCommand(label, cmd, metrics_src, metrics_dst, temp_dir)


TECH_BUILDERS = {
    "wifi": build_wifi_commands,
    "nr": build_nr_commands,
    "lte": build_lte_commands,
}


def copy_metrics(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(f"Metrics file not found: {src}")
    ensure_parent(dst)
    shutil.copy2(src, dst)


def attempt_scenario(scenario: ScenarioCommand) -> tuple[ScenarioCommand, bool, str | None]:
    print(f"Running: {scenario.describe()}")
    try:
        run_command(scenario.command)
    except subprocess.CalledProcessError as exc:
        print(f"  !! Simulation failed: {exc}")
        return scenario, False, f"Simulation failed: {exc}"
    except Exception as exc:  # pragma: no cover - defensive
        print(f"  !! Unexpected error while running command: {exc}")
        return scenario, False, f"Run error: {exc}"

    try:
        copy_metrics(scenario.metrics_src, scenario.metrics_dst)
    except Exception as exc:
        print(f"  !! Failed to archive metrics: {exc}")
        return scenario, False, f"Archive error: {exc}"

    print(f"  -> Metrics archived to {scenario.metrics_dst}")
    if scenario.temp_output_dir.exists():
        shutil.rmtree(scenario.temp_output_dir, ignore_errors=True)
    return scenario, True, None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute comparison scenarios and archive metrics.")
    parser.add_argument(
        "--tech",
        nargs="+",
        choices=TECH_BUILDERS.keys(),
        default=list(TECH_BUILDERS.keys()),
        help="Subset of technologies to run (default: all).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the commands without executing them.",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=1,
        help="Number of concurrent simulations to run (default: 1).",
    )
    args = parser.parse_args(argv)

    scenarios: List[ScenarioCommand] = []
    for tech in args.tech:
        scenarios.extend(TECH_BUILDERS[tech]())

    print(f"Prepared {len(scenarios)} scenario runs.")
    for scenario in scenarios:
        print(scenario.describe())

    if args.dry_run:
        print("Dry-run requested; exiting without executing commands.")
        return 0

    jobs = max(1, args.jobs)
    results: List[tuple[ScenarioCommand, bool, str | None]] = []

    if jobs == 1:
        for scenario in scenarios:
            results.append(attempt_scenario(scenario))
    else:
        print(f"Executing with concurrency: {jobs} workers")
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
            future_map = {executor.submit(attempt_scenario, scenario): scenario for scenario in scenarios}
            for future in concurrent.futures.as_completed(future_map):
                results.append(future.result())

    failed = [(scenario, error) for scenario, ok, error in results if not ok]

    if failed:
        print(f"\nRetrying {len(failed)} failed scenario(s)...")
        retry_results: List[tuple[ScenarioCommand, bool, str | None]] = []
        for scenario, _ in failed:
            retry_results.append(attempt_scenario(scenario))

        results = [
            (scenario, ok, error)
            for scenario, ok, error in results
            if ok
        ] + retry_results

    remaining_failures = [(scenario, error) for scenario, ok, error in results if not ok]

    if remaining_failures:
        print("\nThe following scenarios failed after retry:")
        for scenario, error in remaining_failures:
            print(f"  {scenario.label} -> {error}")
        return 1

    print("All scenarios completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

