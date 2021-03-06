# SPDX-License-Identifier: GPL-2.0-or-later
import struct

from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtWidgets import QLineEdit, QToolButton, QComboBox, QWidget, QSizePolicy

from flowlayout import FlowLayout
from keycodes import KEYCODES_BASIC, KEYCODES_ISO, KEYCODES_MEDIA
from util import tr


MACRO_SEQUENCE_KEYCODES = KEYCODES_BASIC + KEYCODES_ISO + KEYCODES_MEDIA
KC_A = MACRO_SEQUENCE_KEYCODES[0]

SS_QMK_PREFIX = 1

SS_TAP_CODE = 1
SS_DOWN_CODE = 2
SS_UP_CODE = 3
SS_DELAY_CODE = 4


class BasicAction(QObject):

    changed = pyqtSignal()

    def __init__(self, container):
        super().__init__()
        self.container = container


class ActionText(BasicAction):

    def __init__(self, container, text=""):
        super().__init__(container)
        self.text = QLineEdit()
        self.text.setText(text)
        self.text.textChanged.connect(self.on_change)

    def insert(self, row):
        self.container.addWidget(self.text, row, 2)

    def remove(self):
        self.container.removeWidget(self.text)

    def delete(self):
        self.text.deleteLater()

    def serialize(self, vial_protocol):
        return self.text.text().encode("utf-8")

    def on_change(self):
        self.changed.emit()


class ActionSequence(BasicAction):

    def __init__(self, container, sequence=None):
        super().__init__(container)
        if sequence is None:
            sequence = []
        self.sequence = sequence

        self.btn_plus = QToolButton()
        self.btn_plus.setText("+")
        self.btn_plus.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.btn_plus.clicked.connect(self.on_add)

        self.layout = FlowLayout()
        self.layout_container = QWidget()
        self.layout_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.layout_container.setLayout(self.layout)
        self.widgets = []
        self.recreate_sequence()

    def recreate_sequence(self):
        self.layout.removeWidget(self.btn_plus)
        for w in self.widgets:
            self.layout.removeWidget(w)
            w.deleteLater()
        self.widgets.clear()

        for item in self.sequence:
            w = QComboBox()
            w.view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            w.setStyleSheet("QComboBox { combobox-popup: 0; }")
            w.addItem(tr("MacroEditor", "Remove"))
            w.insertSeparator(1)
            for k in MACRO_SEQUENCE_KEYCODES:
                w.addItem(k.label.replace("\n", ""))
            w.setCurrentIndex(2 + MACRO_SEQUENCE_KEYCODES.index(item))
            w.currentIndexChanged.connect(self.on_change)
            self.layout.addWidget(w)
            self.widgets.append(w)
        self.layout.addWidget(self.btn_plus)

    def insert(self, row):
        self.container.addWidget(self.layout_container, row, 2)

    def remove(self):
        self.container.removeWidget(self.layout_container)

    def delete(self):
        for w in self.widgets:
            w.deleteLater()
        self.btn_plus.deleteLater()
        self.layout_container.deleteLater()

    def on_add(self):
        self.sequence.append(KC_A)
        self.recreate_sequence()
        self.changed.emit()

    def on_change(self):
        for x in range(len(self.sequence)):
            index = self.widgets[x].currentIndex()
            if index == 0:
                # asked to remove this item
                del self.sequence[x]
                self.recreate_sequence()
                break
            else:
                self.sequence[x] = MACRO_SEQUENCE_KEYCODES[self.widgets[x].currentIndex() - 2]
        self.changed.emit()

    def serialize_prefix(self):
        raise NotImplementedError

    def serialize(self, vial_protocol):
        if vial_protocol >= 2:
            out = b"\x01"
        else:
            out = b""
        for k in self.sequence:
            out += self.serialize_prefix()
            out += struct.pack("B", k.code)
        return out


class ActionDown(ActionSequence):

    def serialize_prefix(self):
        return b"\x02"


class ActionUp(ActionSequence):

    def serialize_prefix(self):
        return b"\x03"


class ActionTap(ActionSequence):

    def serialize_prefix(self):
        return b"\x01"


class ActionDelay(BasicAction):

    def __init__(self, container, delay=0):
        super().__init__(container)
        self.text = QLineEdit()
        self.text.setText(str(delay))
        self.text.textChanged.connect(self.on_change)

    def insert(self, row):
        self.container.addWidget(self.text, row, 2)

    def remove(self):
        self.container.removeWidget(self.text)

    def delete(self):
        self.text.deleteLater()

    def on_change(self):
        self.changed.emit()

    def serialize(self, vial_protocol):
        if vial_protocol < 2:
            raise RuntimeError("ActionDelay can only be used with vial_protocol>=2")
        delay = int(self.text.text())
        return struct.pack("BBBB", SS_QMK_PREFIX, SS_DELAY_CODE, (delay % 255) + 1, (delay // 255) + 1)
