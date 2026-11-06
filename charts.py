"""The charts for the README. Each function takes the tables from data/ and returns a figure; `save` writes it to charts/.

Usage:  python charts.py     draws every chart from the tables in data/

One style for all of them: a warm paper ground so the images read the same on a light or dark GitHub page, dark ink for text, one accent for what the chart is about,
grey for everything else, and a fixed colour for each format wherever formats are compared.
"""
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PAPER, INK, MUTED, RULE, ACCENT = "#FAF8F5", "#1A1A1A", "#6B6B6B", "#E3DED6", "#C4313A"
FORMAT_COLOUR = {"TEST": "#1F3A5F", "ODI": "#C4313A", "T20": "#D9A441"}
FORMAT_NAME = {"TEST": "Tests", "ODI": "ODIs", "T20": "T20s"}
ORDER = ["TEST", "ODI", "T20"]
CHARTS = Path("charts")

plt.rcParams.update({
    "figure.facecolor": PAPER, "axes.facecolor": PAPER, "savefig.facecolor": PAPER,
    "font.family": ["Avenir Next", "Helvetica Neue", "DejaVu Sans"], "font.size": 11,
    "text.color": INK, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": RULE, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "figure.dpi": 100, "savefig.dpi": 200,
})


def _title(fig, title: str, sub: str | None = None) -> None:
    fig.text(0.02, 0.975, title, fontsize=17, fontweight="bold", va="top", ha="left")
    if sub:
        fig.text(0.02, 0.915, sub, fontsize=11, color=MUTED, va="top", ha="left")


def _source(fig) -> None:
    fig.text(0.98, 0.012, "Data: Cricsheet (ODC-BY)", fontsize=8, color=MUTED, ha="right", va="bottom")


def save(fig, name: str) -> Path:
    CHARTS.mkdir(exist_ok=True)
    path = CHARTS / f"{name}.png"
    fig.savefig(path)
    return path


def top_century_makers(centuries: pd.DataFrame, n: int = 8):
    """Who scored the most centuries in each format."""
    fig, axes = plt.subplots(1, 3, figsize=(12, 5), gridspec_kw={"wspace": 0.55})
    for ax, f in zip(axes, ORDER):
        top = centuries[centuries.format == f].groupby("player").size().sort_values(ascending=False).head(n)[::-1]
        ax.barh(top.index, top.values, color=FORMAT_COLOUR[f], height=0.68)
        for y, v in enumerate(top.values):
            ax.text(v + top.max() * 0.02, y, str(v), va="center", fontsize=10, fontweight="bold")
        ax.set_title(FORMAT_NAME[f])
        ax.set_xticks([]); ax.spines[["left", "bottom"]].set_visible(False)
        ax.tick_params(axis="y", length=0, labelsize=10, labelcolor=INK)
        ax.set_xlim(0, top.max() * 1.15)
    _title(fig, "Root, Kohli and Gayle lead their formats", "Most centuries in the data, by format. Coverage is thin before 2006, so earlier careers are cut short")
    fig.subplots_adjust(top=0.8, bottom=0.07, left=0.12, right=0.97)
    _source(fig)
    return fig


def conversion(player_format: pd.DataFrame, minimum: int = 40, n: int = 12):
    """Of the innings that reached 50, how many went on to 100."""
    p = player_format.groupby(["player_id", "player"], as_index=False)[["fifties", "hundreds"]].sum()
    p["reached_50"] = p.fifties + p.hundreds
    p = p[p.reached_50 >= minimum].copy()
    p["rate"] = p.hundreds / p.reached_50 * 100
    overall = p.hundreds.sum() / p.reached_50.sum() * 100
    top = p.sort_values("rate", ascending=False).head(n)[::-1]
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.hlines(top.player, 0, top.rate, color=RULE, linewidth=2)
    ax.scatter(top.rate, top.player, s=70, color=ACCENT, zorder=3)
    for y, (r, h, t) in enumerate(zip(top.rate, top.hundreds, top.reached_50)):
        ax.text(r + 0.7, y, f"{r:.0f}%  ({h} of {t})", va="center", fontsize=10)
    ax.axvline(overall, color=MUTED, linestyle=(0, (3, 3)), linewidth=1)
    ax.text(overall + 0.4, -0.9, f"all {len(p)} players: {overall:.0f}%", color=MUTED, fontsize=9, va="top")
    ax.set_xlim(0, top.rate.max() * 1.22); ax.set_xticks([]); ax.spines[["left", "bottom"]].set_visible(False)
    ax.tick_params(axis="y", length=0, labelcolor=INK); ax.set_ylim(-1.3, len(top) - 0.4)
    _title(fig, "Who turns fifties into hundreds", f"Share of 50-plus innings that reached 100, all formats, players with at least {minimum} such innings")
    fig.subplots_adjust(top=0.82, bottom=0.07, left=0.16, right=0.97)
    _source(fig)
    return fig


def centuries_per_year(centuries: pd.DataFrame):
    """How many centuries were scored each year."""
    years = centuries[centuries.year >= 2006].groupby(["year", "format"]).size().unstack(fill_value=0).reindex(columns=ORDER, fill_value=0)
    fig, ax = plt.subplots(figsize=(10, 5.4))
    for f in ORDER:
        ax.plot(years.index, years[f], color=FORMAT_COLOUR[f], linewidth=2.4, marker="o", markersize=4)
        ax.text(years.index[-1] + 0.35, years[f].iloc[-1], FORMAT_NAME[f], color=FORMAT_COLOUR[f], fontsize=11, fontweight="bold", va="center")
    ax.set_xlim(years.index[0], years.index[-1] + 2.4)
    ax.set_ylim(0, None)
    ax.yaxis.grid(True, color=RULE, linewidth=0.8); ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False); ax.tick_params(length=0)
    _title(fig, "T20 centuries have overtaken Tests", "Centuries scored each year, by format, from 2006. 2026 runs to early October")
    fig.subplots_adjust(top=0.84, bottom=0.09, left=0.07, right=0.97)
    _source(fig)
    return fig


def pace_by_era(centuries: pd.DataFrame):
    """How fast the hundred came up, by era."""
    bins = {"TEST": [2005, 2010, 2015, 2020, 2026], "ODI": [2005, 2010, 2015, 2020, 2026], "T20": [2005, 2015, 2020, 2026]}
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.8), gridspec_kw={"wspace": 0.35})
    for ax, f in zip(axes, ORDER):
        d = centuries[centuries.format == f].copy()
        edges = bins[f]
        d["era"] = pd.cut(d.year, edges)
        med = d.groupby("era", observed=True).balls_to_100.median()
        labels = [f"{int(i.left) + 1}–{int(i.right)}" if i.right < 2026 else f"{int(i.left) + 1}–" for i in med.index]
        ax.plot(range(len(med)), med.values, color=FORMAT_COLOUR[f], linewidth=2.6, marker="o", markersize=7)
        for x, v in enumerate(med.values):
            ax.annotate(f"{v:.0f}", (x, v), xytext=(0, 11), textcoords="offset points", ha="center", fontsize=10, fontweight="bold", color=INK)
        ax.set_xticks(range(len(med))); ax.set_xticklabels(labels, fontsize=9)
        lo, hi = med.min(), med.max(); pad = max(4, (hi - lo) * 0.8)
        ax.set_ylim(lo - pad, hi + pad)
        ax.set_yticks([]); ax.spines[["left"]].set_visible(False); ax.tick_params(length=0)
        ax.set_title(FORMAT_NAME[f])
    _title(fig, "The hundred has barely got quicker", "Median balls faced to reach 100, by era, from 2006. Each panel has its own scale")
    fig.subplots_adjust(top=0.78, bottom=0.12, left=0.03, right=0.98)
    _source(fig)
    return fig


def first_or_chasing(centuries: pd.DataFrame, team_innings: pd.DataFrame):
    """Where in a match and in the order centuries come."""
    t = team_innings.copy()
    t["rate"] = t.with_a_century / t.team_innings * 100
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw={"width_ratios": [1, 1.25], "wspace": 0.25})
    width = 0.36
    for i, f in enumerate(ORDER):
        for j, chasing in enumerate([False, True]):
            v = t[(t.format == f) & (t.chasing == chasing)].rate.iloc[0]
            a.bar(i + (j - 0.5) * width, v, width * 0.94, color=FORMAT_COLOUR[f], alpha=1 if not chasing else 0.45)
            a.text(i + (j - 0.5) * width, v + 0.8, f"{v:.0f}%", ha="center", fontsize=10, fontweight="bold")
            a.text(i + (j - 0.5) * width, -1.2, "chasing" if chasing else "first", ha="center", va="top", fontsize=8.5, color=MUTED)
    a.set_xticks(range(3)); a.set_xticklabels([FORMAT_NAME[f] for f in ORDER], fontsize=11, color=INK)
    a.tick_params(axis="x", length=0, pad=22); a.set_yticks([]); a.spines[["left"]].set_visible(False)
    a.set_title("Team innings with a century")
    pos = centuries.assign(position=centuries.position.clip(upper=8))
    share = pos.groupby(["format", "position"]).size().unstack(fill_value=0)
    share = share.div(share.sum(axis=1), axis=0) * 100
    for f in ORDER:
        b.plot(share.columns, share.loc[f], color=FORMAT_COLOUR[f], linewidth=2.6, marker="o", markersize=5)
        peak = share.loc[f].idxmax()
        b.annotate(FORMAT_NAME[f], (peak, share.loc[f].max()), xytext=(12, 4) if f != "TEST" else (0, 10), textcoords="offset points", color=FORMAT_COLOUR[f], fontsize=11, fontweight="bold", ha="left" if f != "TEST" else "center")
    b.set_xticks(range(1, 9)); b.set_xticklabels([str(i) for i in range(1, 8)] + ["8+"], color=INK)
    b.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%"); b.yaxis.grid(True, color=RULE, linewidth=0.8); b.set_axisbelow(True)
    b.spines["left"].set_visible(False); b.tick_params(length=0); b.set_xlabel("Batting position")
    b.set_title("Share of centuries by batting position")
    _title(fig, "Hundreds are harder to make in a chase", "Centuries are rarer in a chase, and in limited-overs cricket most come from the top three")
    fig.subplots_adjust(top=0.78, bottom=0.17, left=0.03, right=0.98)
    _source(fig)
    return fig


def results(centuries: pd.DataFrame, team_results: pd.DataFrame):
    """How the match ended, with and without a century."""
    kinds = ["won", "draw", "tied", "no result", "lost"]
    colours = {"won": ACCENT, "draw": "#9A958C", "tied": "#C9C4BA", "no result": "#E3DED6", "lost": "#3B3B3B"}
    fig, axes = plt.subplots(3, 1, figsize=(10, 5.6), gridspec_kw={"hspace": 0.9})
    for ax, f in zip(axes, ORDER):
        base = team_results[team_results.format == f].set_index("result").team_matches.reindex(kinds, fill_value=0)
        base = base / base.sum() * 100
        with_c = centuries[centuries.format == f].result.value_counts().reindex(kinds, fill_value=0)
        with_c = with_c / with_c.sum() * 100
        rows = [("All teams", base), ("Team with a century", with_c)]
        for y, (label, s) in zip([1, 0], rows):
            left = 0
            for k in kinds:
                v = s[k]
                ax.barh(y, v, left=left, color=colours[k], height=0.62, edgecolor=PAPER, linewidth=1)
                if v >= 8:
                    ax.text(left + v / 2, y, f"{v:.0f}%", ha="center", va="center", fontsize=10, fontweight="bold",
                            color="white" if k in ("won", "lost", "draw") else INK)
                left += v
        ax.set_yticks([1, 0]); ax.set_yticklabels([r[0] for r in rows], fontsize=10, color=INK)
        ax.set_xlim(0, 100); ax.set_xticks([]); ax.spines[["left", "bottom"]].set_visible(False); ax.tick_params(length=0)
        ax.set_title(FORMAT_NAME[f], fontsize=12)
    handles = [plt.Rectangle((0, 0), 1, 1, color=colours[k]) for k in kinds]
    fig.legend(handles, kinds, loc="lower center", ncol=5, frameon=False, fontsize=9.5, bbox_to_anchor=(0.5, 0.0))
    _title(fig, "A century usually means a win", "How the match ended for the team that scored it, against every team's matches")
    fig.subplots_adjust(top=0.80, bottom=0.12, left=0.2, right=0.97)
    _source(fig)
    return fig


def how_it_is_built(centuries: pd.DataFrame):
    """The second fifty comes faster, and boundaries carry about half the runs outside T20."""
    d = centuries.assign(second_50=centuries.balls_to_100 - centuries.balls_to_50, share=(4 * centuries.fours + 6 * centuries.sixes) / centuries.runs * 100)
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.8), gridspec_kw={"wspace": 0.35})
    for y, f in enumerate(ORDER[::-1]):
        s = d[d.format == f]
        first, second = s.balls_to_50.median(), s.second_50.median()
        a.hlines(y, second, first, color=RULE, linewidth=4, zorder=1)
        a.scatter([first], [y], s=110, color=FORMAT_COLOUR[f], zorder=3)
        a.scatter([second], [y], s=110, facecolor=PAPER, edgecolor=FORMAT_COLOUR[f], linewidth=2.4, zorder=3)
        a.text(first, y + 0.3, f"{first:.0f}", ha="center", fontsize=10, fontweight="bold")
        a.text(second, y + 0.3, f"{second:.0f}", ha="center", fontsize=10, fontweight="bold")
    a.set_yticks(range(3)); a.set_yticklabels([FORMAT_NAME[f] for f in ORDER[::-1]], fontsize=11, color=INK)
    a.set_ylim(-0.6, 2.7); a.set_xlim(0, None); a.xaxis.grid(True, color=RULE, linewidth=0.8); a.set_axisbelow(True)
    a.spines[["left", "bottom"]].set_visible(False); a.tick_params(length=0)
    a.set_xlabel("Median balls faced")
    a.scatter([], [], s=70, color=MUTED, label="first 50"); a.scatter([], [], s=70, facecolor=PAPER, edgecolor=MUTED, linewidth=2, label="second 50")
    a.legend(frameon=False, loc="lower right", fontsize=9)
    a.set_title("Balls for the first and the second 50")
    for y, f in enumerate(ORDER[::-1]):
        s = d[d.format == f].share
        q1, med, q3 = s.quantile([0.25, 0.5, 0.75])
        b.hlines(y, q1, q3, color=FORMAT_COLOUR[f], linewidth=9, alpha=0.35, zorder=1)
        b.scatter([med], [y], s=110, color=FORMAT_COLOUR[f], zorder=3)
        b.text(med, y + 0.3, f"{med:.0f}%", ha="center", fontsize=10, fontweight="bold")
    b.set_yticks(range(3)); b.set_yticklabels([FORMAT_NAME[f] for f in ORDER[::-1]], fontsize=11, color=INK)
    b.set_ylim(-0.6, 2.7); b.set_xlim(20, 100); b.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    b.xaxis.grid(True, color=RULE, linewidth=0.8); b.set_axisbelow(True); b.spines[["left", "bottom"]].set_visible(False); b.tick_params(length=0)
    b.set_xlabel("Share of runs from fours and sixes")
    b.set_title("Runs from boundaries (middle half shaded)")
    _title(fig, "The second fifty is faster in every format", "How a century is built")
    fig.subplots_adjust(top=0.78, bottom=0.16, left=0.07, right=0.98)
    _source(fig)
    return fig


def main() -> None:
    centuries = pd.read_csv("data/centuries.csv")
    player_format = pd.read_csv("data/player_format.csv")
    team_innings = pd.read_csv("data/team_innings.csv")
    team_results = pd.read_csv("data/team_results.csv")
    drawings = {
        "01_top_century_makers": lambda: top_century_makers(centuries),
        "02_conversion": lambda: conversion(player_format),
        "03_centuries_per_year": lambda: centuries_per_year(centuries),
        "04_pace_by_era": lambda: pace_by_era(centuries),
        "05_first_or_chasing": lambda: first_or_chasing(centuries, team_innings),
        "06_results": lambda: results(centuries, team_results),
        "07_how_it_is_built": lambda: how_it_is_built(centuries),
    }
    for name, draw in drawings.items():
        print(save(draw(), name))


if __name__ == "__main__":
    main()
