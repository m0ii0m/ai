"""Draw the figures of REPORT.md from the files in results/.

usage (from the "Fuzzy control" folder): .venv/bin/python simulations/make_figures.py
"""
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
RESULTS, FIGURES = HERE / "results", HERE / "figures"

# reference palette (categorical slots 1-2) and chart ink, light mode
BLUE, ORANGE = "#2a78d6", "#eb6834"
SURFACE, INK, INK_2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK_2, "axes.titlecolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 10, "axes.titlesize": 11, "lines.linewidth": 2, "lines.markersize": 7,
    "legend.frameon": False,
})


def read_csv(name):
    with open(RESULTS / f"{name}.csv") as f:
        return list(csv.DictReader(f))


def number(value):
    return float(value) if value not in ("", "None") else float("nan")


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIGURES / f"{name}.png", dpi=150)
    plt.close(fig)


def dead_zone():
    rows = read_csv("dead_zone")
    gap = [int(r["gap_px"]) for r in rows]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot(gap, [abs(number(r["tsk_velocity"])) for r in rows], color=BLUE, label="tsk (stop rule: v = 0)")
    ax.plot(gap, [abs(number(r["edge_velocity"])) for r in rows], color=ORANGE, label="edge (stop rule: v = -gap)")
    ax.axhline(0.5, color=MUTED, lw=1, ls="--")
    ax.text(60, 0.75, "moves under 0.5 px are rounded away", ha="right", color=INK_2, fontsize=9)
    ax.set_xlabel("gap between paddle centre and target [px]")
    ax.set_ylabel("commanded speed [px/frame]")
    ax.set_title("Commanded speed near the target (dy = 30 px)")
    ax.set_xlim(0, 60)
    ax.set_ylim(0, 10.5)
    ax.legend(loc="center right")
    save(fig, "dead_zone")


def two_panels(name, rows, x_key, x_label, title, panels, default, numeric_x=True):
    """One figure, one measure per panel (never two y-scales on one axis)."""
    labels = [r[x_key] for r in rows]
    x = [number(v) for v in labels] if numeric_x else list(range(len(rows)))
    fig, axes = plt.subplots(1, len(panels), figsize=(4.2 * len(panels), 3.4))
    for ax, (key, y_label, scale) in zip(axes, panels):
        y = [number(r[key]) * scale for r in rows]
        ax.plot(x, y, color=BLUE, marker="o")
        d = labels.index(default)
        ax.plot([x[d]], [y[d]], marker="o", markersize=11, color=BLUE, markerfacecolor=SURFACE, mew=2)
        rising = d + 1 < len(y) and y[d + 1] > y[d]   # keep the label off the line
        ax.annotate("Pong.py", (x[d], y[d]), textcoords="offset points",
                    xytext=(9, -14 if rising else 9), ha="left", color=INK_2, fontsize=9)
        ax.set_ylabel(y_label)
        ax.set_xlabel(x_label)
        if not numeric_x:
            ax.set_xticks(x, [label.replace("/", "\n") for label in labels])
        if scale == 100:
            ax.set_ylim(0, 108)
        else:
            top = max(v for v in y if v == v)
            ax.set_ylim(0, top * 1.2 if top > 0 else 1)
    fig.suptitle(title, color=INK, fontsize=11)
    save(fig, name)


def baseline():
    data = json.loads((RESULTS / "baseline_rallies.json").read_text())
    methods = list(data)
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.4))
    panels = [("player_loss_rate", "rallies lost by the fuzzy paddle [%]", 100),
              ("speed_at_player_loss_mean", "ball speed when it loses [px/frame]", 1)]
    for ax, (key, y_label, scale) in zip(axes, panels):
        values = [(data[m]["summary"][key] or 0) * scale for m in methods]
        bars = ax.bar(methods, values, color=BLUE, width=0.55)
        for bar, value, method in zip(bars, values, methods):
            text = "never loses" if data[method]["summary"]["player_losses"] == 0 else f"{value:.1f}"
            ax.annotate(text, (bar.get_x() + bar.get_width() / 2, value), textcoords="offset points",
                        xytext=(0, 4), ha="center", color=INK_2, fontsize=9)
        ax.set_ylabel(y_label)
        ax.set_ylim(0, max(values) * 1.25 if max(values) else 1)
        ax.grid(axis="x", visible=False)
    fig.suptitle(f"{data[methods[0]]['summary']['rallies']} random rallies against NaiveOponent",
                 color=INK, fontsize=11)
    save(fig, "baseline")


if __name__ == "__main__":
    FIGURES.mkdir(exist_ok=True)
    dead_zone()
    baseline()
    two_panels("sweep_edge_offset", read_csv("sweep_edge_offset"), "edge_offset",
               "edge_offset [px]", "Edge mode: aimed offset (edge zone is 30 < |dx| < 50)",
               [("player_loss_rate", "rallies lost by the fuzzy paddle [%]", 100),
                ("player_edge_hit_rate", "returns hit with the edge [%]", 100)], "40")
    two_panels("sweep_edge_stop_gain", read_csv("sweep_edge_stop_gain"), "stop_gain",
               "gain of the stop rule (v = -k * gap)", "Edge mode: gain of the stop rule",
               [("player_loss_rate", "rallies lost by the fuzzy paddle [%]", 100),
                ("player_edge_hit_rate", "returns hit with the edge [%]", 100)], "1.0")
    two_panels("sweep_gains", read_csv("sweep_gains"), "fast/slow", "gain of the fast rules (top) / slow rules (bottom)",
               "TSK ball following: gains of the fast and slow rules",
               [("player_loss_rate", "rallies lost by the fuzzy paddle [%]", 100),
                ("speed_at_player_loss_mean", "ball speed when it loses [px/frame]", 1)],
               "0.25/0.15", numeric_x=False)
    two_panels("sweep_near_far", read_csv("sweep_near_far"), "near_end/far_full",
               "near ends at (top) / far is full at (bottom) [px]", "TSK ball following: where near turns into far",
               [("player_loss_rate", "rallies lost by the fuzzy paddle [%]", 100),
                ("speed_at_player_loss_mean", "ball speed when it loses [px/frame]", 1)],
               "100/250", numeric_x=False)
    print("figures written to", FIGURES)
