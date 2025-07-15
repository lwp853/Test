import argparse
import pandas as pd
import matplotlib.pyplot as plt


def load_octave_csv(path: str) -> pd.DataFrame:
    """Load CSV with frequency and level columns."""
    df = pd.read_csv(path)
    if df.shape[1] < 2:
        raise ValueError("CSV must have at least two columns: frequency and level")
    df = df.iloc[:, :2].copy()
    df.columns = ["Frequency", "Level"]
    return df


def apply_smoothing(series: pd.Series, window: int = 3) -> pd.Series:
    """Return rolling mean for simple smoothing."""
    return series.rolling(window=window, center=True, min_periods=1).mean()


def normalize(series: pd.Series) -> pd.Series:
    """Zero-normalize a series."""
    return series - series.mean()


def main(args: argparse.Namespace) -> None:
    df1 = load_octave_csv(args.file1)
    df2 = load_octave_csv(args.file2)

    if args.smooth:
        df1["Level"] = apply_smoothing(df1["Level"])
        df2["Level"] = apply_smoothing(df2["Level"])

    if args.normalize:
        df1["Level"] = normalize(df1["Level"])
        df2["Level"] = normalize(df2["Level"])

    df = pd.merge(df1, df2, on="Frequency", suffixes=("_1", "_2"))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6))

    ax1.plot(df["Frequency"], df["Level_1"], marker="o", label=args.label1)
    ax1.plot(df["Frequency"], df["Level_2"], marker="o", label=args.label2)
    ax1.set_xscale("log")
    ax1.set_xlabel("Frequency (Hz)")
    ax1.set_ylabel("SPL (dB)")
    ax1.set_title("Octave Band Spectra")
    ax1.grid(True, which="both", ls="--", alpha=0.5)
    ax1.legend()

    diff = df["Level_2"] - df["Level_1"]
    ax2.bar(df["Frequency"], diff, width=df["Frequency"] * 0.3)
    ax2.set_xscale("log")
    ax2.set_xlabel("Frequency (Hz)")
    ax2.set_ylabel("Delta (dB)")
    ax2.set_title("Spectrum Difference")
    ax2.grid(True, which="both", ls="--", alpha=0.5)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare two 1/1 octave band spectra from CSV files"
    )
    parser.add_argument("file1", help="CSV file for first condition")
    parser.add_argument("file2", help="CSV file for second condition")
    parser.add_argument("--label1", default="Condition 1", help="Legend label for first file")
    parser.add_argument("--label2", default="Condition 2", help="Legend label for second file")
    parser.add_argument("--smooth", action="store_true", help="Apply 3-point smoothing to spectra")
    parser.add_argument(
        "--normalize", action="store_true", help="Zero-normalize each spectrum"
    )
    args = parser.parse_args()
    main(args)
