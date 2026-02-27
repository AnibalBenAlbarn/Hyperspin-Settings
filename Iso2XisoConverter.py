import os
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QListWidget, QListWidgetItem, QMessageBox, QLineEdit,
    QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal


class ConverterThread(QThread):
    progress = pyqtSignal(str)

    def __init__(self, exe_path, iso_paths):
        super().__init__()
        self.exe_path = exe_path
        self.iso_paths = iso_paths

    def run(self):
        for iso in self.iso_paths:
            self.progress.emit(f"Convirtiendo: {iso}")

            base = os.path.splitext(iso)[0]
            output_iso = f"{base}.xiso.iso"

            cmd = [self.exe_path, "pack", iso, output_iso]

            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )

                for line in process.stdout:
                    self.progress.emit(line.strip())

                process.wait()
                if process.returncode == 0:
                    self.progress.emit(f"✔ Finalizado: {output_iso}")
                else:
                    self.progress.emit(f"✖ Error al convertir: {iso}")

            except Exception as e:
                self.progress.emit(f"✖ Error ejecutando xdvdfs: {str(e)}")


class XisoConverterApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("XISO Converter GUI - PyQt6")
        self.setGeometry(300, 200, 750, 550)

        layout = QVBoxLayout()

        # ---- EXECUTABLE INPUT ----
        exe_row = QHBoxLayout()
        self.exe_input = QLineEdit()
        btn_exe = QPushButton("Seleccionar xdvdfs.exe")
        btn_exe.clicked.connect(self.select_exe)
        exe_row.addWidget(QLabel("Ruta ejecutable xdvdfs.exe:"))
        exe_row.addWidget(self.exe_input)
        exe_row.addWidget(btn_exe)
        layout.addLayout(exe_row)

        # ---- FOLDER INPUT ----
        folder_row = QHBoxLayout()
        self.folder_input = QLineEdit()
        btn_folder = QPushButton("Seleccionar carpeta")
        btn_folder.clicked.connect(self.select_folder)
        folder_row.addWidget(QLabel("Carpeta de ISOs:"))
        folder_row.addWidget(self.folder_input)
        folder_row.addWidget(btn_folder)
        layout.addLayout(folder_row)

        # ---- ISO LIST ----
        self.iso_list = QListWidget()
        layout.addWidget(self.iso_list)

        # ---- BUTTONS ----
        btn_row = QHBoxLayout()
        btn_selected = QPushButton("Convertir seleccionados")
        btn_all = QPushButton("Convertir todos")

        btn_selected.clicked.connect(self.convert_selected)
        btn_all.clicked.connect(self.convert_all)

        btn_row.addWidget(btn_selected)
        btn_row.addWidget(btn_all)
        layout.addLayout(btn_row)

        # ---- LOG BOX ----
        layout.addWidget(QLabel("Log:"))
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

        self.setLayout(layout)

    def log(self, text):
        self.log_box.append(text)

    def select_exe(self):
        file, _ = QFileDialog.getOpenFileName(self, "Seleccionar xdvdfs.exe", "", "Executable (*.exe)")
        if file:
            self.exe_input.setText(file)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta con ISOs")
        if folder:
            self.folder_input.setText(folder)
            self.load_iso_list()

    def load_iso_list(self):
        folder = self.folder_input.text()
        self.iso_list.clear()

        if not os.path.isdir(folder):
            return

        for file in os.listdir(folder):
            if file.lower().endswith(".iso") and not file.lower().endswith(".xiso.iso"):
                item = QListWidgetItem(file)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.iso_list.addItem(item)

        if self.iso_list.count() == 0:
            QMessageBox.information(self, "Info", "No se encontraron archivos .iso")

    def get_selected_isos(self):
        folder = self.folder_input.text()
        paths = []

        for i in range(self.iso_list.count()):
            item = self.iso_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                paths.append(os.path.join(folder, item.text()))

        return paths

    def convert_selected(self):
        iso_paths = self.get_selected_isos()
        if not iso_paths:
            QMessageBox.warning(self, "Aviso", "No seleccionaste ningún ISO.")
            return
        self.start_conversion(iso_paths)

    def convert_all(self):
        folder = self.folder_input.text()
        iso_paths = []

        for i in range(self.iso_list.count()):
            file = self.iso_list.item(i).text()
            iso_paths.append(os.path.join(folder, file))

        if not iso_paths:
            QMessageBox.warning(self, "Aviso", "No hay archivos para convertir.")
            return

        self.start_conversion(iso_paths)

    def start_conversion(self, iso_paths):
        exe_path = self.exe_input.text()
        if not exe_path or not os.path.isfile(exe_path):
            QMessageBox.warning(self, "Error", "Debes seleccionar un archivo xdvdfs.exe válido.")
            return

        self.log("---- Iniciando conversión ----")

        self.thread = ConverterThread(exe_path, iso_paths)
        self.thread.progress.connect(self.log)
        self.thread.start()


if __name__ == "__main__":
    app = QApplication([])
    window = XisoConverterApp()
    window.show()
    app.exec()
