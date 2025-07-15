# NR Rating Tool

This repository contains a Tkinter-based application for evaluating octave band sound pressure levels (SPL) against Noise Rating (NR) curves.

## Requirements

- Python 3.8+
- matplotlib

Install dependencies using:

```bash
pip install matplotlib
```

## Running the Application

From the repository root, run:

```bash
python nr_tool.py
```

Follow the on-screen instructions to enter octave band SPLs for Low, Medium and High conditions, select NR curves to compare against and generate plots/results. Use the "Save Plot" button to export a PNG or PDF of the graph.

## Third-Octave to Octave Converter

A simple Streamlit utility for converting third-octave band levels into
ISO standard 1/1 octave bands. Paste data copied from Excel and download
the aggregated octave band SPLs as CSV.

### Requirements

- streamlit
- pandas
- matplotlib

Install with:

```bash
pip install streamlit pandas matplotlib
```

### Running the App

From the repository root, run:


```bash
streamlit run octave_converter_app.py
```

Alternatively, run the script directly with Python which will internally
invoke `streamlit run`:

```bash
python octave_converter_app.py
```

The app provides a text area for pasting third-octave band data and
outputs a table of the resulting octave band values along with a plot for
comparison.
