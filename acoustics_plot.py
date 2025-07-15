# -*- coding: utf-8 -*-
"""Room acoustics plotting tool.

This script reads Odeon simulation output files (CSV or whitespace
separated) containing acoustic parameters such as RT, C50 and C80 for
multiple receivers. The data can optionally include a ``Source`` column.
Results are grouped by receiver or source and plotted using matplotlib.

Example usage::

    python acoustics_plot.py results.csv --group-by Receiver

"""

from __future__ import annotations

import argparse
from typing import Dict, Iterable

import pandas as pd
import matplotlib.pyplot as plt


PARAMETERS = ["RT", "C50", "C80"]


def load_odeon_data(path: str) -> pd.DataFrame:
    """Load Odeon output data.

    The function tries to automatically detect the delimiter so it can
    handle both comma separated and whitespace separated files.
    The returned dataframe must at least contain the ``Receiver`` column
    and the parameters listed in :data:`PARAMETERS`.
    """

    try:
        df = pd.read_csv(path, sep=None, engine="python")
    except Exception as exc:
        raise ValueError(f"Could not read {path}: {exc}") from exc

    missing = [col for col in ["Receiver", *PARAMETERS] if col not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns: {', '.join(missing)}")

    return df


def group_data(df: pd.DataFrame, by: str) -> pd.DataFrame:
    """Return mean values of PARAMETERS grouped by *by* column."""

    if by not in df.columns:
        raise ValueError(f"Column '{by}' not found in data")

    cols = [by] + PARAMETERS
    grouped = df[cols].groupby(by).mean(numeric_only=True)
    return grouped


def plot_parameters(
    grouped: pd.DataFrame,
    thresholds: Dict[str, float] | None = None,
    group_label: str = "Receiver",
) -> None:
    """Plot acoustic parameters across groups.

    Parameters are expected as columns in ``grouped``. ``thresholds`` is a
    mapping from parameter name to threshold value used for performance
    highlighting.
    """

    thresholds = thresholds or {}
    fig, axes = plt.subplots(len(PARAMETERS), 1, figsize=(8, 4 * len(PARAMETERS)), sharex=True)

    if not isinstance(axes, Iterable):
        axes = [axes]

    for ax, param in zip(axes, PARAMETERS):
        if param not in grouped.columns:
            continue
        values = grouped[param]
        bars = ax.bar(grouped.index.astype(str), values, color="tab:blue")
        thresh = thresholds.get(param)
        if thresh is not None:
            ax.axhline(thresh, color="red", linestyle="--", label=f"Threshold {thresh}")
            for bar, val in zip(bars, values):
                if val > thresh:
                    bar.set_color("tab:red")
        ax.set_ylabel(param)
        ax.grid(True, axis="y", linestyle=":", alpha=0.5)
        if thresh is not None:
            ax.legend()

    axes[-1].set_xlabel(group_label)
    plt.tight_layout()
    plt.show()


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot Odeon acoustic parameters")
    parser.add_argument("file", help="CSV or text file with Odeon results")
    parser.add_argument(
        "--group-by",
        choices=["Receiver", "Source"],
        default="Receiver",
        help="Column to group data by",
    )
    parser.add_argument(
        "--rt-threshold",
        type=float,
        default=1.5,
        help="RT threshold for highlighting (seconds)",
    )
    args = parser.parse_args()

    df = load_odeon_data(args.file)
    grouped = group_data(df, args.group_by)
    thresholds = {"RT": args.rt_threshold}
    plot_parameters(grouped, thresholds, group_label=args.group_by)


if __name__ == "__main__":
    main()
