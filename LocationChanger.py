import os
import json
import xml.etree.ElementTree as ET
import psutil
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QTextEdit,
    QProgressDialog,
)
from PyQt6.QtCore import Qt

"""
This module provides a small utility for maintaining configuration files used
with arcade front‑ends. Originally the tool was designed only for TeknoParrot,
which stores per‑game profiles as XML files under a UserProfiles directory.

The updated version adds support for a second system called ``PC Games``.  In
addition to switching between systems via a drop‑down, the GUI adapts its
controls: when ``TeknoParrot`` is selected the user can choose a UserProfiles
folder and set a new drive letter for the ``GamePath`` entries in each XML
profile.  When ``PC Games`` is selected the tool allows picking a single
``.ini`` file (typically the PCLauncher module file for HyperSpin) and a
target games directory; it will then rewrite the ``Application=`` entries in
that INI so that each absolute path is updated to reside beneath the new
root.  Relative paths (those starting with ``..``) are left unchanged.

Configuration options (last used folders and files) are persisted to a
``config.json`` file in the working directory.  This makes it easy to return
to the same directories on subsequent runs.
"""


CONFIG_FILE = "config.json"


class TeknoParrotTool(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Editor de GamePath para TeknoParrot y PC Games")
        # Maintain a reasonable fixed size; the height grows to fit new widgets.
        self.setFixedSize(500, 600)

        # Initialise persistent values before loading configuration.
        self.folder = ""  # UserProfiles folder for TeknoParrot
        self.pc_ini_file = ""  # PC Games INI file path
        self.pc_games_dir = ""  # Target root directory for PC Games

        layout = QVBoxLayout()

        # ------------------------
        # SISTEMA SELECTION
        # ------------------------
        layout.addWidget(QLabel("Sistema:"))
        self.comboSystem = QComboBox()
        # TeknoParrot remains the default system
        self.comboSystem.addItem("TeknoParrot")
        # Add a new option for PC Games
        self.comboSystem.addItem("PC Games")
        self.comboSystem.currentIndexChanged.connect(self.update_ui_for_system)
        layout.addWidget(self.comboSystem)

        # ------------------------
        # TEKNOPARROT: CARPETA USERPROFILES
        # ------------------------
        self.labelUserProfilesDesc = QLabel("Carpeta de UserProfiles:")
        layout.addWidget(self.labelUserProfilesDesc)
        self.btnBrowse = QPushButton("Seleccionar carpeta")
        self.btnBrowse.clicked.connect(self.select_folder)
        layout.addWidget(self.btnBrowse)
        self.labelFolder = QLabel("(ninguna carpeta seleccionada)")
        layout.addWidget(self.labelFolder)

        # ------------------------
        # TEKNOPARROT: LETRA DE UNIDAD
        # ------------------------
        self.labelDriveDesc = QLabel("Nueva letra de unidad detectada:")
        layout.addWidget(self.labelDriveDesc)
        self.comboDrive = QComboBox()
        self.load_available_drives()
        layout.addWidget(self.comboDrive)

        # ------------------------
        # PC GAMES: INI FILE
        # ------------------------
        self.labelIniDesc = QLabel("Archivo INI de PC Games:")
        layout.addWidget(self.labelIniDesc)
        self.btnBrowseIni = QPushButton("Seleccionar archivo INI")
        self.btnBrowseIni.clicked.connect(self.select_ini)
        layout.addWidget(self.btnBrowseIni)
        self.labelIniFile = QLabel("(ningún archivo seleccionado)")
        layout.addWidget(self.labelIniFile)

        # ------------------------
        # PC GAMES: DIRECTORIO DE JUEGOS
        # ------------------------
        self.labelPcDirDesc = QLabel("Carpeta de juegos de PC:")
        layout.addWidget(self.labelPcDirDesc)
        self.btnBrowsePcDir = QPushButton("Seleccionar carpeta")
        self.btnBrowsePcDir.clicked.connect(self.select_pc_dir)
        layout.addWidget(self.btnBrowsePcDir)
        self.labelPcDir = QLabel("(ninguna carpeta seleccionada)")
        layout.addWidget(self.labelPcDir)

        # ------------------------
        # LOG DE ACTIVIDAD
        # ------------------------
        layout.addWidget(QLabel("Log de actividad:"))
        self.logBox = QTextEdit()
        self.logBox.setReadOnly(True)
        self.logBox.setFixedHeight(200)
        layout.addWidget(self.logBox)

        # ------------------------
        # BOTÓN APLICAR
        # ------------------------
        self.btnApply = QPushButton("Aplicar cambios")
        self.btnApply.clicked.connect(self.apply_changes)
        layout.addWidget(self.btnApply)

        self.setLayout(layout)

        # Load configuration from disk.  This will populate
        # self.folder, self.pc_ini_file and self.pc_games_dir where available.
        self.load_config()

        # After loading configuration, update UI to reflect the default system.
        self.update_ui_for_system()

    # --------------------------------------------------
    # Persist configuration to JSON
    # --------------------------------------------------
    def save_config(self):
        data = {
            "last_folder": self.folder,
            "pc_ini_file": self.pc_ini_file,
            "pc_games_dir": self.pc_games_dir,
            # Also remember the selected drive letter if present
            "last_drive": self.comboDrive.currentText() if self.comboDrive.count() > 0 else "",
            "last_system": self.comboSystem.currentText(),
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            # Silent failure; do not interrupt user
            print(f"Warning: could not save configuration: {e}")

    # --------------------------------------------------
    # Load configuration from JSON if available
    # --------------------------------------------------
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.folder = data.get("last_folder", "")
                    self.pc_ini_file = data.get("pc_ini_file", "")
                    self.pc_games_dir = data.get("pc_games_dir", "")
                    # Set the text of selection labels if paths exist
                    if self.folder and os.path.exists(self.folder):
                        self.labelFolder.setText(self.folder)
                        self.log(f"Carpeta cargada desde config.json: {self.folder}")
                    else:
                        self.folder = ""
                    if self.pc_ini_file and os.path.exists(self.pc_ini_file):
                        self.labelIniFile.setText(self.pc_ini_file)
                        self.log(f"Archivo INI cargado desde config.json: {self.pc_ini_file}")
                    else:
                        self.pc_ini_file = ""
                    if self.pc_games_dir and os.path.exists(self.pc_games_dir):
                        self.labelPcDir.setText(self.pc_games_dir)
                        self.log(f"Carpeta de juegos cargada desde config.json: {self.pc_games_dir}")
                    else:
                        self.pc_games_dir = ""
                    # Restore previously selected system if saved
                    last_system = data.get("last_system", "TeknoParrot")
                    index = self.comboSystem.findText(last_system)
                    if index >= 0:
                        self.comboSystem.setCurrentIndex(index)
                    # Restore previously selected drive letter if available
                    last_drive = data.get("last_drive", "")
                    if last_drive:
                        idx = self.comboDrive.findText(last_drive)
                        if idx >= 0:
                            self.comboDrive.setCurrentIndex(idx)
            except Exception:
                # Ignore errors while loading configuration
                pass

    # --------------------------------------------------
    # Detect available drives on the host system
    # --------------------------------------------------
    def load_available_drives(self):
        drives = []
        try:
            # Use psutil to list mounted partitions; fallback to scanning letters.
            partitions = psutil.disk_partitions(all=False)
            for p in partitions:
                if os.path.exists(p.device):
                    # p.device may be like 'C:\\' or '/dev/sda1'; we only care for
                    # Windows style mount points.  Compose the root path.
                    if ":" in p.device:
                        root = p.device.split(":")[0] + ":\\"
                        drives.append(root)
        except Exception:
            pass
        if not drives:
            # Fallback: brute force A: through Z:
            for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                if os.path.exists(f"{c}:\\"):
                    drives.append(f"{c}:\\")
        # Clear and populate the combo box
        self.comboDrive.clear()
        self.comboDrive.addItems(drives)

    # --------------------------------------------------
    # UI: select UserProfiles folder (TeknoParrot)
    # --------------------------------------------------
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de UserProfiles")
        if folder:
            self.folder = folder
            self.labelFolder.setText(folder)
            self.log("Carpeta seleccionada: " + folder)
            self.save_config()

    # --------------------------------------------------
    # UI: select INI file (PC Games)
    # --------------------------------------------------
    def select_ini(self):
        # Only allow selection of files with .ini extension for clarity
        ini_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo INI",
            "",
            "Archivos INI (*.ini);;Todos los archivos (*)",
        )
        if ini_path:
            self.pc_ini_file = ini_path
            self.labelIniFile.setText(ini_path)
            self.log("Archivo INI seleccionado: " + ini_path)
            self.save_config()

    # --------------------------------------------------
    # UI: select PC games directory (PC Games)
    # --------------------------------------------------
    def select_pc_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de juegos de PC")
        if dir_path:
            self.pc_games_dir = dir_path
            self.labelPcDir.setText(dir_path)
            self.log("Carpeta de juegos seleccionada: " + dir_path)
            self.save_config()

    # --------------------------------------------------
    # Append text to the log box
    # --------------------------------------------------
    def log(self, message):
        self.logBox.append(message)

    # --------------------------------------------------
    # Update UI controls based on selected system
    # --------------------------------------------------
    def update_ui_for_system(self):
        system = self.comboSystem.currentText()
        # For TeknoParrot we show UserProfiles folder and drive letter
        if system == "TeknoParrot":
            # Show TeknoParrot controls
            self.labelUserProfilesDesc.show()
            self.btnBrowse.show()
            self.labelFolder.show()
            self.labelDriveDesc.show()
            self.comboDrive.show()
            # Hide PC Games controls
            self.labelIniDesc.hide()
            self.btnBrowseIni.hide()
            self.labelIniFile.hide()
            self.labelPcDirDesc.hide()
            self.btnBrowsePcDir.hide()
            self.labelPcDir.hide()
        else:  # PC Games
            # Hide TeknoParrot controls
            self.labelUserProfilesDesc.hide()
            self.btnBrowse.hide()
            self.labelFolder.hide()
            self.labelDriveDesc.hide()
            self.comboDrive.hide()
            # Show PC Games controls
            self.labelIniDesc.show()
            self.btnBrowseIni.show()
            self.labelIniFile.show()
            self.labelPcDirDesc.show()
            self.btnBrowsePcDir.show()
            self.labelPcDir.show()

    # --------------------------------------------------
    # Apply changes depending on selected system
    # --------------------------------------------------
    def apply_changes(self):
        system = self.comboSystem.currentText()
        if system == "TeknoParrot":
            self.apply_changes_tekno()
        else:
            self.apply_changes_pc_games()

    # --------------------------------------------------
    # Modify TeknoParrot XML profile files
    # --------------------------------------------------
    def apply_changes_tekno(self):
        if not self.folder:
            QMessageBox.warning(self, "Error", "Debes seleccionar una carpeta con UserProfiles.")
            return
        # New drive letter is derived from comboDrive (e.g. "E:\\")
        new_drive_full = self.comboDrive.currentText()
        if not new_drive_full:
            QMessageBox.warning(self, "Error", "No se ha detectado una letra de unidad válida.")
            return
        new_letter = new_drive_full[0]  # e.g. 'E'
        # Gather XML files from the selected folder
        try:
            xml_files = [f for f in os.listdir(self.folder) if f.lower().endswith(".xml")]
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al listar archivos: {e}")
            return
        num_files = len(xml_files)
        if num_files == 0:
            QMessageBox.information(self, "Sin archivos", "No se encontraron XML en la carpeta seleccionada.")
            return
        # Show an indeterminate progress dialog
        progress = QProgressDialog("Modificando archivos XML...", None, 0, 0, self)
        progress.setWindowTitle("Trabajando...")
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.show()
        self.log("------ INICIO DEL PROCESO ------")
        self.log(f"Total de perfiles: {num_files}")
        self.log(f"Nueva letra: {new_letter}")
        modified_count = 0
        for file in xml_files:
            xml_path = os.path.join(self.folder, file)
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                gamePath_node = root.find("GamePath")
                if gamePath_node is not None:
                    old_path = gamePath_node.text
                    if old_path and len(old_path) > 2 and old_path[1] == ":":
                        # Replace drive letter only
                        new_path = new_letter + old_path[1:]
                        gamePath_node.text = new_path
                        tree.write(xml_path, encoding="utf-8", xml_declaration=True)
                        modified_count += 1
                        self.log(f"[OK] {file} → {new_path}")
            except Exception as e:
                self.log(f"[ERROR] {file}: {e}")
            QApplication.processEvents()
        progress.close()
        self.log("------ PROCESO COMPLETADO ------")
        QMessageBox.information(self, "Completado", f"Perfiles modificados: {modified_count}")
        # Save the drive letter for next session
        self.save_config()

    # --------------------------------------------------
    # Modify PC Games INI file
    # --------------------------------------------------
    def apply_changes_pc_games(self):
        # Validate inputs
        if not self.pc_ini_file or not os.path.isfile(self.pc_ini_file):
            QMessageBox.warning(self, "Error", "Debes seleccionar un archivo INI válido.")
            return
        if not self.pc_games_dir or not os.path.isdir(self.pc_games_dir):
            QMessageBox.warning(self, "Error", "Debes seleccionar la carpeta donde están los juegos de PC.")
            return
        # Normalise path (ensure no trailing backslash); avoid trailing path separators for join
        pc_root = self.pc_games_dir.rstrip("\\/")
        # Read the INI file line by line so that comments and formatting are preserved
        try:
            with open(self.pc_ini_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo leer el archivo INI: {e}")
            return
        # Set up progress dialog; use an approximate count of entries to update
        total_app_lines = sum(1 for line in lines if line.strip().lower().startswith("application="))
        progress = QProgressDialog("Modificando archivo INI...", None, 0, total_app_lines, self)
        progress.setWindowTitle("Trabajando...")
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.show()
        modified_count = 0
        new_lines = []
        step = 0
        for line in lines:
            stripped = line.strip()
            lower = stripped.lower()
            if lower.startswith("application="):
                key, value = line.split("=", 1)
                original_path = value.strip()
                # Preserve surrounding quotes if present
                quote_char = ''
                if original_path and (original_path[0] == original_path[-1]) and original_path[0] in ('\'"', "\'"):
                    quote_char = original_path[0]
                    path_content = original_path[1:-1]
                else:
                    path_content = original_path
                # Determine if this is an absolute path with a drive letter
                if len(path_content) > 1 and path_content[1] == ":":
                    # Split on backslash; handle missing directories gracefully
                    parts = path_content.split("\\")
                    # Remove the drive letter part (e.g. 'G:'), remove the first folder
                    # Example: 'G:\\PC\\Brawlout\\Brawlout.exe' → ['G:', 'PC', 'Brawlout', 'Brawlout.exe']
                    # relative_parts = ['Brawlout', 'Brawlout.exe']
                    if len(parts) >= 3:
                        relative_parts = parts[2:]
                    elif len(parts) == 2:
                        relative_parts = parts[1:]
                    else:
                        relative_parts = []
                    # Build the new path
                    new_path_content = os.path.join(pc_root, *relative_parts)
                    # Normalise slashes to backslashes for consistency
                    new_path_content = new_path_content.replace("/", "\\")
                    new_val = f"{quote_char}{new_path_content}{quote_char}" if quote_char else new_path_content
                    new_line = f"{key}={new_val}\n"
                    new_lines.append(new_line)
                    modified_count += 1
                    self.log(f"[OK] {key.strip()} → {new_path_content}")
                else:
                    # Relative path; leave unchanged
                    new_lines.append(line)
                step += 1
                progress.setValue(step)
                QApplication.processEvents()
            else:
                new_lines.append(line)
        progress.close()
        # Write modifications back to file
        try:
            with open(self.pc_ini_file, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo escribir el archivo INI: {e}")
            return
        # Inform the user of completion
        QMessageBox.information(
            self,
            "Completado",
            f"Entradas modificadas: {modified_count}",
        )
        # Save current configuration
        self.save_config()


# ------------------------------------------------------
# Application entry point
# ------------------------------------------------------
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = TeknoParrotTool()
    window.show()
    sys.exit(app.exec())