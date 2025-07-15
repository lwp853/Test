# NR Rating Tool

This repository contains three utilities:

1. **NR Rating Tool**
   A Tkinter-based application for evaluating octave-band sound pressure levels (SPL) against Noise Rating (NR) curves. The tool reports fractional NR values (e.g. NR 26.2) using interpolation between the standard NR curves.

2. **Third-Octave to Octave Converter**
   A simple Streamlit utility for converting third-octave band levels into ISO standard 1/1-octave bands. Paste data copied from Excel and download the aggregated octave-band SPLs as CSV.

3. **Sound Level Heatmap**
   A command-line script for visualising sound level data from a CSV file as a 2D heatmap.

---

## 1. NR Rating Tool

### Requirements

- Python 3.8+
- matplotlib
- pandas
- numpy
- scipy

Install dependencies:

```bash
pip install matplotlib pandas numpy scipy
```

---

## 2. Sound Level Heatmap

`plot_db_heatmap.py` loads a CSV containing `X`, `Y` and `Level_dB` columns, interpolates the sound levels onto a grid and displays a 2D contour plot. Use `-o` to save the plot as PNG instead of showing it on screen.

```bash
python plot_db_heatmap.py data.csv -o heatmap.png
```
