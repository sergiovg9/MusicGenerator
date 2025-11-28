import tkinter as tk
from tkinter import ttk


class NumberSelector(tk.Frame):
    """
    A custom widget with a label, a decrement button, a number display, 
    and an increment button.
    """

    def __init__(self, parent, text, min_value, max_value, start, font=("Arial", 14)):
        super().__init__(parent)

        self.min_value = min_value
        self.max_value = max_value

        self.value = tk.IntVar(value=start)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)

        label = tk.Label(self, text=text, font=font)
        label.grid(row=0, column=0, columnspan=3, pady=(0, 10))

        # Buttons and number display
        self.btn_minus = tk.Button(self, text="–", font=("Arial", 13), width=2, command=self.decrement)
        self.btn_minus.grid(row=1, column=0, sticky="e", padx=5)

        self.display = tk.Label(self, textvariable=self.value, font=("Arial", 16))
        self.display.grid(row=1, column=1)

        self.btn_plus = tk.Button(self, text="+", font=("Arial", 13), width=2, command=self.increment)
        self.btn_plus.grid(row=1, column=2, sticky="w", padx=5)

    def increment(self):
        if self.value.get() < self.max_value:
            self.value.set(self.value.get() + 1)

    def decrement(self):
        if self.value.get() > self.min_value:
            self.value.set(self.value.get() - 1)

    def get_value(self):
        return self.value.get()


class MarkovUI(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(padx=40, pady=40)

        # =====================
        # SELECTORS TOP ROW
        # =====================
        top_frame = tk.Frame(self)
        top_frame.pack(fill="x", pady=(0, 30))

        # 2 columns that expand equally
        top_frame.columnconfigure(0, weight=1)
        top_frame.columnconfigure(1, weight=1)

        # --- Order selector (1–4) ---
        self.order_selector = NumberSelector(
            top_frame,
            text="Markov Chain Order",
            min_value=1,
            max_value=4,
            start=1
        )
        self.order_selector.grid(row=0, column=0, sticky="nsew", padx=10)

        # --- Measures selector (2–8) ---
        self.measures_selector = NumberSelector(
            top_frame,
            text="Measures",
            min_value=2,
            max_value=8,
            start=2
        )
        self.measures_selector.grid(row=0, column=1, sticky="nsew", padx=10)
        
        # TONALITY SELECTORS
        
        tonality_frame = tk.Frame(self)
        tonality_frame.pack(fill="x", pady=(0, 30))

        tonality_frame.columnconfigure(0, weight=1)
        tonality_frame.columnconfigure(1, weight=1)
        tonality_frame.columnconfigure(2, weight=1)

        label_font = ("Arial", 14)
        combo_font = ("Arial", 14)

        # --- Note ---
        tk.Label(tonality_frame, text="Note", font=label_font).grid(row=0, column=0, pady=(0, 10))
        self.note_var = tk.StringVar(value="C")
        note_selector = ttk.Combobox(
            tonality_frame,
            textvariable=self.note_var,
            values=["C", "D", "E", "F", "G", "A", "B"],
            state="readonly",
            font=combo_font,
            width=5
        )
        note_selector.grid(row=1, column=0, padx=10, sticky="ew")

        # --- Sharp / Flat ---
        tk.Label(tonality_frame, text="#", font=label_font).grid(row=0, column=1, pady=(0, 10))
        self.acc_var = tk.StringVar(value="")  # default: natural
        acc_selector = ttk.Combobox(
            tonality_frame,
            textvariable=self.acc_var,
            values=["", "#"],
            state="readonly",
            font=combo_font,
            width=5
        )
        acc_selector.grid(row=1, column=1, padx=10, sticky="ew")

        # --- Major / Minor ---
        tk.Label(tonality_frame, text="Mode", font=label_font).grid(row=0, column=2, pady=(0, 10))
        self.mode_var = tk.StringVar(value="M")
        mode_selector = ttk.Combobox(
            tonality_frame,
            textvariable=self.mode_var,
            values=["M", "m"],
            state="readonly",
            font=combo_font,
            width=5
        )
        mode_selector.grid(row=1, column=2, padx=10, sticky="ew")


        # =====================
        # TEST BUTTON
        # =====================
        test_button = tk.Button(
            self,
            text="Generate with Markov",
            command=self.debug_print_values,
            height=2,
            font=("Arial", 18)
        )
        test_button.pack(pady=20)

    def debug_print_values(self):
        order = self.order_selector.get_value()
        measures = self.measures_selector.get_value()

        tonality = f"{self.note_var.get()}{self.acc_var.get()}{self.mode_var.get()}"


        print("=== Selected Values ===")
        print(f"Chain Order: {order}")
        print(f"Measures: {measures}")
        print(f"Tonality: {tonality}")
        print("========================")

