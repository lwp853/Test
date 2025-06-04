import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
from scipy.stats import mode  # for mode calculation
import sqlite3
import logging

# PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# For handling temporary files and mapping
import os
import webbrowser
import folium
import matplotlib.pyplot as plt

# ------------------ Logging Setup ------------------
logging.basicConfig(
    filename='acoustic_processor.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)
logging.info("Acoustic Processor started.")

# ------------------ Helper Functions ------------------

def nth_highest(series, n):
    series = series.dropna().sort_values(ascending=False)
    return series.iloc[n - 1] if len(series) >= n else None

def nth_lowest(series, n):
    series = series.dropna().sort_values()
    return series.iloc[n - 1] if len(series) >= n else None

def parse_date(x):
    # Try mm/dd/yyyy format first (e.g., "2/24/2023")
    try:
        return pd.to_datetime(x, format="%m/%d/%Y")
    except Exception:
        pass
    # Then try ISO8601 (yyyy-mm-dd)
    try:
        return pd.to_datetime(x, format="%Y-%m-%d")
    except Exception:
        return pd.NaT

def safe_date_str(dt):
    """Return a formatted date string if dt is valid; otherwise, return an empty string."""
    return "" if pd.isnull(dt) else dt.strftime("%Y-%m-%d")

def get_date_only(dt):
    """
    If dt is NaT, return NaT.
    Otherwise, if dt.time() < 07:00, subtract 1 day from dt.date().
    (This is the simpler version without special handling for the first day.)
    """
    if pd.isnull(dt):
        return pd.NaT
    return (dt - timedelta(days=1)).date() if dt.time() < time(7, 0, 0) else dt.date()

def round_if_number(x, decimals=1):
    if isinstance(x, (int, float, np.number)):
        return round(x, decimals)
    return x

# Mapping function using Folium
def show_map_with_folium(latitudes, longitudes, labels=None, values=None):
    """Creates an interactive map with markers using Folium.
    If values are provided, markers are colour-coded based on the value
    (simple green/orange/red scheme).
    """
    if len(latitudes) == 0 or len(longitudes) == 0:
        messagebox.showwarning("Mapping", "No valid location data available.")
        return
    avg_lat = np.mean(latitudes)
    avg_lon = np.mean(longitudes)
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=10)
    def value_color(v):
        try:
            if v is None or v == "No Data" or np.isnan(v):
                return "blue"
            if v < 50:
                return "green"
            elif v < 70:
                return "orange"
            else:
                return "red"
        except Exception:
            return "blue"

    for i in range(len(latitudes)):
        label = labels[i] if (labels and i < len(labels)) else f"Site {i+1}"
        color = value_color(values[i]) if values and i < len(values) else "blue"
        folium.CircleMarker(
            location=[latitudes[i], longitudes[i]],
            radius=6,
            color=color,
            fill=True,
            fill_color=color,
            popup=str(label),
        ).add_to(m)
    map_file = "temp_map.html"
    m.save(map_file)
    webbrowser.open(os.path.abspath(map_file))

def store_to_database(summary_df):
    """
    Stores summary_df into the 'summary' table, automatically adding new columns
    (such as 'Latitude' or 'Longitude') if they don't already exist.
    """
    try:
        conn = sqlite3.connect("acoustic_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='summary'")
        result = cursor.fetchone()
        if result:
            cursor.execute("PRAGMA table_info(summary)")
            existing_cols = [row[1] for row in cursor.fetchall()]  # row[1] is the column name
            for col in summary_df.columns:
                if col not in existing_cols:
                    col_type = "FLOAT" if pd.api.types.is_numeric_dtype(summary_df[col]) else "TEXT"
                    alter_sql = f"ALTER TABLE summary ADD COLUMN '{col}' {col_type};"
                    cursor.execute(alter_sql)
            conn.commit()
        summary_df.to_sql("summary", conn, if_exists="append", index=False)
        conn.close()
        messagebox.showinfo("Database", "Data stored in the database successfully.")
    except Exception as ex:
        messagebox.showerror("Database Error", str(ex))

# ------------------ Main Application ------------------

class DataProcessorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Acoustic Data Processor")
        self.geometry("1000x700")
        self.input_file = None
        self.anomaly_threshold = 2.0  # default anomaly threshold (in standard deviations)
        self.latest_summary = None   # Daily summary DataFrame
        self.latest_overall = None   # Overall metrics dict
        self.raw_data = None        # Full processed DataFrame
        self.create_widgets()
    
    def create_widgets(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)
        
        self.tab1 = ttk.Frame(notebook)
        notebook.add(self.tab1, text="Process Data")
        self.create_process_tab(self.tab1)
        
        self.tab2 = ttk.Frame(notebook)
        notebook.add(self.tab2, text="Batch Processing")
        self.create_batch_tab(self.tab2)
        
        self.tab3 = ttk.Frame(notebook)
        notebook.add(self.tab3, text="Settings")
        self.create_settings_tab(self.tab3)
        
        self.tab4 = ttk.Frame(notebook)
        notebook.add(self.tab4, text="Reports")
        self.create_reports_tab(self.tab4)
        
        self.tab5 = ttk.Frame(notebook)
        notebook.add(self.tab5, text="Database")
        self.create_database_tab(self.tab5)
        
        self.tab6 = ttk.Frame(notebook)
        notebook.add(self.tab6, text="Mapping")
        self.create_mapping_tab(self.tab6)

        self.tab7 = ttk.Frame(notebook)
        notebook.add(self.tab7, text="Graphs")
        self.create_graph_tab(self.tab7)
    
    def create_process_tab(self, frame):
        btn_frame = tk.Frame(frame)
        btn_frame.pack(pady=10)
        browse_btn = tk.Button(btn_frame, text="Browse Input File", command=self.browse_file)
        browse_btn.pack(side="left", padx=5)
        process_btn = tk.Button(btn_frame, text="Process Data", command=self.process_data)
        process_btn.pack(side="left", padx=5)
        self.process_output_label = tk.Label(frame, text="", fg="green")
        self.process_output_label.pack(pady=10)
    
    def create_batch_tab(self, frame):
        btn_frame = tk.Frame(frame)
        btn_frame.pack(pady=10)
        batch_btn = tk.Button(btn_frame, text="Select Multiple Files", command=self.batch_process)
        batch_btn.pack(padx=5)
        self.batch_output_label = tk.Label(frame, text="", fg="green")
        self.batch_output_label.pack(pady=10)
    
    def create_settings_tab(self, frame):
        lbl = tk.Label(frame, text="Set Anomaly Threshold (standard deviations):")
        lbl.pack(pady=5)
        self.threshold_entry = tk.Entry(frame)
        self.threshold_entry.insert(0, str(self.anomaly_threshold))
        self.threshold_entry.pack(pady=5)
        btn = tk.Button(frame, text="Save Settings", command=self.save_settings)
        btn.pack(pady=5)
    
    def save_settings(self):
        try:
            self.anomaly_threshold = float(self.threshold_entry.get())
            messagebox.showinfo("Settings", f"Anomaly threshold set to {self.anomaly_threshold}")
        except Exception as ex:
            messagebox.showerror("Settings Error", str(ex))
    
    def create_reports_tab(self, frame):
        btn = tk.Button(frame, text="Generate PDF Report", command=self.generate_pdf_report)
        btn.pack(pady=20)
    
    def create_database_tab(self, frame):
        btn = tk.Button(frame, text="Store Summary in Database", command=self.store_summary_to_db)
        btn.pack(pady=20)
    
    def store_summary_to_db(self):
        if self.latest_summary is not None:
            store_to_database(self.latest_summary)
        else:
            messagebox.showwarning("Database", "No summary data available. Please process a file first.")
    
    def create_mapping_tab(self, frame):
        btn = tk.Button(frame, text="Show Map", command=self.run_mapping)
        btn.pack(pady=20)

    def create_graph_tab(self, frame):
        btn1 = tk.Button(frame, text="Overlay LAeq/LAmax/LA90", command=self.plot_overlaid_levels)
        btn1.pack(pady=5)
        btn2 = tk.Button(frame, text="Distribution Histograms", command=self.plot_histograms)
        btn2.pack(pady=5)
        btn3 = tk.Button(frame, text="Long-term Trend", command=self.plot_long_term_trend)
        btn3.pack(pady=5)
        btn4 = tk.Button(frame, text="Event Detection", command=self.detect_events)
        btn4.pack(pady=5)
        btn5 = tk.Button(frame, text="Octave Band Analysis", command=self.plot_octave_band)
        btn5.pack(pady=5)
        btn6 = tk.Button(frame, text="Time Series (Full Data)", command=self.plot_time_series)
        btn6.pack(pady=5)
    
    def run_mapping(self):
        """
        Uses the processed data (self.latest_summary) to generate a map.
        If 'Latitude' and 'Longitude' columns do not exist, prompts user to input them for all rows.
        """
        if self.latest_summary is None or self.latest_summary.empty:
            messagebox.showwarning("Mapping", "No processed data available. Please process a file first.")
            return
        has_lat = "Latitude" in self.latest_summary.columns
        has_lon = "Longitude" in self.latest_summary.columns
        if not (has_lat and has_lon):
            answer = messagebox.askyesno("Location Data Missing",
                                         "Location data (Latitude/Longitude) not found. Would you like to enter a single lat/lon for all rows?")
            if answer:
                lat = simpledialog.askfloat("Enter Latitude", "Latitude (e.g., 53.3736):", minvalue=-90, maxvalue=90)
                lon = simpledialog.askfloat("Enter Longitude", "Longitude (e.g., -1.4625):", minvalue=-180, maxvalue=180)
                if lat is not None and lon is not None:
                    self.latest_summary["Latitude"] = lat
                    self.latest_summary["Longitude"] = lon
                else:
                    messagebox.showwarning("Mapping", "Latitude/Longitude entry was cancelled.")
                    return
            else:
                return
        latitudes = self.latest_summary["Latitude"].dropna().tolist()
        longitudes = self.latest_summary["Longitude"].dropna().tolist()
        labels = []
        if "Date" in self.latest_summary.columns:
            labels = [row["Date"].strftime("%d/%m/%Y") if hasattr(row["Date"], 'strftime') else str(row["Date"])
                      for _, row in self.latest_summary.iterrows()]
        if not latitudes or not longitudes:
            messagebox.showwarning("Mapping", "No valid lat/lon data to plot after user entry.")
            return
        values = None
        if "LAeq Day" in self.latest_summary.columns:
            values = self.latest_summary["LAeq Day"].tolist()
        show_map_with_folium(latitudes, longitudes, labels, values)

    def plot_overlaid_levels(self):
        if self.latest_summary is None or self.latest_summary.empty:
            messagebox.showwarning("Graph", "Please process a file first.")
            return
        df = self.latest_summary
        plt.figure(figsize=(10, 6))
        plt.plot(df['Date'], df['LAeq Day'], marker='o', label='LAeq Day')
        if 'LAmax Day' in df.columns:
            plt.plot(df['Date'], df['LAmax Day'], marker='o', label='LAmax Day')
        if 'LA90 Day' in df.columns:
            plt.plot(df['Date'], df['LA90 Day'], marker='o', label='LA90 Day')
        plt.xlabel('Date')
        plt.ylabel('Sound Level (dB)')
        plt.legend()
        plt.title('Daily Noise Levels')
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    def plot_histograms(self):
        if self.latest_summary is None or self.latest_summary.empty:
            messagebox.showwarning("Graph", "Please process a file first.")
            return
        df = self.latest_summary
        cols = [c for c in ['LAeq Day', 'LAmax Day', 'LA90 Day'] if c in df.columns]
        if not cols:
            messagebox.showwarning("Graph", "No suitable columns for histogram.")
            return
        df[cols].hist(bins=20, figsize=(8, 6))
        plt.suptitle('Distribution of Noise Levels (Day)')
        plt.tight_layout()
        plt.show()

    def plot_long_term_trend(self):
        if self.latest_summary is None or self.latest_summary.empty:
            messagebox.showwarning("Graph", "Please process a file first.")
            return
        if 'Date' not in self.latest_summary.columns or 'LAeq Day' not in self.latest_summary.columns:
            messagebox.showwarning("Graph", "Required columns missing.")
            return
        df = self.latest_summary.sort_values('Date')
        df['MA7'] = df['LAeq Day'].rolling(window=7, min_periods=1).mean()
        plt.figure(figsize=(10, 6))
        plt.plot(df['Date'], df['LAeq Day'], label='LAeq Day')
        plt.plot(df['Date'], df['MA7'], label='7-day Moving Avg', linestyle='--')
        plt.xlabel('Date')
        plt.ylabel('LAeq Day (dB)')
        plt.legend()
        plt.title('Long-term Trend')
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    def detect_events(self):
        if self.latest_summary is None or self.latest_summary.empty:
            messagebox.showwarning("Events", "Please process a file first.")
            return
        if 'LAmax Day' not in self.latest_summary.columns:
            messagebox.showwarning("Events", "LAmax Day column missing.")
            return
        threshold = simpledialog.askfloat("Threshold", "Enter LAmax threshold:", minvalue=0)
        if threshold is None:
            return
        exceed = self.latest_summary[self.latest_summary['LAmax Day'] > threshold]
        if exceed.empty:
            messagebox.showinfo("Events", "No exceedances detected.")
        else:
            dates = ', '.join(exceed['Date'].astype(str))
            messagebox.showinfo("Events", f"Exceedances on: {dates}")

    def plot_octave_band(self):
        if self.latest_summary is None or self.latest_summary.empty:
            messagebox.showwarning("Spectrum", "Please process a file first.")
            return
        freq_cols = [c for c in self.latest_summary.columns if c.endswith('Hz')]
        if not freq_cols:
            messagebox.showwarning("Spectrum", "No octave-band data found.")
            return
        spectrum = self.latest_summary[freq_cols].mean()
        plt.figure(figsize=(8, 6))
        spectrum.plot(kind='bar')
        plt.xlabel('Frequency Band (Hz)')
        plt.ylabel('Level (dB)')
        plt.title('Average Octave Band Spectrum')
        plt.tight_layout()
        plt.show()

    def plot_time_series(self):
        if self.raw_data is None or self.raw_data.empty:
            messagebox.showwarning("Graph", "Please process a file first.")
            return
        df = self.raw_data.dropna(subset=['DateTime']).sort_values('DateTime')
        if df.empty:
            messagebox.showwarning("Graph", "No DateTime information available.")
            return
        plt.figure(figsize=(10, 6))
        if 'LAeq' in df.columns:
            plt.plot(df['DateTime'], df['LAeq'], label='LAeq')
        if 'LAmax' in df.columns:
            plt.plot(df['DateTime'], df['LAmax'], label='LAmax')
        if 'LA90' in df.columns:
            plt.plot(df['DateTime'], df['LA90'], label='LA90')
        plt.xlabel('Date and Time')
        plt.ylabel('Sound Level (dB)')
        plt.legend()
        plt.title('Noise Levels Over Time')
        plt.grid(True)
        plt.tight_layout()
        plt.show()
    
    def browse_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Excel files", "*.xlsx;*.xls"), ("All files", "*.*")],
            title="Select an Excel file"
        )
        if file_path:
            self.input_file = file_path
            self.process_output_label.config(text=f"Selected file: {file_path}")
        else:
            self.process_output_label.config(text="No file selected")
    
    def process_data(self):
        """
        Processes the data and saves an Excel file.
        Also sets self.latest_summary (DataFrame) and self.latest_overall (dict)
        so that generate_pdf_report() can produce a PDF with the same data.
        This version calculates LAeq, LAmax, LA90, and LAmin for both Day and Night,
        the 10th Highest Lmax and 10th Lowest L90, additional percentile levels,
        day–evening–night (Lden) and day–night (Ldn) metrics, and the standard deviation of LAeq.
        """
        try:
            logging.info("Processing file: %s", self.input_file)
            df = pd.read_excel(self.input_file)
            
            # Step 1: Parse columns
            df['ParsedDate'] = df['Date'].apply(parse_date)
            df['Time_str'] = df['Time'].apply(lambda t: t.strftime("%H:%M:%S") if pd.notnull(t) else "")
            df['DateTime'] = pd.to_datetime(df['ParsedDate'].dt.strftime("%Y-%m-%d") + " " + df['Time_str'],
                                            format="%Y-%m-%d %H:%M:%S", errors='coerce')
            
            def classify_period(dt):
                if pd.isnull(dt):
                    return ""
                t = dt.time()
                return "Night-time" if t >= time(23, 0, 0) or t < time(7, 0, 0) else "Daytime"
            
            df['Period'] = df['DateTime'].apply(classify_period)
            df['Integrated_LAeq'] = df['LAeq'].apply(lambda x: 10 ** (x / 10) if pd.notnull(x) else np.nan)
            df['DateOnly'] = df['DateTime'].apply(get_date_only)
            
            logging.info("Data parsed successfully.")
            print("\nSample of parsed DateTime and computed DateOnly:")
            print(df[['Date', 'Time', 'ParsedDate', 'DateTime', 'DateOnly', 'Period']].head(10))
            
            # Step 2: Compute daily summary (LAeq, LAmax, LA90, LAmin for Day and Night)
            unique_dates = sorted(df['DateOnly'].dropna().unique())
            daily_data = []
            for d in unique_dates:
                day_rows = df[(df['Period'] == "Daytime") & (df['DateOnly'] == d)]
                night_rows = df[(df['Period'] == "Night-time") & (df['DateOnly'] == d)]
                
                LAeq_day = (10 * np.log10(day_rows['Integrated_LAeq'].mean())
                            if not day_rows.empty and not day_rows['Integrated_LAeq'].dropna().empty
                            else "No Data")
                LAeq_night = (10 * np.log10(night_rows['Integrated_LAeq'].mean())
                              if not night_rows.empty and not night_rows['Integrated_LAeq'].dropna().empty
                              else "No Data")
                
                LAmax_day = (np.percentile(day_rows['LAmax'].dropna(), 95)
                             if not day_rows.empty and not day_rows['LAmax'].dropna().empty
                             else "No Data")
                LAmax_night = (np.percentile(night_rows['LAmax'].dropna(), 95)
                               if not night_rows.empty and not night_rows['LAmax'].dropna().empty
                               else "No Data")
                
                LA90_day = (day_rows['LA90'].mode().iloc[0] if not day_rows.empty and not day_rows['LA90'].dropna().empty
                            else "No Data")
                LA90_night = (night_rows['LA90'].mode().iloc[0] if not night_rows.empty and not night_rows['LA90'].dropna().empty
                              else "No Data")
                
                LAmin_day = (np.percentile(day_rows['LAmin'].dropna(), 5)
                             if not day_rows.empty and not day_rows['LAmin'].dropna().empty
                             else "No Data")
                LAmin_night = (np.percentile(night_rows['LAmin'].dropna(), 5)
                               if not night_rows.empty and not night_rows['LAmin'].dropna().empty
                               else "No Data")
                
                daily_data.append({
                    "Date": d,
                    "LAeq Day": LAeq_day,
                    "LAeq Night": LAeq_night,
                    "LAmax Day": LAmax_day,
                    "LAmax Night": LAmax_night,
                    "LA90 Day": LA90_day,
                    "LA90 Night": LA90_night,
                    "LAmin Day": LAmin_day,
                    "LAmin Night": LAmin_night
                })
            daily_summary_df = pd.DataFrame(daily_data)
            
            # Step 3: Compute overall values
            overall_LAeq_day = (10 * np.log10(df.loc[df['Period'] == "Daytime", "Integrated_LAeq"].mean())
                                if not df.loc[df['Period'] == "Daytime", "Integrated_LAeq"].dropna().empty else "No Data")
            overall_LAeq_night = (10 * np.log10(df.loc[df['Period'] == "Night-time", "Integrated_LAeq"].mean())
                                  if not df.loc[df['Period'] == "Night-time", "Integrated_LAeq"].dropna().empty else "No Data")
            overall_LAmax_day = (np.percentile(df.loc[df['Period'] == "Daytime", "LAmax"].dropna(), 95)
                                 if not df.loc[df['Period'] == "Daytime", "LAmax"].dropna().empty else "No Data")
            overall_LAmax_night = (np.percentile(df.loc[df['Period'] == "Night-time", "LAmax"].dropna(), 95)
                                   if not df.loc[df['Period'] == "Night-time", "LAmax"].dropna().empty else "No Data")
            overall_LA90_day = (df.loc[df['Period'] == "Daytime", "LA90"].mode().iloc[0]
                                if not df.loc[df['Period'] == "Daytime", "LA90"].dropna().empty else "No Data")
            overall_LA90_night = (df.loc[df['Period'] == "Night-time", "LA90"].mode().iloc[0]
                                  if not df.loc[df['Period'] == "Night-time", "LA90"].dropna().empty else "No Data")
            overall_LAmin_day = (np.percentile(df.loc[df['Period'] == "Daytime", "LAmin"].dropna(), 5)
                                 if not df.loc[df['Period'] == "Daytime", "LAmin"].dropna().empty else "No Data")
            overall_LAmin_night = (np.percentile(df.loc[df['Period'] == "Night-time", "LAmin"].dropna(), 5)
                                   if not df.loc[df['Period'] == "Night-time", "LAmin"].dropna().empty else "No Data")
            
            overall_values = {
                "Overall LAeq Day": overall_LAeq_day,
                "Overall LAeq Night": overall_LAeq_night,
                "Overall LAmax Day": overall_LAmax_day,
                "Overall LAmax Night": overall_LAmax_night,
                "Overall LA90 Day": overall_LA90_day,
                "Overall LA90 Night": overall_LA90_night,
                "Overall LAmin Day": overall_LAmin_day,
                "Overall LAmin Night": overall_LAmin_night
            }
            
            # -- Added Nth Highest/Lowest for Lmax & L90 --
            day_lmax_10_highest = nth_highest(df.loc[df['Period'] == "Daytime", "LAmax"], 10)
            night_lmax_10_highest = nth_highest(df.loc[df['Period'] == "Night-time", "LAmax"], 10)
            day_l90_10_lowest = nth_lowest(df.loc[df['Period'] == "Daytime", "LA90"], 10)
            night_l90_10_lowest = nth_lowest(df.loc[df['Period'] == "Night-time", "LA90"], 10)
            
            overall_values["10th Highest Lmax Day"] = day_lmax_10_highest if day_lmax_10_highest is not None else "No Data"
            overall_values["10th Highest Lmax Night"] = night_lmax_10_highest if night_lmax_10_highest is not None else "No Data"
            overall_values["10th Lowest L90 Day"] = day_l90_10_lowest if day_l90_10_lowest is not None else "No Data"
            overall_values["10th Lowest L90 Night"] = night_l90_10_lowest if night_l90_10_lowest is not None else "No Data"
            # -------------------------------------------
            
            # -- Additional Percentile Levels from LAeq --
            day_LAeq = df.loc[df['Period'] == "Daytime", "LAeq"].dropna()
            night_LAeq = df.loc[df['Period'] == "Night-time", "LAeq"].dropna()
            
            overall_L10_day = np.percentile(day_LAeq, 90) if not day_LAeq.empty else "No Data"
            overall_L50_day = np.percentile(day_LAeq, 50) if not day_LAeq.empty else "No Data"
            overall_L95_day = np.percentile(day_LAeq, 5) if not day_LAeq.empty else "No Data"
            
            overall_L10_night = np.percentile(night_LAeq, 90) if not night_LAeq.empty else "No Data"
            overall_L50_night = np.percentile(night_LAeq, 50) if not night_LAeq.empty else "No Data"
            overall_L95_night = np.percentile(night_LAeq, 5) if not night_LAeq.empty else "No Data"
            
            overall_values["Overall L10 Day"] = overall_L10_day
            overall_values["Overall L50 Day"] = overall_L50_day
            overall_values["Overall L95 Day"] = overall_L95_day
            overall_values["Overall L10 Night"] = overall_L10_night
            overall_values["Overall L50 Night"] = overall_L50_night
            overall_values["Overall L95 Night"] = overall_L95_night
            # -------------------------------------------
            
            # -- Day–Evening–Night (Lden) Calculation --
            # Define new period classification for Lden:
            def classify_period_lden(dt):
                if pd.isnull(dt):
                    return ""
                t = dt.time()
                if t >= time(7, 0, 0) and t < time(19, 0, 0):
                    return "Day"
                elif t >= time(19, 0, 0) and t < time(23, 0, 0):
                    return "Evening"
                else:
                    return "Night"
            
            df['Period_lden'] = df['DateTime'].apply(classify_period_lden)
            day_lden = df.loc[df['Period_lden'] == "Day", "LAeq"].dropna()
            evening_lden = df.loc[df['Period_lden'] == "Evening", "LAeq"].dropna()
            night_lden = df.loc[df['Period_lden'] == "Night", "LAeq"].dropna()
            
            if not day_lden.empty:
                LAeq_day_lden = 10 * np.log10(day_lden.apply(lambda x: 10**(x/10)).mean())
            else:
                LAeq_day_lden = None
            if not evening_lden.empty:
                LAeq_evening_lden = 10 * np.log10(evening_lden.apply(lambda x: 10**(x/10)).mean())
            else:
                LAeq_evening_lden = None
            if not night_lden.empty:
                LAeq_night_lden = 10 * np.log10(night_lden.apply(lambda x: 10**(x/10)).mean())
            else:
                LAeq_night_lden = None
            
            if LAeq_day_lden is not None and LAeq_evening_lden is not None and LAeq_night_lden is not None:
                Lden = 10 * np.log10((12/24)*10**(LAeq_day_lden/10) + (4/24)*10**((LAeq_evening_lden+5)/10) + (8/24)*10**((LAeq_night_lden+10)/10))
            else:
                Lden = "No Data"
            overall_values["Lden (Day-Evening-Night)"] = Lden
            # -------------------------------------------
            
            # -- Day–Night (Ldn) Calculation --
            day_dn = df.loc[df['Period'] == "Daytime", "LAeq"].dropna()
            night_dn = df.loc[df['Period'] == "Night-time", "LAeq"].dropna()
            if not day_dn.empty:
                LAeq_day_dn = 10 * np.log10(day_dn.apply(lambda x: 10**(x/10)).mean())
            else:
                LAeq_day_dn = None
            if not night_dn.empty:
                LAeq_night_dn = 10 * np.log10(night_dn.apply(lambda x: 10**(x/10)).mean())
            else:
                LAeq_night_dn = None
            if LAeq_day_dn is not None and LAeq_night_dn is not None:
                Ldn = 10 * np.log10((16/24)*10**(LAeq_day_dn/10) + (8/24)*10**((LAeq_night_dn+10)/10))
            else:
                Ldn = "No Data"
            overall_values["Ldn (Day-Night)"] = Ldn
            # -------------------------------------------
            
            # -- Statistical Spread (Standard Deviation) of LAeq --
            overall_LAeq_std_day = np.std(day_LAeq) if not day_LAeq.empty else "No Data"
            overall_LAeq_std_night = np.std(night_LAeq) if not night_LAeq.empty else "No Data"
            overall_values["Overall LAeq Std Day"] = overall_LAeq_std_day
            overall_values["Overall LAeq Std Night"] = overall_LAeq_std_night
            # -------------------------------------------
            
            self.latest_overall = overall_values
            self.latest_summary = daily_summary_df
            self.raw_data = df
            
            # Step 4: Export custom Excel output
            output_file = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                                       filetypes=[("Excel files", "*.xlsx;*.xls")],
                                                       title="Save Custom Output as")
            if output_file:
                with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
                    daily_summary_df.to_excel(writer, sheet_name="Daily Summary", index=False)
                    ov_df = pd.DataFrame(list(overall_values.items()), columns=["Metric", "Value"])
                    ov_df.to_excel(writer, sheet_name="Overall Metrics", index=False)
                    df.to_excel(writer, sheet_name="Full Data", index=False)
                    freq_cols = [c for c in df.columns if c.endswith('Hz')]
                    if freq_cols:
                        df[freq_cols].to_excel(writer, sheet_name="Octave Bands", index=False)
                messagebox.showinfo("Success", "Data processed successfully! Excel file created. You can now generate a PDF report.")
            else:
                messagebox.showinfo("Success", "Data processed successfully (Excel save was skipped). You can now generate a PDF report.")
            
        except Exception as e:
            logging.error("Processing error: %s", str(e))
            messagebox.showerror("Processing Error", str(e))
    
    def generate_pdf_report(self):
        """
        Generates a PDF report with overall metrics and daily summary.
        Numeric values are displayed rounded to 1 decimal place.
        """
        if self.latest_summary is None or self.latest_summary.empty:
            messagebox.showwarning("Report", "No summary data available. Please process a file first.")
            return
        pdf_file = filedialog.asksaveasfilename(defaultextension=".pdf",
                                                filetypes=[("PDF files", "*.pdf")],
                                                title="Save PDF Report As")
        if not pdf_file:
            return
        try:
            # Round overall metrics
            rounded_overall = {k: round_if_number(v, 1) for k, v in self.latest_overall.items()}
            
            # Round daily summary DataFrame
            df_rounded = self.latest_summary.copy()
            for col in df_rounded.columns:
                df_rounded[col] = df_rounded[col].apply(lambda x: round_if_number(x, 1))
            
            doc = SimpleDocTemplate(pdf_file, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Title
            title_para = Paragraph("Acoustic Data Report", styles['Title'])
            story.append(title_para)
            story.append(Spacer(1, 12))
            
            # Overall Metrics
            overall_text = "<b>Overall Metrics (rounded to 1 decimal):</b><br/>"
            for key, value in rounded_overall.items():
                overall_text += f"{key}: {value}<br/>"
            overall_para = Paragraph(overall_text, styles['Normal'])
            story.append(overall_para)
            story.append(Spacer(1, 12))
            
            # Daily Summary Table
            story.append(Paragraph("<b>Daily Summary (rounded to 1 decimal):</b>", styles['Heading2']))
            story.append(Spacer(1, 12))
            
            headers = list(df_rounded.columns)
            table_data = [headers]
            for idx, row in df_rounded.iterrows():
                row_data = []
                for col in headers:
                    cell = row[col]
                    if hasattr(cell, 'strftime'):
                        cell = cell.strftime("%d/%m/%Y")
                    row_data.append(str(cell))
                table_data.append(row_data)
            
            summary_table = Table(table_data, repeatRows=1)
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
            ]))
            story.append(summary_table)
            
            doc.build(story)
            messagebox.showinfo("Report", f"PDF Report generated successfully:\n{pdf_file}")
        except Exception as ex:
            logging.error("Report Error: %s", str(ex))
            messagebox.showerror("Report Error", str(ex))
    
    def batch_process(self):
        # Stub or your existing batch logic
        pass

if __name__ == '__main__':
    app = DataProcessorApp()
    app.mainloop()
