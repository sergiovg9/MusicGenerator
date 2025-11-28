from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QMouseEvent, QShowEvent
from PyQt6.QtWidgets import (
    QMainWindow, QStyleOptionGraphicsItem, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QSpinBox, QPushButton, QMessageBox, QGraphicsView,
    QGraphicsScene, QGraphicsItem, QGraphicsSceneMouseEvent
)

from markov_generator import generate_sequence
from playback import play_from_pitches
from typing import Callable, Optional, cast

# Constants
SEMITONE_PX = 6
BASE_PITCH = 60  # NOTE_60 = Do central
STAFF_LINES = 5
STAFF_SPACING = 10

class NoteItem(QGraphicsItem):
    def __init__(self, midi_pitch, width=14, height=10):
        super().__init__()
        self.pitch_base = midi_pitch   # pitch sin sostenido
        self.accidental = 0            # 0 = natural, 1 = sharp
        self.width = width
        self.height = height

        self.sharp_text = None

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        )

    # pitch final
    @property
    def pitch(self):
        return self.pitch_base + self.accidental

    def boundingRect(self):
        return QRectF(-self.width/2 - 10, -self.height/2, self.width + 10, self.height)

    def paint(self, painter: QPainter | None, option: QStyleOptionGraphicsItem | None, widget: QWidget | None = None) -> None:
        if painter is None or option is None:
            return  # seguridad en caso de tipado estático
        
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(30, 30, 30)))
        painter.setPen(QPen(Qt.GlobalColor.black))
        painter.drawEllipse(QRectF(-self.width/2, -self.height/2, self.width, self.height))

        if self.accidental == 1:
            font = QFont("Times", 12)
            painter.setFont(font)
            painter.drawText(QPointF(-self.width/2 - 12, 4), "#")

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent | None):
        assert event is not None
        
        if event.button() == Qt.MouseButton.LeftButton:
            # toggle sostenido
            self.accidental = 1 - self.accidental
            self.update()

        elif event.button() == Qt.MouseButton.RightButton:
            # pedir al padre la eliminación
            scene = cast(StaffScene, self.scene())
            if scene.delete_note_callback:
                scene.delete_note_callback(self)

        super().mousePressEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            pos = value
            y = round(pos.y() / SEMITONE_PX) * SEMITONE_PX
            x = pos.x()
            self.setPos(QPointF(x, y))
            self.pitch_base = BASE_PITCH - int(round(y / SEMITONE_PX))
        return super().itemChange(change, value)

class StaffScene(QGraphicsScene):
    delete_note_callback: Optional[Callable[["NoteItem"], None]]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.delete_note_callback = None

class StaffView(QGraphicsView):
    def __init__(self, measures=4):
        super().__init__()
        self.scene_obj = QGraphicsScene(self)
        self.scene_obj = StaffScene(self)
        self.scene_obj.delete_note_callback = self.delete_note
        self.setScene(self.scene_obj)
        self.setRenderHints(self.renderHints() | QPainter.RenderHint.Antialiasing)
        self.setMinimumHeight(260)
        self.setMinimumWidth(800)
        self.measures = measures
        self.note_items = []
        self.seed_items = []
        self.generated_items = []
        self.update_scene()

    def update_scene(self):
        self.scene_obj.clear()
        self.note_items.clear()
        left = 40
        top = 40
        width = 760
        pen = QPen(QColor(0,0,0))
        for i in range(STAFF_LINES):
            y = top + i * STAFF_SPACING
            self.scene_obj.addLine(left, y, left + width, y, pen)

        clef = self.scene_obj.addText('\U0001D11E')  # G clef
        assert clef is not None
        clef.setFont(QFont('Times', 32))
        clef.setPos(left - 30, top - 20)

        total_slots = self.measures * 4
        slot_w = width / total_slots
        for i in range(total_slots + 1):
            x = left + i * slot_w
            if i % 4 == 0:
                self.scene_obj.addLine(x, top - 8, x, top + (STAFF_LINES-1)*STAFF_SPACING + 8, pen)

        self.setSceneRect(0, 0, left + width + 20, top + STAFF_LINES*STAFF_SPACING + 40)

    def set_measures(self, measures):
        self.measures = measures
        self.update_scene()

    def mouseDoubleClickEvent(self, event):
        assert isinstance(event, QMouseEvent)

        pos = self.mapToScene(event.position().toPoint())
        left = 40
        width = 760
        total_slots = self.measures * 4
        slot_w = width / total_slots
        idx = int((pos.x() - left) / slot_w)
        idx = max(0, min(idx, total_slots - 1))
        x = left + idx * slot_w + slot_w/2
        y = round((pos.y() - 40) / SEMITONE_PX) * SEMITONE_PX
        pitch = BASE_PITCH - int(round(y / SEMITONE_PX))
        note = NoteItem(pitch)
        note.setPos(QPointF(x, y))
        self.scene_obj.addItem(note)
        self.seed_items.append(note)
        self.note_items.append(note)
        super().mouseDoubleClickEvent(event)
    
    def delete_note(self, note):
        if note in self.seed_items:
            self.seed_items.remove(note)
        if note in self.generated_items:
            self.generated_items.remove(note)
        if note in self.note_items:
            self.note_items.remove(note)

        self.scene_obj.removeItem(note)
        note.deleteLater()

    def clear_generated(self):
        for it in self.generated_items:
            self.scene_obj.removeItem(it)
            if it in self.note_items:
                self.note_items.remove(it)
        self.generated_items = []

    def add_generated_sequence(self, pitches):
        left = 40
        width = 760
        total_slots = self.measures * 4
        slot_w = width / total_slots

        start_slot = len(self.seed_items)

        parent_ui = cast("MarkovUI", self.parent())
        max_gen = min(len(pitches) - start_slot, parent_ui.order_box.currentIndex() + 1)

        for i in range(max_gen):
            p = pitches[start_slot + i]
            slot_idx = start_slot + i
            if slot_idx >= total_slots:
                break

            x = left + slot_idx * slot_w + slot_w/2
            y = - (p - BASE_PITCH) * SEMITONE_PX + 40

            note = NoteItem(p)
            note.setPos(QPointF(x, y))
            self.scene_obj.addItem(note)

            self.generated_items.append(note)
            self.note_items.append(note)

    def get_seed_pitches_items(self):
        return sorted(self.seed_items, key=lambda it: it.scenePos().x())

    def get_seed_pitches(self):
        items = sorted(self.seed_items, key=lambda it: it.scenePos().x())
        return [it.pitch for it in items]

    def total_seed_count(self):
        return len(self.seed_items)

    def all_pitches_sequence(self):
        items = sorted(self.note_items, key=lambda it: it.scenePos().x())
        return [it.pitch for it in items]

class MarkovUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Markov Music Generator - PyQt")
        self.resize(900, 600)

        main = QWidget()
        v = QVBoxLayout()
        main.setLayout(v)
        self.setCentralWidget(main)

        top_bar = QHBoxLayout()
        v.addLayout(top_bar)
        top_bar.addWidget(QLabel("Order:"))
        self.order_box = QComboBox()
        self.order_box.addItems(["1","2","3","4"])
        self.order_box.currentIndexChanged.connect(self._order_changed)
        top_bar.addWidget(self.order_box)

        top_bar.addWidget(QLabel("Measures:"))
        self.measures_spin = QSpinBox()
        self.measures_spin.setMinimum(2)
        self.measures_spin.setMaximum(8)
        self.measures_spin.setValue(4)
        self.measures_spin.valueChanged.connect(self._measures_changed)
        top_bar.addWidget(self.measures_spin)

        left_bar = QHBoxLayout()
        v.addLayout(left_bar)
        left_bar.addWidget(QLabel("Key:"))
        self.key_note = QComboBox()
        self.key_note.addItems(["C","D","E","F","G","A","B"])
        left_bar.addWidget(self.key_note)
        self.key_accidental = QComboBox()
        self.key_accidental.addItems(["","#","-"])
        left_bar.addWidget(self.key_accidental)
        self.key_quality = QComboBox()
        self.key_quality.addItems(["M","m"])
        left_bar.addWidget(self.key_quality)

        self.staff = StaffView(measures=self.measures_spin.value())
        v.addWidget(self.staff)

        bottom_bar = QHBoxLayout()
        v.addLayout(bottom_bar)
        self.generate_btn = QPushButton("Generate Melody")
        self.generate_btn.setEnabled(False)
        self.generate_btn.clicked.connect(self.on_generate)
        bottom_bar.addWidget(self.generate_btn)

        self.play_btn = QPushButton("Play Audio")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self.on_play)
        bottom_bar.addWidget(self.play_btn)

        self.reset_btn = QPushButton("Reset Generated")
        self.reset_btn.clicked.connect(self.on_reset)
        bottom_bar.addWidget(self.reset_btn)

        self.info_label = QLabel("Double-click on the staff to add seed notes. Drag notes to move them.")
        v.addWidget(self.info_label)

        self.generated = False

    def _order_changed(self):
        self._update_generate_button_state()

    def _measures_changed(self, val):
        self.staff.set_measures(val)
        self._update_generate_button_state()

    def _current_key_str(self):
        note = self.key_note.currentText()
        acc = self.key_accidental.currentText()
        qual = self.key_quality.currentText()
        k = note
        if acc == '#':
            k += '#'
        elif acc == '-':
            k += 'b'
        if qual == 'm':
            k += 'm'
        return k

    def _update_generate_button_state(self):
        order = int(self.order_box.currentText())
        seed_count = self.staff.total_seed_count()
        enabled = seed_count >= order
        self.generate_btn.setEnabled(enabled)

    def on_generate(self):
        try:
            order = int(self.order_box.currentText())
            seed_pitches = self.staff.get_seed_pitches()
            seed_pitches = []
            for it in self.staff.get_seed_pitches_items():
                seed_pitches.append(it.pitch)  # pitch con accidental
            seed = [f"NOTE_{p}" for p in seed_pitches]
            measures = int(self.measures_spin.value())
            key = self._current_key_str()
            key = key.replace('b', '')
            sequence = generate_sequence(order, seed, measures, key)
            pitches = [int(s.split('_')[1]) for s in sequence]
            self.staff.clear_generated()
            self.staff.add_generated_sequence(pitches)
            self.generated = True
            self.play_btn.setEnabled(True)
            QMessageBox.information(self, "Generated", "Melody generated and written to staff.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def on_play(self):
        if not self.generated:
            QMessageBox.warning(self, "No melody", "No generated melody to play.")
            return
        pitches = self.staff.all_pitches_sequence()
        play_from_pitches(pitches)

    def on_reset(self):
        self.staff.clear_generated()
        self.generated = False
        self.play_btn.setEnabled(False)

    def showEventer(self, a0: QShowEvent):
        super().showEvent(a0)
        self._update_generate_button_state()