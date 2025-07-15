# NR Rating Tool

This repository contains two utilities:

1. **NR Rating Tool**  
   A Tkinter‑based application for evaluating octave‑band sound pressure levels (SPL) against Noise Rating (NR) curves. The tool reports fractional NR values (e.g. NR 26.2) using interpolation between the standard NR curves.

2. **Third‑Octave to Octave Converter**  
   A simple Streamlit utility for converting third‑octave band levels into ISO standard 1/1‑octave bands. Paste data copied from Excel and download the aggregated octave‑band SPLs as CSV.

---

## 1. NR Rating Tool

### Requirements

- Python 3.8+
- matplotlib

Install dependencies:

```bash
pip install matplotlib
```

---

## 2. Room Acoustics Plotter

### Requirements

- pandas
- matplotlib

Install dependencies:

```bash
pip install pandas matplotlib
```

This command line utility plots common acoustic parameters from Odeon simulation output files. Provide a CSV or whitespace separated text file containing columns `Receiver`, `Source`, `RT`, `C50` and `C80`. Each parameter is plotted across receivers (or sources) in separate subplots with optional threshold highlighting.

Example:

```bash
python acoustics_plot.py results.csv --group-by Receiver --rt-threshold 1.5
```
