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

## 3. Noise Metrics Tool

A utility for calculating daily **LAeq** and **Lden** values from hourly noise measurements. Results can be produced via the command line or through a simple Tkinter based interface. The tool can also generate a blank spreadsheet with the required columns.

### Example

```bash
pip install pandas numpy matplotlib openpyxl
# command-line usage
python noise_metrics.py your_data.csv -o results.xlsx

# launch the GUI
python noise_metrics.py --gui

# create an empty template
python noise_metrics.py --template blank.xlsx
```
