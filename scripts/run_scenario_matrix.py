#!/usr/bin/env python3
"""
Automation helper to execute the Wi-Fi, NR and LTE scenario matrices and archive metrics.

Usage examples:

    # Dry-run to preview commands for all technologies
    python3 scripts/run_scenario_matrix.py --dry-run

    # Execute only Wi-Fi scenarios
    python3 scripts/run_scenario_matrix.py --tech wifi

    # Execute Wi-Fi + NR with concurrency limited to 1 (default)
    python3 scripts/run_scenario_matrix.py --tech wifi nr
"""

from __future__ import annotations

import argparse
import concurrent.futures
import itertools
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = REPO_ROOT / "results"


@dataclass(frozen=True)
class ScenarioCommand:
    """Description of a single simulation command and where to archive results."""

    label_parts: Dict[str, str]
    command: List[str]
    metrics_src: Path
    metrics_dst: Path
    temp_output_dir: Path

    def summarise(self) -> str:
        labels = ", ".join(f"{k}={v}" for k, v in self.label_parts.items())
        return f"[{labels}] -> {' '.join(self.command)}"


def packet_label(packet_size: int) -> str:
    mapping = {1024: "1k", 10240: "10k", 1048576: "1m"}
    if packet_size in mapping:
        return mapping[packet_size]
    if packet_size % 1024 == 0:
        return f"{packet_size // 1024}k"
    return str(packet_size)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def build_wifi_commands(id_iter: Iterable[int]) -> Iterable[ScenarioCommand]:
    bands = ["5g", "2g"]
    spawns = ["uniform", "anchored"]
    sta_counts = [5, 10, 15]
    packet_sizes = [1024, 10240, 1048576]

    for band, spawn, sta_count, pkt in itertools.product(bands, spawns, sta_counts, packet_sizes):
        spawn_flag = "true" if spawn == "uniform" else "false"
        label_parts = {
            "tech": "wifi",
            "band": band,
            "spawn": spawn,
            "sta": str(sta_count),
            "packet": packet_label(pkt),
        }
        scenario_id = next(id_iter)
        temp_dir = RESULTS_ROOT / "_tmp" / "wifi" / f"run-{scenario_id}"
        metrics_src = temp_dir / "wifi-test-2-adhoc-grid-six-metrics.md"
        metrics_dst = (
            RESULTS_ROOT
            / "wifi"
            / band
            / spawn
            / f"sta{sta_count}"
            / f"packet-{packet_label(pkt)}"
            / "metrics.md"
        )
        ns3_cmd = [
            "./ns3",
            "run",
            "scratch/wifi-test-2-adhoc-grid-six "
            f"--numStaNodes={sta_count} "
            f"--staUniformSpawn={spawn_flag} "
            f"--hotspotBand={band} "
            f"--packetSize={pkt} "
            f"--outputDir={temp_dir.as_posix()}",
        ]
        yield ScenarioCommand(label_parts, ns3_cmd, metrics_src, metrics_dst, temp_dir)


def build_nr_commands(id_iter: Iterable[int]) -> Iterable[ScenarioCommand]:
    spawn_modes = ["uniform", "anchored"]
    ue_counts = [5, 10, 15]
    packet_sizes = [1024, 10240, 1048576]

    for spawn, ue_count, pkt in itertools.product(spawn_modes, ue_counts, packet_sizes):
        spawn_flag = "true" if spawn == "anchored" else "false"
        label_parts = {
            "tech": "nr",
            "spawn": spawn,
            "ue": str(ue_count),
            "packet": packet_label(pkt),
        }
        scenario_id = next(id_iter)
        temp_dir = RESULTS_ROOT / "_tmp" / "nr" / f"run-{scenario_id}"
        metrics_src = temp_dir / "nr-playfield-metrics.md"
        metrics_dst = (
            RESULTS_ROOT
            / "nr"
            / spawn
            / f"ue{ue_count}"
            / f"packet-{packet_label(pkt)}"
            / "metrics.md"
        )
        cmd = [
            "./ns3",
            "run",
            "scratch/nr_playfield_traces "
            f"--nUes={ue_count} "
            f"--useAnchorPositions={spawn_flag} "
            f"--packetSize={pkt} "
            f"--outputDir={temp_dir.as_posix()}",
        ]
        yield ScenarioCommand(label_parts, cmd, metrics_src, metrics_dst, temp_dir)


def build_lte_commands(id_iter: Iterable[int]) -> Iterable[ScenarioCommand]:
    spawn_modes = ["uniform", "anchored"]
    ue_counts = [5, 10, 15]
    packet_sizes = [1024, 10240, 1048576]

    for spawn, ue_count, pkt in itertools.product(spawn_modes, ue_counts, packet_sizes):
        spawn_flag = "true" if spawn == "anchored" else "false"
        label_parts = {
            "tech": "lte",
            "spawn": spawn,
            "ue": str(ue_count),
            "packet": packet_label(pkt),
        }
        scenario_id = next(id_iter)
        temp_dir = RESULTS_ROOT / "_tmp" / "lte" / f"run-{scenario_id}"
        metrics_src = temp_dir / "lte-playfield-metrics.md"
        metrics_dst = (
            RESULTS_ROOT
            / "lte"
            / spawn
            / f"ue{ue_count}"
            / f"packet-{packet_label(pkt)}"
            / "metrics.md"
        )
        cmd = [
            "./ns3",
            "run",
            "scratch/lte_playfield_traces "
            f"--nUes={ue_count} "
            f"--useAnchorPositions={spawn_flag} "
            f"--packetSize={pkt} "
            f"--outputDir={temp_dir.as_posix()}",
        ]
        yield ScenarioCommand(label_parts, cmd, metrics_src, metrics_dst, temp_dir)


TECH_BUILDERS = {
    "wifi": build_wifi_commands,
    "nr": build_nr_commands,
    "lte": build_lte_commands,
}


def run_command(cmd: Sequence[str]) -> None:
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def copy_metrics(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(f"Metrics file not found: {src}")
    ensure_parent(dst)
    shutil.copy2(src, dst)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute scenario matrices and archive metrics.")
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
        help="Print commands without executing them.",
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
    scenario_id_iter = itertools.count()
    for tech in args.tech:
        builder = TECH_BUILDERS[tech]
        scenarios.extend(builder(scenario_id_iter))

    print(f"Prepared {len(scenarios)} scenario runs.")
    for scenario in scenarios:
        print(scenario.summarise())

    if args.dry_run:
        print("Dry-run requested; exiting without executing commands.")
        return 0

    def _execute(scenario: ScenarioCommand) -> None:
        print(f"Running: {scenario.summarise()}")
        run_command(scenario.command)
        copy_metrics(scenario.metrics_src, scenario.metrics_dst)
        print(f"  -> Metrics archived to {scenario.metrics_dst}")
        if scenario.temp_output_dir.exists():
            shutil.rmtree(scenario.temp_output_dir, ignore_errors=True)

    jobs = max(1, args.jobs)

    if jobs == 1:
        for scenario in scenarios:
            _execute(scenario)
    else:
        print(f"Executing with concurrency: {jobs} workers")
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
            futures = [executor.submit(_execute, scenario) for scenario in scenarios]
            for future in concurrent.futures.as_completed(futures):
                future.result()

    print("All scenarios completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

