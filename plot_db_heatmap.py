import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata


def load_data(path: str) -> pd.DataFrame:
    """Load CSV data with columns X, Y, Level_dB."""
    df = pd.read_csv(path)
    required = {"X", "Y", "Level_dB"}
    if not required.issubset(df.columns):
        missing = required - set(df.columns)
        raise ValueError(f"Missing columns: {', '.join(missing)}")
    return df


def create_grid(df: pd.DataFrame, grid_size: int = 100):
    """Interpolate Level_dB onto a regular grid."""
    x = df["X"].values
    y = df["Y"].values
    z = df["Level_dB"].values

    xi = np.linspace(x.min(), x.max(), grid_size)
    yi = np.linspace(y.min(), y.max(), grid_size)
    xi, yi = np.meshgrid(xi, yi)

    zi = griddata((x, y), z, (xi, yi), method="cubic")
    return xi, yi, zi


def plot_heatmap(xi, yi, zi, title: str, output: str | None):
    """Plot contour heatmap and optionally save to PNG."""
    fig, ax = plt.subplots(figsize=(6, 5))
    cmap = ax.contourf(xi, yi, zi, levels=50, cmap="viridis")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title(title)
    fig.colorbar(cmap, ax=ax, label="Level (dB)")

    if output:
        fig.savefig(output, dpi=300, bbox_inches="tight")
        print(f"Saved plot to {output}")
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser(description="Plot sound level heatmap from CSV")
    parser.add_argument("csv", help="CSV file with X, Y, Level_dB columns")
    parser.add_argument("-o", "--output", help="Save figure to PNG")
    parser.add_argument("--grid", type=int, default=100, help="Grid resolution")
    parser.add_argument("--title", default="Sound Level Heatmap", help="Plot title")
    args = parser.parse_args()

    df = load_data(args.csv)
    xi, yi, zi = create_grid(df, grid_size=args.grid)
    plot_heatmap(xi, yi, zi, args.title, args.output)


if __name__ == "__main__":
    main()
