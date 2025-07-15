"""Compute LAeq and Lden from hourly noise level data."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


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
@@ -46,40 +49,137 @@ def calculate_daily_metrics(df: pd.DataFrame) -> pd.DataFrame:
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


def create_template(path: str | Path) -> None:
    """Create an empty spreadsheet with required columns."""
    hours = pd.date_range('00:00', '23:00', freq='1h').time
    df = pd.DataFrame({'Hour': hours, 'Level_dB': [np.nan] * len(hours)})
    df.to_excel(path, index=False)


class NoiseMetricsApp(tk.Tk):
    """Tkinter-based UI for LAeq and Lden calculations."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Noise Metrics")
        self.df: pd.DataFrame | None = None
        self.summary: pd.DataFrame | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        frame = tk.Frame(self)
        frame.pack(padx=10, pady=10)

        btn_frame = tk.Frame(frame)
        btn_frame.pack()
        tk.Button(btn_frame, text="Load CSV", command=self._load).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Create Template", command=self._template).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Export Results", command=self._export).grid(row=0, column=2, padx=5)

        self.text = tk.Text(frame, width=50, height=5)
        self.text.pack(pady=5)

        self.fig, self.ax = plt.subplots(figsize=(6, 3))
        self.canvas = FigureCanvasTkAgg(self.fig, master=frame)
        self.canvas.get_tk_widget().pack()

    def _load(self) -> None:
        path = filedialog.askopenfilename(filetypes=[('CSV', '*.csv')])
        if not path:
            return
        try:
            self.df = load_data(path)
            self.summary = calculate_daily_metrics(self.df)
            self._update_plot()
            self._show_summary()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _template(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension='.xlsx', filetypes=[('Excel', '*.xlsx')])
        if path:
            create_template(path)
            messagebox.showinfo("Template", f"Template saved to {path}")

    def _export(self) -> None:
        if self.df is None or self.summary is None:
            messagebox.showerror("No data", "Load data first")
            return
        path = filedialog.asksaveasfilename(defaultextension='.xlsx', filetypes=[('Excel', '*.xlsx')])
        if path:
            export_results(self.df, self.summary, path)
            messagebox.showinfo("Exported", f"Results exported to {path}")

    def _update_plot(self) -> None:
        assert self.summary is not None
        self.ax.clear()
        self.ax.plot(self.summary['Date'], self.summary['LAeq'], marker='o', label='LAeq')
        self.ax.plot(self.summary['Date'], self.summary['Lden'], marker='o', label='Lden')
        self.ax.set_xlabel('Date')
        self.ax.set_ylabel('dB(A)')
        self.ax.grid(True)
        self.ax.legend()
        self.fig.tight_layout()
        self.canvas.draw()

    def _show_summary(self) -> None:
        assert self.summary is not None
        text = "\n".join(
            f"{row.Date}: LAeq {row.LAeq:.1f} dB, Lden {row.Lden:.1f} dB" for row in self.summary.itertuples()
        )
        self.text.delete('1.0', tk.END)
        self.text.insert(tk.END, text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute LAeq and Lden from hourly noise levels")
    parser.add_argument('csv', help='Input CSV file with Hour and Level_dB columns')
    parser.add_argument('csv', nargs='?', help='Input CSV file with Hour and Level_dB columns')
    parser.add_argument('-o', '--output', default='noise_metrics.xlsx', help='Output Excel file')
    parser.add_argument('--template', metavar='PATH', help='Create blank template spreadsheet')
    parser.add_argument('--gui', action='store_true', help='Launch graphical interface')
    args = parser.parse_args()

    if args.template:
        create_template(args.template)
        print(f"Template saved to {args.template}")
        return

    if args.gui:
        app = NoiseMetricsApp()
        app.mainloop()
        return

    if not args.csv:
        parser.error('csv argument is required unless --gui or --template is used')

    df = load_data(args.csv)
    summary = calculate_daily_metrics(df)
    plot_daily_levels(summary)
    export_results(df, summary, args.output)
    print(f"Results exported to {args.output}")


if __name__ == '__main__':
    main()