import tkinter as tk
from tkinter import ttk
from markov_generator import generate_sequence
from playback import play_midi_sequence
import threading
from PIL import Image, ImageTk

# Existing NumberSelector
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

        self.btn_minus = tk.Button(self, text="–", font=("Arial", 13), width=2, command=self.decrement)
        self.btn_minus.grid(row=1, column=0, sticky="e", padx=5)

        self.display = tk.Label(self, textvariable=self.value, font=("Arial", 16))
        self.display.grid(row=1, column=1)

        self.btn_plus = tk.Button(self, text="+", font=("Arial", 13), width=2, command=self.increment)
        self.btn_plus.grid(row=1, column=2, sticky="w", padx=5)

    def increment(self):
        if self.value.get() < self.max_value:
            self.value.set(self.value.get() + 1)
            self.event_generate("<<ValueChanged>>")

    def decrement(self):
        if self.value.get() > self.min_value:
            self.value.set(self.value.get() - 1)
            self.event_generate("<<ValueChanged>>")

    def get_value(self):
        return self.value.get()


# StaffCanvas: interactive staff
class StaffCanvas(tk.Canvas):
    """
    Canvas that draws a treble staff, measure lines and supports:
      - double-click to add a natural note into the first empty slot (L->R)
      - left-click on a note to toggle sharp (#) if allowed (not allowed for B/E)
      - right-click on a note to delete it
    Slots: measures * 4 (4 quarter-note slots per measure)
    Internals:
      - slots: list of dicts {occupied, midi, is_generated, canvas_ids, measure_index, slot_index}
    """

    # Natural notes sequence (names) for reference (C, D, E, F, G, A, B)
    NATURAL_NAMES = ["C", "D", "E", "F", "G", "A", "B"]

    def __init__(self, parent, controller, measures=4, chain_order=1, *args, **kwargs):
        super().__init__(parent, *args, **kwargs, height=370)
        self.controller = controller

        # Staff geometry
        self.margin_x = 40
        self.margin_y = 140
        self.line_spacing = 16  # px between staff lines
        self.staff_lines = 5

        # Cleff image
        image = Image.open("src/3-Generator_and_UI/treble_clef.png")
        image = image.resize((int(self.line_spacing * 3), int(self.line_spacing * 6)), Image.Resampling.LANCZOS)
        self.clef_image = ImageTk.PhotoImage(image)

        # musical range: we'll create a mapping of natural notes (no accidentals) across octaves
        # We'll use naturals from MIDI 24 (C1) up to MIDI 108 (C8) — plenty of range for clicks
        self.natural_midis = self._generate_natural_midis(24, 108)  # list of midi numbers for naturals only
        # find index of E4 (midi 64) in natural_midis: we'll align that to bottom staff line
        self.bottom_line_natural_midi = 64  # E4 natural on bottom line of treble
        if self.bottom_line_natural_midi in self.natural_midis:
            self.bottom_index = self.natural_midis.index(self.bottom_line_natural_midi)
        else:
            # fallback
            self.bottom_index = 4

        # measures/slots
        self.measures = measures
        self.slots = []  # will be filled by self._init_slots()
        self.chain_order = 1 # default
        self._init_slots()

        # draw initial staff
        self.bind("<Configure>", lambda e: self.redraw())  # handle resize
        self.bind("<Double-Button-1>", self.on_double_click)
        self.bind("<Button-1>", self.on_left_click)
        self.bind("<Button-3>", self.on_right_click)

        # small visual config
        self.note_radius_x = 10
        self.note_radius_y = 7
        self.acc_offset_x = 18

        # initial draw
        self.redraw()

    # -----------------------------
    # low-level helpers
    # -----------------------------
    def _generate_natural_midis(self, low_midi, high_midi):
        """
        Return a list of naturals between low_midi and high_midi inclusive.
        Naturals are C D E F G A B semitone pattern: +2 +2 +1 +2 +2 +2 +1
        We'll walk from lowest C below/at low_midi upward.
        """
        # find the C of the octave containing low_midi (or lower) to start
        # find midi for the C of the octave of low_midi
        c = low_midi
        # decrement until it's a C
        while (c % 12) != 0:
            c -= 1
        mids = []
        # sequence of intervals between naturals (in semitones): C->D 2, D->E 2, E->F 1, F->G 2, G->A 2, A->B 2, B->C 1
        intervals = [2, 2, 1, 2, 2, 2, 1]
        note = c
        while note <= high_midi:
            # append only naturals >= low_midi
            if note >= low_midi:
                mids.append(note)
            # step by next interval
            step = intervals[(len(mids) + (0)) % 7]  # approximate; order doesn't strictly matter here
            # Actually better to advance through cycle of intervals
            break

        # Simpler deterministic implementation: iterate all midi and pick naturals by name.
        result = []
        for midi in range(low_midi, high_midi + 1):
            name = self._midi_to_name(midi)
            # include only naturals (no #)
            if ("#" not in name) and ("b" not in name):
                result.append(midi)
        return result

    def _midi_to_name(self, midi: int) -> str:
        """Return name like C4, C#4, D4 ..."""
        names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        octave = (midi // 12) - 1
        name = names[midi % 12]
        return f"{name}{octave}"

    def _midi_natural_name(self, midi: int) -> str:
        """Return natural letter for midi ignoring accidental (e.g., 60 -> C)."""
        names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        return names[midi % 12].replace("#", "")

    # -----------------------------
    # Slots init & geometry
    # -----------------------------
    def _init_slots(self):
        """Initialize slots structure according to current measures."""
        total_slots = self.measures * 4
        self.slots = []
        for mi in range(self.measures):
            for si in range(4):
                self.slots.append({
                    "occupied": False,
                    "midi": None,
                    "is_generated": False,
                    "canvas_ids": [],  # ids for notehead, stem, accidental
                    "measure_index": mi,
                    "slot_index": si,
                })

    def set_measures(self, measures: int):
        seed_notes = self.get_seed_notes()

        self.measures = measures
        self._init_slots()

        self.load_seed_notes_into_slots(seed_notes)   

        self.redraw()

    def set_chain_order(self, order: int):
        self.chain_order = order

    def total_slots(self):
        return len(self.slots)

    # -----------------------------
    # Mapping positions <-> midi naturals
    # -----------------------------
    def _y_for_natural_index(self, natural_index: int) -> float:
        """
        natural_index: index into self.natural_midis (0 .. n-1)
        We'll map natural_index into pixel Y such that self.bottom_index maps to bottom staff line.
        Each natural step corresponds to half the staff line spacing (line->space->line).
        """
        # staff baseline positions
        staff_top = self.margin_y
        staff_bottom = self.margin_y + (self.staff_lines - 1) * self.line_spacing
        # natural step px
        step_px = self.line_spacing / 2.0
        # compute offset in steps from bottom natural index
        delta = natural_index - self.bottom_index
        # y increases downward, and higher naturals (bigger midi) are higher on staff (smaller y)
        y = staff_bottom - (delta * step_px)
        return y

    def _closest_natural_index_for_y(self, y_click: float) -> int:
        """Find the natural_index whose y is nearest to y_click."""
        if not self.natural_midis:
            return 0

        best_i = 0
        best_dist = 1e9

        for i in range(len(self.natural_midis)):
            y = self._y_for_natural_index(i)
            d = abs(y - y_click)
            if d < best_dist:
                best_dist = d
                best_i = i

        return best_i

    def _natural_index_to_midi(self, natural_index: int) -> int:
        return self.natural_midis[natural_index]

    def _midi_to_natural_index(self, midi: int) -> int:
        """Return index in natural_midis for the natural midi value (strip accidental)."""
        # find nearest natural midi (exact match preferred)
        if midi in self.natural_midis:
            return self.natural_midis.index(midi)
        # if midi is sharp (midi-1 may be natural)
        if (midi - 1) in self.natural_midis:
            return self.natural_midis.index(midi - 1)
        # fallback closest
        best_i = min(range(len(self.natural_midis)), key=lambda i: abs(self.natural_midis[i] - midi))
        return best_i

    # -----------------------------
    # Draw staff & measures & notes
    # -----------------------------
    def redraw(self):
        """Redraw entire canvas (staff lines, measure bars, notes)."""
        self.delete("all")
        w = self.winfo_width() or self.width
        h = self.winfo_height() or self.height

        self.width = w
        self.height = h

        # staff geometry
        staff_top = self.margin_y
        staff_bottom = self.margin_y + (self.staff_lines - 1) * self.line_spacing

        # draqw staff left/right positions 
        clef_offset_x = 40
        staff_left = self.margin_x + clef_offset_x
        staff_right = w - self.margin_x

        # draw staff lines
        for i in range(self.staff_lines):
            y = staff_top + i * self.line_spacing
            self.create_line(staff_left, y, staff_right, y, width=1, fill="black")

        # draw measure separators
        measure_width = (staff_right - staff_left) / max(1, self.measures)
        for m in range(self.measures + 1):
            x = staff_left + m * measure_width
            self.create_line(x, staff_top - 6, x, staff_bottom + 6, width=1)

        # draw treble clef at the left margin (before the notes)
        self.create_image(
            self.margin_x, 
            staff_top + (self.staff_lines * self.line_spacing) / 2,
            image=self.clef_image,
            anchor="w"
        )

        # draw existing notes from slots
        for idx, slot in enumerate(self.slots):
            if slot["occupied"]:
                self._draw_note_in_slot(idx, slot)

    def _slot_center(self, slot_index):
        """Return center x,y for a given slot index (0..total_slots-1)."""
        # x-coordinate
        clef_offset_x = 40
        staff_left = self.margin_x + clef_offset_x
        staff_right = self.width - self.margin_x

        measure_width = (staff_right - staff_left) / max(1, self.measures)
        mi = slot_index // 4
        si = slot_index % 4
        slot_width = measure_width / 4.0
        cx = staff_left + mi * measure_width + si * slot_width + slot_width / 2.0

        # y-coordinate
        if self.slots[slot_index]["midi"] is not None:
            midi = self.slots[slot_index]["midi"]
            natural_index = self._midi_to_natural_index(midi)
        else:
            natural_index = self.bottom_index + 4
        cy = self._y_for_natural_index(natural_index)
        return cx, cy

    def _draw_note_in_slot(self, slot_idx: int, slot: dict):
        """Draw the note (notehead, stem, accidental) for the given slot."""
        # remove previous canvas ids if any
        for cid in slot.get("canvas_ids", []):
            try:
                self.delete(cid)
            except Exception:
                pass
        slot["canvas_ids"] = []

        cx, cy = self._slot_center(slot_idx)
        rX = self.note_radius_x
        rY = self.note_radius_y
        # notehead (black oval)
        oid = self.create_oval(cx - rX, cy - rY, cx + rX, cy + rY, fill="black", outline="black")
        slot["canvas_ids"].append(oid)
        # small stem (upwards on right side)
        stem = self.create_line(cx + rX - 2, cy, cx + rX - 2, cy - 35, width=1, fill="black")
        slot["canvas_ids"].append(stem)

        # draw accidental if required
        midi = slot.get("midi")
        if midi is not None:
            # if midi not natural, then it's sharp: detect if midi not in natural_midis and equals natural+1
            if midi not in self.natural_midis:
                # draw '#'
                acc = self.create_text(cx - self.acc_offset_x, cy, text="#", font=("Arial", 14))
                slot["canvas_ids"].append(acc)
        
        # tag all parts so we can find them on clicks
        for cid in slot["canvas_ids"]:
            self.addtag_withtag(f"slot_{slot_idx}", cid)

    # -----------------------------
    # Interaction handlers
    # -----------------------------
    def on_double_click(self, event):
        """Add a natural note at clicked vertical position into the first empty slot (L->R)."""
        # compute natural closest to click
        y = event.y
        natural_idx = self._closest_natural_index_for_y(y)
        midi_nat = self._natural_index_to_midi(natural_idx)

        user_notes = sum(1 for s in self.slots if s["occupied"] and not s["is_generated"])
        if user_notes >= self.chain_order:
            self._flash_message(f"Maximum: {self.chain_order} slots for a {self.chain_order}-order chain.")
            return

        # find first empty slot (now allowed because we passed the chain limit)
        empty_idx = None
        for i, s in enumerate(self.slots):
            if not s["occupied"]:
                empty_idx = i
                break
        if empty_idx is None:
            self._flash_message("No empty slots available.")
            return

        # place as user seed (is_generated False)
        self.slots[empty_idx]["occupied"] = True
        self.slots[empty_idx]["midi"] = midi_nat
        self.slots[empty_idx]["is_generated"] = False
        self._draw_note_in_slot(empty_idx, self.slots[empty_idx])
        self.controller.update_generate_button()

    def on_left_click(self, event):
        """Toggle sharp on clicked note (if allowed). Also allows clicking on empty canvas (ignored)."""
        x = event.x
        y = event.y
        # find items under cursor
        items = self.find_overlapping(x, y, x, y)
        if not items:
            return
        # find slot tag among items
        slot_idx = None
        for item in items:
            tags = self.gettags(item)
            for t in tags:
                if t.startswith("slot_"):
                    try:
                        slot_idx = int(t.split("_", 1)[1])
                        break
                    except Exception:
                        pass
            if slot_idx is not None:
                break
        if slot_idx is None:
            return
        slot = self.slots[slot_idx]
        if not slot["occupied"]:
            return

        midi = slot["midi"]
        # compute natural name for base (strip accidental)
        natural = self._midi_natural_name(midi)
        # if natural is B or E -> cannot add sharp
        if natural in ("B", "E"):
            # visual feedback: flash note
            self._flash_note(slot_idx)
            return

        # toggle sharp: if midi is natural (in natural_midis), set midi+1, else if sharp, subtract 1
        if midi in self.natural_midis:
            # natural -> sharp
            slot["midi"] = midi + 1
        else:
            # currently sharp -> back to natural
            # make sure midi-1 is natural
            if (midi - 1) in self.natural_midis:
                slot["midi"] = midi - 1
            else:
                # fallback: remove accidental
                slot["midi"] = self.natural_midis[self._midi_to_natural_index(midi)]
        # redraw this slot
        self._draw_note_in_slot(slot_idx, slot)

    def on_right_click(self, event):
        """Delete note if right-clicked on it."""
        x = event.x
        y = event.y
        items = self.find_overlapping(x, y, x, y)
        if not items:
            return
        slot_idx = None
        for item in items:
            tags = self.gettags(item)
            for t in tags:
                if t.startswith("slot_"):
                    try:
                        slot_idx = int(t.split("_", 1)[1])
                        break
                    except Exception:
                        pass
            if slot_idx is not None:
                break
        if slot_idx is None:
            return
        # clear slot
        for cid in self.slots[slot_idx]["canvas_ids"]:
            try:
                self.delete(cid)
            except Exception:
                pass
        self.slots[slot_idx] = {
            "occupied": False,
            "midi": None,
            "is_generated": False,
            "canvas_ids": [],
            "measure_index": self.slots[slot_idx]["measure_index"],
            "slot_index": self.slots[slot_idx]["slot_index"]
        }
        self.controller.update_generate_button()

    def _flash_message(self, text, duration=800):
        """Temporary message in the middle of canvas."""
        mid_x = self.width / 2
        mid_y = self.height / 2
        tid = self.create_text(mid_x, mid_y, text=text, font=("Arial", 12), fill="red")
        self.after(duration, lambda: self.delete(tid))

    def _flash_note(self, slot_idx, flashes=2, interval=150):
        """Tiny visual flash for slot to indicate invalid action."""
        # highlight by drawing a red oval border briefly
        cx, cy = self._slot_center(slot_idx)
        rX = self.note_radius_x + 2
        rY = self.note_radius_y + 2
        bbox_id = self.create_oval(cx - rX, cy - rY, cx + rX, cy + rY, outline="red", width=2)
        def clear():
            try:
                self.delete(bbox_id)
            except Exception:
                pass
        self.after(interval, clear)

    # -----------------------------
    # Data interface for MarkovUI
    # -----------------------------
    def get_seed_notes(self):
        """Return list of NOTE_midi strings for occupied slots that are user-added (is_generated False),
        in left->right order (slot order)."""
        res = []
        for slot in self.slots:
            if slot["occupied"] and not slot.get("is_generated", False):
                res.append(f"NOTE_{slot['midi']}")
        return res

    def clear_generated_notes(self):
        """Remove notes that were marked as generated (is_generated True)"""
        for idx, slot in enumerate(self.slots):
            if slot["occupied"] and slot.get("is_generated", False):
                for cid in slot.get("canvas_ids", []):
                    try:
                        self.delete(cid)
                    except Exception:
                        pass
                # clear slot but keep measure index info
                self.slots[idx] = {
                    "occupied": False,
                    "midi": None,
                    "is_generated": False,
                    "canvas_ids": [],
                    "measure_index": self.slots[idx]["measure_index"],
                    "slot_index": self.slots[idx]["slot_index"]
                }

    def draw_generated_notes(self, notes_list):
        """
        notes_list: list of strings like "NOTE_60","NOTE_67"...
        Place them into the first empty slots in order L->R and mark them is_generated=True.
        """
        # find all free slots
        free_slots = [i for i, s in enumerate(self.slots) if not s["occupied"]]
        max_new_notes = len(free_slots)

        if max_new_notes == 0:
            print("[INFO] No free slots available. Cannot generate more notes.")
            return

        # limit sequence to available space
        generated_notes = notes_list[:max_new_notes]

        # place generated notes in free slots
        for note_str, slot_index in zip(generated_notes, free_slots):
            midi = int(note_str.split("_")[1])
            slot = self.slots[slot_index]
            slot["occupied"] = True
            slot["midi"] = midi
            slot["is_generated"] = True
            # keep canvas_ids list intact
            if "canvas_ids" not in slot:
                slot["canvas_ids"] = []
            self._draw_note_in_slot(slot_index, slot)

        print(f"[INFO] Wrote {len(generated_notes)} generated notes into the staff.")

    # utility: fill canvas from a given list (clear then place seed as user notes)
    def load_seed_notes_into_slots(self, seed_notes):
        """
        seed_notes: list of "NOTE_60" etc; clears current slots and fills left->right
        as user notes.
        """
        # clear all
        self._init_slots()
        free = [i for i, s in enumerate(self.slots) if not s["occupied"]]
        for i, n in enumerate(seed_notes):
            if i >= len(free):
                break
            midi = int(n.split("_", 1)[1])
            idx = free[i]
            self.slots[idx]["occupied"] = True
            self.slots[idx]["midi"] = midi
            self.slots[idx]["is_generated"] = False
        self.redraw()

    def _delete_note_in_slot(self, idx):
        slot = self.slots[idx]
        for cid in slot["canvas_ids"]:
            try:
                self.delete(cid)
            except:
                pass
        slot["canvas_ids"] = []
        slot["occupied"] = False
        slot["midi"] = None
        slot["is_generated"] = False


# -------------------------
# MarkovUI integrated with StaffCanvas
# -------------------------
class MarkovUI(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(padx=30, pady=10)

        # TOP ROW: order and measures
        top_frame = tk.Frame(self)
        top_frame.pack(fill="x", pady=(10, 6))

        top_frame.columnconfigure(0, weight=1)
        top_frame.columnconfigure(1, weight=1)

        # --- Order selector ---
        self.order_selector = NumberSelector(top_frame, "Markov Chain Order", 1, 4, 1)
        self.order_selector.grid(row=0, column=0, sticky="nsew", padx=8)

        # Bind a single handler to update both chain order and sync seed notes
        self.order_selector.bind("<<ValueChanged>>", 
            lambda e: (
                self.staff.clear_generated_notes(),
                self.staff.set_chain_order(self.order_selector.get_value()),
                self.sync_seed_notes(),
                self.update_generate_button()
                ))
        
        # --- Measures selector ---
        self.measures_selector = NumberSelector(top_frame, "Measures", 2, 8, 2)
        self.measures_selector.grid(row=0, column=1, sticky="nsew", padx=8)
        
        # Bind a single handler to update staff measures
        self.measures_selector.bind("<<ValueChanged>>", 
            lambda e: (
                self.staff.clear_generated_notes(), 
                self.staff.set_measures(self.measures_selector.get_value())
                ))
        
        # TONALITY SELECTORS
        tonality_frame = tk.Frame(self)
        tonality_frame.pack(fill="x", pady=(12, 6))

        # 6 equal columns
        for i in range(6):
            tonality_frame.columnconfigure(i, weight=1)

        label_font = ("Arial", 12)
        combo_font = ("Arial", 12)

        # --- Key ---
        tk.Label(tonality_frame, text="Key", font=label_font)\
            .grid(row=0, column=0, sticky="e", padx=5)

        self.note_var = tk.StringVar(value="C")
        note_selector = ttk.Combobox(
            tonality_frame,
            textvariable=self.note_var,
            values=["C", "D", "E", "F", "G", "A", "B"],
            state="readonly",
            font=combo_font,
            width=4
        )
        note_selector.grid(row=0, column=1, sticky="w", padx=5)

        self.note_var.trace_add("write",
            lambda *args: self.update_accidentals())
        
        # --- Sharp/Natural ---
        tk.Label(tonality_frame, text="Acc", font=label_font)\
            .grid(row=0, column=2, sticky="e", padx=5)

        self.acc_var = tk.StringVar(value="")
        self.acc_selector = ttk.Combobox(
            tonality_frame,
            textvariable=self.acc_var,
            values=["", "#"],
            state="readonly",
            font=combo_font,
            width=4
        )
        self.acc_selector.grid(row=0, column=3, sticky="w", padx=5)
        
        self.acc_var.trace_add("write",
            lambda *args: setattr(self, "current_acc", self.acc_var.get()))

        # Bind event so that altering Note updates allowed accidentals
        note_selector.bind("<<ComboboxSelected>>", self.update_accidentals)

        # --- Major/Minor ---
        tk.Label(tonality_frame, text="Mode", font=label_font)\
            .grid(row=0, column=4, sticky="e", padx=5)
        self.mode_var = tk.StringVar(value="")
        ttk.Combobox(
            tonality_frame,
            textvariable=self.mode_var,
            values=["", "m"],
            state="readonly",
            font=combo_font,
            width=4
        ).grid(row=0, column=5, sticky="w", padx=5)

        self.mode_var.trace_add("write",
            lambda *args: setattr(self, "current_mode", self.mode_var.get()))

        # STAFF CANVAS (center)
        self.staff = StaffCanvas(self, controller=self, measures=self.measures_selector.get_value())
        self.staff.pack(fill="both", expand=False, pady=(50, 12))
        # modern tkinter: trace_add
        self.measures_selector.value.trace_add("write", lambda *args: self.staff.set_measures(self.measures_selector.get_value()))

        # ABC OUTPUT BOX
        self.abc_box = tk.Text(self, height=1, width=95, font=("Consolas", 12),)
        self.abc_box.pack(pady=50)

        # BUTTON FRAME
        button_frame = tk.Frame(self)
        button_frame.pack(pady=8)

        # --- Generate Button ---
        self.generate_button = tk.Button(
            button_frame,
            text="Generate with Markov",
            command=self.debug_print_values,
            height=2,
            font=("Arial", 14)
        )
        self.generate_button.pack(side="left", padx=6)

        
        # --- Reset Button ---
        reset_button = tk.Button(
            button_frame,
            text="Reset Staff",
            command=self.reset_staff,
            height=2,
            font=("Arial", 14)
        )
        reset_button.pack(side="left", padx=6)

        # --- Play Button ---
        play_button = tk.Button(
            button_frame,
            text="Play Sequence",
            command=self.play_sequence,
            height=2,
            font=("Arial", 14)
        )
        play_button.pack(side="left", padx=6)

        help_label = tk.Label(
            self,
            text="Double click: add note\nClick: modify accidental\nRight click: delete note",
            font=("Arial", 13),
            fg="#555555"
        )

        help_label.place(rely=1.0, anchor="sw", x=50, y=-100)

    def seq_to_abc(self, seq):
        abc = []

        for note in seq:
            if not note.startswith("NOTE_"):
                continue
            
            midi = int(note.split("_")[1])

            # Convert MIDI to ABC pitch name
            names = ["C", "^C", "D", "^D", "E", "F", "^F", "G", "^G", "A", "^A", "B"]
            base = names[midi % 12]

            # Octave handling
            octave = midi // 12
            if octave > 5:
                # ABC lower-case = higher octave
                base = base.replace("C","c").replace("D","d").replace("E","e") \
                        .replace("F","f").replace("G","g").replace("A","a").replace("B","b")
            
            abc.append(base)

        sequence=" ".join(abc)

        return " ABC notation: " + sequence

    def update_generate_button(self):
        """Enable/disable generate button depending on number of user notes."""
        required = self.order_selector.get_value()
        user_notes = len(self.staff.get_seed_notes())

        if user_notes >= required:
            self.generate_button.config(state="normal")
        else:
            self.generate_button.config(state="disabled")

    def reset_staff(self):
        """Remove all notes from the staff (user and generated)."""
        for idx, slot in enumerate(self.staff.slots):
            self.staff._delete_note_in_slot(idx)
        self.staff.redraw()
        self.abc_box.delete("1.0", tk.END)

    
    def play_sequence(self):
        """Play the last generated Markov sequence seq."""
        if not hasattr(self, "last_generated_seq") or not self.last_generated_seq:
            print("[AUDIO] No generated sequence available.")
            return

        seq = self.last_generated_seq
        print("[AUDIO] Playing:", seq)

        # Convert NOTE_XX → MIDI integer
        midi_list = [int(n.split("_")[1]) for n in seq]

        threading.Thread(
            target=play_midi_sequence,
            args=(midi_list,),
            daemon=True
        ).start()
 
    
    def sync_seed_notes(self):
        """Ensure number of manual notes equals Markov order by deleting last ones if needed."""
        required = self.order_selector.get_value()

        # count current user-added notes (not generated notes)
        user_notes = [i for i, s in enumerate(self.staff.slots) if s["occupied"] and not s["is_generated"]]

        if len(user_notes) > required:
            # remove extra notes starting from the last added
            to_remove = user_notes[required:]  # indexes to delete
            for idx in reversed(to_remove):
                self.staff._delete_note_in_slot(idx)
            self.staff.redraw()


    def debug_print_values(self):
        order = self.order_selector.get_value()
        measures = self.measures_selector.get_value()
        tonality = f"{self.note_var.get()}{self.acc_var.get()}{self.mode_var.get()}"

        # get seed notes from staff (user-added)
        seed = self.staff.get_seed_notes()

        if len(seed) < order:
            self.staff._flash_message(f"Need {order} notes for order {order}.")
            return

        print("=== Selected Values ===")
        print(f"Chain Order: {order}")
        print(f"Measures: {measures}")
        print(f"Tonality: {tonality}")
        print(f"Seed notes (left->right): {seed}")
        print("========================")

        # -------------------------
        # Placeholder generation behavior:
        # You said: "at generation time write in staff (in reverse) so that if output is NOTE_60, NOTE_67
        # they get drawn left->right as C, then G" — for demo we'll take the seed, reverse it as the generated
        # output, and draw it into empty slots.
        # Replace this block with a call to your markov_generator(seed, order, measures, tonality)
        # which should return a list like ["NOTE_60","NOTE_67", ...]
        # -------------------------
        
        if seed:
            seq = generate_sequence(
                order=order,
                seed=seed,
                measures=measures,
                key=tonality
            )
        else:
            seq = []

        # clear previously generated notes (if any)
        self.staff.clear_generated_notes()

        # limit to available slots
        free_slots = len([s for s in self.staff.slots if not s["occupied"]])
        
        self.last_generated_seq = seq  # store for playback

        # Write ABC notation
        abc_str = self.seq_to_abc(seq)
        self.abc_box.delete("1.0", tk.END)
        self.abc_box.insert(tk.END, abc_str)

        print(f"[DEBUG] Demo generated notes: {seq}")

        order = self.order_selector.get_value()

        # Remove only the seed notes (first 'order' notes)
        generated_only = seq[order:]

        # Limit to available slots
        generated_only = generated_only[:free_slots]

        # Draw
        self.staff.draw_generated_notes(generated_only)


    def update_accidentals(self, event=None):
        """Disable '#' when the selected note is B or E."""
        note = self.note_var.get()

        if note in ("B", "E"):
            # Remove '#' option
            self.acc_selector["values"] = [""]
            self.acc_var.set("")  # reset accidental
        else:
            # Restore normal options
            self.acc_selector["values"] = ["", "#"]
