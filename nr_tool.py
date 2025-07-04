import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Reference NR curves for octave bands 63 Hz to 8 kHz
NR_CURVES = {
    'NR20': [51, 39, 30, 22, 17, 14, 12, 11],
    'NR25': [55, 44, 35, 28, 23, 20, 18, 17],
    'NR30': [59, 48, 39, 33, 28, 25, 23, 22],
    'NR35': [63, 52, 44, 38, 33, 30, 28, 27],
    'NR40': [67, 56, 48, 42, 38, 35, 33, 32],
    'NR45': [71, 60, 52, 47, 43, 40, 38, 37],
    'NR50': [75, 64, 56, 51, 48, 45, 43, 42],
}

FREQUENCIES = ['63', '125', '250', '500', '1k', '2k', '4k', '8k']

class NRTool(tk.Tk):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.title("NR Rating Tool")
        self.curve_vars = {}
        self.entries = {'Low': [], 'Medium': [], 'High': []}
        self._build_ui()

    def _build_ui(self):
        """Create input fields and controls."""
        frm = ttk.Frame(self)
        frm.pack(padx=10, pady=10)

        # NR curve selector
        curves_frame = ttk.LabelFrame(frm, text="NR Curves")
        curves_frame.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        for i, curve in enumerate(NR_CURVES.keys()):
            var = tk.BooleanVar(value=curve == 'NR35')
            cb = ttk.Checkbutton(curves_frame, text=curve, variable=var)
            cb.grid(row=i // 4, column=i % 4, sticky='w')
            self.curve_vars[curve] = var

        # Input fields
        input_frame = ttk.LabelFrame(frm, text="Octave Band SPL (dB)")
        input_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        for col, freq in enumerate(FREQUENCIES):
            ttk.Label(input_frame, text=f"{freq} Hz").grid(row=0, column=col + 1)
        for row, cond in enumerate(self.entries.keys(), 1):
            ttk.Label(input_frame, text=cond).grid(row=row, column=0, sticky='e')
            for col in range(len(FREQUENCIES)):
                e = ttk.Entry(input_frame, width=5)
                e.grid(row=row, column=col + 1)
                self.entries[cond].append(e)

        # Action buttons
        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=2, column=0, pady=5)
        ttk.Button(btn_frame, text="Generate", command=self.generate).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Save Plot", command=self.save_plot).grid(row=0, column=1, padx=5)

        # Text output
        self.output = tk.Text(frm, width=80, height=10)
        self.output.grid(row=3, column=0, pady=5)

        # Matplotlib Figure
        self.fig, self.ax = plt.subplots(figsize=(8, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=frm)
        self.canvas.get_tk_widget().grid(row=4, column=0)
        self.ax.set_xlabel('Frequency (Hz)')
        self.ax.set_ylabel('SPL (dB)')
        self.ax.set_xticks(range(len(FREQUENCIES)))
        self.ax.set_xticklabels(FREQUENCIES)

    def _read_inputs(self):
        """Return dictionary of condition -> list of SPL values. Raise ValueError if invalid."""
        data = {}
        for cond, entries in self.entries.items():
            values = []
            for e in entries:
                val = e.get()
                if not val:
                    raise ValueError(f"Missing value for {cond}")
                try:
                    values.append(float(val))
                except ValueError:
                    raise ValueError(f"Invalid numeric value '{val}' for {cond}")
            data[cond] = values
        return data

    def generate(self):
        """Calculate NR ratings and update plot/output."""
        try:
            measurements = self._read_inputs()
        except ValueError as exc:
            messagebox.showerror("Input Error", str(exc))
            return

        selected_curves = {c: v.get() for c, v in self.curve_vars.items() if v.get()}
        if not selected_curves:
            messagebox.showerror("Input Error", "Select at least one NR curve")
            return

        self.ax.clear()
        results = []
        colors = {'Low': 'tab:blue', 'Medium': 'tab:orange', 'High': 'tab:green'}

        # Plot NR curves
        for curve_name in selected_curves:
            self.ax.plot(FREQUENCIES, NR_CURVES[curve_name], label=curve_name, linestyle='--')

        # Evaluate each condition
        for cond, values in measurements.items():
            self.ax.plot(FREQUENCIES, values, marker='o', label=cond, color=colors[cond])
            rating, exceeded = self._nr_rating(values)
            results.append(f"{cond}: NR{rating} (exceed at {', '.join(exceeded) if exceeded else 'none'})")

        self.ax.legend()
        self.ax.set_xlabel('Frequency (Hz)')
        self.ax.set_ylabel('SPL (dB)')
        self.ax.grid(True)
        self.canvas.draw()

        self.output.delete('1.0', tk.END)
        self.output.insert(tk.END, "\n".join(results))
        self.output.insert(tk.END, "\n\nCopy for report:\n")
        self.output.insert(tk.END, "\n".join(results))

    def _nr_rating(self, values):
        """Return highest NR curve exceeded and list of frequencies exceeded."""
        exceeded = []
        rating = None
        for curve_name, curve_vals in NR_CURVES.items():
            for val, ref, freq in zip(values, curve_vals, FREQUENCIES):
                if val > ref:
                    exceeded.append(freq)
                    rating = int(curve_name[2:])
                    break
            if exceeded:
                break
        if rating is None:
            rating = 20
        return rating, exceeded

    def save_plot(self):
        """Save current plot to PNG or PDF."""
        filetypes = [('PNG', '*.png'), ('PDF', '*.pdf')]
        path = filedialog.asksaveasfilename(defaultextension='.png', filetypes=filetypes)
        if path:
            self.fig.savefig(path)
            messagebox.showinfo("Saved", f"Plot saved to {path}")

if __name__ == '__main__':
    app = NRTool()
    app.mainloop()
