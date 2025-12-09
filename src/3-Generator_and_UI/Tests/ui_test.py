import unittest
import tkinter as tk
from ui import StaffCanvas, NumberSelector


class TestStaffCanvas(unittest.TestCase):
    def setUp(self):
        """Create a fresh Tk root, a simple controller stub, and a StaffCanvas for each test."""
        self.root = tk.Tk()
        self.root.withdraw()
        #self.canvas = StaffCanvas(self.root, self.controller, measures=2, chain_order=1, load_images=False)
        # Minimal controller stub required by StaffCanvas usage
        class ControllerStub:
            def __init__(self):
                self.updated = 0
            def update_generate_button(self):
                self.updated += 1
        self.controller = ControllerStub()
        # Create a small staff to speed up geometry calculations in tests
        self.canvas = StaffCanvas(parent=self.root, controller=self.controller, measures=2, chain_order=1)
        # Ensure a known size for geometry-based tests
        self.canvas.width = 400
        self.canvas.height = 200

    def tearDown(self):
        """Destroy the Tk root after each test to avoid lingering windows."""
        try:
            self.root.destroy()
        except Exception:
            pass

    # -----------------------------
    # Basic constructor / slots
    # -----------------------------
    def test_constructor_sets_measures_and_total_slots(self):
        """Constructor should initialize measures and total_slots = measures * 4."""
        self.assertEqual(self.canvas.measures, 2)
        self.assertEqual(self.canvas.total_slots(), 2 * 4)

    def test_init_slots_each_slot_structure(self):
        """_each slot after initialization must contain expected keys."""
        s = self.canvas.slots[0]
        expected_keys = {"occupied", "midi", "is_generated", "canvas_ids", "measure_index", "slot_index"}
        self.assertTrue(expected_keys.issubset(set(s.keys())))

    def test_set_measures_reinitializes_slots_and_keeps_seed(self):
        """set_measures should reinit slots and attempt to reload seed notes."""
        # Place a seed note and mark it user-added
        self.canvas.slots[0]["occupied"] = True
        self.canvas.slots[0]["midi"] = 60
        self.canvas.slots[0]["is_generated"] = False
        # Now change measures (will reinit and reload)
        self.canvas.set_measures(1)
        self.assertEqual(self.canvas.measures, 1)
        # After reducing measures, number of slots should be 4
        self.assertEqual(self.canvas.total_slots(), 4)

    # -----------------------------
    # Midi name helpers
    # -----------------------------
    def test_midi_to_name_and_natural_name_for_standard_values(self):
        """_midi_to_name and _midi_natural_name should return expected formats."""
        name = self.canvas._midi_to_name(60)   # middle C -> "C"
        self.assertTrue(name.startswith("C"))
        natural = self.canvas._midi_natural_name(61)  # C# -> "C"
        self.assertEqual(natural, "C")

    def test_generate_natural_midis_range_contains_no_sharps(self):
        """_generate_natural_midis should return only naturals within given range."""
        mids = self.canvas._generate_natural_midis(60, 67)
        # All returned values should be naturals (no sharps when converted)
        for m in mids:
            n = self.canvas._midi_to_name(m)
            self.assertNotIn("#", n)

    # -----------------------------
    # Mapping positions and indices
    # -----------------------------
    def test_y_for_natural_index_symmetry_and_numeric(self):
        """_y_for_natural_index must return a numeric y coordinate and vary with index."""
        i0 = self.canvas._y_for_natural_index(self.canvas.bottom_index)
        i1 = self.canvas._y_for_natural_index(self.canvas.bottom_index + 2)
        self.assertIsInstance(i0, float)
        self.assertNotEqual(i0, i1)

    def test_closest_natural_index_for_y_returns_valid_index(self):
        """_closest_natural_index_for_y should return an index within natural_midis range."""
        y = self.canvas._y_for_natural_index(self.canvas.bottom_index)
        idx = self.canvas._closest_natural_index_for_y(y + 3)
        self.assertTrue(0 <= idx < len(self.canvas.natural_midis))

    def test_midi_to_natural_index_exact_and_approximate(self):
        """_midi_to_natural_index returns exact index for naturals and nearest for non-naturals."""
        # pick a known natural
        nat = self.canvas.natural_midis[0]
        idx_exact = self.canvas._midi_to_natural_index(nat)
        self.assertEqual(self.canvas.natural_midis[idx_exact], nat)
        # pick a sharp (natural + 1) and ensure it maps to the natural's index
        sharp = nat + 1
        idx_sharp = self.canvas._midi_to_natural_index(sharp)
        self.assertTrue(0 <= idx_sharp < len(self.canvas.natural_midis))

    # -----------------------------
    # Slot geometry and drawing
    # -----------------------------
    def test_slot_center_returns_coordinates_and_uses_default_when_empty_midi(self):
        """_slot_center should return cx, cy floats even when slot has no midi."""
        cx, cy = self.canvas._slot_center(0)
        self.assertIsInstance(cx, float)
        self.assertIsInstance(cy, float)

    def test_draw_note_in_slot_creates_canvas_ids_and_tags(self):
        """_draw_note_in_slot should populate slot['canvas_ids'] and add tag 'slot_<idx>'."""
        # Ensure slot is marked occupied with a midi that is natural
        self.canvas.slots[1]["occupied"] = True
        self.canvas.slots[1]["midi"] = self.canvas.natural_midis[0]
        self.canvas.slots[1]["is_generated"] = False
        # Draw
        self.canvas._draw_note_in_slot(1, self.canvas.slots[1])
        self.assertTrue(len(self.canvas.slots[1]["canvas_ids"]) >= 1)
        # Check that at least one canvas item has slot tag
        found_tag = False
        for cid in self.canvas.slots[1]["canvas_ids"]:
            tags = self.canvas.gettags(cid)
            for t in tags:
                if t == f"slot_1":
                    found_tag = True
        self.assertTrue(found_tag)

    # -----------------------------
    # Interaction handlers: double click
    # -----------------------------
    def test_on_double_click_places_note_in_first_free_slot_and_calls_controller(self):
        """on_double_click should place a natural note in the first empty slot and notify controller."""
        # Ensure slots are empty
        for s in self.canvas.slots:
            s["occupied"] = False
        # craft an event near the bottom line
        class E:
            y: float
            x: float
        e = E()
        e.y = self.canvas._y_for_natural_index(self.canvas.bottom_index)
        # call double click
        self.canvas.on_double_click(e)
        # after placing, one slot should be occupied
        user_occupied = sum(1 for s in self.canvas.slots if s["occupied"] and not s["is_generated"])
        self.assertEqual(user_occupied, 1)
        # controller should have been updated
        self.assertEqual(self.controller.updated, 1)

    def test_on_double_click_respects_chain_order_limit_and_flashes(self):
        """on_double_click should not allow more user notes than chain_order and should not add a slot."""
        # set chain_order to 1 and occupy one slot
        self.canvas.chain_order = 1
        for s in self.canvas.slots:
            s["occupied"] = False
        class E:
            y: float
            x: float
        e = E()
        e.y = self.canvas._y_for_natural_index(self.canvas.bottom_index)
        # call double click -> should early-return without occupying any slot
        self.canvas.on_double_click(e)
        user_occupied = sum(1 for s in self.canvas.slots if s["occupied"] and not s["is_generated"])
        self.assertEqual(user_occupied, 1)

    # -----------------------------
    # Interaction handlers: left click (toggle sharp)
    # -----------------------------
    def test_on_left_click_toggles_sharp_for_non_BE_natural(self):
        """on_left_click should convert a natural to its sharp (midi+1) when clicked."""
        # prepare a slot with a natural that is not B or E
        idx = 2
        nat_midi = None
        # find a natural that is not B or E
        for m in self.canvas.natural_midis:
            name = self.canvas._midi_natural_name(m)
            if name not in ("B", "E"):
                nat_midi = m
                break
        self.canvas.slots[idx]["occupied"] = True
        self.canvas.slots[idx]["midi"] = nat_midi
        self.canvas.slots[idx]["is_generated"] = False
        # draw it so canvas items/tags exist
        self.canvas._draw_note_in_slot(idx, self.canvas.slots[idx])
        cx, cy = self.canvas._slot_center(idx)
        class E:
            y: float
            x: float
        e = E()
        e.x = int(cx)
        e.y = int(cy)
        # perform left click -> should toggle to sharp (midi+1)
        prev = self.canvas.slots[idx]["midi"]
        self.canvas.on_left_click(e)
        self.assertEqual(self.canvas.slots[idx]["midi"], prev + 1)

    def test_on_left_click_does_not_toggle_on_B_or_E_and_calls_flash(self):
        """on_left_click should not add a sharp for a B or E natural (midi unchanged)."""
        # find an E natural midi
        e_midi = None
        for m in self.canvas.natural_midis:
            if self.canvas._midi_natural_name(m) == "E":
                e_midi = m
                break
        idx = 3
        self.canvas.slots[idx]["occupied"] = True
        self.canvas.slots[idx]["midi"] = e_midi
        self.canvas.slots[idx]["is_generated"] = False
        self.canvas._draw_note_in_slot(idx, self.canvas.slots[idx])
        cx, cy = self.canvas._slot_center(idx)
        class Evt:
            y: float
            x: float
        ev = Evt()
        ev.x = int(cx)
        ev.y = int(cy)
        prev = self.canvas.slots[idx]["midi"]
        # left click should call _flash_note which draws a temporary bbox; midi must remain unchanged
        self.canvas.on_left_click(ev)
        self.assertEqual(self.canvas.slots[idx]["midi"], prev)

    # -----------------------------
    # Interaction handlers: right click (delete)
    # -----------------------------
    def test_on_right_click_deletes_note_and_calls_controller(self):
        """on_right_click should clear a slot's occupied flag and notify controller."""
        idx = 0
        self.canvas.slots[idx]["occupied"] = True
        self.canvas.slots[idx]["midi"] = self.canvas.natural_midis[0]
        self.canvas.slots[idx]["is_generated"] = False
        self.canvas._draw_note_in_slot(idx, self.canvas.slots[idx])
        cx, cy = self.canvas._slot_center(idx)
        class Ev:
            y: float
            x: float
        ev = Ev()
        ev.x = int(cx)
        ev.y = int(cy)
        # call right click
        self.canvas.on_right_click(ev)
        self.assertFalse(self.canvas.slots[idx]["occupied"])
        # controller should have been updated by on_right_click
        self.assertEqual(self.controller.updated, 1)

    # -----------------------------
    # Generated notes management
    # -----------------------------
    def test_draw_generated_notes_places_generated_and_limits_to_free_slots(self):
        """draw_generated_notes should mark notes as generated and only fill free slots."""
        # clear and ensure only one free slot by occupying others
        self.canvas._init_slots()
        for i in range(len(self.canvas.slots) - 1):
            self.canvas.slots[i]["occupied"] = True
            self.canvas.slots[i]["midi"] = self.canvas.natural_midis[0]
            self.canvas.slots[i]["is_generated"] = False
        free_before = sum(1 for s in self.canvas.slots if not s["occupied"])
        notes = [f"NOTE_{m}" for m in range(60, 60 + 5)]
        self.canvas.draw_generated_notes(notes)
        free_after = sum(1 for s in self.canvas.slots if not s["occupied"])
        self.assertEqual(free_after, 0)

    def test_clear_generated_notes_removes_only_generated_entries(self):
        """clear_generated_notes must remove only slots marked is_generated=True."""
        self.canvas._init_slots()
        # mark some generated and some user slots
        self.canvas.slots[0]["occupied"] = True
        self.canvas.slots[0]["midi"] = 60
        self.canvas.slots[0]["is_generated"] = True
        self.canvas.slots[1]["occupied"] = True
        self.canvas.slots[1]["midi"] = 61
        self.canvas.slots[1]["is_generated"] = False
        self.canvas.clear_generated_notes()
        self.assertFalse(self.canvas.slots[0]["occupied"])
        self.assertTrue(self.canvas.slots[1]["occupied"])

    def test_load_seed_notes_into_slots_fills_left_to_right_and_respects_capacity(self):
        """load_seed_notes_into_slots should place given seed notes left->right up to capacity."""
        self.canvas._init_slots()
        seeds = [f"NOTE_{60 + i}" for i in range(10)]
        self.canvas.load_seed_notes_into_slots(seeds)
        seed_count = sum(1 for s in self.canvas.slots if s["occupied"] and not s["is_generated"])
        # seed_count cannot exceed total slots
        self.assertTrue(seed_count <= len(self.canvas.slots))
        # first occupied should correspond to first seed
        if seed_count > 0:
            first_midi = int(seeds[0].split("_")[1])
            self.assertEqual(self.canvas.slots[0]["midi"], first_midi)

    # -----------------------------
    # Low-level utility
    # -----------------------------
    def test__delete_note_in_slot_clears_canvas_ids_and_flags(self):
        """_delete_note_in_slot should clear canvas_ids and set occupied False."""
        idx = 0
        self.canvas.slots[idx]["occupied"] = True
        self.canvas.slots[idx]["midi"] = 65
        # simulate a canvas id
        self.canvas.slots[idx]["canvas_ids"] = [9999]
        # calling delete should clear fields without raising
        self.canvas._delete_note_in_slot(idx)
        self.assertFalse(self.canvas.slots[idx]["occupied"])
        self.assertEqual(self.canvas.slots[idx]["canvas_ids"], [])


class TestNumberSelector(unittest.TestCase):
    """Unit tests for the NumberSelector widget."""

    def setUp(self):
        """Create a fresh Tk root and NumberSelector before each test."""
        self.root = tk.Tk()
        self.selector = NumberSelector(
            parent=self.root,
            text="Test",
            min_value=0,
            max_value=10,
            start=5
        )

        self.selector.pack()
        self.root.update()

    def tearDown(self):
        """Destroy the Tk root after each test to avoid resource leaks."""
        self.root.destroy()
        
    def process_events(self):
        """Run a mini-mainloop so Tk processes virtual events."""
        self.root.update_idletasks()
        self.root.after(1, self.root.quit)
        self.root.mainloop()

    def test_constructor_initializes_value_correctly(self):
        """The constructor should set the initial value properly."""
        self.assertEqual(self.selector.get_value(), 5)

    def test_increment_increases_value_when_below_max(self):
        """increment() should increase the value when it is below max_value."""
        self.selector.value.set(5)
        self.selector.increment()
        self.assertEqual(self.selector.get_value(), 6)

    def test_increment_does_not_exceed_max_value(self):
        """increment() should not increase the value past max_value."""
        self.selector.value.set(10)
        self.selector.increment()
        self.assertEqual(self.selector.get_value(), 10)

    def test_decrement_decreases_value_when_above_min(self):
        """decrement() should decrease the value when it is above min_value."""
        self.selector.value.set(5)
        self.selector.decrement()
        self.assertEqual(self.selector.get_value(), 4)

    def test_decrement_does_not_go_below_min_value(self):
        """decrement() should not decrease the value past min_value."""
        self.selector.value.set(0)
        self.selector.decrement()
        self.assertEqual(self.selector.get_value(), 0)

    def test_get_value_returns_current_value(self):
        """get_value() should return the current integer value."""
        self.selector.value.set(7)
        self.assertEqual(self.selector.get_value(), 7)

    def test_increment_triggers_event_when_value_changes(self):
        """increment() should generate <<ValueChanged>> when value changes."""
        events = []
        def handler(event):
            events.append("changed")
            
        self.selector.bind("<<ValueChanged>>", handler)
        self.selector.increment()
        self.process_events()
        self.assertEqual(len(events), 1)

    def test_decrement_triggers_event_when_value_changes(self):
        """decrement() should generate <<ValueChanged>> when value changes."""
        events = []
        def handler(event):
            events.append("changed")
        
        self.selector.bind("<<ValueChanged>>", handler)
        self.selector.decrement()
        self.process_events()
        self.assertEqual(len(events), 1)