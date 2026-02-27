import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

from PyQt6.QtCore import QProcess, Qt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog, QMessageBox,
    QLabel, QLineEdit, QPushButton, QPlainTextEdit, QProgressBar,
    QHBoxLayout, QVBoxLayout, QGroupBox, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox
)


VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"}


def human_path(p: str) -> str:
    return os.path.normpath(p.strip().strip('"').strip())


def script_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def config_path() -> Path:
    return script_dir() / "config.json"


def load_config() -> dict:
    p = config_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_config(cfg: dict) -> None:
    p = config_path()
    try:
        p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        # No bloqueamos la app por esto, pero lo registramos en consola si existe.
        print(f"[WARN] No pude guardar config.json: {e}", file=sys.stderr)


def get_default_ffmpeg_path() -> Optional[str]:
    """
    Busca ffmpeg.exe en este orden:
    1) PyInstaller (sys._MEIPASS)
    2) ffmpeg.exe junto al script
    3) PATH del sistema
    """
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", script_dir()))
        ff = base / "ffmpeg.exe"
        if ff.exists():
            return str(ff)

    ff_local = script_dir() / "ffmpeg.exe"
    if ff_local.exists():
        return str(ff_local)

    return shutil.which("ffmpeg")


def get_default_ffprobe_path(ffmpeg_path: str) -> Optional[str]:
    """
    Si existe ffprobe.exe junto a ffmpeg.exe, úsalo.
    Si no, intenta PATH.
    """
    try:
        ffmpeg_p = Path(ffmpeg_path)
        ffprobe_local = ffmpeg_p.parent / "ffprobe.exe"
        if ffprobe_local.exists():
            return str(ffprobe_local)
    except Exception:
        pass
    return shutil.which("ffprobe")


def safe_stem_with_suffix(stem: str, suffix: str) -> str:
    # Evitar dobles sufijos si el archivo ya termina con "_convirtiendo"
    if stem.lower().endswith(suffix.lower()):
        return stem
    return f"{stem}{suffix}"


def parse_time_to_seconds(t: str) -> Optional[float]:
    m = re.match(r"(?P<h>\d+):(?P<m>\d+):(?P<s>\d+(?:\.\d+)?)", t)
    if not m:
        return None
    h = int(m.group("h"))
    mi = int(m.group("m"))
    s = float(m.group("s"))
    return h * 3600 + mi * 60 + s


def probe_duration_seconds(ffmpeg_path: str, video_path: str) -> Optional[float]:
    """
    Intenta ffprobe primero; si no, usa ffmpeg -i parseando 'Duration:'.
    """
    ffprobe = get_default_ffprobe_path(ffmpeg_path)
    if ffprobe:
        try:
            p = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", video_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )
            s = p.stdout.strip()
            if s:
                return float(s)
        except Exception:
            pass

    # Fallback ffmpeg -i
    try:
        p = subprocess.run(
            [ffmpeg_path, "-i", video_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        m = re.search(r"Duration:\s*(\d+:\d+:\d+(?:\.\d+)?)", p.stdout)
        if not m:
            return None
        return parse_time_to_seconds(m.group(1))
    except Exception:
        return None


@dataclass
class Job:
    input_path: str
    temp_path: str
    final_path: str
    duration_sec: Optional[float] = None
    row_index: int = -1


class MainWindow(QMainWindow):
    COL_CHECK = 0
    COL_NAME = 1
    COL_EXT = 2
    COL_SIZE = 3
    COL_STATUS = 4

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Conversor vídeos a HyperSpin (FFmpeg) - PyQt6")
        self.resize(1100, 720)

        self.cfg = load_config()

        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self.on_ready_read)
        self.proc.finished.connect(self.on_finished)

        self.jobs: List[Job] = []
        self.current_job: Optional[Job] = None
        self.total_jobs: int = 0
        self.jobs_done: int = 0

        # ----- UI -----
        central = QWidget()
        self.setCentralWidget(central)

        # Carpeta
        gb_folder = QGroupBox("Carpeta de vídeos")
        folder_layout = QFormLayout()

        self.le_folder = QLineEdit()
        self.le_folder.setPlaceholderText("Selecciona una carpeta…")
        self.le_folder.setText(self.cfg.get("last_folder", ""))

        btn_folder = QPushButton("Elegir carpeta…")
        btn_folder.clicked.connect(self.pick_folder)

        btn_scan = QPushButton("Escanear")
        btn_scan.clicked.connect(self.scan_folder)

        row_folder = QHBoxLayout()
        row_folder.addWidget(self.le_folder, 1)
        row_folder.addWidget(btn_folder)
        row_folder.addWidget(btn_scan)

        folder_layout.addRow(QLabel("Carpeta:"), self._wrap(row_folder))
        gb_folder.setLayout(folder_layout)

        # FFmpeg
        gb_ff = QGroupBox("FFmpeg")
        ff_layout = QFormLayout()

        self.le_ffmpeg = QLineEdit()
        self.le_ffmpeg.setPlaceholderText("Ruta a ffmpeg.exe (si lo dejas vacío, se usa ffmpeg.exe local o PATH)")
        default_ff = self.cfg.get("ffmpeg_path") or get_default_ffmpeg_path() or ""
        self.le_ffmpeg.setText(default_ff)

        btn_ff = QPushButton("Buscar ffmpeg.exe…")
        btn_ff.clicked.connect(self.pick_ffmpeg)

        row_ff = QHBoxLayout()
        row_ff.addWidget(self.le_ffmpeg, 1)
        row_ff.addWidget(btn_ff)

        ff_layout.addRow(QLabel("FFmpeg:"), self._wrap(row_ff))
        gb_ff.setLayout(ff_layout)

        # Seleccionar todos
        self.chk_all = QCheckBox("Seleccionar todos")
        self.chk_all.stateChanged.connect(self.on_select_all)

        # Tabla
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Convertir", "Archivo", "Ext", "Tamaño", "Estado"])
        self.table.horizontalHeader().setSectionResizeMode(self.COL_CHECK, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(self.COL_NAME, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(self.COL_EXT, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(self.COL_SIZE, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(self.COL_STATUS, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # Controles
        self.btn_convert = QPushButton("Convertir seleccionados")
        self.btn_convert.clicked.connect(self.start_batch)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.cancel)
        self.btn_cancel.setEnabled(False)

        controls = QHBoxLayout()
        controls.addWidget(self.chk_all)
        controls.addStretch(1)
        controls.addWidget(self.btn_convert)
        controls.addWidget(self.btn_cancel)

        # Progreso
        self.progress_file = QProgressBar()
        self.progress_file.setRange(0, 100)
        self.progress_file.setValue(0)

        self.progress_total = QProgressBar()
        self.progress_total.setRange(0, 100)
        self.progress_total.setValue(0)

        # Log
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(gb_folder)
        layout.addWidget(gb_ff)
        layout.addLayout(controls)
        layout.addWidget(QLabel("Lista de vídeos:"))
        layout.addWidget(self.table, 1)

        layout.addWidget(QLabel("Progreso archivo actual:"))
        layout.addWidget(self.progress_file)
        layout.addWidget(QLabel("Progreso total:"))
        layout.addWidget(self.progress_total)

        layout.addWidget(QLabel("Log:"))
        layout.addWidget(self.log, 1)

        central.setLayout(layout)

        # Si hay carpeta guardada, escanear al arrancar
        if self.le_folder.text().strip():
            self.scan_folder()

    def _wrap(self, hbox: QHBoxLayout) -> QWidget:
        w = QWidget()
        w.setLayout(hbox)
        return w

    def append_log(self, text: str):
        self.log.appendPlainText(text.rstrip())

    def pick_folder(self):
        start = self.le_folder.text().strip() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Selecciona carpeta", start)
        if folder:
            self.le_folder.setText(human_path(folder))
            self.cfg["last_folder"] = self.le_folder.text().strip()
            save_config(self.cfg)

    def pick_ffmpeg(self):
        start = str(Path(self.le_ffmpeg.text().strip() or str(Path.home())).parent)
        exe_path, _ = QFileDialog.getOpenFileName(
            self, "Selecciona ffmpeg.exe", start,
            "FFmpeg (ffmpeg.exe);;Ejecutables (*.exe);;Todos (*.*)"
        )
        if exe_path:
            self.le_ffmpeg.setText(human_path(exe_path))
            self.cfg["ffmpeg_path"] = self.le_ffmpeg.text().strip()
            save_config(self.cfg)

    def ffmpeg_exe(self) -> Optional[str]:
        s = self.le_ffmpeg.text().strip()
        if s:
            s = human_path(s)
            if os.path.exists(s):
                return s
        # si no está escrito o es inválido
        return get_default_ffmpeg_path()

    def scan_folder(self):
        folder = self.le_folder.text().strip()
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, "Carpeta inválida", "Selecciona una carpeta válida.")
            return

        self.cfg["last_folder"] = folder
        save_config(self.cfg)

        p = Path(folder)
        videos = []
        for f in p.iterdir():
            if f.is_file() and f.suffix.lower() in VIDEO_EXTS:
                # Evitar listar temporales "*_convirtiendo"
                if f.stem.lower().endswith("_convirtiendo"):
                    continue
                videos.append(f)

        videos.sort(key=lambda x: x.name.lower())

        self.table.setRowCount(0)
        self.chk_all.blockSignals(True)
        self.chk_all.setChecked(False)
        self.chk_all.blockSignals(False)

        for f in videos:
            self.add_video_row(f)

        self.append_log(f"Escaneo completado: {len(videos)} vídeos encontrados en {folder}")

    def add_video_row(self, f: Path):
        row = self.table.rowCount()
        self.table.insertRow(row)

        chk = QCheckBox()
        chk.setChecked(False)
        chk.setTristate(False)
        chk.setStyleSheet("margin-left:12px;")  # centrar un poco
        self.table.setCellWidget(row, self.COL_CHECK, chk)

        name_item = QTableWidgetItem(f.stem)
        ext_item = QTableWidgetItem(f.suffix.lower())
        size_mb = f.stat().st_size / (1024 * 1024)
        size_item = QTableWidgetItem(f"{size_mb:.1f} MB")
        status_item = QTableWidgetItem("Pendiente")

        for it in (name_item, ext_item, size_item, status_item):
            it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)

        self.table.setItem(row, self.COL_NAME, name_item)
        self.table.setItem(row, self.COL_EXT, ext_item)
        self.table.setItem(row, self.COL_SIZE, size_item)
        self.table.setItem(row, self.COL_STATUS, status_item)

        # Guardar ruta completa en el item (UserRole)
        name_item.setData(Qt.ItemDataRole.UserRole, str(f))

    def on_select_all(self, state: int):
        checked = (state == Qt.CheckState.Checked.value)
        for r in range(self.table.rowCount()):
            w = self.table.cellWidget(r, self.COL_CHECK)
            if isinstance(w, QCheckBox):
                w.setChecked(checked)

    def selected_video_paths(self) -> List[str]:
        paths = []
        for r in range(self.table.rowCount()):
            w = self.table.cellWidget(r, self.COL_CHECK)
            if isinstance(w, QCheckBox) and w.isChecked():
                item = self.table.item(r, self.COL_NAME)
                if item:
                    path = item.data(Qt.ItemDataRole.UserRole)
                    if path and os.path.exists(path):
                        paths.append(path)
        return paths

    def set_row_status(self, row: int, status: str):
        it = self.table.item(row, self.COL_STATUS)
        if it:
            it.setText(status)

    def start_batch(self):
        ff = self.ffmpeg_exe()
        if not ff or not os.path.exists(ff) and shutil.which(ff) is None:
            QMessageBox.critical(
                self, "FFmpeg no encontrado",
                "No encuentro ffmpeg.\n\n"
                "Asegúrate de que ffmpeg.exe está junto al script o selecciona su ruta."
            )
            return

        selected = self.selected_video_paths()
        if not selected:
            QMessageBox.information(self, "Nada seleccionado", "Marca al menos un vídeo para convertir.")
            return

        # Guardar config
        self.cfg["ffmpeg_path"] = self.le_ffmpeg.text().strip()
        self.cfg["last_folder"] = self.le_folder.text().strip()
        save_config(self.cfg)

        # Preparar trabajos
        self.jobs = []
        for r in range(self.table.rowCount()):
            w = self.table.cellWidget(r, self.COL_CHECK)
            if isinstance(w, QCheckBox) and w.isChecked():
                item = self.table.item(r, self.COL_NAME)
                if not item:
                    continue
                inp = item.data(Qt.ItemDataRole.UserRole)
                if not inp or not os.path.exists(inp):
                    continue

                inp_path = Path(inp)
                temp_stem = safe_stem_with_suffix(inp_path.stem, "_convirtiendo")
                temp_path = str(inp_path.with_name(temp_stem + inp_path.suffix))  # mantiene extensión original
                final_path = str(inp_path)  # se reemplazará con el mismo nombre original

                job = Job(
                    input_path=str(inp_path),
                    temp_path=temp_path,
                    final_path=final_path,
                    duration_sec=None,
                    row_index=r
                )
                self.jobs.append(job)

        if not self.jobs:
            QMessageBox.information(self, "Nada válido", "No hay vídeos válidos seleccionados.")
            return

        # UI estado
        self.total_jobs = len(self.jobs)
        self.jobs_done = 0
        self.progress_total.setValue(0)
        self.progress_file.setValue(0)
        self.log.clear()

        self.btn_convert.setEnabled(False)
        self.btn_cancel.setEnabled(True)

        self.append_log(f"=== Iniciando conversión por lotes: {self.total_jobs} vídeos ===")
        self.process_next_job()

    def build_ffmpeg_args(self, job: Job) -> List[str]:
        # Importante: -map 0:a? para que NO falle si el vídeo no tiene audio
        return [
            "-y",
            "-i", job.input_path,
            "-map", "0:v:0",
            "-map", "0:a?",
            "-c:v", "libx264", "-profile:v", "high", "-level", "4.1",
            "-pix_fmt", "yuv420p",
            "-preset", "slow", "-crf", "18",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart",
            job.temp_path
        ]

    def process_next_job(self):
        if self.proc.state() != QProcess.ProcessState.NotRunning:
            return

        if not self.jobs:
            # Fin
            self.btn_convert.setEnabled(True)
            self.btn_cancel.setEnabled(False)
            self.progress_file.setValue(0)
            self.progress_total.setValue(100)
            self.append_log("\n=== TODO TERMINADO ===")
            QMessageBox.information(self, "Listo", "Conversión por lotes finalizada.")
            return

        ff = self.ffmpeg_exe()
        if not ff:
            QMessageBox.critical(self, "FFmpeg no encontrado", "No encuentro ffmpeg para continuar.")
            self.btn_convert.setEnabled(True)
            self.btn_cancel.setEnabled(False)
            return

        self.current_job = self.jobs.pop(0)
        job = self.current_job

        # Status tabla
        self.set_row_status(job.row_index, "Calculando duración…")
        job.duration_sec = probe_duration_seconds(ff, job.input_path)
        self.progress_file.setValue(0)

        inp_name = Path(job.input_path).name
        self.append_log(f"\n--- Convirtiendo: {inp_name} ---")
        self.append_log(f"Temp: {Path(job.temp_path).name}")
        self.append_log("")

        # Si existe el temp de antes, eliminarlo
        try:
            if os.path.exists(job.temp_path):
                os.remove(job.temp_path)
        except Exception:
            pass

        self.set_row_status(job.row_index, "Convirtiendo…")

        args = self.build_ffmpeg_args(job)
        self.proc.setProgram(ff)
        self.proc.setArguments(args)
        self.proc.start()

        if not self.proc.waitForStarted(3000):
            self.set_row_status(job.row_index, "ERROR: no inicia FFmpeg")
            self.append_log("ERROR: No pude iniciar FFmpeg.")
            self.jobs_done += 1
            self.update_total_progress()
            self.process_next_job()

    def update_total_progress(self):
        if self.total_jobs <= 0:
            self.progress_total.setValue(0)
            return
        pct = int((self.jobs_done / self.total_jobs) * 100)
        self.progress_total.setValue(max(0, min(100, pct)))

    def cancel(self):
        if self.proc.state() != QProcess.ProcessState.NotRunning:
            self.append_log("\nCancelando proceso…")
            self.proc.kill()
        # También vaciamos cola
        self.jobs.clear()

    def on_ready_read(self):
        data = bytes(self.proc.readAllStandardOutput()).decode("utf-8", errors="ignore")
        if not data:
            return

        self.append_log(data)

        job = self.current_job
        if not job or not job.duration_sec:
            return

        # Buscar time=HH:MM:SS.xx
        m = re.findall(r"time=(\d+:\d+:\d+(?:\.\d+)?)", data)
        if m:
            t = parse_time_to_seconds(m[-1])
            if t is not None and job.duration_sec > 0:
                pct = int(max(0, min(100, (t / job.duration_sec) * 100)))
                self.progress_file.setValue(pct)

    def on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus):
        job = self.current_job
        self.current_job = None

        if not job:
            return

        if exit_status == QProcess.ExitStatus.CrashExit or exit_code != 0:
            self.set_row_status(job.row_index, f"ERROR (code {exit_code})")
            self.append_log(f"ERROR: FFmpeg terminó con código {exit_code}.")
            # No tocamos el original
            try:
                if os.path.exists(job.temp_path):
                    os.remove(job.temp_path)
            except Exception:
                pass

            self.jobs_done += 1
            self.update_total_progress()
            self.process_next_job()
            return

        # Éxito: borrar original y renombrar temp al original
        try:
            # 1) borrar original
            if os.path.exists(job.final_path):
                os.remove(job.final_path)

            # 2) renombrar temp -> original (mismo nombre sin _convirtiendo)
            os.replace(job.temp_path, job.final_path)

            self.set_row_status(job.row_index, "OK (reemplazado)")
            self.progress_file.setValue(100)

            # Actualizar tamaño en tabla (por si cambia)
            try:
                out_size_mb = Path(job.final_path).stat().st_size / (1024 * 1024)
                self.table.item(job.row_index, self.COL_SIZE).setText(f"{out_size_mb:.1f} MB")
            except Exception:
                pass

        except Exception as e:
            self.set_row_status(job.row_index, f"ERROR reemplazo")
            self.append_log(f"ERROR al reemplazar archivo: {e}")
            # Intento de recuperación: si el original se borró y el temp existe, dejarlo al menos
            # (pero NO inventamos más reglas; lo dejamos registrado)
            pass

        self.jobs_done += 1
        self.update_total_progress()
        self.process_next_job()


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
