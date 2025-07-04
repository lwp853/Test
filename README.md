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

Follow the on-screen instructions to enter octave band SPLs for Low, Medium and High conditions. Each condition provides a text box where you can paste one or more rows of eight numbers (one set per line). Values may be separated by spaces or commas. Select the NR curves to compare against and click **Generate** to create the plot and results. Use the "Save Plot" button to export a PNG or PDF of the graph.
