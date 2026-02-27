# This is a sample Python script.

# Press Mayús+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

# /main.py
"""
HyperSpin INI GUI Editor (PyQt6)

Features
- Select HyperSpin "Settings" folder.
- Category dropdown:
  1) Hyperspin -> Global Settings.ini, Global Bezel.ini
  2) MainMenuChanger -> PC Games.ini, All.ini, Arcades.ini, Back.ini, Collections.ini, Consoles.ini, Handhelds.ini
  3) Sistemas X -> all other .ini files in folder (excluding the above)
- Second dropdown loads selected INI and renders editable controls per key:
  - bool: checkbox
  - int/float: spin boxes
  - 0xRRGGBB / 0xAARRGGBB: color picker + hex editor
  - fallback: text
- Save updates existing key lines in-place (preserving comments/unknown formatting as much as possible).

Run:
  python main.py
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStatusBar,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


_SECTION_RE = re.compile(r"^\s*\[(?P<section>[^\]]+)\]\s*$")
_KEYVAL_RE = re.compile(r"^(?P<prefix>\s*)(?P<key>[^=;\r\n]+?)\s*=\s*(?P<val>.*?)(?P<suffix>\s*)$")


def _norm_section(s: str) -> str:
    return s.strip()


def _norm_key(k: str) -> str:
    return k.strip()


def _is_bool_text(v: str) -> Optional[bool]:
    t = v.strip().lower()
    if t in {"true", "1", "yes", "on"}:
        return True
    if t in {"false", "0", "no", "off"}:
        return False
    return None


def _parse_int(v: str) -> Optional[int]:
    try:
        s = v.strip()
        if s.lower().startswith("0x"):
            return int(s, 16)
        return int(s, 10)
    except Exception:
        return None


def _parse_float(v: str) -> Optional[float]:
    try:
        return float(v.strip())
    except Exception:
        return None


_HEX_COLOR_RE = re.compile(r"^\s*0x(?P<hex>[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\s*$")


def _parse_hex_color(v: str) -> Optional[QColor]:
    m = _HEX_COLOR_RE.match(v)
    if not m:
        return None
    hx = m.group("hex")
    if len(hx) == 6:
        r = int(hx[0:2], 16)
        g = int(hx[2:4], 16)
        b = int(hx[4:6], 16)
        return QColor(r, g, b)
    a = int(hx[0:2], 16)
    r = int(hx[2:4], 16)
    g = int(hx[4:6], 16)
    b = int(hx[6:8], 16)
    c = QColor(r, g, b)
    c.setAlpha(a)
    return c


def _to_hex_color(c: QColor, keep_alpha: bool) -> str:
    if keep_alpha:
        return f"0x{c.alpha():02X}{c.red():02X}{c.green():02X}{c.blue():02X}"
    return f"0x{c.red():02X}{c.green():02X}{c.blue():02X}"


@dataclass
class IniValueRef:
    section: str
    key: str
    value: str
    line_index: int
    prefix: str
    suffix: str


class IniDocument:
    """
    Minimal INI editor that preserves file lines and updates key=value lines in place.

    Limitations
    - Assumes one key per line.
    - If duplicate keys exist in same section, last one wins (and will be edited).
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self.lines: List[str] = []
        self.refs: Dict[Tuple[str, str], IniValueRef] = {}
        self.section_order: List[str] = []
        self._loaded = False

    def load(self) -> None:
        if not os.path.isfile(self.path):
            raise FileNotFoundError(self.path)

        with open(self.path, "r", encoding="utf-8", errors="replace") as f:
            self.lines = f.read().splitlines(True)  # keep newlines

        self.refs.clear()
        self.section_order.clear()

        current_section = ""
        seen_sections = set()

        for idx, raw in enumerate(self.lines):
            sm = _SECTION_RE.match(raw)
            if sm:
                current_section = _norm_section(sm.group("section"))
                if current_section not in seen_sections:
                    self.section_order.append(current_section)
                    seen_sections.add(current_section)
                continue

            km = _KEYVAL_RE.match(raw)
            if not km:
                continue

            key = _norm_key(km.group("key"))
            val = km.group("val").rstrip("\r\n")
            prefix = km.group("prefix")
            suffix = km.group("suffix")
            s = _norm_section(current_section)

            self.refs[(s, key)] = IniValueRef(
                section=s,
                key=key,
                value=val,
                line_index=idx,
                prefix=prefix,
                suffix=suffix,
            )

        self._loaded = True

    def sections(self) -> List[str]:
        self._ensure_loaded()
        return list(self.section_order)

    def items(self, section: str) -> List[Tuple[str, str]]:
        self._ensure_loaded()
        s = _norm_section(section)
        out = [(k, ref.value) for (sec, k), ref in self.refs.items() if sec == s]
        out.sort(key=lambda kv: kv[0].lower())
        return out

    def all_items(self) -> List[IniValueRef]:
        self._ensure_loaded()
        refs = list(self.refs.values())
        refs.sort(key=lambda r: (r.section.lower(), r.key.lower()))
        return refs

    def get(self, section: str, key: str) -> Optional[str]:
        self._ensure_loaded()
        ref = self.refs.get((_norm_section(section), _norm_key(key)))
        return None if ref is None else ref.value

    def set(self, section: str, key: str, value: str) -> None:
        self._ensure_loaded()
        s = _norm_section(section)
        k = _norm_key(key)
        t = (s, k)
        if t in self.refs:
            ref = self.refs[t]
            ref.value = value
            newline = "\n" if self.lines[ref.line_index].endswith("\n") else ""
            self.lines[ref.line_index] = f"{ref.prefix}{ref.key}={value}{ref.suffix}{newline}"
            return

        # Add new key under section (append near end of section; simplest: append at file end if section not found)
        insert_at = len(self.lines)
        section_line_idx = self._find_section_line_index(s)
        if section_line_idx is not None:
            insert_at = self._find_section_end_index(section_line_idx + 1)

        line = f"{k}={value}\n"
        self.lines.insert(insert_at, line)
        self.refs[t] = IniValueRef(
            section=s, key=k, value=value, line_index=insert_at, prefix="", suffix=""
        )
        self._reindex_refs_from(insert_at)

        if s and s not in self.section_order:
            self.section_order.append(s)

    def save(self) -> None:
        self._ensure_loaded()
        with open(self.path, "w", encoding="utf-8", errors="replace") as f:
            f.writelines(self.lines)

    def _find_section_line_index(self, section: str) -> Optional[int]:
        want = _norm_section(section)
        current = ""
        for idx, raw in enumerate(self.lines):
            sm = _SECTION_RE.match(raw)
            if sm:
                current = _norm_section(sm.group("section"))
                if current == want:
                    return idx
        return None

    def _find_section_end_index(self, start_idx: int) -> int:
        for i in range(start_idx, len(self.lines)):
            if _SECTION_RE.match(self.lines[i]):
                return i
        return len(self.lines)

    def _reindex_refs_from(self, start_idx: int) -> None:
        # After insertion, shift any stored line indices >= start_idx
        for ref in self.refs.values():
            if ref.line_index >= start_idx and self.lines[ref.line_index] is not self.lines[start_idx]:
                pass
        # Safer: rebuild mapping of line_index by re-parsing (still preserves lines)
        # This is simpler and avoids tricky shifts.
        path = self.path
        self._loaded = False
        self.load()
        self.path = path

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()


class ColorEditor(QWidget):
    def __init__(self, initial_text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._keep_alpha = False
        self._color = QColor()

        m = _HEX_COLOR_RE.match(initial_text or "")
        if m:
            hx = m.group("hex")
            self._keep_alpha = len(hx) == 8
            c = _parse_hex_color(initial_text)
            if c is not None:
                self._color = c

        self.line = QLineEdit(initial_text)
        self.btn = QToolButton()
        self.btn.setText("🎨")
        self.btn.setToolTip("Elegir color")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.line, 1)
        layout.addWidget(self.btn)

        self.btn.clicked.connect(self._pick_color)

    def _pick_color(self) -> None:
        current = _parse_hex_color(self.line.text())
        if current is None:
            current = self._color if self._color.isValid() else QColor(0, 0, 0)

        dlg = QColorDialog(current, self)
        dlg.setOption(QColorDialog.ColorDialogOption.ShowAlphaChannel, True)
        if dlg.exec():
            c = dlg.currentColor()
            # If original had alpha, keep it; otherwise keep RGB unless user explicitly changed alpha.
            keep_alpha = self._keep_alpha or c.alpha() != 255
            self.line.setText(_to_hex_color(c, keep_alpha))

    def text(self) -> str:
        return self.line.text()


class IniEditorWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.doc: Optional[IniDocument] = None
        self._controls: Dict[Tuple[str, str], QWidget] = {}

        self.header = QLabel("Selecciona un INI para editar.")
        self.header.setWordWrap(True)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.form_host = QWidget()
        self.form = QFormLayout(self.form_host)
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.form_host)

        self.btn_reload = QPushButton("Recargar")
        self.btn_save = QPushButton("Guardar")
        self.btn_save.setEnabled(False)
        self.btn_reload.setEnabled(False)

        btns = QHBoxLayout()
        btns.addWidget(self.btn_reload)
        btns.addWidget(self.btn_save)
        btns.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.header)
        layout.addWidget(self.scroll, 1)
        layout.addLayout(btns)

        self.btn_reload.clicked.connect(self.reload)
        self.btn_save.clicked.connect(self.save)

    def set_document(self, doc: Optional[IniDocument]) -> None:
        self.doc = doc
        self._controls.clear()
        self._clear_form()

        if doc is None:
            self.header.setText("Selecciona un INI para editar.")
            self.btn_save.setEnabled(False)
            self.btn_reload.setEnabled(False)
            return

        self.header.setText(f"Editando: {os.path.basename(doc.path)}")
        self.btn_save.setEnabled(True)
        self.btn_reload.setEnabled(True)

        for ref in doc.all_items():
            self._add_control(ref.section, ref.key, ref.value)

    def reload(self) -> None:
        if not self.doc:
            return
        try:
            self.doc.load()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo recargar:\n{e}")
            return
        self.set_document(self.doc)

    def save(self) -> None:
        if not self.doc:
            return
        try:
            self._apply_controls_to_doc()
            self.doc.save()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{e}")
            return
        QMessageBox.information(self, "OK", "Guardado correctamente.")

    def _clear_form(self) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)

    def _add_section_divider(self, title: str) -> None:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        lbl = QLabel(f"[{title}]")
        lbl.setStyleSheet("font-weight: 600;")
        self.form.addRow(lbl, line)

    def _add_control(self, section: str, key: str, value: str) -> None:
        if not self._controls or (section, "") not in self._controls:
            # add divider for each new section (in sorted iteration, section changes)
            pass

        # Add divider when first key of a section is seen
        if (section, "") not in self._controls:
            self._controls[(section, "")] = QLabel("")  # marker
            self._add_section_divider(section if section else "GLOBAL")

        widget: QWidget

        b = _is_bool_text(value)
        if b is not None:
            cb = QCheckBox()
            cb.setChecked(b)
            widget = cb
        else:
            color = _parse_hex_color(value)
            if color is not None:
                widget = ColorEditor(value)
            else:
                iv = _parse_int(value)
                fv = _parse_float(value)

                if iv is not None and (value.strip().lower().startswith("0x") or re.fullmatch(r"\s*-?\d+\s*", value)):
                    sp = QSpinBox()
                    sp.setRange(-2_147_483_648, 2_147_483_647)
                    sp.setValue(iv)
                    widget = sp
                elif fv is not None and re.fullmatch(r"\s*-?\d+(\.\d+)?\s*", value):
                    dsp = QDoubleSpinBox()
                    dsp.setDecimals(6)
                    dsp.setRange(-1e12, 1e12)
                    dsp.setValue(fv)
                    widget = dsp
                else:
                    le = QLineEdit(value)
                    widget = le

        widget.setProperty("ini_section", section)
        widget.setProperty("ini_key", key)

        self._controls[(section, key)] = widget
        self.form.addRow(QLabel(key), widget)

    def _apply_controls_to_doc(self) -> None:
        assert self.doc is not None
        for (section, key), w in self._controls.items():
            if key == "":
                continue

            if isinstance(w, QCheckBox):
                new_val = "true" if w.isChecked() else "false"
            elif isinstance(w, QSpinBox):
                new_val = str(w.value())
            elif isinstance(w, QDoubleSpinBox):
                # Keep compact formatting, similar to INI conventions
                v = w.value()
                new_val = str(int(v)) if abs(v - int(v)) < 1e-12 else f"{v:.6f}".rstrip("0").rstrip(".")
            elif isinstance(w, ColorEditor):
                new_val = w.text().strip()
            elif isinstance(w, QLineEdit):
                new_val = w.text()
            else:
                continue

            self.doc.set(section, key, new_val)


class HyperSpinTab(QWidget):
    HYPERSPIN_FILES = ["Global Settings.ini", "Global Bezel.ini"]
    MAINMENUCHANGER_FILES = [
        "PC Games.ini",
        "All.ini",
        "Arcades.ini",
        "Back.ini",
        "Collections.ini",
        "Consoles.ini",
        "Handhelds.ini",
    ]

    def __init__(self, status: QStatusBar, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.status = status

        self.settings_path = QLineEdit()
        self.btn_browse = QPushButton("Buscar…")

        self.category = QComboBox()
        self.category.addItems(["Hyperspin", "MainMenuChanger", "Sistemas X"])

        self.file_combo = QComboBox()
        self.system_combo = QComboBox()
        self.system_combo.setVisible(False)

        self.editor = IniEditorWidget()

        top = QHBoxLayout()
        top.addWidget(QLabel("Carpeta Settings:"))
        top.addWidget(self.settings_path, 1)
        top.addWidget(self.btn_browse)

        mid = QHBoxLayout()
        mid.addWidget(QLabel("Tipo:"))
        mid.addWidget(self.category)
        mid.addSpacing(10)
        mid.addWidget(QLabel("INI:"))
        mid.addWidget(self.file_combo, 1)
        mid.addSpacing(10)
        mid.addWidget(QLabel("Sistema:"))
        mid.addWidget(self.system_combo, 1)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addLayout(mid)
        layout.addWidget(self.editor, 1)

        self.btn_browse.clicked.connect(self._browse_folder)
        self.category.currentIndexChanged.connect(self._refresh_lists)
        self.file_combo.currentIndexChanged.connect(self._load_selected_ini)
        self.system_combo.currentIndexChanged.connect(self._load_selected_ini)

        self._refresh_lists()

    def _browse_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Selecciona carpeta Settings")
        if not path:
            return
        self.settings_path.setText(path)
        self._refresh_lists()

    def _list_ini_files(self) -> List[str]:
        folder = self.settings_path.text().strip()
        if not folder or not os.path.isdir(folder):
            return []
        files = []
        for name in os.listdir(folder):
            if name.lower().endswith(".ini") and os.path.isfile(os.path.join(folder, name)):
                files.append(name)
        files.sort(key=lambda s: s.lower())
        return files

    def _refresh_lists(self) -> None:
        category = self.category.currentText()
        all_inis = self._list_ini_files()

        self.file_combo.blockSignals(True)
        self.system_combo.blockSignals(True)
        self.file_combo.clear()
        self.system_combo.clear()

        if category == "Hyperspin":
            self.system_combo.setVisible(False)
            for f in self.HYPERSPIN_FILES:
                if f in all_inis:
                    self.file_combo.addItem(f)
            if self.file_combo.count() == 0:
                for f in self.HYPERSPIN_FILES:
                    self.file_combo.addItem(f)

        elif category == "MainMenuChanger":
            self.system_combo.setVisible(False)
            for f in self.MAINMENUCHANGER_FILES:
                if f in all_inis:
                    self.file_combo.addItem(f)
            if self.file_combo.count() == 0:
                for f in self.MAINMENUCHANGER_FILES:
                    self.file_combo.addItem(f)

        else:  # Sistemas X
            self.system_combo.setVisible(True)
            exclude = {*(self.HYPERSPIN_FILES), *(self.MAINMENUCHANGER_FILES)}
            systems = [f for f in all_inis if f not in exclude]
            if not systems:
                systems = [f for f in all_inis if f not in exclude]  # stays empty if none
            self.file_combo.addItem("Sistemas X")
            for f in systems:
                self.system_combo.addItem(f)

        self.file_combo.blockSignals(False)
        self.system_combo.blockSignals(False)
        self._load_selected_ini()

    def _selected_ini_path(self) -> Optional[str]:
        folder = self.settings_path.text().strip()
        if not folder or not os.path.isdir(folder):
            return None

        category = self.category.currentText()
        if category == "Sistemas X":
            name = self.system_combo.currentText().strip()
            if not name:
                return None
            return os.path.join(folder, name)

        name = self.file_combo.currentText().strip()
        if not name:
            return None
        return os.path.join(folder, name)

    def _load_selected_ini(self) -> None:
        path = self._selected_ini_path()
        if not path:
            self.editor.set_document(None)
            self.status.showMessage("Selecciona una carpeta Settings válida.", 3000)
            return

        if not os.path.isfile(path):
            self.editor.set_document(None)
            self.status.showMessage(f"No existe: {os.path.basename(path)}", 4000)
            return

        try:
            doc = IniDocument(path)
            doc.load()
        except Exception as e:
            self.editor.set_document(None)
            QMessageBox.critical(self, "Error", f"No se pudo abrir:\n{path}\n\n{e}")
            return

        self.editor.set_document(doc)
        self.status.showMessage(f"Cargado: {os.path.basename(path)}", 2500)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("HyperSpin Settings Editor (PyQt6)")
        self.resize(1100, 750)

        self.status = QStatusBar()
        self.setStatusBar(self.status)

        tabs = QTabWidget()
        tabs.addTab(HyperSpinTab(self.status), "HYPERSPIN")
        self.setCentralWidget(tabs)


def main() -> int:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())