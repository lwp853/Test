import re
import io
from typing import List, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt


def parse_pasted_data(text: str) -> Tuple[List[float], List[float]]:
    """Parse pasted text into frequency and dB lists.

    Parameters
    ----------
    text : str
        Two rows of tab/space/comma separated values copied from Excel.

    Returns
    -------
    Tuple[List[float], List[float]]
        Frequencies in Hz and SPL values in dB.
    """
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if len(lines) < 2:
        raise ValueError("Paste two rows: frequencies and dB values.")

    sep = r"[\s,\t]+"
    freqs = [float(f) for f in re.split(sep, lines[0]) if f]
    values = [float(v) for v in re.split(sep, lines[1]) if v]

    if len(freqs) != len(values):
        raise ValueError("Number of frequencies and values must match.")

    return freqs, values


def third_to_octave(freqs: List[float], values: List[float]) -> pd.DataFrame:
    """Convert 1/3 octave band data to 1/1 octave bands using power summation."""
    iso_octaves = np.array([
        31.5,
        63,
        125,
        250,
        500,
        1000,
        2000,
        4000,
        8000,
        16000,
    ])
    freqs = np.asarray(freqs, dtype=float)
    spl = np.asarray(values, dtype=float)

    octave_spl = []
    for center in iso_octaves:
        lower = center / np.sqrt(2)
        upper = center * np.sqrt(2)
        mask = (freqs >= lower) & (freqs < upper)
        if mask.any():
            power = np.sum(10 ** (spl[mask] / 10))
            octave_spl.append(10 * np.log10(power))
        else:
            octave_spl.append(np.nan)

    return pd.DataFrame({"Frequency (Hz)": iso_octaves, "SPL (dB)": octave_spl})


st.title("Third-Octave to Octave Converter")
st.write(
    "Paste two rows of third-octave band data copied from Excel. The first row\n"
    "should contain center frequencies in Hz, and the second row the correspo"
    "nding\nSPL values in dB. Values may be separated by tabs, commas or spac"
    "es."
)

user_input = st.text_area("Paste Data", height=150)

if user_input:
    try:
        third_freqs, third_values = parse_pasted_data(user_input)
        df_third = pd.DataFrame(
            {"Frequency (Hz)": third_freqs, "SPL (dB)": third_values}
        )

        df_octave = third_to_octave(third_freqs, third_values)

        st.subheader("1/1 Octave Band Results")
        st.dataframe(
            df_octave.style.format({"Frequency (Hz)": "{:.1f}", "SPL (dB)": "{:.1f}"}),
            use_container_width=True,
        )

        csv = df_octave.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, file_name="octave_bands.csv")

        st.subheader("Comparison Plot")
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(df_third["Frequency (Hz)"], df_third["SPL (dB)"], width=2,
               alpha=0.5, label="Third-Octave")
        ax.bar(df_octave["Frequency (Hz)"], df_octave["SPL (dB)"], width=30,
               alpha=0.5, label="1/1 Octave")
        ax.set_xscale("log")
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("SPL (dB)")
        ax.legend()
        st.pyplot(fig)

    except Exception as exc:
        st.error(str(exc))

