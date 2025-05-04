import sqlite3
from datetime import datetime, timedelta

import tkinter as tk
from tkinter import messagebox, ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates

from tkcalendar import DateEntry

DB_NAME = "streaks.db"

class StreakTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Streak Tracker")
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Define a prominent button style with a pleasing teal color
        self.style.configure('Prominent.TButton',
                             font=('Arial', 11, 'bold'),
                             foreground='white',
                             background='#008080')
        self.style.map('Prominent.TButton',
                       foreground=[('active', 'white')],
                       background=[('active', '#005050')])

        self.conn = sqlite3.connect(DB_NAME)
        self.create_table()

        self.selected_module_index = None  # Track selected module index

        self.create_widgets()
        self.load_modules()
        self.load_data()
        self.plot_streak()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        # Check if streaks table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='streaks'")
        if cursor.fetchone() is None:
            self._create_streaks_table(cursor)
            self.conn.commit()
        else:
            cursor.execute("PRAGMA table_info(streaks)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'module_id' not in columns:
                self._migrate_streaks_table(cursor)
                self.conn.commit()

    def _create_streaks_table(self, cursor):
        cursor.execute('''
            CREATE TABLE streaks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                module_id INTEGER NOT NULL,
                UNIQUE(date, module_id),
                FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE
            )
        ''')

    def _migrate_streaks_table(self, cursor):
        cursor.execute("ALTER TABLE streaks RENAME TO streaks_old")
        self._create_streaks_table(cursor)
        cursor.execute("SELECT id FROM modules WHERE id=1")
        if cursor.fetchone() is None:
            cursor.execute("INSERT INTO modules (id, name) VALUES (1, 'default')")
        cursor.execute("INSERT INTO streaks (id, date, module_id) SELECT id, date, 1 FROM streaks_old")
        cursor.execute("DROP TABLE streaks_old")

    def create_widgets(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left frame for the graph
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Right frame for controls
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)

        self._create_module_management(right_frame)
        self._create_single_date_entry(right_frame)
        self._create_range_date_entry(right_frame)
        self._create_streak_info_labels(right_frame)
        self._create_dates_listbox(right_frame)
        self._create_delete_range_entry(right_frame)
        self._create_plot_area(left_frame)

    def _create_module_management(self, parent):
        module_frame = ttk.Frame(parent)
        module_frame.pack(pady=5, fill=tk.X)
        ttk.Label(module_frame, text="Modules:").grid(row=0, column=0, padx=5)
        self.module_listbox = tk.Listbox(module_frame, height=4)
        self.module_listbox.grid(row=1, column=0, padx=5, sticky="ew")
        self.module_listbox.bind("<<ListboxSelect>>", self.on_module_select)

        module_button_frame = ttk.Frame(module_frame)
        module_button_frame.grid(row=1, column=1, padx=5, sticky="ns")
        add_module_button = ttk.Button(module_button_frame, text="+", width=3, command=self.add_module, style='Prominent.TButton')
        add_module_button.pack(pady=2)
        delete_module_button = ttk.Button(module_button_frame, text="-", width=3, command=self.delete_module, style='Prominent.TButton')
        delete_module_button.pack(pady=2)
        rename_module_button = ttk.Button(module_button_frame, text="R", width=3, command=self.rename_module, style='Prominent.TButton')
        rename_module_button.pack(pady=2)

    def _create_single_date_entry(self, parent):
        single_date_frame = ttk.Frame(parent)
        single_date_frame.pack(pady=5, fill=tk.X)
        ttk.Label(single_date_frame, text="Streak Date (YYYY-MM-DD):").grid(row=0, column=0, padx=5)
        self.date_entry = DateEntry(single_date_frame, date_pattern='yyyy-MM-dd')
        self.date_entry.grid(row=0, column=1, padx=5)

        add_button = ttk.Button(single_date_frame, text="Add Date", command=self.add_date, style='Prominent.TButton')
        add_button.grid(row=0, column=2, padx=5)

        delete_date_button = ttk.Button(single_date_frame, text="Delete Date", command=self.delete_date, style='Prominent.TButton')
        delete_date_button.grid(row=0, column=3, padx=5)

    def _create_range_date_entry(self, parent):
        range_date_frame = ttk.Frame(parent)
        range_date_frame.pack(pady=5, fill=tk.X)
        ttk.Label(range_date_frame, text="Add Date Range:").grid(row=0, column=0, padx=5)
        self.start_date_entry = DateEntry(range_date_frame, date_pattern='yyyy-MM-dd')
        self.start_date_entry.grid(row=0, column=1, padx=5)
        self.end_date_entry = DateEntry(range_date_frame, date_pattern='yyyy-MM-dd')
        self.end_date_entry.grid(row=0, column=2, padx=5)

        add_range_button = ttk.Button(range_date_frame, text="Add Date Range", command=self.add_date_range, style='Prominent.TButton')
        add_range_button.grid(row=0, column=3, padx=5)

    def _create_streak_info_labels(self, parent):
        self.breaks_label = ttk.Label(parent, text="Streak breaks: 0", font=("Arial", 12))
        self.breaks_label.pack(pady=5)
        self.highest_streak_label = ttk.Label(parent, text="Highest streak: 0", font=("Arial", 12))
        self.highest_streak_label.pack(pady=5)

    def _create_dates_listbox(self, parent):
        list_frame = ttk.Frame(parent)
        list_frame.pack(pady=10, fill=tk.BOTH, expand=False)

        self.dates_listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, height=6)
        self.dates_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def ignore_event(event):
            return "break"
        self.dates_listbox.bind("<Button-1>", ignore_event)
        self.dates_listbox.bind("<B1-Motion>", ignore_event)
        self.dates_listbox.bind("<Key>", ignore_event)

        self.module_listbox.bind("<FocusOut>", self.on_module_listbox_focus_out)
        self.module_listbox.bind("<FocusIn>", self.on_module_listbox_focus_in)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        scrollbar.config(command=self.dates_listbox.yview)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.dates_listbox.config(yscrollcommand=scrollbar.set)

    def _create_delete_range_entry(self, parent):
        delete_range_frame = ttk.Frame(parent)
        delete_range_frame.pack(pady=10, fill=tk.X)

        ttk.Label(delete_range_frame, text="Delete Date Range:").grid(row=0, column=0, padx=5)
        self.delete_start_date_entry = DateEntry(delete_range_frame, date_pattern='yyyy-MM-dd')
        self.delete_start_date_entry.grid(row=0, column=1, padx=5)
        self.delete_end_date_entry = DateEntry(delete_range_frame, date_pattern='yyyy-MM-dd')
        self.delete_end_date_entry.grid(row=0, column=2, padx=5)

        delete_range_button = ttk.Button(delete_range_frame, text="Delete Date Range", command=self.delete_date_range, style='Prominent.TButton')
        delete_range_button.grid(row=0, column=3, padx=5)

    def _create_plot_area(self, parent):
        plt.style.use('ggplot')
        self.figure = plt.Figure(figsize=(6,4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Streak Over Time", color="#2E4053", fontsize=14, fontweight='bold')
        self.ax.set_xlabel("Date", color="#34495E", fontsize=12)
        self.ax.set_ylabel("Streak Length (days)", color="#34495E", fontsize=12)
        self.ax.spines['bottom'].set_color('#34495E')
        self.ax.spines['left'].set_color('#34495E')
        self.ax.tick_params(axis='x', colors='#34495E')
        self.ax.tick_params(axis='y', colors='#34495E')
        self.ax.grid(True, linestyle='--', alpha=0.5, color='#D5D8DC')

        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def add_date(self):
        date_str = self.date_entry.get()
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Invalid Date", "Please enter a valid date in YYYY-MM-DD format.")
            return

        module_id = self.get_selected_module_id()
        if module_id is None:
            messagebox.showwarning("No Module Selected", "Please select a module to add the date.")
            return

        cursor = self.conn.cursor()
        try:
            cursor.execute("INSERT INTO streaks (date, module_id) VALUES (?, ?)", (date_str, module_id))
            self.conn.commit()
            self.load_data()
            self.plot_streak()
        except sqlite3.IntegrityError:
            messagebox.showwarning("Duplicate Date", "This date is already recorded for the selected module.")
        except Exception as e:
            messagebox.showerror("Database Error", f"An error occurred: {e}")

    def load_data(self):
        module_id = self.get_selected_module_id()
        if module_id is None:
            self.dates = []
        else:
            cursor = self.conn.cursor()
            cursor.execute("SELECT date FROM streaks WHERE module_id = ? ORDER BY date", (module_id,))
            rows = cursor.fetchall()
            self.dates = [datetime.strptime(row[0], "%Y-%m-%d").date() for row in rows]

        # Update the listbox with dates
        self.dates_listbox.delete(0, tk.END)
        for date in self.dates:
            self.dates_listbox.insert(tk.END, date.strftime("%Y-%m-%d"))

    def add_date_range(self):
        start_date_str = self.start_date_entry.get()
        end_date_str = self.end_date_entry.get()
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Invalid Date", "Please enter valid dates in YYYY-MM-DD format.")
            return

        if end_date < start_date:
            messagebox.showerror("Invalid Range", "End date must be after or equal to start date.")
            return

        module_id = self.get_selected_module_id()
        if module_id is None:
            messagebox.showwarning("No Module Selected", "Please select a module to add the date range.")
            return

        cursor = self.conn.cursor()
        current_date = start_date
        added_count = 0
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            try:
                cursor.execute("INSERT INTO streaks (date, module_id) VALUES (?, ?)", (date_str, module_id))
                added_count += 1
            except sqlite3.IntegrityError:
                # Ignore duplicates
                pass
            except Exception as e:
                messagebox.showerror("Database Error", f"An error occurred: {e}")
                break
            current_date += timedelta(days=1)
        self.conn.commit()

        self.load_data()
        self.plot_streak()

        messagebox.showinfo("Date Range Added", f"Added {added_count} new date(s) to the streaks.")

    def delete_date_range(self):
        start_date_str = self.delete_start_date_entry.get()
        end_date_str = self.delete_end_date_entry.get()
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Invalid Date", "Please enter valid dates in YYYY-MM-DD format.")
            return

        if end_date < start_date:
            messagebox.showerror("Invalid Range", "End date must be after or equal to start date.")
            return

        module_id = self.get_selected_module_id()
        if module_id is None:
            messagebox.showwarning("No Module Selected", "Please select a module to delete dates from.")
            return

        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM streaks WHERE date BETWEEN ? AND ? AND module_id = ?", (start_date_str, end_date_str, module_id))
        self.conn.commit()

        self.load_data()
        self.plot_streak()

        messagebox.showinfo("Date Range Deleted", f"Deleted dates from {start_date_str} to {end_date_str}.")

    def plot_streak(self):
        self.ax.clear()
        self.ax.set_title("Streak Over Time", color="#2E4053", fontsize=14, fontweight='bold')
        self.ax.set_xlabel("Date", color="#34495E", fontsize=12)
        self.ax.set_ylabel("Streak Length (days)", color="#34495E", fontsize=12)
        self.ax.spines['bottom'].set_color('#34495E')
        self.ax.spines['left'].set_color('#34495E')
        self.ax.tick_params(axis='x', colors='#34495E')
        self.ax.tick_params(axis='y', colors='#34495E')
        self.ax.grid(True, linestyle='--', alpha=0.5, color='#D5D8DC')

        if not self.dates:
            self.breaks_label.config(text="Streak breaks: 0")
            self.highest_streak_label.config(text="Highest streak: 0")
            self.canvas.draw()
            return

        streak_lengths = []
        max_streak = 0
        current_streak = 0
        previous_date = None
        breaks_dates = []

        for date in self.dates:
            if previous_date and (date - previous_date).days == 1:
                current_streak += 1
            else:
                if previous_date is not None:
                    breaks_dates.append(date)
                current_streak = 1
            streak_lengths.append(current_streak)
            if current_streak > max_streak:
                max_streak = current_streak
            previous_date = date

        # Update the breaks label with the count of streak breaks
        self.breaks_label.config(text=f"Streak breaks: {len(breaks_dates)}")
        # Update the highest streak label with the max streak value
        self.highest_streak_label.config(text=f"Highest streak: {max_streak}")

        line, = self.ax.plot(self.dates, streak_lengths, marker='o', linestyle='-', color='#2980B9', markerfacecolor='#85C1E9', markeredgecolor='#1B4F72', linewidth=2)
        self.ax.set_ylim(0, max_streak + 1)

        # Highlight the highest streak points with a different marker and color
        max_streak_value = max(streak_lengths)
        max_streak_indices = [i for i, val in enumerate(streak_lengths) if val == max_streak_value]
        max_streak_dates = [self.dates[i] for i in max_streak_indices]
        max_streak_points = [streak_lengths[i] for i in max_streak_indices]

        self.ax.scatter(max_streak_dates, max_streak_points, color='#E74C3C', s=100, label='Highest Streak', zorder=5, edgecolors='black')

        # Highlight the streak breaks with a different marker and color
        if breaks_dates:
            self.ax.scatter(breaks_dates, [0]*len(breaks_dates), color='#F39C12', s=100, label='Streak Break', zorder=5, edgecolors='black', marker='X')

        # Format x-axis with date locator and formatter for better readability
        self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        self.figure.autofmt_xdate()

        self.ax.legend()

        # Create annotation for hover
        annot = self.ax.annotate("", xy=(0,0), xytext=(15,15), textcoords="offset points",
                                 bbox=dict(boxstyle="round", fc="w"),
                                 arrowprops=dict(arrowstyle="->"))
        annot.set_visible(False)

        def update_annot(ind):
            x, y = line.get_data()
            annot.xy = (x[ind["ind"][0]], y[ind["ind"][0]])
            date_str = self.dates[ind["ind"][0]].strftime('%Y-%m-%d')
            text = f"Date: {date_str}\nStreak: {y[ind['ind'][0]]}"
            annot.set_text(text)
            annot.get_bbox_patch().set_alpha(0.9)

        def hover(event):
            vis = annot.get_visible()
            if event.inaxes == self.ax:
                cont, ind = line.contains(event)
                if cont:
                    update_annot(ind)
                    annot.set_visible(True)
                    self.canvas.draw_idle()
                else:
                    if vis:
                        annot.set_visible(False)
                        self.canvas.draw_idle()

        self.figure.canvas.mpl_connect("motion_notify_event", hover)

        self.canvas.draw()

    def on_module_select(self, event):
        selected_indices = self.module_listbox.curselection()
        if selected_indices:
            self.selected_module_index = selected_indices[0]
        else:
            self.selected_module_index = None
        self.load_data()
        self.plot_streak()

    def on_dates_listbox_focus(self, event):
        pass  # Removed to avoid interference

    def on_dates_listbox_click(self, event):
        pass  # Removed to avoid interference

    def on_module_listbox_focus_out(self, event):
        # Save the current selection index on focus out
        selected_indices = self.module_listbox.curselection()
        if selected_indices:
            self.selected_module_index = selected_indices[0]

    def on_module_listbox_focus_in(self, event):
        # Restore the selection on focus in
        if self.selected_module_index is not None:
            self.module_listbox.selection_clear(0, tk.END)
            self.module_listbox.selection_set(self.selected_module_index)
            self.module_listbox.activate(self.selected_module_index)

    def get_selected_module_id(self):
        selected_indices = self.module_listbox.curselection()
        if not selected_indices:
            # fallback to self.selected_module_index if available
            if self.selected_module_index is not None:
                selected_module_name = self.module_listbox.get(self.selected_module_index)
            else:
                return None
        else:
            selected_module_name = self.module_listbox.get(selected_indices[0])
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM modules WHERE name = ?", (selected_module_name,))
        result = cursor.fetchone()
        if result:
            return result[0]
        return None

    def add_module(self):
        module_name = tk.simpledialog.askstring("Add Module", "Enter module name:")
        if module_name:
            cursor = self.conn.cursor()
            try:
                cursor.execute("INSERT INTO modules (name) VALUES (?)", (module_name,))
                self.conn.commit()
                self.load_modules()
            except sqlite3.IntegrityError:
                messagebox.showwarning("Duplicate Module", "This module already exists.")

    def delete_date(self):
        date_str = self.date_entry.get()
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Invalid Date", "Please enter a valid date in YYYY-MM-DD format.")
            return

        module_id = self.get_selected_module_id()
        if module_id is None:
            messagebox.showwarning("No Module Selected", "Please select a module to delete the date from.")
            return

        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM streaks WHERE date = ? AND module_id = ?", (date_str, module_id))
        if cursor.fetchone() is None:
            messagebox.showwarning("Date Not Found", "The specified date is not recorded for the selected module.")
            return

        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the date {date_str}?")
        if not confirm:
            return

        cursor.execute("DELETE FROM streaks WHERE date = ? AND module_id = ?", (date_str, module_id))
        self.conn.commit()

        self.load_data()
        self.plot_streak()

    def load_modules(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM modules ORDER BY name")
        modules = cursor.fetchall()
        self.module_listbox.delete(0, tk.END)
        for module in modules:
            self.module_listbox.insert(tk.END, module[0])
        if modules:
            self.module_listbox.selection_set(0)
            self.on_module_select(None)

    def delete_module(self):
        selected_indices = self.module_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select a module to delete.")
            return

        module_name = self.module_listbox.get(selected_indices[0])
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the module '{module_name}'?")
        if not confirm:
            return

        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM modules WHERE name = ?", (module_name,))
        self.conn.commit()
        self.load_modules()
        self.load_data()
        self.plot_streak()

    def rename_module(self):
        selected_indices = self.module_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select a module to rename.")
            return

        old_name = self.module_listbox.get(selected_indices[0])
        new_name = tk.simpledialog.askstring("Rename Module", f"Enter new name for module '{old_name}':")
        if not new_name:
            return

        cursor = self.conn.cursor()
        # Check if new name already exists
        cursor.execute("SELECT id FROM modules WHERE name = ?", (new_name,))
        if cursor.fetchone():
            messagebox.showwarning("Duplicate Module", "A module with this name already exists.")
            return

        try:
            cursor.execute("UPDATE modules SET name = ? WHERE name = ?", (new_name, old_name))
            self.conn.commit()
            self.load_modules()
            self.load_data()
            self.plot_streak()
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while renaming the module: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = StreakTrackerApp(root)
    root.mainloop()
