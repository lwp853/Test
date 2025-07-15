"""Compute LAeq and Lden from hourly noise level data."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def load_data(csv_path: str | Path) -> pd.DataFrame:
    """Load hourly noise levels from a CSV file.

    The CSV must contain columns ``Hour`` (datetime) and ``Level_dB``.
    """
    df = pd.read_csv(csv_path)
    df['Hour'] = pd.to_datetime(df['Hour'])
    return df


def classify_period(ts: pd.Timestamp) -> str:
    """Return the period of the day for a timestamp."""
    h = ts.hour
    if 7 <= h < 19:
        return 'day'
    if 19 <= h < 23:
        return 'evening'
    return 'night'


def calculate_daily_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate LAeq and Lden for each day."""
    df = df.copy()
    df['Period'] = df['Hour'].apply(classify_period)
    df['Date'] = df['Hour'].dt.date

    summary = []
    for date, group in df.groupby('Date'):
        laeq = 10 * np.log10(np.mean(10 ** (group['Level_dB'] / 10)))
        day_energy = (10 ** (group.loc[group['Period'] == 'day', 'Level_dB'] / 10)).sum()
        eve_energy = (10 ** ((group.loc[group['Period'] == 'evening', 'Level_dB'] + 5) / 10)).sum()
        night_energy = (10 ** ((group.loc[group['Period'] == 'night', 'Level_dB'] + 10) / 10)).sum()
        lden = 10 * np.log10((day_energy + eve_energy + night_energy) / 24)
        summary.append({'Date': date, 'LAeq': laeq, 'Lden': lden})

    return pd.DataFrame(summary)


def plot_daily_levels(summary: pd.DataFrame) -> None:
    """Plot LAeq and Lden over time."""
    plt.figure(figsize=(8, 4))
    plt.plot(summary['Date'], summary['LAeq'], marker='o', label='LAeq')
    plt.plot(summary['Date'], summary['Lden'], marker='o', label='Lden')
    plt.xlabel('Date')
    plt.ylabel('dB(A)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def export_results(hourly: pd.DataFrame, summary: pd.DataFrame, path: str | Path) -> None:
    """Export hourly data and computed metrics to an Excel file."""
    with pd.ExcelWriter(path) as writer:
        hourly.to_excel(writer, index=False, sheet_name='Hourly Data')
        summary.to_excel(writer, index=False, sheet_name='Daily Metrics')


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute LAeq and Lden from hourly noise levels")
    parser.add_argument('csv', help='Input CSV file with Hour and Level_dB columns')
    parser.add_argument('-o', '--output', default='noise_metrics.xlsx', help='Output Excel file')
    args = parser.parse_args()

    df = load_data(args.csv)
    summary = calculate_daily_metrics(df)
    plot_daily_levels(summary)
    export_results(df, summary, args.output)
    print(f"Results exported to {args.output}")


if __name__ == '__main__':
    main()
