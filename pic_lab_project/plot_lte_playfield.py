#!/usr/bin/env python3
"""
Plot the LTE playfield layout used in lte_playfield_traces.cc.

- Canvas: 400 m × 400 m (top-down, X right, Y up)
- Buildings drawn as colored rectangles with labels
- eNB towers shown as grey circles outside the field
- UEs plotted as green dots with labels
"""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

FIELD_SIZE = 400  # meters

BUILDINGS = [
    ("Left Below", "#0D47A1", (0, 60), (96, 104)),
    ("Right Below", "#00838F", (340, 400), (96, 104)),
    ("Left Above", "#6A1B9A", (0, 60), (296, 304)),
    ("Right Above", "#AD1457", (340, 400), (296, 304)),
    ("Cluster 250a", "#FB8C00", (80, 140), (220, 228)),
    ("Cluster 250b", "#FDD835", (170, 250), (220, 228)),
    ("Cluster 50", "#E53935", (255, 335), (20, 28)),
]

ENBS = [
    ("eNB-West", (-100, 200)),
    ("eNB-East", (500, 200)),
]

UES = [
    ("UE0", (50, 50)),
    ("UE1", (100, 80)),
    ("UE2", (150, 120)),
    ("UE3", (200, 180)),
    ("UE4", (250, 220)),
    ("UE5", (300, 280)),
    ("UE6", (350, 320)),
    ("UE7", (100, 300)),
    ("UE8", (200, 100)),
    ("UE9", (350, 350)),
]


def main() -> None:
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_xlim(-120, FIELD_SIZE + 120)
    ax.set_ylim(-40, FIELD_SIZE + 40)
    ax.set_aspect("equal", adjustable="box")
    ax.set_title("LTE Playfield Layout (400 m × 400 m)", fontsize=14, weight="bold")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")

    ax.add_patch(
        Rectangle(
            (0, 0),
            FIELD_SIZE,
            FIELD_SIZE,
            linewidth=1.0,
            edgecolor="black",
            facecolor="#F5F5F5",
            zorder=0,
        )
    )

    for name, color, (x1, x2), (y1, y2) in BUILDINGS:
        width = x2 - x1
        height = y2 - y1
        ax.add_patch(
            Rectangle(
                (x1, y1),
                width,
                height,
                facecolor=color,
                edgecolor="black",
                linewidth=1.2,
                alpha=0.85,
            )
        )
        ax.text(
            x1 + width / 2,
            y1 + height / 2,
            f"{name}\n{width:.0f} m × {height:.0f} m",
            color="white",
            fontsize=8,
            ha="center",
            va="center",
            weight="bold",
        )

    field_corners = [(0, 0), (FIELD_SIZE, 0), (FIELD_SIZE, FIELD_SIZE), (0, FIELD_SIZE)]

    radius_text = {}
    for label, (x, y) in ENBS:
        max_dist = 0.0
        for corner in field_corners:
            dx = corner[0] - x
            dy = corner[1] - y
            max_dist = max(max_dist, (dx**2 + dy**2) ** 0.5)
        for _, (ux, uy) in UES:
            dx = ux - x
            dy = uy - y
            max_dist = max(max_dist, (dx**2 + dy**2) ** 0.5)
        radius_text[label] = max_dist
        ax.add_patch(
            Circle(
                (x, y),
                max_dist,
                facecolor="#B0BEC5",
                edgecolor="none",
                alpha=0.15,
                zorder=1,
            )
        )
        ax.add_patch(
            Circle((x, y), 15, facecolor="#9E9E9E", edgecolor="black", zorder=3)
        )
        ax.text(
            x,
            y - 25,
            f"{label}\nRadius ≈ {max_dist:.0f} m",
            fontsize=10,
            ha="center",
            va="top",
            color="black",
            weight="bold",
        )

    for label, (x, y) in UES:
        ax.scatter(x, y, color="#43A047", edgecolor="black", s=80, zorder=5)
        ax.text(x + 5, y + 5, label, fontsize=9, color="black", weight="bold")

    ax.set_xticks(range(0, FIELD_SIZE + 1, 100))
    ax.set_yticks(range(0, FIELD_SIZE + 1, 100))
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.4)

    handles = [
        Rectangle((0, 0), 1, 1, facecolor=color, edgecolor="black")
        for _, color, *_ in BUILDINGS
    ]
    labels = [name for name, *_ in BUILDINGS]
    handles += [
        Circle((0, 0), 15, facecolor="#9E9E9E", edgecolor="black"),
        Circle((0, 0), 15, facecolor="#B0BEC5", edgecolor="black", alpha=0.3),
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="#43A047",
            markeredgecolor="black",
            markersize=10,
        ),
    ]
    labels += ["eNB Tower", "Coverage Radius", "UE Position"]

    legend = ax.legend(
        handles,
        labels,
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        title="Legend",
    )
    legend.get_title().set_fontweight("bold")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()

