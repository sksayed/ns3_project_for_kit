#!/usr/bin/env python3
"""
Generate a cross-technology comparison report (Markdown + PDF) from the
structured metrics emitted by `run_comparison_matrix.py`.

The script has two separate functionalities:
  1. Generate Markdown report from metrics data (with optional PDF)
  2. Convert an existing Markdown file to PDF (standalone conversion)

Mode 1: Generate Report from Metrics
  - Reads metrics from results directory
  - Creates a Markdown (.md) file with analysis
  - Optionally converts Markdown to PDF (use --no-pdf to skip)

Mode 2: Convert Markdown to PDF
  - Takes an existing Markdown file as input
  - Converts it to PDF using markdown and weasyprint

The script focuses on the following analyses:
  1. Cross-technology performance comparison
  2. Scalability trends (node count sensitivity)
  4. Statistical summaries (mean/min/max/std)
  6. Traffic load impact (flow scale sensitivity)

Dependencies:
    - markdown: Convert Markdown to HTML
    - weasyprint: Convert HTML to PDF (for PDF generation)
    - matplotlib: Generate charts/figures (optional, for visualizations)
    - seaborn: Enhanced chart styling (optional, for visualizations)

Examples:
    # Generate both Markdown and PDF from metrics
    python3 scripts/generate_comparison_report.py \\
        --results-dir results/2025-11-14 \\
        --output-dir analysis_reports/2025-11-14

    # Generate only Markdown (no PDF)
    python3 scripts/generate_comparison_report.py \\
        --results-dir results/2025-11-14 \\
        --output-dir analysis_reports/2025-11-14 \\
        --no-pdf

    # Convert existing Markdown file to PDF
    python3 scripts/generate_comparison_report.py \\
        --convert-md-to-pdf analysis_reports/report.md \\
        --output-dir analysis_reports
"""

from __future__ import annotations

import argparse
import math
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    MARKDOWN_AVAILABLE = False

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    WEASYPRINT_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend for server environments
    import matplotlib.pyplot as plt
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    MATPLOTLIB_AVAILABLE = False


FLOW_SCALE_VALUES = {
    "0p1": 0.1,
    "0p5": 0.5,
    "1p0": 1.0,
}

METRIC_COLUMNS = {
    "PDR (%)": "pdr",
    "Avg Delay (ms)": "avg_delay",
    "Avg Jitter (ms)": "avg_jitter",
    "Throughput (Mbps)": "throughput",
    "Lost Packets": "lost_packets",
}

METRIC_ORDER = [
    "pdr",
    "throughput",
    "avg_delay",
    "avg_jitter",
    "lost_packets",
]

METRIC_LABELS = {
    "pdr": "PDR (%)",
    "throughput": "Throughput (Mbps)",
    "avg_delay": "Avg Delay (ms)",
    "avg_jitter": "Avg Jitter (ms)",
    "lost_packets": "Lost Packets",
}

# Technology display mapping
TECH_DISPLAY_MAP = {
    ("wifi", "2g"): "WiFi (2.4GHz)",
    ("wifi", "5g"): "WiFi (5GHz)",
    ("lte", "default"): "4G",
    ("nr", "default"): "5G",
    ("5g", "default"): "5G",  # Handle both "nr" and "5g"
}

# Technology order for consistent display
TECH_ORDER = [
    ("wifi", "2g"),
    ("wifi", "5g"),
    ("lte", "default"),
    ("nr", "default"),
    ("5g", "default"),
]


@dataclass
class ScenarioRecord:
    technology: str
    variant: str
    seed: int
    node_count: int
    flow_tag: str
    flow_scale: float
    metrics: Dict[str, float]

    @property
    def tech_label(self) -> str:
        return f"{self.technology.upper()} ({self.variant})"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    default_results = Path("results") / datetime.now().strftime("%Y-%m-%d")
    parser = argparse.ArgumentParser(
        description="Generate Markdown and PDF comparison reports from metrics."
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=default_results,
        help="Path to the results directory (default: results/<today>).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("analysis_reports"),
        help="Directory where the reports will be written (default: analysis_reports).",
    )
    parser.add_argument(
        "--report-name",
        default="comparison-report",
        help="Base name (without extension) for the generated reports.",
    )
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="Skip PDF generation, only create Markdown file.",
    )
    parser.add_argument(
        "--markdown-only",
        action="store_true",
        help="Alias for --no-pdf. Only generate Markdown file.",
    )
    parser.add_argument(
        "--convert-md-to-pdf",
        type=Path,
        metavar="MARKDOWN_FILE",
        help="Convert an existing Markdown file to PDF and exit. "
             "If --output-dir is provided, PDF will be saved there with same name.",
    )
    return parser.parse_args(argv)


def discover_metric_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        raise FileNotFoundError(f"Results directory not found: {root}")
    yield from root.rglob("metrics.md")


def _clean_cell(value: str) -> str:
    return value.strip().strip("*").strip()


def _to_float(value: str) -> float:
    value = value.replace("%", "").replace(",", "").strip()
    if not value:
        return math.nan
    try:
        return float(value)
    except ValueError:
        return math.nan


def parse_markdown_table(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8") as handle:
        lines = [line.strip() for line in handle if line.strip().startswith("|")]

    if len(lines) < 2:
        return rows

    headers = [_clean_cell(col) for col in lines[0].strip("|").split("|")]
    for line in lines[2:]:
        cols = [_clean_cell(col) for col in line.strip("|").split("|")]
        if len(cols) != len(headers):
            continue
        row = dict(zip(headers, cols))
        rows.append(row)
    return rows


def extract_scenario_metadata(results_dir: Path, metrics_path: Path) -> Tuple[str, str, int, int, str, float]:
    rel_parts = metrics_path.relative_to(results_dir).parts
    technology = rel_parts[0]
    variant = "default"
    idx = 1
    if technology == "wifi":
        variant = rel_parts[idx]
        idx += 1
    seed = int(rel_parts[idx].split("_")[1])
    idx += 1
    node_part = rel_parts[idx]
    idx += 1
    if technology == "wifi":
        node_count = int(node_part.replace("sta", ""))
    else:
        node_count = int(node_part.replace("ue", ""))
    flow_tag = rel_parts[idx]
    flow_scale = FLOW_SCALE_VALUES.get(flow_tag, math.nan)
    return technology, variant, seed, node_count, flow_tag, flow_scale


def scenario_record_from_table(
    technology: str,
    variant: str,
    seed: int,
    node_count: int,
    flow_tag: str,
    flow_scale: float,
    rows: List[Dict[str, str]],
) -> ScenarioRecord | None:
    if not rows:
        return None

    def row_to_metrics(row: Dict[str, str]) -> Dict[str, float]:
        metrics: Dict[str, float] = {}
        for header, key in METRIC_COLUMNS.items():
            value = _to_float(row.get(header, ""))
            metrics[key] = value
        return metrics

    avg_row = next((row for row in rows if row.get("STA IP", "").lower() == "average" or row.get("UE", "").lower() == "average" or row.get("**Average**", "").lower() == "average" or row.get("Average", "").lower() == "average"), None)
    if avg_row is None:
        candidates = [
            row_to_metrics(row)
            for row in rows
            if row.get("STA IP", "").lower() != "average"
            and row.get("UE", "").lower() != "average"
        ]
        metrics: Dict[str, float] = {}
        for key in METRIC_COLUMNS.values():
            values = [m[key] for m in candidates if not math.isnan(m[key])]
            metrics[key] = sum(values) / len(values) if values else math.nan
    else:
        metrics = row_to_metrics(avg_row)

    return ScenarioRecord(
        technology=technology,
        variant=variant,
        seed=seed,
        node_count=node_count,
        flow_tag=flow_tag,
        flow_scale=flow_scale,
        metrics=metrics,
    )


def collect_records(results_dir: Path) -> List[ScenarioRecord]:
    records: List[ScenarioRecord] = []
    for metrics_file in discover_metric_files(results_dir):
        try:
            meta = extract_scenario_metadata(results_dir, metrics_file)
        except Exception:
            continue
        rows = parse_markdown_table(metrics_file)
        record = scenario_record_from_table(*meta, rows)
        if record:
            records.append(record)
    if not records:
        raise RuntimeError(f"No metrics found under {results_dir}")
    return records


def group_records(records: Iterable[ScenarioRecord], keys: Sequence[str]) -> Dict[Tuple, List[ScenarioRecord]]:
    grouped: Dict[Tuple, List[ScenarioRecord]] = {}
    for record in records:
        key = tuple(getattr(record, key_name) for key_name in keys)
        grouped.setdefault(key, []).append(record)
    return grouped


def summarize_group(records: Sequence[ScenarioRecord]) -> Dict[str, float]:
    summary: Dict[str, float] = {}
    for metric in METRIC_ORDER:
        values = [rec.metrics[metric] for rec in records if not math.isnan(rec.metrics[metric])]
        summary[metric] = sum(values) / len(values) if values else math.nan
    return summary


def compute_statistics(records: Sequence[ScenarioRecord], metric: str) -> Dict[str, float]:
    values = [rec.metrics[metric] for rec in records if not math.isnan(rec.metrics[metric])]
    if not values:
        return {"mean": math.nan, "min": math.nan, "max": math.nan, "std": math.nan}
    mean = statistics.fmean(values)
    std = statistics.pstdev(values) if len(values) > 1 else 0.0
    return {"mean": mean, "min": min(values), "max": max(values), "std": std}


def format_value(value: float, digits: int = 2) -> str:
    if math.isnan(value):
        return "—"
    if abs(value - round(value)) < 1e-9:
        return f"{value:.0f}"
    return f"{value:.{digits}f}"


def render_md_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    header_line = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join(["---"] * len(headers)) + " |"
    row_lines = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header_line, separator, *row_lines])


def build_cross_tech_section(records: List[ScenarioRecord]) -> Tuple[str, List[str], List[List[str]]]:
    grouped = group_records(records, ["technology", "variant"])
    rows: List[List[str]] = []
    for (tech, variant), items in sorted(grouped.items()):
        summary = summarize_group(items)
        rows.append(
            [
                tech.upper(),
                variant,
                format_value(summary["pdr"]),
                format_value(summary["throughput"]),
                format_value(summary["avg_delay"]),
                format_value(summary["avg_jitter"]),
            ]
        )

    def describe(metric: str, reverse: bool = True) -> str:
        filtered = [
            (name, summarize_group(items)[metric])
            for name, items in grouped.items()
            if not math.isnan(summarize_group(items)[metric])
        ]
        if not filtered:
            return "Not enough data to rank technologies."
        best = max(filtered, key=lambda item: item[1]) if reverse else min(filtered, key=lambda item: item[1])
        descriptor = "highest" if reverse else "lowest"
        metric_label = METRIC_LABELS[metric]
        return f"{best[0][0].upper()} ({best[0][1]}) achieves the {descriptor} {metric_label} ({format_value(best[1])})."

    paragraphs = [
        describe("throughput"),
        describe("pdr"),
        describe("avg_delay", reverse=False),
    ]
    headers = ["Technology", "Variant", "Mean PDR (%)", "Mean Throughput (Mbps)", "Mean Delay (ms)", "Mean Jitter (ms)"]
    return ("1. Cross-Technology Performance", paragraphs, [headers, *rows])


def build_scalability_section(records: List[ScenarioRecord]) -> Tuple[str, List[str], List[List[str]]]:
    grouped = group_records(records, ["technology", "variant", "node_count"])
    rows: List[List[str]] = []
    insights: List[str] = []
    for (tech, variant, node_count), items in sorted(grouped.items()):
        summary = summarize_group(items)
        rows.append(
            [
                tech.upper(),
                variant,
                str(node_count),
                format_value(summary["pdr"]),
                format_value(summary["throughput"]),
                format_value(summary["avg_delay"]),
            ]
        )
    tech_groups = group_records(records, ["technology", "variant"])
    for (tech, variant), items in sorted(tech_groups.items()):
        per_node_grouped = {
            key[0]: value for key, value in group_records(items, ["node_count"]).items()
        }
        if len(per_node_grouped) < 2:
            continue
        sorted_nodes = sorted(per_node_grouped.items())
        first_node, first_data = sorted_nodes[0]
        last_node, last_data = sorted_nodes[-1]
        first_summary = summarize_group(first_data)
        last_summary = summarize_group(last_data)
        delta_pdr = last_summary["pdr"] - first_summary["pdr"]
        delta_delay = last_summary["avg_delay"] - first_summary["avg_delay"]
        insights.append(
            f"{tech.upper()} ({variant}) PDR changes by {format_value(delta_pdr)} points and delay by {format_value(delta_delay)} ms between {first_node} and {last_node} nodes."
        )
    headers = ["Technology", "Variant", "Node Count", "Mean PDR (%)", "Mean Throughput (Mbps)", "Mean Delay (ms)"]
    return ("2. Scalability Trends", insights, [headers, *rows])


def build_statistical_section(records: List[ScenarioRecord]) -> Tuple[str, List[str], List[List[str]]]:
    rows: List[List[str]] = []
    grouped = group_records(records, ["technology", "variant"])
    for metric in METRIC_ORDER:
        for (tech, variant), items in sorted(grouped.items()):
            stats = compute_statistics(items, metric)
            rows.append(
                [
                    METRIC_LABELS[metric],
                    tech.upper(),
                    variant,
                    format_value(stats["mean"]),
                    format_value(stats["std"]),
                    format_value(stats["min"]),
                    format_value(stats["max"]),
                ]
            )
    headers = ["Metric", "Technology", "Variant", "Mean", "Std Dev", "Min", "Max"]
    paragraphs = [
        "Tables below summarize distribution of core KPIs across seeds, node counts, and flow scales."
    ]
    return ("3. Statistical Summary", paragraphs, [headers, *rows])


def build_flow_section(records: List[ScenarioRecord]) -> Tuple[str, List[str], List[List[str]]]:
    grouped = group_records(records, ["technology", "variant", "flow_tag"])
    rows: List[List[str]] = []
    insights: List[str] = []
    for (tech, variant, flow_tag), items in sorted(grouped.items()):
        summary = summarize_group(items)
        rows.append(
            [
                tech.upper(),
                variant,
                flow_tag,
                format_value(summary["pdr"]),
                format_value(summary["throughput"]),
                format_value(summary["avg_delay"]),
            ]
        )
    for (tech, variant), items in sorted(group_records(records, ["technology", "variant"]).items()):
        per_flow_grouped = {
            key[0]: value for key, value in group_records(items, ["flow_tag"]).items()
        }
        if len(per_flow_grouped) < 2:
            continue
        low_tag = min(per_flow_grouped)
        high_tag = max(per_flow_grouped)
        low_flow = summarize_group(per_flow_grouped[low_tag])
        high_flow = summarize_group(per_flow_grouped[high_tag])
        pdr_drop = low_flow["pdr"] - high_flow["pdr"]
        delay_increase = high_flow["avg_delay"] - low_flow["avg_delay"]
        insights.append(
            f"{tech.upper()} ({variant}) loses {format_value(pdr_drop)} PDR points and adds {format_value(delay_increase)} ms delay from {low_tag} to {high_tag} load."
        )
    headers = ["Technology", "Variant", "Flow Tag", "Mean PDR (%)", "Mean Throughput (Mbps)", "Mean Delay (ms)"]
    return ("4. Traffic Load Impact", insights, [headers, *rows])


def get_tech_display_name(tech: str, variant: str) -> str:
    """Get display name for technology."""
    tech_lower = tech.lower()
    variant_lower = variant.lower()
    
    # Handle "nr" -> "5G" case
    if tech_lower == "nr":
        tech_lower = "5g"
    # Handle variant for technologies other than wifi
    if tech_lower != "wifi" and variant_lower == "default":
        # Map technology directly
        if tech_lower == "lte":
            return "4G"
        elif tech_lower == "5g" or tech_lower == "nr":
            return "5G"
    
    return TECH_DISPLAY_MAP.get((tech_lower, variant_lower), f"{tech.upper()} ({variant})")


def get_tech_key(tech: str, variant: str) -> int:
    """Get sort key for consistent technology ordering."""
    tech_lower = tech.lower()
    variant_lower = variant.lower()
    
    # Normalize "nr" to "5g" for ordering
    if tech_lower == "nr":
        tech_lower = "5g"
    
    key = (tech_lower, variant_lower)
    
    # Try exact match first
    try:
        return TECH_ORDER.index(key)
    except ValueError:
        # Try with default variant mapping
        if tech_lower == "lte":
            try:
                return TECH_ORDER.index(("lte", "default"))
            except ValueError:
                pass
        elif tech_lower == "5g" or tech_lower == "nr":
            try:
                return TECH_ORDER.index(("5g", "default"))
            except ValueError:
                pass
        return 999  # Put unknown techs at end


def generate_chart_section1_cross_tech(records: List[ScenarioRecord], figures_dir: Path) -> List[str]:
    """Generate grouped bar charts for Section 1: Cross-Technology Performance."""
    if not MATPLOTLIB_AVAILABLE:
        return []
    
    grouped = group_records(records, ["technology", "variant"])
    tech_data: Dict[Tuple[str, str], Dict[str, float]] = {}
    
    for (tech, variant), items in grouped.items():
        summary = summarize_group(items)
        tech_data[(tech, variant)] = summary
    
    # Sort technologies for consistent ordering
    sorted_techs = sorted(tech_data.keys(), key=lambda x: get_tech_key(x[0], x[1]))
    tech_names = [get_tech_display_name(tech, variant) for tech, variant in sorted_techs]
    
    # Metrics to plot
    metrics = [
        ("pdr", "PDR (%)", "Percentage"),
        ("throughput", "Throughput (Mbps)", "Mbps"),
        ("avg_delay", "Avg Delay (ms)", "ms"),
        ("avg_jitter", "Avg Jitter (ms)", "ms"),
    ]
    
    image_refs: List[str] = []
    for metric_key, metric_label, metric_unit in metrics:
        values = [tech_data[(tech, variant)][metric_key] for tech, variant in sorted_techs]
        
        # Filter out NaN values
        valid_data = [(name, val) for name, val in zip(tech_names, values) if not math.isnan(val)]
        if not valid_data:
            continue
            
        names, vals = zip(*valid_data)
        
        # Use seaborn style if available for better aesthetics
        if MATPLOTLIB_AVAILABLE:
            try:
                sns.set_style("whitegrid")
                sns.set_palette("husl")
            except:
                pass
        
        # Smaller figure size to fit side by side
        plt.figure(figsize=(5, 3.5), facecolor='white')
        
        # Professional color palette
        colors = ['#2563eb', '#10b981', '#f59e0b', '#ef4444']  # Blue, Green, Amber, Red
        
        # Shorten technology names for display
        short_names = [name.replace("WIFI Mesh (2.4 GHz)", "WiFi (2.4GHz)")
                       .replace("WIFI Mesh (5 GHz)", "WiFi (5GHz)")
                       .replace("WIFI Mesh (2.4GHz)", "WiFi (2.4GHz)")
                       .replace("WIFI Mesh (5GHz)", "WiFi (5GHz)") for name in names]
        
        # Create bars with much narrower width (0.3 for thinner bars)
        bars = plt.bar(short_names, vals, width=0.3, color=colors[:len(short_names)], 
                      edgecolor='white', linewidth=1.2, alpha=0.85)
        
        # Reduced font sizes for smaller figure - remove x-axis label
        plt.xlabel('', fontsize=0)  # Empty x-axis label
        plt.ylabel(metric_label, fontsize=10, fontweight='600', color='#374151', labelpad=8)
        plt.title(f'{metric_label} Comparison', fontsize=11, fontweight='bold', 
                 color='#1f2937', pad=10)
        
        # Improve grid
        plt.grid(axis='y', alpha=0.2, linestyle='--', linewidth=0.6)
        plt.grid(axis='x', alpha=0)
        
        # Rotate x-axis labels
        plt.xticks(rotation=45, ha='right', fontsize=9, color='#374151')
        plt.yticks(fontsize=9, color='#374151')
        
        # Set background color
        ax = plt.gca()
        ax.set_facecolor('#fafafa')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#e5e7eb')
        ax.spines['bottom'].set_color('#e5e7eb')
        
        # Add value labels on bars with better styling (smaller font)
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}',
                    ha='center', va='bottom', fontsize=8, fontweight='500',
                    color='#1f2937', bbox=dict(boxstyle='round,pad=0.2', 
                    facecolor='white', edgecolor='none', alpha=0.7))
        
        plt.tight_layout()
        filename = f"section1_{metric_key}.png"
        filepath = figures_dir / filename
        plt.savefig(filepath, dpi=120, bbox_inches='tight', facecolor='white', edgecolor='none')
        plt.close()
        
        image_refs.append(f"![{metric_label} Comparison](figures/{filename})")
    
    return image_refs


def generate_chart_section2_scalability(records: List[ScenarioRecord], figures_dir: Path) -> List[str]:
    """Generate line plots for Section 2: Scalability Trends."""
    if not MATPLOTLIB_AVAILABLE:
        return []
    
    grouped = group_records(records, ["technology", "variant", "node_count"])
    tech_groups = group_records(records, ["technology", "variant"])
    
    # Organize data by technology and node count
    tech_node_data: Dict[Tuple[str, str], Dict[int, Dict[str, float]]] = {}
    for (tech, variant), items in tech_groups.items():
        per_node = {}
        for (node_count,), node_items in group_records(items, ["node_count"]).items():
            per_node[node_count] = summarize_group(node_items)
        if len(per_node) >= 2:  # Need at least 2 node counts for a trend
            tech_node_data[(tech, variant)] = per_node
    
    # Metrics to plot
    metrics = [
        ("pdr", "PDR (%)"),
        ("throughput", "Throughput (Mbps)"),
        ("avg_delay", "Avg Delay (ms)"),
    ]
    
    image_refs: List[str] = []
    for metric_key, metric_label in metrics:
        plt.figure(figsize=(10, 6))
        
        sorted_techs = sorted(tech_node_data.keys(), key=lambda x: get_tech_key(x[0], x[1]))
        for tech, variant in sorted_techs:
            node_data = tech_node_data[(tech, variant)]
            node_counts = sorted(node_data.keys())
            values = [node_data[nc][metric_key] for nc in node_counts]
            
            # Filter out NaN
            valid_pairs = [(nc, v) for nc, v in zip(node_counts, values) if not math.isnan(v)]
            if len(valid_pairs) < 2:
                continue
            node_counts, values = zip(*valid_pairs)
            
            tech_name = get_tech_display_name(tech, variant)
            plt.plot(node_counts, values, marker='o', linewidth=2, markersize=8, label=tech_name)
        
        plt.xlabel('Number of Nodes', fontsize=12, fontweight='bold')
        plt.ylabel(metric_label, fontsize=12, fontweight='bold')
        plt.title(f'Scalability Trends: {metric_label}', fontsize=14, fontweight='bold')
        plt.legend(loc='best', fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.xticks(sorted(set([nc for tech_data in tech_node_data.values() for nc in tech_data.keys()])))
        
        plt.tight_layout()
        filename = f"section2_{metric_key}.png"
        filepath = figures_dir / filename
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        image_refs.append(f"![Scalability Trends: {metric_label}](figures/{filename})")
    
    return image_refs


def generate_chart_section3_statistical(records: List[ScenarioRecord], figures_dir: Path) -> List[str]:
    """Generate true box plots for Section 3: Statistical Summary."""
    if not MATPLOTLIB_AVAILABLE:
        return []
    
    grouped = group_records(records, ["technology", "variant"])
    
    # Metrics to plot (excluding lost_packets)
    metrics = [
        ("pdr", "PDR (%)"),
        ("throughput", "Throughput (Mbps)"),
        ("avg_delay", "Avg Delay (ms)"),
        ("avg_jitter", "Avg Jitter (ms)"),
    ]
    
    image_refs: List[str] = []
    for metric_key, metric_label in metrics:
        # Collect all data points for each technology
        data_for_boxplot = []
        tech_names = []
        
        sorted_techs = sorted(grouped.keys(), key=lambda x: get_tech_key(x[0], x[1]))
        for tech, variant in sorted_techs:
            tech_records = grouped[(tech, variant)]
            # Extract all individual metric values
            values = [rec.metrics[metric_key] for rec in tech_records 
                     if not math.isnan(rec.metrics[metric_key])]
            
            if values:  # Only add if we have data
                data_for_boxplot.append(values)
                tech_name = get_tech_display_name(tech, variant)
                # Shorten WiFi names
                tech_name = tech_name.replace("WIFI Mesh (2.4 GHz)", "WiFi (2.4GHz)")
                tech_name = tech_name.replace("WIFI Mesh (5 GHz)", "WiFi (5GHz)")
                tech_names.append(tech_name)
        
        if not data_for_boxplot:
            continue
        
        # Create true box plot
        plt.figure(figsize=(10, 6), facecolor='white')
        
        # Use seaborn style if available
        try:
            sns.set_style("whitegrid")
        except:
            pass
        
        # Create box plot with all data points
        bp = plt.boxplot(data_for_boxplot, labels=tech_names, patch_artist=True,
                        showmeans=True, meanline=True,
                        boxprops=dict(facecolor='lightblue', alpha=0.7, linewidth=1.5),
                        medianprops=dict(color='red', linewidth=2),
                        meanprops=dict(color='green', linewidth=1.5, linestyle='--'),
                        whiskerprops=dict(linewidth=1.5),
                        capprops=dict(linewidth=1.5),
                        flierprops=dict(marker='o', markerfacecolor='red', 
                                      markersize=5, alpha=0.5, markeredgecolor='none'))
        
        # Styling - increased font sizes
        plt.xlabel('', fontsize=0)  # Remove x-axis label
        plt.ylabel(metric_label, fontsize=14, fontweight='600', color='#374151', labelpad=10)
        plt.title(f'Distribution Summary: {metric_label}', fontsize=16, fontweight='bold', 
                 color='#1f2937', pad=15)
        plt.xticks(rotation=45, ha='right', fontsize=13, color='#374151')
        plt.yticks(fontsize=13, color='#374151')
        plt.grid(axis='y', alpha=0.2, linestyle='--', linewidth=0.8)
        
        # Set background color
        ax = plt.gca()
        ax.set_facecolor('#fafafa')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#e5e7eb')
        ax.spines['bottom'].set_color('#e5e7eb')
        
        # Add legend - increased font size
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='lightblue', alpha=0.7, label='IQR (25th-75th percentile)'),
            plt.Line2D([0], [0], color='red', linewidth=2, label='Median'),
            plt.Line2D([0], [0], color='green', linewidth=1.5, linestyle='--', label='Mean'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='red', 
                      markersize=5, alpha=0.5, label='Outliers', linestyle='None')
        ]
        plt.legend(handles=legend_elements, loc='upper right', fontsize=11, framealpha=0.9)
        
        plt.tight_layout()
        filename = f"section3_{metric_key}.png"
        filepath = figures_dir / filename
        plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
        plt.close()
        
        image_refs.append(f"![Distribution Summary: {metric_label}](figures/{filename})")
    
    return image_refs


def generate_chart_section4_traffic_load(records: List[ScenarioRecord], figures_dir: Path) -> List[str]:
    """Generate line plots for Section 4: Traffic Load Impact."""
    if not MATPLOTLIB_AVAILABLE:
        return []
    
    grouped = group_records(records, ["technology", "variant", "flow_tag"])
    tech_groups = group_records(records, ["technology", "variant"])
    
    # Payload mapping
    payload_labels = {"0p1": "10KB", "0p5": "50KB", "1p0": "1MB"}
    payload_order = ["0p1", "0p5", "1p0"]
    
    # Organize data by technology and payload
    tech_payload_data: Dict[Tuple[str, str], Dict[str, Dict[str, float]]] = {}
    for (tech, variant), items in tech_groups.items():
        per_payload = {}
        for (flow_tag,), payload_items in group_records(items, ["flow_tag"]).items():
            if flow_tag in payload_labels:
                per_payload[flow_tag] = summarize_group(payload_items)
        if len(per_payload) >= 2:  # Need at least 2 payload sizes
            tech_payload_data[(tech, variant)] = per_payload
    
    # Metrics to plot
    metrics = [
        ("pdr", "PDR (%)"),
        ("throughput", "Throughput (Mbps)"),
        ("avg_delay", "Avg Delay (ms)"),
    ]
    
    image_refs: List[str] = []
    for metric_key, metric_label in metrics:
        plt.figure(figsize=(10, 6))
        
        sorted_techs = sorted(tech_payload_data.keys(), key=lambda x: get_tech_key(x[0], x[1]))
        for tech, variant in sorted_techs:
            payload_data = tech_payload_data[(tech, variant)]
            payload_tags = [pt for pt in payload_order if pt in payload_data]
            payload_labels_list = [payload_labels[pt] for pt in payload_tags]
            values = [payload_data[pt][metric_key] for pt in payload_tags]
            
            # Filter out NaN
            valid_pairs = [(pl, v) for pl, v in zip(payload_labels_list, values) if not math.isnan(v)]
            if len(valid_pairs) < 2:
                continue
            payload_labels_list, values = zip(*valid_pairs)
            
            tech_name = get_tech_display_name(tech, variant)
            plt.plot(payload_labels_list, values, marker='o', linewidth=2, markersize=8, label=tech_name)
        
        plt.xlabel('Payload Size', fontsize=12, fontweight='bold')
        plt.ylabel(metric_label, fontsize=12, fontweight='bold')
        plt.title(f'Traffic Load Impact: {metric_label}', fontsize=14, fontweight='bold')
        plt.legend(loc='best', fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.xticks(payload_labels_list)
        
        plt.tight_layout()
        filename = f"section4_{metric_key}.png"
        filepath = figures_dir / filename
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        image_refs.append(f"![Traffic Load Impact: {metric_label}](figures/{filename})")
    
    return image_refs


def build_markdown_report(output_path: Path, context: Dict[str, str], sections: List[Tuple[str, List[str], List[List[str]]]], records: List[ScenarioRecord] | None = None, figures_dir: Path | None = None) -> None:
    lines: List[str] = []
    lines.append(f"# Cross-Technology Network Performance Analysis: 4G, 5G, and WiFi Mesh")
    lines.append("")
    lines.append(f"- Scenarios analyzed: {context['scenario_count']}")
    lines.append(f"- Generated on: {context['generated_at']}")
    lines.append("")
    
    # Generate charts if records and figures_dir are provided
    chart_images: Dict[str, List[str]] = {}
    if records and figures_dir and MATPLOTLIB_AVAILABLE:
        figures_dir.mkdir(parents=True, exist_ok=True)
        
        # Map section numbers to chart generators
        chart_images["1"] = generate_chart_section1_cross_tech(records, figures_dir)
        chart_images["2"] = generate_chart_section2_scalability(records, figures_dir)
        chart_images["3"] = generate_chart_section3_statistical(records, figures_dir)
        chart_images["4"] = generate_chart_section4_traffic_load(records, figures_dir)
    
    for title, paragraphs, table in sections:
        # Extract section number from title (e.g., "1. Cross-Technology Performance" -> "1")
        title_parts = title.split(".", 1)
        if title_parts[0].strip().isdigit():
            section_num = title_parts[0].strip()
            section_title = title_parts[1].strip() if len(title_parts) > 1 else title
        else:
            section_num = ""
            section_title = title
        
        lines.append(f"## {title}")
        lines.append("")
        
        for paragraph in paragraphs:
            lines.append(f"- {paragraph}")
        lines.append("")
        
        headers, *rows = table
        lines.append(render_md_table(headers, rows))
        lines.append("")
        
        # Add chart images after the table if available
        if section_num in chart_images and chart_images[section_num]:
            for img_ref in chart_images[section_num]:
                lines.append(img_ref)
                lines.append("")
    
    output_path.write_text("\n".join(lines), encoding="utf-8")


def extract_table_data_from_markdown(markdown_path: Path) -> Dict[str, List[Dict[str, str]]]:
    """Extract all tables from a markdown file organized by section."""
    if not markdown_path.exists():
        return {}
    
    content = markdown_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    
    tables: Dict[str, List[Dict[str, str]]] = {}
    current_section = None
    current_subsection = None
    in_table = False
    table_lines: List[str] = []
    
    for line in lines:
        line_stripped = line.strip()
        
        # Detect section headers (## or ###)
        if line_stripped.startswith("##"):
            # Save previous table if any
            if in_table and current_section and table_lines:
                table_data = _parse_table_lines(table_lines)
                if table_data:
                    section_key = current_section
                    if current_subsection:
                        section_key = f"{current_section}:{current_subsection}"
                    if section_key not in tables:
                        tables[section_key] = []
                    tables[section_key].extend(table_data)
                table_lines = []
                in_table = False
            
            # Extract section name
            if line_stripped.startswith("###"):
                # Subsection - store with parent section
                current_subsection = line_stripped.lstrip("#").strip()
            else:
                # Main section
                current_section = line_stripped.lstrip("#").strip()
                current_subsection = None
        
        # Detect table start
        if line_stripped.startswith("|") and "---" not in line_stripped:
            in_table = True
            table_lines.append(line)
        elif in_table and line_stripped.startswith("|"):
            table_lines.append(line)
        elif in_table and (not line_stripped or not line_stripped.startswith("|")):
            # End of table
            if table_lines:
                table_data = _parse_table_lines(table_lines)
                if table_data and current_section:
                    section_key = current_section
                    if current_subsection:
                        section_key = f"{current_section}:{current_subsection}"
                    if section_key not in tables:
                        tables[section_key] = []
                    tables[section_key].extend(table_data)
            table_lines = []
            in_table = False
    
    # Handle last table
    if in_table and current_section and table_lines:
        table_data = _parse_table_lines(table_lines)
        if table_data:
            section_key = current_section
            if current_subsection:
                section_key = f"{current_section}:{current_subsection}"
            if section_key not in tables:
                tables[section_key] = []
            tables[section_key].extend(table_data)
    
    return tables


def _parse_table_lines(table_lines: List[str]) -> List[Dict[str, str]]:
    """Parse markdown table lines into list of dictionaries."""
    if len(table_lines) < 2:
        return []
    
    # Skip separator line (---)
    header_line = table_lines[0]
    data_lines = [l for l in table_lines[1:] if "---" not in l]
    
    headers = [_clean_cell(col) for col in header_line.strip("|").split("|")]
    rows = []
    for line in data_lines:
        cols = [_clean_cell(col) for col in line.strip("|").split("|")]
        if len(cols) == len(headers):
            rows.append(dict(zip(headers, cols)))
    
    return rows


def generate_charts_from_markdown(markdown_path: Path, figures_dir: Path) -> bool:
    """Generate charts from markdown table data if they don't exist."""
    if not MATPLOTLIB_AVAILABLE:
        return False
    
    if not markdown_path.exists():
        return False
    
    # Create figures directory
    figures_dir.mkdir(parents=True, exist_ok=True)
    
    # Check which section charts exist
    existing_sections = set()
    for chart_file in figures_dir.glob("section*.png"):
        # Extract section number from filename (e.g., "section1_pdr.png" -> "1")
        parts = chart_file.stem.split("_")
        if len(parts) >= 2 and parts[0].startswith("section"):
            section_num = parts[0].replace("section", "")
            existing_sections.add(section_num)
    
    try:
        tables = extract_table_data_from_markdown(markdown_path)
        
        # Generate Section 1 charts (Cross-Technology Performance) if missing
        if "1" not in existing_sections:
            if "1. Cross-Technology Performance" in tables or "Cross-Technology Performance" in tables:
                section_key = "1. Cross-Technology Performance" if "1. Cross-Technology Performance" in tables else "Cross-Technology Performance"
                _generate_section1_charts_from_tables(tables[section_key], figures_dir)
        
        # Generate Section 2 charts (Scalability Trends) if missing
        if "2" not in existing_sections:
            # Check for Scalability Trends subsections (the function handles subsections directly)
            section2_keys = [k for k in tables.keys() if "Scalability Trends" in k and ":" in k]
            if section2_keys:
                # Use any subsection key - the function will find all subsections
                section_key = section2_keys[0].split(":")[0]  # Get main section name
                _generate_section2_charts_from_tables(tables, section_key, figures_dir)
        
        # Generate Section 3 charts (Statistical Summary) - handle subsections if missing
        if "3" not in existing_sections:
            section3_keys = [k for k in tables.keys() if "Statistical Summary" in k]
            for section_key in section3_keys:
                if ":" in section_key:
                    # Subsection - extract metric name
                    subsection = section_key.split(":", 1)[1]
                    _generate_section3_chart_from_subsection(tables[section_key], subsection, figures_dir)
        
        # Generate Section 4 charts (Traffic Load Impact) if missing
        if "4" not in existing_sections:
            # Check for Traffic Load Impact subsections (the function handles subsections directly)
            section4_keys = [k for k in tables.keys() if "Traffic Load Impact" in k and ":" in k]
            if section4_keys:
                # Use any subsection key - the function will find all subsections
                section_key = section4_keys[0].split(":")[0]  # Get main section name
                _generate_section4_charts_from_tables(tables, section_key, figures_dir)
        
        return True
    except Exception as e:
        print(f"Warning: Could not generate charts from markdown: {e}")
        return False


def _generate_section1_charts_from_tables(tables: List[Dict[str, str]], figures_dir: Path) -> None:
    """Generate Section 1 charts from table data."""
    tech_names = []
    pdr_values = []
    throughput_values = []
    delay_values = []
    jitter_values = []
    
    # Find rows with Technology column and Mean PDR
    for row in tables:
        if "Technology" in row and "Mean PDR (%)" in row:
            tech_name = row.get("Technology", "").strip()
            if not tech_name or tech_name == "Technology" or tech_name == "---":
                continue
            
            tech_names.append(tech_name)
            pdr_values.append(_to_float(row.get("Mean PDR (%)", "")))
            throughput_values.append(_to_float(row.get("Mean Throughput (Mbps)", "")))
            delay_values.append(_to_float(row.get("Mean Delay (ms)", "")))
            jitter_values.append(_to_float(row.get("Mean Jitter (ms)", "")))
    
    if not tech_names:
        return
    
    # Generate charts
    metrics = [
        ("pdr", "PDR (%)", pdr_values),
        ("throughput", "Throughput (Mbps)", throughput_values),
        ("avg_delay", "Avg Delay (ms)", delay_values),
        ("avg_jitter", "Avg Jitter (ms)", jitter_values),
    ]
    
    for metric_key, metric_label, values in metrics:
        valid_data = [(name, val) for name, val in zip(tech_names, values) if not math.isnan(val)]
        if not valid_data:
            continue
        
        names, vals = zip(*valid_data)
        
        # Use seaborn style if available for better aesthetics
        if MATPLOTLIB_AVAILABLE:
            try:
                sns.set_style("whitegrid")
                sns.set_palette("husl")
            except:
                pass
        
        # Smaller figure size to fit side by side
        plt.figure(figsize=(5, 3.5), facecolor='white')
        
        # Professional color palette
        colors = ['#2563eb', '#10b981', '#f59e0b', '#ef4444']  # Blue, Green, Amber, Red
        
        # Shorten technology names for display
        short_names = [name.replace("WIFI Mesh (2.4 GHz)", "WiFi (2.4GHz)")
                       .replace("WIFI Mesh (5 GHz)", "WiFi (5GHz)")
                       .replace("WIFI Mesh (2.4GHz)", "WiFi (2.4GHz)")
                       .replace("WIFI Mesh (5GHz)", "WiFi (5GHz)") for name in names]
        
        # Create bars with much narrower width (0.3 for thinner bars)
        bars = plt.bar(short_names, vals, width=0.3, color=colors[:len(short_names)], 
                      edgecolor='white', linewidth=1.2, alpha=0.85)
        
        # Reduced font sizes for smaller figure - remove x-axis label
        plt.xlabel('', fontsize=0)  # Empty x-axis label
        plt.ylabel(metric_label, fontsize=10, fontweight='600', color='#374151', labelpad=8)
        plt.title(f'{metric_label} Comparison', fontsize=11, fontweight='bold', 
                 color='#1f2937', pad=10)
        
        # Improve grid
        plt.grid(axis='y', alpha=0.2, linestyle='--', linewidth=0.6)
        plt.grid(axis='x', alpha=0)
        
        # Rotate x-axis labels
        plt.xticks(rotation=45, ha='right', fontsize=9, color='#374151')
        plt.yticks(fontsize=9, color='#374151')
        
        # Set background color
        ax = plt.gca()
        ax.set_facecolor('#fafafa')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#e5e7eb')
        ax.spines['bottom'].set_color('#e5e7eb')
        
        # Add value labels on bars with better styling (smaller font)
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}',
                    ha='center', va='bottom', fontsize=8, fontweight='500',
                    color='#1f2937', bbox=dict(boxstyle='round,pad=0.2', 
                    facecolor='white', edgecolor='none', alpha=0.7))
        
        plt.tight_layout()
        filename = f"section1_{metric_key}.png"
        plt.savefig(figures_dir / filename, dpi=120, bbox_inches='tight', facecolor='white', edgecolor='none')
        plt.close()


def _generate_section2_charts_from_tables(tables: Dict[str, List[Dict[str, str]]], section_key: str, figures_dir: Path) -> None:
    """Generate Section 2 charts from table data."""
    # Extract node count sections (### 5 Nodes, ### 10 Nodes, etc.)
    # Find all subsections for Scalability Trends
    section2_keys = [k for k in tables.keys() if "Scalability Trends" in k and ":" in k]
    
    if not section2_keys:
        return
    
    # Extract node counts and organize data by technology
    tech_node_data: Dict[str, Dict[int, Dict[str, float]]] = {}
    
    # Map metric names from tables
    metric_map = {
        "Mean PDR (%)": "pdr",
        "Mean Throughput (Mbps)": "throughput",
        "Mean Delay (ms)": "avg_delay",
    }
    
    for subsection_key in section2_keys:
        # Extract node count from subsection (e.g., "2. Scalability Trends:5 Nodes" -> 5)
        subsection = subsection_key.split(":", 1)[1]
        node_count_str = subsection.replace(" Nodes", "").strip()
        try:
            node_count = int(node_count_str)
        except ValueError:
            continue
        
        # Extract data from tables
        rows = tables[subsection_key]
        for row in rows:
            if "Technology" in row:
                tech_name = row.get("Technology", "").strip()
                if not tech_name or tech_name == "Technology" or tech_name == "---":
                    continue
                
                # Shorten WiFi names
                tech_name = tech_name.replace("WIFI Mesh (2.4 GHz)", "WiFi (2.4GHz)")
                tech_name = tech_name.replace("WIFI Mesh (5 GHz)", "WiFi (5GHz)")
                tech_name = tech_name.replace("WIFI Mesh (2.4GHz)", "WiFi (2.4GHz)")
                tech_name = tech_name.replace("WIFI Mesh (5GHz)", "WiFi (5GHz)")
                
                if tech_name not in tech_node_data:
                    tech_node_data[tech_name] = {}
                
                if node_count not in tech_node_data[tech_name]:
                    tech_node_data[tech_name][node_count] = {}
                
                # Extract metric values
                for col_name, metric_key in metric_map.items():
                    if col_name in row:
                        value = _to_float(row.get(col_name, ""))
                        if not math.isnan(value):
                            tech_node_data[tech_name][node_count][metric_key] = value
    
    if not tech_node_data:
        return
    
    # Metrics to plot
    metrics = [
        ("pdr", "PDR (%)"),
        ("throughput", "Throughput (Mbps)"),
        ("avg_delay", "Avg Delay (ms)"),
    ]
    
    # Professional color palette
    colors = ['#2563eb', '#10b981', '#f59e0b', '#ef4444']  # Blue, Green, Amber, Red
    
    for metric_key, metric_label in metrics:
        # Filter technologies that have at least 2 node counts
        valid_techs = {
            tech: data for tech, data in tech_node_data.items()
            if len([nc for nc, vals in data.items() if metric_key in vals]) >= 2
        }
        
        if not valid_techs:
            continue
        
        plt.figure(figsize=(10, 6), facecolor='white')
        
        # Use seaborn style if available
        try:
            sns.set_style("whitegrid")
        except:
            pass
        
        color_idx = 0
        for tech_name, node_data in sorted(valid_techs.items()):
            # Sort by node count
            node_counts = sorted([nc for nc, vals in node_data.items() if metric_key in vals])
            values = [node_data[nc][metric_key] for nc in node_counts]
            
            if len(node_counts) < 2:
                continue
            
            plt.plot(node_counts, values, marker='o', linewidth=2.5, markersize=10,
                    label=tech_name, color=colors[color_idx % len(colors)])
            color_idx += 1
        
        plt.xlabel('Number of Nodes', fontsize=14, fontweight='600', color='#374151', labelpad=10)
        plt.ylabel(metric_label, fontsize=14, fontweight='600', color='#374151', labelpad=10)
        plt.title(f'Scalability Trends: {metric_label}', fontsize=16, fontweight='bold',
                 color='#1f2937', pad=15)
        plt.legend(loc='best', fontsize=12, framealpha=0.9)
        plt.grid(axis='both', alpha=0.2, linestyle='--', linewidth=0.8)
        plt.xticks(fontsize=13, color='#374151')
        plt.yticks(fontsize=13, color='#374151')
        
        # Set background color
        ax = plt.gca()
        ax.set_facecolor('#fafafa')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#e5e7eb')
        ax.spines['bottom'].set_color('#e5e7eb')
        
        plt.tight_layout()
        filename = f"section2_{metric_key}.png"
        plt.savefig(figures_dir / filename, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
        plt.close()


def _generate_section3_chart_from_subsection(tables: List[Dict[str, str]], subsection: str, figures_dir: Path) -> None:
    """Generate Section 3 chart from a subsection table."""
    # Tables should have Mean, Std Dev, Min, Max columns
    if not tables or not any("Mean" in row for row in tables if "Technology" in row):
        return
    
    tech_names = []
    means = []
    stds = []
    mins = []
    maxs = []
    
    for row in tables:
        if "Technology" in row and "Mean" in row:
            tech_name = row.get("Technology", "").strip()
            if not tech_name or tech_name == "Technology" or tech_name == "---":
                continue
            
            tech_names.append(tech_name)
            means.append(_to_float(row.get("Mean", "")))
            stds.append(_to_float(row.get("Std Dev", "")))
            mins.append(_to_float(row.get("Min", "")))
            maxs.append(_to_float(row.get("Max", "")))
    
    if not tech_names:
        return
    
    # Determine metric key from subsection name
    metric_key = None
    metric_label = subsection
    
    if "PDR" in subsection or "pdr" in subsection.lower():
        metric_key = "pdr"
        metric_label = "PDR (%)"
    elif "Throughput" in subsection or "throughput" in subsection.lower():
        metric_key = "throughput"
        metric_label = "Throughput (Mbps)"
    elif "Delay" in subsection or "delay" in subsection.lower():
        metric_key = "avg_delay"
        metric_label = "Avg Delay (ms)"
    elif "Jitter" in subsection or "jitter" in subsection.lower():
        metric_key = "avg_jitter"
        metric_label = "Avg Jitter (ms)"
    
    if not metric_key:
        return
    
    # Create box plot-like visualization from summary stats
    # Since we only have mean, std, min, max, we'll create a simplified box plot
    # Note: This is an approximation since we don't have quartiles from markdown tables
    plt.figure(figsize=(10, 6), facecolor='white')
    
    try:
        sns.set_style("whitegrid")
    except:
        pass
    
    x_pos = range(len(tech_names))
    
    # Shorten WiFi names
    short_names = [name.replace("WIFI Mesh (2.4 GHz)", "WiFi (2.4GHz)")
                   .replace("WIFI Mesh (5 GHz)", "WiFi (5GHz)")
                   .replace("WIFI Mesh (2.4GHz)", "WiFi (2.4GHz)")
                   .replace("WIFI Mesh (5GHz)", "WiFi (5GHz)") for name in tech_names]
    
    # Create simplified box plots using mean, std, min, max
    # Box: mean ± std/2 (approximation)
    # Whiskers: min to max
    for i, (mean, std, min_val, max_val) in enumerate(zip(means, stds, mins, maxs)):
        if math.isnan(mean):
            continue
        
        # Box: mean ± std/2 (approximation of IQR)
        box_low = mean - std / 2
        box_high = mean + std / 2
        box_width = 0.6
        
        # Draw box
        box = plt.Rectangle((i - box_width/2, box_low), box_width, box_high - box_low,
                          facecolor='lightblue', alpha=0.7, edgecolor='black', linewidth=1.5)
        plt.gca().add_patch(box)
        
        # Median line (using mean as approximation since we don't have median)
        plt.plot([i - box_width/2, i + box_width/2], [mean, mean], 
                color='red', linewidth=2, label='Mean' if i == 0 else '')
        
        # Whiskers: from min to box, and from box to max
        plt.plot([i, i], [min_val, box_low], 'k-', linewidth=1.5)
        plt.plot([i, i], [box_high, max_val], 'k-', linewidth=1.5)
        plt.plot([i - 0.1, i + 0.1], [min_val, min_val], 'k-', linewidth=1.5)
        plt.plot([i - 0.1, i + 0.1], [max_val, max_val], 'k-', linewidth=1.5)
    
    plt.xlabel('', fontsize=0)  # Remove x-axis label
    plt.ylabel(metric_label, fontsize=14, fontweight='600', color='#374151', labelpad=10)
    plt.title(f'Distribution Summary: {metric_label}', fontsize=16, fontweight='bold',
             color='#1f2937', pad=15)
    plt.xticks(x_pos, short_names, rotation=45, ha='right', fontsize=13, color='#374151')
    plt.yticks(fontsize=13, color='#374151')
    plt.grid(axis='y', alpha=0.2, linestyle='--', linewidth=0.8)
    
    # Set background color
    ax = plt.gca()
    ax.set_facecolor('#fafafa')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#e5e7eb')
    ax.spines['bottom'].set_color('#e5e7eb')
    
    # Add legend - increased font size
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='lightblue', alpha=0.7, label='Mean ± Std/2 (approx IQR)'),
        plt.Line2D([0], [0], color='red', linewidth=2, label='Mean'),
    ]
    plt.legend(handles=legend_elements, loc='upper right', fontsize=11, framealpha=0.9)
    
    plt.tight_layout()
    filename = f"section3_{metric_key}.png"
    plt.savefig(figures_dir / filename, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()


def _generate_section4_charts_from_tables(tables: Dict[str, List[Dict[str, str]]], section_key: str, figures_dir: Path) -> None:
    """Generate Section 4 charts from table data."""
    # Extract payload size sections (### 10KB Payload, ### 50KB Payload, etc.)
    # Find all subsections for Traffic Load Impact
    section4_keys = [k for k in tables.keys() if "Traffic Load Impact" in k and ":" in k]
    
    if not section4_keys:
        return
    
    # Extract payload sizes and organize data by technology
    tech_payload_data: Dict[str, Dict[str, Dict[str, float]]] = {}
    
    # Map metric names from tables
    metric_map = {
        "Mean PDR (%)": "pdr",
        "Mean Throughput (Mbps)": "throughput",
        "Mean Delay (ms)": "avg_delay",
    }
    
    # Payload size mapping for ordering
    payload_order = ["10KB", "50KB", "1MB"]
    payload_size_map = {
        "10KB Payload": "10KB",
        "50KB Payload": "50KB",
        "1MB Payload": "1MB",
    }
    
    for subsection_key in section4_keys:
        # Extract payload size from subsection (e.g., "4. Traffic Load Impact:10KB Payload" -> "10KB")
        subsection = subsection_key.split(":", 1)[1]
        payload_size = payload_size_map.get(subsection.strip(), subsection.strip())
        
        # Skip if not a recognized payload size
        if payload_size not in payload_order:
            continue
        
        # Extract data from tables
        rows = tables[subsection_key]
        for row in rows:
            if "Technology" in row:
                tech_name = row.get("Technology", "").strip()
                if not tech_name or tech_name == "Technology" or tech_name == "---":
                    continue
                
                # Shorten WiFi names
                tech_name = tech_name.replace("WIFI Mesh (2.4 GHz)", "WiFi (2.4GHz)")
                tech_name = tech_name.replace("WIFI Mesh (5 GHz)", "WiFi (5GHz)")
                tech_name = tech_name.replace("WIFI Mesh (2.4GHz)", "WiFi (2.4GHz)")
                tech_name = tech_name.replace("WIFI Mesh (5GHz)", "WiFi (5GHz)")
                
                if tech_name not in tech_payload_data:
                    tech_payload_data[tech_name] = {}
                
                if payload_size not in tech_payload_data[tech_name]:
                    tech_payload_data[tech_name][payload_size] = {}
                
                # Extract metric values
                for col_name, metric_key in metric_map.items():
                    if col_name in row:
                        value = _to_float(row.get(col_name, ""))
                        if not math.isnan(value):
                            tech_payload_data[tech_name][payload_size][metric_key] = value
    
    if not tech_payload_data:
        return
    
    # Metrics to plot
    metrics = [
        ("pdr", "PDR (%)"),
        ("throughput", "Throughput (Mbps)"),
        ("avg_delay", "Avg Delay (ms)"),
    ]
    
    # Professional color palette
    colors = ['#2563eb', '#10b981', '#f59e0b', '#ef4444']  # Blue, Green, Amber, Red
    
    for metric_key, metric_label in metrics:
        # Filter technologies that have at least 2 payload sizes
        valid_techs = {
            tech: data for tech, data in tech_payload_data.items()
            if len([ps for ps, vals in data.items() if metric_key in vals]) >= 2
        }
        
        if not valid_techs:
            continue
        
        plt.figure(figsize=(10, 6), facecolor='white')
        
        # Use seaborn style if available
        try:
            sns.set_style("whitegrid")
        except:
            pass
        
        color_idx = 0
        for tech_name, payload_data in sorted(valid_techs.items()):
            # Sort by payload order
            payload_sizes = [ps for ps in payload_order if ps in payload_data and metric_key in payload_data[ps]]
            values = [payload_data[ps][metric_key] for ps in payload_sizes]
            
            if len(payload_sizes) < 2:
                continue
            
            plt.plot(payload_sizes, values, marker='o', linewidth=2.5, markersize=10,
                    label=tech_name, color=colors[color_idx % len(colors)])
            color_idx += 1
        
        plt.xlabel('Payload Size', fontsize=14, fontweight='600', color='#374151', labelpad=10)
        plt.ylabel(metric_label, fontsize=14, fontweight='600', color='#374151', labelpad=10)
        plt.title(f'Traffic Load Impact: {metric_label}', fontsize=16, fontweight='bold',
                 color='#1f2937', pad=15)
        plt.legend(loc='best', fontsize=12, framealpha=0.9)
        plt.grid(axis='both', alpha=0.2, linestyle='--', linewidth=0.8)
        plt.xticks(fontsize=13, color='#374151')
        plt.yticks(fontsize=13, color='#374151')
        
        # Set background color
        ax = plt.gca()
        ax.set_facecolor('#fafafa')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#e5e7eb')
        ax.spines['bottom'].set_color('#e5e7eb')
        
        plt.tight_layout()
        filename = f"section4_{metric_key}.png"
        plt.savefig(figures_dir / filename, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
        plt.close()


def build_pdf_report(markdown_path: Path, output_path: Path) -> None:
    """
    Convert a Markdown file to PDF.
    
    Args:
        markdown_path: Path to the input Markdown file
        output_path: Path where the PDF will be written
    """
    if not MARKDOWN_AVAILABLE:
        raise RuntimeError(
            "Markdown library is required for PDF generation. "
            "Install via `pip install markdown`."
        )
    
    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError(
            "WeasyPrint is required for PDF generation. "
            "Install via `pip install weasyprint`."
        )
    
    if not markdown_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {markdown_path}")

    # Read the Markdown file
    markdown_content = markdown_path.read_text(encoding="utf-8")
    
    # Convert Markdown to HTML
    html_content = markdown.markdown(
        markdown_content,
        extensions=["tables", "fenced_code", "nl2br"]
    )
    
    # Post-process HTML to wrap consecutive images in a container for 2x2 grid
    import re
    
    def wrap_consecutive_images(text):
        """Wrap consecutive image paragraphs in a chart-grid container."""
        # Find all consecutive <p><img>...</p> patterns
        pattern = r'(<p><img[^>]*></p>)(?:\s*(?=<p><img[^>]*></p>))*'
        
        def replace_images(match):
            # Get the full match and find all image paragraphs in it
            full_match = match.group(0)
            images = re.findall(r'<p><img[^>]*></p>', full_match)
            if len(images) >= 2:
                # Wrap all images in a container
                return '<div class="chart-grid">' + ''.join(images) + '</div>'
            return full_match
        
        # Replace consecutive image patterns
        result = re.sub(r'(?:<p><img[^>]*></p>\s*){2,}', replace_images, text)
        return result
    
    html_content = wrap_consecutive_images(html_content)
    
    # Add CSS styling for better PDF appearance
    html_with_style = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{
            color: #1f4e79;
            border-bottom: 3px solid #1f4e79;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #2e5f8a;
            margin-top: 30px;
            border-bottom: 2px solid #2e5f8a;
            padding-bottom: 5px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
            font-size: 0.9em;
        }}
        th {{
            background-color: #1f4e79;
            color: white;
            padding: 10px;
            text-align: center;
            font-weight: bold;
        }}
        td {{
            padding: 8px;
            text-align: center;
            border: 1px solid #ddd;
        }}
        tr:nth-child(even) {{
            background-color: #f5f5f5;
        }}
        tr:nth-child(odd) {{
            background-color: white;
        }}
        ul {{
            margin: 10px 0;
            padding-left: 25px;
        }}
        li {{
            margin: 5px 0;
        }}
        code {{
            background-color: #f4f4f4;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 0;
            page-break-inside: avoid;
        }}
        /* Chart grid container for 2x2 layout using float (WeasyPrint compatible) */
        .chart-grid {{
            width: 100%;
            margin: 10px 0;
            overflow: hidden;
            clear: both;
        }}
        .chart-grid::after {{
            content: "";
            display: table;
            clear: both;
        }}
        .chart-grid p {{
            margin: 0 1% 10px 0;
            width: 48%;
            float: left;
            box-sizing: border-box;
        }}
        .chart-grid p:nth-child(2n) {{
            margin-right: 0;
        }}
        .chart-grid img {{
            width: 100%;
            height: auto;
            display: block;
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""
    
    # Convert HTML to PDF
    # Use base_url to resolve relative image paths (e.g., figures/image.png)
    base_url = str(markdown_path.parent.absolute())
    HTML(string=html_with_style, base_url=base_url).write_pdf(output_path)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    
    # Mode 1: Convert existing Markdown file to PDF (standalone conversion)
    if args.convert_md_to_pdf:
        md_path = args.convert_md_to_pdf
        if not md_path.exists():
            print(f"Error: Markdown file not found: {md_path}")
            return 1
        
        # Generate charts from markdown if they don't exist
        if args.output_dir:
            figures_dir = args.output_dir / "figures"
        else:
            figures_dir = md_path.parent / "figures"
        
        charts_generated = generate_charts_from_markdown(md_path, figures_dir)
        if charts_generated:
            print(f"Charts generated in {figures_dir}")
        
        # Determine output PDF path
        if args.output_dir:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = args.output_dir / md_path.with_suffix(".pdf").name
        else:
            pdf_path = md_path.with_suffix(".pdf")
        
        try:
            build_pdf_report(md_path, pdf_path)
            print(f"PDF report written to {pdf_path}")
            return 0
        except RuntimeError as e:
            print(f"Error: Could not generate PDF: {e}")
            return 1
    
    # Mode 2: Generate Markdown report from metrics data
    records = collect_records(args.results_dir)
    sections = [
        build_cross_tech_section(records),
        build_scalability_section(records),
        build_statistical_section(records),
        build_flow_section(records),
    ]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    context = {
        "run_date": args.results_dir.name,
        "results_dir": str(args.results_dir),
        "scenario_count": len(records),
        "generated_at": timestamp,
    }
    md_path = args.output_dir / f"{args.report_name}.md"
    figures_dir = args.output_dir / "figures"
    
    # Generate Markdown file with charts
    try:
        build_markdown_report(md_path, context, sections, records, figures_dir)
        print(f"Markdown report written to {md_path}")
        if MATPLOTLIB_AVAILABLE and figures_dir.exists():
            num_charts = len(list(figures_dir.glob("*.png")))
            if num_charts > 0:
                print(f"Generated {num_charts} chart(s) in {figures_dir}")
    except Exception as e:
        print(f"Warning: Error generating charts: {e}")
        print("Generating report without charts...")
    build_markdown_report(md_path, context, sections)
    print(f"Markdown report written to {md_path}")
    
    # Optionally generate PDF from the Markdown file
    if not (args.no_pdf or args.markdown_only):
        pdf_path = args.output_dir / f"{args.report_name}.pdf"
        try:
            build_pdf_report(md_path, pdf_path)
            print(f"PDF report written to {pdf_path}")
        except RuntimeError as e:
            print(f"Warning: Could not generate PDF: {e}")
            print("The Markdown file has been created successfully.")
            return 1
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

