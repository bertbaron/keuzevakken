import os
import platform
import tkinter as tk
from threading import Thread
from tkinter import filedialog

from model import HandledException
from model_io import load, write_to_excel
from solver import Solver, SolverResult


class AppUI:

    def __init__(self):
        pass

    def run(self):
        root = self._create_app_root()
        self._create_main_window(root)
        root.mainloop()

    def _create_app_root(self):
        root = tk.Tk()
        root.title("Keuzevakken verdelen")

        window_width = 500
        window_height = 300
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        position_top = int(screen_height / 2 - window_height / 2)
        position_right = int(screen_width / 2 - window_width / 2)
        root.geometry(f'{window_width}x{window_height}+{position_right}+{position_top}')
        return root

    def _create_main_window(self, root):
        input_file_button = tk.Button(root, text="Invoer bestand", command=self._select_input_file)
        input_file_button.grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.input_file_label = tk.Label(root, text="<geen bestand geselecteerd>")
        self.input_file_label.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # tooltip_message = "Optioneel: selecteer een eerder resultaat om het aantal wijzigingen te minimaliseren"
        previous_file_button = tk.Button(root, text="Eerder resultaat", command=self._select_previous_file)
        previous_file_button.grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.previous_file_label = tk.Label(root, text="<geen bestand geselecteerd>")
        self.previous_file_label.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        output_file_label = tk.Label(root, text="Uitvoer bestandsnaam:")
        output_file_label.grid(row=2, column=0, padx=10, pady=10, sticky="e")
        self.output_file_entry = tk.Entry(root)
        self.output_file_entry.grid(row=2, column=1, padx=10, pady=10, sticky="w")
        self.output_file_entry.insert(0, "Resultaat.xlsx")

        # Create calculate button
        calculate_button = tk.Button(root, text="Bereken", command=self._calculate)
        calculate_button.grid(row=3, column=1, padx=10, pady=20)

    def _select_input_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        self.input_file_label.config(text=file_path)

    def _select_previous_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        self.previous_file_label.config(text=file_path)

    def _calculate(self):
        self.solver_exception = None
        self.result = None
        self.data = None
        input_path = self.input_file_label.cget('text')
        previous_path = self.previous_file_label.cget('text')
        if previous_path.startswith("<"):
            previous_path = None
        try:
            self.data = load(input_path, previous_path)
        except Exception as e:
            self._error_dialog(e)
            if not isinstance(e, HandledException):
                raise e
            return

        solver = Solver(self.data, self.data.previous_result is not None, False)

        self._start_spinner()

        self.calculation_thread = Thread(target=self._solve, args=(solver,))
        self.calculation_thread.start()
        self._check_thread()

    def _solve(self, solver):
        try:
            self.result = solver.solve()
        except Exception as e:
            self.solver_exception = e

    def _start_spinner(self):
        self.spinner_window = self._create_dialog("Rekenen", 200, 100)
        self.spinner_label = tk.Label(self.spinner_window, text="Aan het rekenen...")
        self.spinner_label.pack(pady=20)

        self.spinner_window.grab_set()

    def _check_thread(self):
        if self.calculation_thread.is_alive():
            self.spinner_window.after(100, self._check_thread)
        else:
            self.spinner_window.destroy()
            if self.solver_exception:
                self._error_dialog(self.solver_exception)
            else:
                self._handle_result(self.result)

    def _handle_result(self, result: SolverResult):
        output_dir = os.path.dirname(self.input_file_label.cget('text'))
        output_file = os.path.join(output_dir, self.output_file_entry.get())

        show_changes = self.data.previous_result is not None
        diffs = 0
        if show_changes:
            diffs = self.data.get_difference_count()

        write_to_excel(self.data, output_file)

        message = ''
        color = None
        if result.schedulable:
            if result.optimal:
                message = 'Optimale oplossing gevonden'
                color = 'green'
            else:
                message = 'Oplossing gevonden, maar mogelijk niet optimaal door overschrijding van de tijdslimiet'
                color = 'orange'
        else:
            if result.optimal:
                message = 'Niet alle vakken kunnen worden ingedeeld,\nmet rood zijn de vakken aangegeven die niet passen'
            else:
                message = 'Niet alle vakken kunnen worden ingedeeld.\ner kon ook niet binnen de tijd een best-mogelijke indeling worden gevonden'
            color = 'red'

        result_window = self._create_dialog("Resultaat", 400, 300)

        result_label = tk.Label(result_window, text=message, fg=color)
        result_label.pack(pady=20)

        if show_changes:
            diff_label = tk.Label(result_window, text=f"{diffs} wijzigingen t.o.v. eerder resultaat")
            diff_label.pack(pady=20)

        open_button = tk.Button(result_window, text="Open resultaat", command=lambda: self._open(output_file))
        open_button.pack(pady=20)

        ok_button = tk.Button(result_window, text="OK", command=result_window.destroy)
        ok_button.pack(pady=20)

        result_window.grab_set()

    def _open(self, file_path):
        """Open the file with the default application, should work on Windows, Linux and MacOS"""
        if platform.system() == 'Windows':
            os.startfile(file_path)
        elif platform.system() == 'Darwin':  # macOS
            os.system(f'open "{file_path}"')
        else:  # Linux and other Unix-like systems
            os.system(f'xdg-open "{file_path}"')

    def _error_dialog(self, e):
        error_window = self._create_dialog("Error", 400, 300)

        error_label = tk.Label(error_window, text=str(e))
        error_label.pack(pady=20)

        ok_button = tk.Button(error_window, text="OK", command=error_window.destroy)
        ok_button.pack(pady=20)

        error_window.grab_set()

    def _create_dialog(self, title, width, height):
        dialog = tk.Toplevel()
        dialog.title(title)

        main_x = dialog.master.winfo_x()
        main_y = dialog.master.winfo_y()
        main_width = dialog.master.winfo_width()
        main_height = dialog.master.winfo_height()
        position_right = main_x + (main_width // 2) - (width // 2)
        position_top = main_y + (main_height // 2) - (height // 2)

        dialog.geometry(f'{width}x{height}+{position_right}+{position_top}')
        return dialog
