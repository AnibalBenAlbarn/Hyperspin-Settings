import sys
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Tuple

from PyQt6 import QtWidgets, QtCore, QtGui

SETTINGS_FILE = "settings.json"


# -----------------------
# Utilities
# -----------------------
def sanitize_filename(name: str) -> str:
    if not name:
        return ""
    # Windows invalid chars + control chars
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name).strip()


def extract_xml_node_text(xml_path: Path, node_name: str) -> Optional[str]:
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        # Try direct find first
        el = root.find(f".//{node_name}")
        if el is None:
            # case-insensitive fallback
            for n in root.iter():
                tag = getattr(n, "tag", "")
                if isinstance(tag, str) and tag.lower().endswith(node_name.lower()):
                    el = n
                    break
        if el is not None and el.text:
            return el.text.strip()
    except Exception:
        pass
    return None


def extract_gamename_internal(xml_path: Path) -> str:
    name = extract_xml_node_text(xml_path, "GameNameInternal")
    return name if name else xml_path.stem


def extract_gamepath(xml_path: Path) -> Optional[str]:
    return extract_xml_node_text(xml_path, "GamePath")


def norm_path_for_match(p: Optional[str]) -> str:
    if not p:
        return ""
    # Normalize separators and lower-case for comparison
    return p.replace("/", "\\").lower()


# -----------------------
# Static categories mapping (display text, list of path prefixes to match)
# The display list will include indentation for subcategories for visual hierarchy.
# -----------------------
def build_static_categories() -> List[Tuple[str, List[str]]]:
    # Base root used in all examples (this is used as the fragment to match; can be any drive)
    ROOT = r"e:\arcade\2-roms"
    # We'll match using lowercase normalized strings
    cats = []

    # All
    cats.append(("Todas", []))  # empty prefixes => show all

    # LIGHTGUN parent (matches anything under LIGHTGUN GAMES)
    cats.append(("LIGHTGUN", [str(Path(ROOT) / "lightgun games").lower()]))

    # LIGHTGUN subcategories (indented items)
    cats.append(("    Arcade Moderno", [str(Path(ROOT) / "lightgun games" / "arcade moderno").lower()]))
    cats.append(("    Namco System 357-369", [str(Path(ROOT) / "lightgun games" / "arcade" / "namco system 357-369").lower()]))
    cats.append(("    Namco System 246-256", [str(Path(ROOT) / "lightgun games" / "arcade" / "namco system 246-256").lower()]))

    # Other main categories (1-PLACAS ARCADE variants)
    cats.append(("Namco System 246-256", [str(Path(ROOT) / "1-placas arcade" / "Namco System 246-256").lower()]))
    cats.append(("Namco System 357-369", [str(Path(ROOT) / "1-placas arcade" / "Namco System 357-369").lower()]))
    cats.append(("Sega Triforce", [str(Path(ROOT) / "1-placas arcade" / "Sega Triforce").lower()]))
    cats.append(("Teknoparrot", [str(Path(ROOT) / "1-placas arcade" / "TEKNOPARROT").lower()]))

    return cats


# -----------------------
# Profile model
# -----------------------
class ProfileItem:
    def __init__(self, xml_path: Path):
        self.xml_path = xml_path
        self.name = extract_gamename_internal(xml_path)
        self.gamepath = extract_gamepath(xml_path) or ""
        self.gamepath_norm = norm_path_for_match(self.gamepath)
        self.category = ""  # will be filled later based on static categories


# -----------------------
# Main window
# -----------------------
class TeknoManager(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TeknoParrot Manager")
        self.resize(1024, 700)

        # State
        self.profiles: List[ProfileItem] = []
        self.categories = build_static_categories()  # list of (display_text, [prefixes])
        self.settings = {
            "exe": "",
            "userprofiles": "",
            "output": "",
            "start_minimized": True,
            "extra_args": "",
            "last_category": "Todas",
            "last_ini": ""
        }

        # UI build
        self._build_ui()

        # Load settings and initial refresh if possible
        self.load_settings()
        if self.settings.get("userprofiles"):
            self.refresh_profiles()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Top form (paths)
        form = QtWidgets.QFormLayout()
        self.exe_line = QtWidgets.QLineEdit()
        btn_exe = QtWidgets.QPushButton("Examinar...")
        btn_exe.clicked.connect(self.browse_exe)
        he = QtWidgets.QHBoxLayout()
        he.addWidget(self.exe_line)
        he.addWidget(btn_exe)
        form.addRow("TeknoParrotUi.exe:", he)

        self.up_line = QtWidgets.QLineEdit()
        btn_up = QtWidgets.QPushButton("Examinar...")
        btn_up.clicked.connect(self.browse_userprofiles)
        hu = QtWidgets.QHBoxLayout()
        hu.addWidget(self.up_line)
        hu.addWidget(btn_up)
        form.addRow("UserProfiles folder:", hu)

        self.out_line = QtWidgets.QLineEdit()
        btn_out = QtWidgets.QPushButton("Examinar...")
        btn_out.clicked.connect(self.browse_output)
        ho = QtWidgets.QHBoxLayout()
        ho.addWidget(self.out_line)
        ho.addWidget(btn_out)
        form.addRow("Output folder (.bat):", ho)

        layout.addLayout(form)

        # Options
        opts = QtWidgets.QHBoxLayout()
        self.start_min_cb = QtWidgets.QCheckBox("Start minimized (--startMinimized)")
        self.start_min_cb.setChecked(True)
        opts.addWidget(self.start_min_cb)
        opts.addStretch()
        self.extra_args_line = QtWidgets.QLineEdit()
        self.extra_args_line.setPlaceholderText("Extra args (e.g. --emuonly)")
        opts.addWidget(QtWidgets.QLabel("Extra args:"))
        opts.addWidget(self.extra_args_line)
        layout.addLayout(opts)

        # Category combo + refresh
        ch = QtWidgets.QHBoxLayout()
        ch.addWidget(QtWidgets.QLabel("Filter by category:"))
        self.category_combo = QtWidgets.QComboBox()
        ch.addWidget(self.category_combo)
        ch.addStretch()
        btn_refresh = QtWidgets.QPushButton("Refresh Profiles")
        btn_refresh.clicked.connect(self.refresh_profiles)
        ch.addWidget(btn_refresh)
        self.count_label = QtWidgets.QLabel("Profiles: 0")
        ch.addWidget(self.count_label)
        layout.addLayout(ch)

        # Adjust combo box contents (fill)
        self._populate_category_combo()

        # Table
        self.table = QtWidgets.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name", "Category", "GamePath", "XML Path", "Actions"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 1)

        # Buttons row
        br = QtWidgets.QHBoxLayout()
        btn_play = QtWidgets.QPushButton("Play Selected")
        btn_play.clicked.connect(self.play_selected)
        br.addWidget(btn_play)

        btn_bat_sel = QtWidgets.QPushButton("Create .bat for Selected")
        btn_bat_sel.clicked.connect(self.create_bat_for_selected)
        br.addWidget(btn_bat_sel)

        btn_bat_vis = QtWidgets.QPushButton("Create .bat for Visible (filtered)")
        btn_bat_vis.clicked.connect(self.create_bat_for_visible)
        br.addWidget(btn_bat_vis)

        # NEW buttons: listado TXT and modify INI
        btn_listado = QtWidgets.QPushButton("Generar listado TXT")
        btn_listado.clicked.connect(self.generate_listado_txt)
        br.addWidget(btn_listado)

        btn_mod_ini = QtWidgets.QPushButton("Modificar módulo INI")
        btn_mod_ini.clicked.connect(self.modify_ini_module)
        br.addWidget(btn_mod_ini)

        br.addStretch()
        layout.addLayout(br)

        # Log
        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log, 1)

        # Connect combo change
        self.category_combo.currentIndexChanged.connect(self.on_category_changed)

    # -----------------------
    # Category combo helpers
    # -----------------------
    def _populate_category_combo(self):
        self.category_combo.clear()
        # Fill with display text in order defined in categories list
        for display, _prefixes in self.categories:
            self.category_combo.addItem(display)
        # Adjust drop-down width to longest item
        fm = self.category_combo.fontMetrics()
        maxw = 0
        for i in range(self.category_combo.count()):
            txt = self.category_combo.itemText(i)
            w = fm.horizontalAdvance(txt)
            if w > maxw:
                maxw = w
        # add some padding
        try:
            self.category_combo.view().setMinimumWidth(maxw + 60)
        except Exception:
            pass

    def _category_prefixes_for_index(self, index: int) -> List[str]:
        if index < 0 or index >= len(self.categories):
            return []
        return self.categories[index][1]

    def on_category_changed(self, idx: int):
        # Save last selected category in settings
        self.settings["last_category"] = self.category_combo.currentText()
        self.save_settings()
        self.populate_table()

    # -----------------------
    # Settings JSON
    # -----------------------
    def save_settings(self):
        try:
            self.settings.update({
                "exe": self.exe_line.text().strip(),
                "userprofiles": self.up_line.text().strip(),
                "output": self.out_line.text().strip(),
                "start_minimized": bool(self.start_min_cb.isChecked()),
                "extra_args": self.extra_args_line.text().strip(),
                "last_category": self.category_combo.currentText() if self.category_combo.count() > 0 else self.settings.get("last_category", "Todas")
            })
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
            self.log_msg("Settings saved to", SETTINGS_FILE)
        except Exception as e:
            self.log_msg("Error saving settings:", e)

    def load_settings(self):
        if Path(SETTINGS_FILE).exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Merge with defaults
                self.settings.update(data)
            except Exception:
                pass
        # Apply to UI
        self.exe_line.setText(self.settings.get("exe", ""))
        self.up_line.setText(self.settings.get("userprofiles", ""))
        self.out_line.setText(self.settings.get("output", ""))
        self.start_min_cb.setChecked(self.settings.get("start_minimized", True))
        self.extra_args_line.setText(self.settings.get("extra_args", ""))
        # set last category if present
        last = self.settings.get("last_category", "Todas")
        # try to set after combo filled
        # find index by text
        idx = self.category_combo.findText(last)
        if idx != -1:
            self.category_combo.setCurrentIndex(idx)

    # -----------------------
    # Browsers
    # -----------------------
    def browse_exe(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select TeknoParrotUi.exe", str(Path.home()), "Executables (*.exe);;All files (*)")
        if path:
            self.exe_line.setText(path)
            self.save_settings()

    def browse_userprofiles(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select UserProfiles folder", str(Path.home()))
        if path:
            self.up_line.setText(path)
            self.save_settings()
            self.refresh_profiles()

    def browse_output(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select output folder for .bat files", str(Path.home()))
        if path:
            self.out_line.setText(path)
            self.save_settings()

    # -----------------------
    # Logging
    # -----------------------
    def log_msg(self, *parts):
        text = " ".join(str(p) for p in parts)
        self.log.append(text)
        print(text)

    # -----------------------
    # Profiles scanning & categorization (static)
    # -----------------------
    def refresh_profiles(self):
        up = self.up_line.text().strip()
        if not up:
            QtWidgets.QMessageBox.warning(self, "UserProfiles missing", "Please set the UserProfiles folder first.")
            return
        p = Path(up)
        if not p.exists() or not p.is_dir():
            QtWidgets.QMessageBox.critical(self, "Invalid folder", f"UserProfiles folder does not exist:\n{up}")
            return

        xml_files = sorted(p.glob("*.xml"))
        self.profiles = [ProfileItem(x) for x in xml_files]

        # Assign categories based on static prefixes. If multiple prefixes match, prefer the longest match (more specific).
        for prof in self.profiles:
            prof.category = "Sin categoría"
            best_prefix = ""
            for display_text, prefixes in self.categories:
                for pref in prefixes:
                    # match: if prof.gamepath_norm contains prefix
                    if pref and pref in prof.gamepath_norm:
                        # prefer longer (more specific) prefix
                        if len(pref) > len(best_prefix):
                            best_prefix = pref
                            # map display_text trimmed (remove indentation)
                            prof.category = display_text.strip()
            # If nothing matched, category remains "Sin categoría"

        self.log_msg(f"Found {len(self.profiles)} profiles")
        self.count_label.setText(f"Profiles: {len(self.profiles)}")
        self.populate_table()
        self.save_settings()

    # -----------------------
    # Table population based on selected category filter
    # -----------------------
    def populate_table(self):
        self.table.setRowCount(0)
        current_idx = self.category_combo.currentIndex()
        prefixes = self._category_prefixes_for_index(current_idx)
        # If prefixes empty and selected is "Todas", show all
        # If prefixes non-empty, we show profiles whose normalized gamepath contains any of these prefixes.
        visible = []
        if not prefixes:
            # "Todas" or category with no prefixes: show all
            visible = self.profiles[:]
        else:
            # match any prefix
            for prof in self.profiles:
                for pref in prefixes:
                    if pref in prof.gamepath_norm:
                        visible.append(prof)
                        break

        # Also handle the parent LIGHTGUN case: if user selected "LIGHTGUN" item, we used prefix lightgun games,
        # that will match everything under it (including subcategories) — that's intended.

        # Fill table
        self._visible_profiles = visible
        for i, prof in enumerate(visible):
            self.table.insertRow(i)
            name_it = QtWidgets.QTableWidgetItem(prof.name)
            name_it.setFlags(name_it.flags() ^ QtCore.Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 0, name_it)

            cat = prof.category or ""
            cat_it = QtWidgets.QTableWidgetItem(cat)
            cat_it.setFlags(cat_it.flags() ^ QtCore.Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 1, cat_it)

            gp_it = QtWidgets.QTableWidgetItem(prof.gamepath)
            gp_it.setFlags(gp_it.flags() ^ QtCore.Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 2, gp_it)

            xp_it = QtWidgets.QTableWidgetItem(str(prof.xml_path))
            xp_it.setFlags(xp_it.flags() ^ QtCore.Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 3, xp_it)

            # Actions (Play, Create .bat)
            w = QtWidgets.QWidget()
            h = QtWidgets.QHBoxLayout()
            h.setContentsMargins(0, 0, 0, 0)
            btn_play = QtWidgets.QPushButton("Play")
            btn_play.clicked.connect(lambda _, row=i: self._play_by_row(row))
            btn_bat = QtWidgets.QPushButton("Create .bat")
            btn_bat.clicked.connect(lambda _, row=i: self._create_bat_by_row(row))
            h.addWidget(btn_play)
            h.addWidget(btn_bat)
            h.addStretch()
            w.setLayout(h)
            self.table.setCellWidget(i, 4, w)

    def _visible_profile_for_row(self, row: int) -> Optional[ProfileItem]:
        try:
            return self._visible_profiles[row]
        except Exception:
            return None

    # -----------------------
    # Play functions
    # -----------------------
    def _play_by_row(self, row: int):
        prof = self._visible_profile_for_row(row)
        if prof:
            self._launch_profile(prof)

    def play_selected(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            QtWidgets.QMessageBox.warning(self, "No selection", "Select at least one profile to play.")
            return
        prof = self._visible_profile_for_row(sel[0].row())
        if prof:
            self._launch_profile(prof)

    def _launch_profile(self, prof: ProfileItem):
        exe = self.exe_line.text().strip()
        if not exe:
            QtWidgets.QMessageBox.warning(self, "Exe missing", "Please select TeknoParrotUi.exe first.")
            return
        if not Path(exe).exists():
            QtWidgets.QMessageBox.critical(self, "Exe not found", exe)
            return
        args = [str(exe)]
        if self.start_min_cb.isChecked():
            args.append("--startMinimized")
        args.append(f"--profile={str(prof.xml_path)}")
        extra = self.extra_args_line.text().strip()
        if extra:
            args.extend(extra.split())
        self.log_msg("Launching:", " ".join(args))
        try:
            subprocess.Popen(args, shell=False)
            self.log_msg("Launched.")
            self.save_settings()
        except Exception as e:
            self.log_msg("Error launching:", e)
            QtWidgets.QMessageBox.critical(self, "Launch error", str(e))

    # -----------------------
    # Create .bat functions
    # -----------------------
    def _bat_content_for_profile(self, prof: ProfileItem) -> str:
        exe = self.exe_line.text().strip()
        extra = self.extra_args_line.text().strip()
        start_flag = "--startMinimized" if self.start_min_cb.isChecked() else ""
        if exe and Path(exe).is_absolute():
            tp_dir = Path(exe).parent
            exe_name = Path(exe).name
            content = (
                f'@echo off\r\n'
                f'REM TeknoParrot launcher for profile: {prof.name}\r\n'
                f'cd /d "{tp_dir}"\r\n'
                f'start "" "{exe_name}" {start_flag} --profile="{prof.xml_path}" {extra}\r\n'
                f'exit\r\n'
            )
        else:
            exe_to_use = exe if exe else "TeknoParrotUi.exe"
            content = (
                f'@echo off\r\n'
                f'REM TeknoParrot launcher for profile: {prof.name}\r\n'
                f'start "" "{exe_to_use}" {start_flag} --profile="{prof.xml_path}" {extra}\r\n'
                f'exit\r\n'
            )
        return content

    def _write_bat_for_profile(self, prof: ProfileItem, out_dir: Path) -> Optional[Path]:
        try:
            name = sanitize_filename(prof.name) or prof.xml_path.stem
            out_dir.mkdir(parents=True, exist_ok=True)
            bat_path = out_dir / f"{name}.bat"
            bat_path.write_text(self._bat_content_for_profile(prof), encoding="utf-8")
            # NOTE: removed .cmd generation - only .bat is created now
            return bat_path
        except Exception as e:
            self.log_msg("Error writing bat for", prof.name, ":", e)
            return None

    def _create_bat_by_row(self, row: int):
        prof = self._visible_profile_for_row(row)
        if not prof:
            return
        out = self.out_line.text().strip()
        if not out:
            QtWidgets.QMessageBox.warning(self, "Output missing", "Select output folder first.")
            return
        path = self._write_bat_for_profile(prof, Path(out))
        if path:
            self.log_msg("Created:", path)
            QtWidgets.QMessageBox.information(self, "Created", f"Created .bat:\n{path}")
            self.save_settings()

    def create_bat_for_selected(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            QtWidgets.QMessageBox.warning(self, "No selection", "Select one or more profiles first.")
            return
        out = self.out_line.text().strip()
        if not out:
            QtWidgets.QMessageBox.warning(self, "Output missing", "Select output folder first.")
            return
        out_dir = Path(out)
        created = 0
        for s in sel:
            prof = self._visible_profile_for_row(s.row())
            if prof:
                p = self._write_bat_for_profile(prof, out_dir)
                if p:
                    created += 1
        self.log_msg(f"Created {created} .bat files in {out_dir}")
        QtWidgets.QMessageBox.information(self, "Done", f"Created {created} .bat files in:\n{out_dir}")
        self.save_settings()

    def create_bat_for_visible(self):
        out = self.out_line.text().strip()
        if not out:
            QtWidgets.QMessageBox.warning(self, "Output missing", "Select output folder first.")
            return
        out_dir = Path(out)
        created = 0
        for prof in getattr(self, "_visible_profiles", []):
            p = self._write_bat_for_profile(prof, out_dir)
            if p:
                created += 1
        self.log_msg(f"Created {created} .bat files for visible profiles in {out_dir}")
        QtWidgets.QMessageBox.information(self, "Done", f"Created {created} .bat files in:\n{out_dir}")
        self.save_settings()

    # -----------------------
    # New: generate listing TXT
    # -----------------------
    def generate_listado_txt(self):
        out, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Guardar listado",
            str(Path.home() / "listado_teknoparrot.txt"),
            "Text files (*.txt);;All files (*)"
        )

        if not out:
            return

        try:
            lines = []
            for prof in self.profiles:
                left = prof.name.strip()
                right = prof.xml_path.stem.strip()
                lines.append(f"{left} = {right}")

            Path(out).write_text("\n".join(lines), encoding="utf-8")

            self.log_msg("Listado creado:", out)
            QtWidgets.QMessageBox.information(self, "Correcto", f"Listado generado:\n{out}")

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))
            self.log_msg("Error creando listado:", e)

    # -----------------------
    # New: modify INI module for a whole system
    # -----------------------
    def modify_ini_module(self):
        # Selección de INI (si hay last_ini lo proponemos como carpeta inicial)
        start_dir = str(Path(self.settings.get("last_ini", "")) if self.settings.get("last_ini") else Path.home())
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo INI",
            start_dir,
            "INI files (*.ini);;All files (*)"
        )
        if not path:
            return

        ini_path = Path(path)
        # Guardar ruta en settings para recordarlo
        self.settings["last_ini"] = str(ini_path)
        self.save_settings()

        try:
            import configparser
            config = configparser.ConfigParser()
            config.optionxform = str  # preserve case
            config.read(ini_path, encoding="utf-8")

            # Create dialog
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle(f"Editar módulo: {ini_path.name}")
            dlg_layout = QtWidgets.QVBoxLayout(dialog)

            edits = {}  # (section, key) -> QLineEdit

            # Mostrar secciones y claves existentes para editar
            for section in config.sections():
                section_label = QtWidgets.QLabel(f"[{section}]")
                section_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
                dlg_layout.addWidget(section_label)

                for key, value in config[section].items():
                    h = QtWidgets.QHBoxLayout()
                    lbl = QtWidgets.QLabel(key)
                    lbl.setFixedWidth(120)
                    edt = QtWidgets.QLineEdit(value)
                    edits[(section, key)] = edt
                    h.addWidget(lbl)
                    h.addWidget(edt)
                    dlg_layout.addLayout(h)

            # Checkbox para elegir si volcar solo visibles o todas
            chk_only_visible = QtWidgets.QCheckBox("Volcar solo perfiles visibles (filtrados por categoría)")
            chk_only_visible.setChecked(True)
            dlg_layout.addWidget(chk_only_visible)

            # Botones: Guardar, Volcar listados, Cancelar
            btns = QtWidgets.QHBoxLayout()
            bsave = QtWidgets.QPushButton("Guardar cambios")
            bdump = QtWidgets.QPushButton("Volcar listados (profiles -> ini)")
            bcancel = QtWidgets.QPushButton("Cancelar")
            btns.addWidget(bsave)
            btns.addWidget(bdump)
            btns.addWidget(bcancel)
            dlg_layout.addLayout(btns)

            def save_changes():
                # Update config with edited values
                for (sec, key), widget in edits.items():
                    if not config.has_section(sec):
                        config.add_section(sec)
                    config[sec][key] = widget.text()
                with open(ini_path, "w", encoding="utf-8") as f:
                    config.write(f)
                self.log_msg("INI actualizado:", ini_path)
                QtWidgets.QMessageBox.information(self, "Guardado", "El módulo fue modificado correctamente.")
                dialog.accept()

            def dump_listings_to_ini():
                """
                Volcar perfiles en el ini siguiendo la estructura:
                [SectionName]
                ShortName=...
                FadeTitle=...
                CommandLine=...
                GamePath=...
                Solo se volcarán los perfiles visibles si chk_only_visible está marcado,
                en caso contrario se volcarán todos los perfiles cargados en self.profiles.
                """
                # Recargar config actual antes de modificar (por si se editó)
                config.read(ini_path, encoding="utf-8")

                # Seleccionar lista a volcar: visibles si existe self._visible_profiles y checkbox marcado
                if chk_only_visible.isChecked():
                    profiles_to_dump = getattr(self, "_visible_profiles", [])[:]  # copia para seguridad
                else:
                    profiles_to_dump = self.profiles[:]

                # Si no hay perfiles visibles y se pidió solo visibles, avisar y salir
                if chk_only_visible.isChecked() and not profiles_to_dump:
                    QtWidgets.QMessageBox.warning(self, "Sin perfiles visibles",
                                                  "No hay perfiles visibles para volcar. Cambia la categoría o desmarca la opción.")
                    return

                # For each profile, add/replace a section named exactamente como prof.name (o sanitized)
                for prof in profiles_to_dump:
                    section_name = prof.name or prof.xml_path.stem
                    section_name = section_name.replace("\n", " ").strip()

                    if not config.has_section(section_name):
                        config.add_section(section_name)

                    shortname = prof.xml_path.stem
                    extra = self.extra_args_line.text().strip()
                    start_flag = "--startMinimized" if self.start_min_cb.isChecked() else ""
                    exe_name = Path(
                        self.exe_line.text().strip()).name if self.exe_line.text().strip() else "TeknoParrotUi.exe"

                    # Puedes ajustar la plantilla FadeTitle aquí si quieres otro formato
                    fade_title = f"Play! - [ {shortname} ] - TeknoParrot"

                    cmd_parts = [exe_name]
                    if start_flag:
                        cmd_parts.append(start_flag)
                    cmd_parts.append(f'--profile="{prof.xml_path}"')
                    if extra:
                        cmd_parts.extend(extra.split())
                    command_line = " ".join(cmd_parts)

                    config[section_name]["ShortName"] = shortname
                    config[section_name]["FadeTitle"] = fade_title
                    config[section_name]["CommandLine"] = command_line
                    if prof.gamepath:
                        config[section_name]["GamePath"] = prof.gamepath
                    else:
                        if "GamePath" in config[section_name]:
                            del config[section_name]["GamePath"]

                # Finalmente escribimos el INI
                with open(ini_path, "w", encoding="utf-8") as f:
                    config.write(f)

                self.log_msg(f"Volcados {len(profiles_to_dump)} perfiles en {ini_path}")
                QtWidgets.QMessageBox.information(self, "Volcado completado",
                                                  f"Volcados {len(profiles_to_dump)} perfiles en:\n{ini_path}")
                dialog.accept()

            bsave.clicked.connect(save_changes)
            bdump.clicked.connect(dump_listings_to_ini)
            bcancel.clicked.connect(dialog.reject)

            dialog.exec()

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))
            self.log_msg("Error modificando INI:", e)


# -----------------------
# Main
# -----------------------
def main():
    app = QtWidgets.QApplication(sys.argv)
    win = TeknoManager()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()