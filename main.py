import os
import sys
import time
import shutil
import ctypes
import subprocess

try:
    import PyQt6  # noqa: F401
except ModuleNotFoundError:
    sys.exit(
        f"PyQt6 non e' installato per questo Python ({sys.executable}).\n"
        "Probabilmente 'python' apre un interprete diverso da quello usato da 'pip'.\n"
        "Avvia l'app con:  avvia.bat   oppure   py -3 main.py\n"
        "(per installare le dipendenze:  py -3 -m pip install -r requirements.txt)"
    )

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QListWidget, QListWidgetItem,
    QTabWidget, QLineEdit, QSplitter, QSpinBox, QTextEdit, QComboBox,
    QMessageBox, QCheckBox
)
from PyQt6.QtGui import QFont, QIcon, QColor
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QSettings

from nbt_codec import load_nbt
from mca_codec import MCARegion, UnsupportedChunkFormat
from structure_manager import Structure
from world_editor import World, inject_structures
import world_locator
from map_viewer import MapViewer
from scraper import search_minecraft_schematics, download_structure, CURATED_ONLINE_CATALOG

# Premium Dark CSS Stylesheet with Neon Green accents
DARK_THEME_STYLE = """
QMainWindow {
    background-color: #141416;
}
QWidget {
    font-family: 'Inter', 'Segoe UI', sans-serif;
    color: #e0e0e8;
}
QDialog, QMessageBox {
    background-color: #1b1b1f;
}
QMessageBox QLabel {
    color: #e0e0e8;
}
QMessageBox QPushButton {
    background-color: #27272a;
    border: 1px solid #3f3f46;
    color: #ffffff;
    padding: 6px 14px;
    min-width: 70px;
}
QMessageBox QPushButton:hover {
    border-color: #2ecc71;
}
QLabel {
    font-weight: 500;
}
QLabel#title_lbl {
    font-size: 18px;
    font-weight: 800;
    color: #2ecc71;
}
QFrame#sidebar {
    background-color: #1b1b1f;
    border-right: 1px solid #27272a;
}
QTabWidget::pane {
    border: 1px solid #27272a;
    background: #1b1b1f;
    border-radius: 8px;
}
QTabBar::tab {
    background: #141416;
    border: 1px solid #27272a;
    padding: 8px 14px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 3px;
    color: #888896;
    font-weight: bold;
    font-size: 11px;
}
QTabBar::tab:selected {
    background: #1b1b1f;
    border-bottom-color: #1b1b1f;
    color: #2ecc71;
}
QPushButton {
    background-color: #27272a;
    border: 1px solid #3f3f46;
    border-radius: 6px;
    padding: 8px 14px;
    font-size: 12px;
    font-weight: 600;
    color: #ffffff;
}
QPushButton:hover {
    background-color: #3f3f46;
    border-color: #2ecc71;
}
QPushButton:pressed {
    background-color: #2ecc71;
    color: #141416;
}
QPushButton#action_btn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2ecc71, stop:1 #00b894);
    color: #111111;
    border: 1px solid #55efc4;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 800;
    padding: 12px 18px;
    text-transform: uppercase;
}
QPushButton#action_btn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #55efc4, stop:1 #2ecc71);
    border: 1px solid #00b894;
}
QPushButton#action_btn:pressed {
    background: #00b894;
    color: #111111;
}
QPushButton#action_btn:disabled {
    background: #2b303b;
    border: 1px solid #3d4454;
    color: #64748b;
}
QLineEdit {
    background-color: #0f0f11;
    border: 1px solid #27272a;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    color: #ffffff;
}
QLineEdit:focus {
    border-color: #2ecc71;
}
QListWidget {
    background-color: #0f0f11;
    border: 1px solid #27272a;
    border-radius: 6px;
    padding: 6px;
}
QListWidget::item {
    padding: 10px;
    border-radius: 6px;
    margin-bottom: 4px;
    background-color: #1b1b1f;
}
QListWidget::item:hover {
    background-color: #27272a;
    color: #2ecc71;
}
QListWidget::item:selected {
    background-color: #2ecc71;
    color: #141416;
    font-weight: bold;
}
QComboBox {
    background-color: #0f0f11;
    border: 1px solid #27272a;
    border-radius: 6px;
    padding: 6px 12px;
    color: #ffffff;
}
QComboBox:focus {
    border-color: #2ecc71;
}
QSpinBox {
    background-color: #0f0f11;
    border: 1px solid #27272a;
    border-radius: 6px;
    padding: 6px;
    color: #ffffff;
}
QSpinBox:focus {
    border-color: #2ecc71;
}
QTextEdit {
    background-color: #0f0f11;
    border: 1px solid #27272a;
    border-radius: 8px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 11px;
    color: #a0a0b0;
}
QScrollBar:vertical {
    border: none;
    background: #141416;
    width: 8px;
}
QScrollBar::handle:vertical {
    background: #27272a;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #2ecc71;
}
QCheckBox {
    spacing: 8px;
    font-size: 11px;
    color: #c8c8d0;
    padding: 2px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #3f3f46;
    border-radius: 4px;
    background: #141416;
}
QCheckBox::indicator:hover {
    border-color: #2ecc71;
}
QCheckBox::indicator:checked {
    background-color: #2ecc71;
    border-color: #2ecc71;
}
QCheckBox::indicator:disabled {
    border-color: #2b303b;
    background-color: #1b1b1f;
}
"""

class InjectionWorker(QThread):
    # Signals
    progress = pyqtSignal(str)
    success = pyqtSignal()
    error = pyqtSignal(str)
    permission_error = pyqtSignal(str)

    def __init__(self, world, placements_to_inject, fill_foundations=True, clear_terrain=True, skip_modded=True):
        super().__init__()
        self.world = world
        self.placements_to_inject = placements_to_inject
        self.fill_foundations = fill_foundations
        self.clear_terrain = clear_terrain
        self.skip_modded = skip_modded
        self.stats = None

    def run(self):
        try:
            t0 = time.perf_counter()
            stats = inject_structures(
                self.world,
                self.placements_to_inject,
                fill_foundations=self.fill_foundations,
                clear_terrain=self.clear_terrain,
                skip_modded=self.skip_modded,
                log=self.progress.emit,
            )
            self.stats = stats
            self.progress.emit(
                f"Blocchi piazzati: {stats['placed']}, scavati: {stats['cleared']}, fondamenta: {stats['foundation']}"
            )
            if stats["skipped_missing"]:
                reasons = sorted(set(self.world.skipped_chunks.values()))
                self.progress.emit(
                    f"Avviso: {stats['skipped_missing']} blocchi saltati in {len(self.world.skipped_chunks)} chunk "
                    f"({', '.join(reasons)}). Esplora l'area in gioco e riprova."
                )
            if stats["skipped_modded"]:
                self.progress.emit(f"Avviso: {stats['skipped_modded']} blocchi di mod saltati.")
            if stats["skipped_height"]:
                self.progress.emit(f"Avviso: {stats['skipped_height']} blocchi fuori dai limiti di altezza del mondo.")

            self.progress.emit("Scrittura dei file di regione modificati...")
            self.world.save(backup=True, log=self.progress.emit)
            self.progress.emit(f"Operazione completata in {time.perf_counter() - t0:.1f} s.")
            self.success.emit()
        except PermissionError as pe:
            self.permission_error.emit(str(pe))
        except UnsupportedChunkFormat as e:
            self.error.emit(str(e))
        except Exception as e:
            import traceback
            err_msg = f"{e}\n{traceback.format_exc()}"
            self.error.emit(err_msg)


class MinecraftBuilderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Minecraft Auto-Builder & Map Editor")
        self.setMinimumSize(1100, 750)
        self.setStyleSheet(DARK_THEME_STYLE)
        
        # Paths: any world-related path (command line, last session, launcher default) is resolved
        # to saves folder + world + dimension by world_locator.
        self.settings = QSettings("MINECRAFT-BUILDER", "MinecraftBuilder")
        self.pending_world = None
        self.pending_dimension = None
        self.available_dims = []
        self.player_dimension = None
        app_dir = os.path.dirname(os.path.abspath(__file__))
        arg_path = _path_from_args(sys.argv[1:])
        self.startup_warning = None
        if arg_path and not world_locator.resolve(arg_path):
            self.startup_warning = f"Errore: nessun mondo trovato nel percorso indicato all'avvio: {arg_path}"
        candidates = [arg_path, self.settings.value("last_path", "", type=str),
                      world_locator.default_saves_dir(), os.path.join(app_dir, "saves")]
        found = None
        for candidate in candidates:
            found = world_locator.resolve(candidate) if candidate else None
            if found:
                break
        if found:
            self.saves_dir = found["saves_dir"]
            self.pending_world = found["world"]
            self.pending_dimension = found["dimension"]
        else:
            self.saves_dir = world_locator.default_saves_dir()
            if not os.path.isdir(self.saves_dir):
                self.saves_dir = os.path.expanduser("~")

        self.templates_dir = os.path.join(app_dir, "templates")
        
        # State Variables
        self.current_world_path = None
        self.current_region = None
        self.selected_structure = None
        self.selected_structure_name = ""
        self.locked_placement = None  # (grid_x, grid_z)
        self.staged_placements = []
        
        self.init_ui()
        self.load_local_templates()
        
        # Defer world scanning to keep window startup instant and buttery smooth
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self.scan_worlds)
        
        self.setAcceptDrops(True)
        self.log("Applicazione avviata. Scegli un mondo con 'Sfoglia...', incolla un percorso o trascina qui una cartella.")
        if self.startup_warning:
            self.log(self.startup_warning)

    def init_ui(self):
        # Central widget splitter (Sidebar, Map View, Actions Inspector)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(main_splitter)
        
        # 1. SIDEBAR (Left Panel - Directory select & Structures library)
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(10)
        
        # Title Header
        title_lbl = QLabel("Minecraft Map Builder")
        title_lbl.setObjectName("title_lbl")
        sidebar_layout.addWidget(title_lbl)
        
        # World Save Directory Selection
        dir_layout = QVBoxLayout()
        dir_lbl = QLabel("Mondo o cartella salvataggi:")
        dir_lbl.setStyleSheet("font-size: 11px; color: #888896;")
        dir_layout.addWidget(dir_lbl)

        self.dir_input = QLineEdit(self.saves_dir)
        self.dir_input.setPlaceholderText("Incolla il percorso del mondo e premi Invio")
        self.dir_input.setToolTip("Va bene la cartella del mondo, una sua sottocartella (region, DIM-1...),\n"
                                  "la cartella saves o la cartella .minecraft. Puoi anche trascinarla sulla finestra.")
        self.dir_input.returnPressed.connect(lambda: self.open_path(self.dir_input.text()))
        dir_layout.addWidget(self.dir_input)
        
        dir_btns = QHBoxLayout()
        sfoglia_btn = QPushButton("Sfoglia...")
        sfoglia_btn.clicked.connect(self.select_saves_folder)
        dir_btns.addWidget(sfoglia_btn)
        
        self.world_select = QComboBox()
        self.world_select.currentIndexChanged.connect(self.world_changed)
        dir_btns.addWidget(self.world_select)
        dir_layout.addLayout(dir_btns)
        
        sidebar_layout.addLayout(dir_layout)
        
        # Region file selector
        region_layout = QVBoxLayout()
        dim_lbl = QLabel("Dimensione:")
        dim_lbl.setStyleSheet("font-size: 11px; color: #888896;")
        region_layout.addWidget(dim_lbl)
        self.dim_select = QComboBox()
        self.dim_select.currentIndexChanged.connect(self.dimension_changed)
        region_layout.addWidget(self.dim_select)

        region_lbl = QLabel("File di Regione (.mca):")
        region_lbl.setStyleSheet("font-size: 11px; color: #888896;")
        region_layout.addWidget(region_lbl)
        
        self.region_select = QComboBox()
        self.region_select.currentIndexChanged.connect(self.region_changed)
        region_layout.addWidget(self.region_select)
        
        # Player coordinate display and mapping button
        self.player_info_lbl = QLabel("Giocatore: Non trovato")
        self.player_info_lbl.setStyleSheet("font-size: 11px; color: #f1c40f; font-weight: bold;")
        region_layout.addWidget(self.player_info_lbl)
        
        self.go_to_player_btn = QPushButton("Trova Giocatore sulla Mappa")
        self.go_to_player_btn.setEnabled(False)
        self.go_to_player_btn.clicked.connect(self.go_to_player_region)
        region_layout.addWidget(self.go_to_player_btn)
        
        sidebar_layout.addLayout(region_layout)
        
        # Structure Library Tab System
        self.tabs = QTabWidget()
        sidebar_layout.addWidget(self.tabs)
        
        # Tab 1: Local structures list
        local_tab = QWidget()
        local_layout = QVBoxLayout(local_tab)
        local_layout.setContentsMargins(4, 4, 4, 4)
        
        self.local_list = QListWidget()
        self.local_list.itemSelectionChanged.connect(self.local_structure_selected)
        local_layout.addWidget(self.local_list)
        
        load_file_btn = QPushButton("Carica File (.nbt/.schem)...")
        load_file_btn.clicked.connect(self.import_custom_structure)
        local_layout.addWidget(load_file_btn)
        
        self.tabs.addTab(local_tab, "Locali")
        
        # Tab 2: Online download search
        online_tab = QWidget()
        online_layout = QVBoxLayout(online_tab)
        online_layout.setContentsMargins(4, 4, 4, 4)
        
        search_box = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Cerca online (es: farm, house)...")
        self.search_input.returnPressed.connect(self.search_online)
        search_box.addWidget(self.search_input)
        
        search_btn = QPushButton("Cerca")
        search_btn.clicked.connect(self.search_online)
        search_box.addWidget(search_btn)
        online_layout.addLayout(search_box)
        
        self.online_list = QListWidget()
        self.online_list.itemSelectionChanged.connect(self.online_structure_selected)
        online_layout.addWidget(self.online_list)
        
        self.download_btn = QPushButton("Scarica Struttura")
        self.download_btn.setObjectName("action_btn")
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self.download_selected_structure)
        online_layout.addWidget(self.download_btn)
        
        self.tabs.addTab(online_tab, "Online")
        
        main_splitter.addWidget(sidebar)
        
        # 2. CENTER PANEL (Map view canvas & coordinate logs)
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        
        # Map Viewer canvas
        self.map_viewer = MapViewer()
        self.map_viewer.hover_changed.connect(self.update_hover_coordinates)
        self.map_viewer.structure_placed.connect(self.lock_placement_coordinate)
        self.map_viewer.rotate_requested.connect(self.rotate_current_structure)
        center_layout.addWidget(self.map_viewer)
        
        # Coordinates status bar at bottom
        self.coord_status = QLabel("Coordinate: X: 0, Z: 0 | Altezza Y: -- | Regione: --")
        self.coord_status.setStyleSheet("background-color: #0f0f11; padding: 10px; font-weight: bold; border-top: 1px solid #27272a;")
        center_layout.addWidget(self.coord_status)
        
        main_splitter.addWidget(center_widget)
        
        # 3. RIGHT PANEL (Inspector & Builder Actions)
        inspector = QWidget()
        inspector.setStyleSheet("background-color: #1b1b1f; border-left: 1px solid #27272a;")
        inspector_layout = QVBoxLayout(inspector)
        inspector_layout.setContentsMargins(12, 12, 12, 12)
        inspector_layout.setSpacing(10)
        
        inspector_title = QLabel("Dettagli Posizionamento")
        inspector_title.setFont(QFont("Outfit", 12, QFont.Weight.Bold))
        inspector_layout.addWidget(inspector_title)
        
        # Selected Structure Metadata Display
        self.struct_info_box = QLabel("Nessuna struttura selezionata.")
        self.struct_info_box.setStyleSheet("background-color: #0f0f11; padding: 10px; border-radius: 6px; font-size: 11px;")
        self.struct_info_box.setWordWrap(True)
        inspector_layout.addWidget(self.struct_info_box)
        
        # Placement Configurations
        config_title = QLabel("Parametri Costruzione:")
        config_title.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        inspector_layout.addWidget(config_title)
        
        # Altitude Selector
        y_select_layout = QHBoxLayout()
        y_lbl = QLabel("Altezza Iniezione Y:")
        y_select_layout.addWidget(y_lbl)
        
        self.y_spinbox = QSpinBox()
        self.y_spinbox.setRange(-64, 319)
        self.y_spinbox.setValue(64)
        y_select_layout.addWidget(self.y_spinbox)
        inspector_layout.addLayout(y_select_layout)
        
        # Integration parameters checkboxes
        self.auto_y_checkbox = QCheckBox("Adatta altezza al terreno")
        self.auto_y_checkbox.setChecked(True)
        inspector_layout.addWidget(self.auto_y_checkbox)
        
        self.fill_foundation_checkbox = QCheckBox("Riempi fondamenta sospese")
        self.fill_foundation_checkbox.setChecked(True)
        inspector_layout.addWidget(self.fill_foundation_checkbox)
        
        self.clear_terrain_checkbox = QCheckBox("Scava ostacoli di terreno (Aria)")
        self.clear_terrain_checkbox.setChecked(True)
        inspector_layout.addWidget(self.clear_terrain_checkbox)

        self.skip_modded_checkbox = QCheckBox("Salta blocchi di mod (mondo vanilla)")
        self.skip_modded_checkbox.setChecked(True)
        self.skip_modded_checkbox.setToolTip(
            "In un mondo senza mod, un blocco sconosciuto fa scartare al gioco l'intera sezione 16x16x16."
        )
        inspector_layout.addWidget(self.skip_modded_checkbox)

        # Suggest Position Button
        self.suggest_pos_btn = QPushButton("Consiglia Posizione Ottimale")
        self.suggest_pos_btn.setEnabled(False)
        self.suggest_pos_btn.clicked.connect(self.suggest_optimal_position)
        inspector_layout.addWidget(self.suggest_pos_btn)
        
        # Rotations shortcuts
        rot_layout = QHBoxLayout()
        rotate_btn = QPushButton("Ruota 90° (R)")
        rotate_btn.clicked.connect(self.rotate_current_structure)
        rot_layout.addWidget(rotate_btn)
        
        center_btn = QPushButton("Centra Mappa")
        center_btn.clicked.connect(self.map_viewer.center_on_map)
        rot_layout.addWidget(center_btn)
        inspector_layout.addLayout(rot_layout)
        
        # Lock coordinates feedback label
        self.lock_feedback_lbl = QLabel("Fai clic sulla mappa per posizionare.")
        self.lock_feedback_lbl.setStyleSheet("color: #e67e22; font-weight: bold; font-size: 11px;")
        self.lock_feedback_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inspector_layout.addWidget(self.lock_feedback_lbl)
        
        # Add to Map Button
        self.stage_btn = QPushButton("Aggiungi alla Mappa")
        self.stage_btn.setEnabled(False)
        self.stage_btn.clicked.connect(self.stage_placement)
        inspector_layout.addWidget(self.stage_btn)
        
        # Queue Header
        queue_title = QLabel("Strutture in Coda:")
        queue_title.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        inspector_layout.addWidget(queue_title)
        
        # Queue List Widget
        self.staged_list = QListWidget()
        self.staged_list.setFixedHeight(110)
        self.staged_list.itemSelectionChanged.connect(self.staged_list_selection_changed)
        inspector_layout.addWidget(self.staged_list)
        
        # Queue Controls
        staged_ctrl_layout = QHBoxLayout()
        self.remove_staged_btn = QPushButton("Rimuovi")
        self.remove_staged_btn.setEnabled(False)
        self.remove_staged_btn.clicked.connect(self.remove_selected_staged)
        staged_ctrl_layout.addWidget(self.remove_staged_btn)
        
        self.clear_staged_btn = QPushButton("Svuota")
        self.clear_staged_btn.setEnabled(False)
        self.clear_staged_btn.clicked.connect(self.clear_all_staged)
        staged_ctrl_layout.addWidget(self.clear_staged_btn)
        inspector_layout.addLayout(staged_ctrl_layout)
        
        # Warning label
        warning_lbl = QLabel("⚠ CHIUDI MINECRAFT prima di iniettare!")
        warning_lbl.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 11px; margin-top: 5px;")
        warning_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inspector_layout.addWidget(warning_lbl)

        sp_lbl = QLabel("Modifica i mondi in Giocatore singolo salvati su questo PC: i server multiplayer non cambiano.")
        sp_lbl.setStyleSheet("color: #888896; font-size: 10px;")
        sp_lbl.setWordWrap(True)
        sp_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inspector_layout.addWidget(sp_lbl)
        
        # Direct Action Button
        self.apply_btn = QPushButton("Inietta Struttura nel Mondo")
        self.apply_btn.setObjectName("action_btn")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self.apply_structure_to_world)
        inspector_layout.addWidget(self.apply_btn)
        
        # Console output
        log_lbl = QLabel("Registro Operazioni:")
        log_lbl.setStyleSheet("font-size: 11px; color: #888896;")
        inspector_layout.addWidget(log_lbl)
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        inspector_layout.addWidget(self.console)
        
        main_splitter.addWidget(inspector)
        
        # Set splitter sizes proportions
        main_splitter.setSizes([260, 600, 240])

    def log(self, msg):
        styled_msg = msg
        lower_msg = msg.lower()
        if "successo" in lower_msg or "completato" in lower_msg:
            styled_msg = f"<span style='color: #2ecc71; font-weight: bold;'>{msg}</span>"
        elif "errore" in lower_msg or "negato" in lower_msg:
            styled_msg = f"<span style='color: #e74c3c; font-weight: bold;'>{msg}</span>"
        elif "ricerca" in lower_msg or "download" in lower_msg or "avviata" in lower_msg:
            styled_msg = f"<span style='color: #3498db;'>{msg}</span>"
        elif "giocatore" in lower_msg or "coordinate" in lower_msg:
            styled_msg = f"<span style='color: #f1c40f;'>{msg}</span>"
            
        self.console.append(f"<span style='color: #888896;'>[{time.strftime('%H:%M:%S')}]</span> {styled_msg}")

    # Saves loading and folder selectors
    def select_saves_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Seleziona il mondo (oppure la cartella saves o .minecraft)", self.current_world_path or self.saves_dir)
        if folder:
            self.open_path(folder)

    def open_path(self, path):
        """Opens whatever world-related path the user gives (world, region, saves, .minecraft...)."""
        found = world_locator.resolve(path)
        if not found:
            self.log(f"Errore: nessun mondo di Minecraft trovato in {path}")
            QMessageBox.warning(
                self, "Mondo non trovato",
                f"Nel percorso:\n{path}\n\nnon c'e' un mondo di Minecraft (manca level.dat) ne' una cartella saves.\n"
                "Scegli la cartella del mondo, ad esempio .minecraft\\saves\\NomeMondo.")
            self.dir_input.setText(self.current_world_path or self.saves_dir)
            return
        self.saves_dir = found["saves_dir"]
        self.pending_world = found["world"]
        self.pending_dimension = found["dimension"]
        what = f"mondo '{found['world']}'" if found["world"] else "cartella dei salvataggi"
        self.log(f"Percorso riconosciuto: {what} ({self.saves_dir})")
        self.scan_worlds()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if urls:
            self.open_path(urls[0])

    def scan_worlds(self):
        worlds = world_locator.list_worlds(self.saves_dir)
        self.world_select.blockSignals(True)
        self.world_select.clear()
        self.world_select.addItems(worlds)
        self.dir_input.setText(self.saves_dir)
        self.log(f"Trovati {len(worlds)} mondi in {self.saves_dir}.")
        if not worlds:
            self.world_select.blockSignals(False)
            self.world_changed()
            return
        # The requested world, otherwise the most recently played one
        target = self.pending_world if self.pending_world in worlds else worlds[0]
        self.pending_world = None
        self.world_select.setCurrentIndex(worlds.index(target))
        self.world_select.blockSignals(False)
        self.world_changed()

    def world_changed(self):
        world_name = self.world_select.currentText()
        self.dim_select.blockSignals(True)
        self.dim_select.clear()
        self.available_dims = []
        if not world_name:
            self.current_world_path = None
            self.dim_select.blockSignals(False)
            self.region_select.clear()
            self.update_player_info_display()
            return

        self.current_world_path = os.path.join(self.saves_dir, world_name)
        self.dir_input.setText(self.current_world_path)
        self.settings.setValue("last_path", self.current_world_path)
        self.available_dims = world_locator.region_dirs(self.current_world_path)
        labels = [label for label, _ in self.available_dims]
        self.dim_select.addItems(labels)
        if labels:
            want = self.pending_dimension or self._player_dimension_label() or "Overworld"
            if self.pending_dimension and want not in labels:
                self.log(f"La dimensione {want} di questo mondo non ha ancora regioni generate: apro {labels[0]}.")
            self.dim_select.setCurrentIndex(labels.index(want) if want in labels else 0)
        self.pending_dimension = None
        self.dim_select.blockSignals(False)
        self.update_player_info_display()
        self.scan_regions()

        # Centering player region automatically on world load after a small delay to let UI settle
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(50, self.go_to_player_region)

    def dimension_changed(self):
        self.scan_regions()
        self.go_to_player_region()

    def current_dimension_id(self):
        label = self.dim_select.currentText() or "Overworld"
        return world_locator.DIMENSION_IDS.get(label, "minecraft:overworld")

    def _player_dimension_label(self):
        self.load_player_position(quiet=True)
        for label, dim_id in world_locator.DIMENSION_IDS.items():
            if dim_id == self.player_dimension:
                return label
        return None

    def get_region_dir(self):
        if not self.current_world_path:
            return None
        idx = self.dim_select.currentIndex()
        if 0 <= idx < len(self.available_dims):
            return self.available_dims[idx][1]
        region_dir = os.path.join(self.current_world_path, "region")
        if not os.path.exists(region_dir):
            region_dir = os.path.join(self.current_world_path, "dimensions", "minecraft", "overworld", "region")
        return region_dir

    def scan_regions(self):
        self.region_select.clear()
        if not self.current_world_path:
            return

        region_dir = self.get_region_dir()
        if not region_dir or not os.path.exists(region_dir):
            world_name = os.path.basename(self.current_world_path)
            self.log(f"Nessun file di regione trovato in {world_name}: apri il mondo almeno una volta in Minecraft.")
            return
            
        # Get all .mca files; open the player's region directly (one load instead of two)
        regions = sorted(f for f in os.listdir(region_dir) if f.endswith(".mca"))
        target = 0
        pos = self.load_player_position(quiet=True)
        if pos and self.player_dimension in (None, self.current_dimension_id()):
            name = f"r.{int(pos[0] // 512)}.{int(pos[2] // 512)}.mca"
            if name in regions:
                target = regions.index(name)
        self.region_select.blockSignals(True)
        self.region_select.addItems(regions)
        self.region_select.setCurrentIndex(target)
        self.region_select.blockSignals(False)
        self.log(f"Scansionati {len(regions)} file di regione nel mondo.")
        self.region_changed()

    def region_changed(self):
        region_file = self.region_select.currentText()
        if not region_file or not self.current_world_path:
            self.current_region = None
            self.map_viewer.set_region(None)
            return
            
        region_path = os.path.join(self.get_region_dir(), region_file)
        self.log(f"Caricamento regione {region_file}...")
        
        try:
            self.current_region = MCARegion(region_path)
            self.map_viewer.set_region(self.current_region)
            self.log(f"Regione {region_file} caricata correttamente! (r.{self.current_region.rx}.{self.current_region.rz})")
            
            # Load player coordinates from world saves
            player_pos = self.load_player_position()
            if player_pos and self.player_dimension not in (None, self.current_dimension_id()):
                player_pos = None
            if player_pos:
                px, py, pz = player_pos
                self.map_viewer.set_player_position(px, pz)
                self.log(f"Posizione giocatore trovata a X: {px:.1f}, Y: {py:.1f}, Z: {pz:.1f}")
            else:
                self.map_viewer.set_player_position(None, None)
                self.log("Dati del giocatore non trovati nel mondo (gioco mai avviato o modalità server).")
            self.update_player_info_display()
        except Exception as e:
            self.log(f"Errore nel caricamento della regione: {e}")
            self.current_region = None
            self.map_viewer.set_region(None)

    def load_player_position(self, quiet=False):
        if not self.current_world_path:
            return None
        log = self.log
        if quiet:
            self.log = lambda msg: None
        try:
            return self._load_player_position()
        finally:
            self.log = log

    @staticmethod
    def _dimension_id(value):
        if value is None:
            return None
        legacy = {0: "minecraft:overworld", -1: "minecraft:the_nether", 1: "minecraft:the_end"}
        try:
            return legacy.get(int(value), "minecraft:overworld")
        except (TypeError, ValueError):
            return str(value)

    def _load_player_position(self):
        self.player_dimension = None
        try:
            # 1. Try reading level.dat Player pos (legacy or modded formats)
            level_path = os.path.join(self.current_world_path, "level.dat")
            if os.path.exists(level_path):
                try:
                    level_nbt, _ = load_nbt(level_path)
                    data = level_nbt.get("Data", {})
                    player = data.get("Player", {})
                    pos_list = player.get("Pos", [])
                    if len(pos_list) >= 3:
                        self.player_dimension = self._dimension_id(player.get("Dimension", "minecraft:overworld"))
                        self.log(f"Coordinate giocatore lette da level.dat: ({float(pos_list[0]):.1f}, {float(pos_list[1]):.1f}, {float(pos_list[2]):.1f})")
                        return float(pos_list[0]), float(pos_list[1]), float(pos_list[2])
                except Exception as e:
                    self.log(f"Avviso: errore lettura level.dat player pos: {e}")

            # 2. Extract UUID of singleplayer player from level.dat (modern Minecraft 1.16+)
            player_uuid_str = None
            if os.path.exists(level_path):
                try:
                    level_nbt, _ = load_nbt(level_path)
                    data = level_nbt.get("Data", {})
                    uuid_ints = data.get("singleplayer_uuid")
                    if uuid_ints and len(uuid_ints) == 4:
                        import struct, uuid
                        uuid_bytes = struct.pack('>4i', *[int(x) for x in uuid_ints])
                        player_uuid_str = str(uuid.UUID(bytes=uuid_bytes))
                except Exception as e:
                    pass

            player_dirs = [
                os.path.join(self.current_world_path, "playerdata"),
                os.path.join(self.current_world_path, "players"),
                os.path.join(self.current_world_path, "players", "data")
            ]

            # Try locating the exact UUID dat file first
            if player_uuid_str:
                for p_dir in player_dirs:
                    if os.path.exists(p_dir):
                        p_path = os.path.join(p_dir, f"{player_uuid_str}.dat")
                        if os.path.exists(p_path):
                            try:
                                p_nbt, _ = load_nbt(p_path)
                                pos_list = p_nbt.get("Pos", [])
                                if len(pos_list) >= 3:
                                    self.player_dimension = self._dimension_id(p_nbt.get("Dimension", "minecraft:overworld"))
                                    self.log(f"Coordinate giocatore lette da {os.path.basename(p_dir)}/{player_uuid_str}.dat: ({float(pos_list[0]):.1f}, {float(pos_list[1]):.1f}, {float(pos_list[2]):.1f})")
                                    return float(pos_list[0]), float(pos_list[1]), float(pos_list[2])
                            except Exception as e:
                                self.log(f"Avviso: Errore lettura file giocatore {p_path}: {e}")

            # Fallback to scanning folder and picking the newest modified dat file
            for p_dir in player_dirs:
                if os.path.exists(p_dir):
                    p_files = [f for f in os.listdir(p_dir) if f.endswith(".dat") and not f.endswith("_old")]
                    if p_files:
                        p_files.sort(key=lambda x: os.path.getmtime(os.path.join(p_dir, x)), reverse=True)
                        p_path = os.path.join(p_dir, p_files[0])
                        try:
                            p_nbt, _ = load_nbt(p_path)
                            pos_list = p_nbt.get("Pos", [])
                            if len(pos_list) >= 3:
                                self.player_dimension = self._dimension_id(p_nbt.get("Dimension", "minecraft:overworld"))
                                self.log(f"Coordinate giocatore lette da {os.path.basename(p_dir)}/{os.path.basename(p_path)}: ({float(pos_list[0]):.1f}, {float(pos_list[1]):.1f}, {float(pos_list[2]):.1f})")
                                return float(pos_list[0]), float(pos_list[1]), float(pos_list[2])
                        except Exception as e:
                            self.log(f"Avviso: Errore lettura file giocatore {p_path}: {e}")

            # 3. Fallback: level.dat spawn position (spawn -> pos)
            if os.path.exists(level_path):
                try:
                    level_nbt, _ = load_nbt(level_path)
                    data = level_nbt.get("Data", {})
                    self.player_dimension = "minecraft:overworld"
                    spawn = data.get("spawn", {})
                    if spawn and "pos" in spawn:
                        pos = spawn["pos"]
                        if len(pos) >= 3:
                            self.log(f"Coordinate spawn lette da level.dat (spawn->pos): ({float(pos[0]):.1f}, {float(pos[1]):.1f}, {float(pos[2]):.1f})")
                            return float(pos[0]), float(pos[1]), float(pos[2])

                    # 4. Secondary fallback SpawnX, SpawnY, SpawnZ
                    sx = data.get("SpawnX")
                    sy = data.get("SpawnY")
                    sz = data.get("SpawnZ")
                    if sx is not None and sy is not None and sz is not None:
                        self.log(f"Coordinate spawn lette da level.dat (SpawnX/Y/Z): ({float(sx):.1f}, {float(sy):.1f}, {float(sz):.1f})")
                        return float(sx), float(sy), float(sz)
                except Exception as e:
                    self.log(f"Avviso: errore lettura level.dat spawn pos: {e}")

        except Exception as e:
            self.log(f"Errore nella lettura dei dati giocatore o spawn: {e}")
        return None

    def update_player_info_display(self):
        player_pos = self.load_player_position()
        if player_pos:
            px, py, pz = player_pos
            rx = int(px // 512)
            rz = int(pz // 512)
            self.player_info_lbl.setText(f"Giocatore: X: {px:.1f}, Y: {py:.1f}, Z: {pz:.1f}\nRegione: r.{rx}.{rz}.mca")
            self.go_to_player_btn.setEnabled(True)
        else:
            self.player_info_lbl.setText("Giocatore: Non trovato")
            self.go_to_player_btn.setEnabled(False)

    def go_to_player_region(self):
        player_pos = self.load_player_position()
        if not player_pos:
            self.log("Impossibile trovare la posizione del giocatore!")
            return
            
        if self.player_dimension not in (None, self.current_dimension_id()):
            self.log(f"Il giocatore si trova in un'altra dimensione ({self.player_dimension}).")
            return
        px, py, pz = player_pos
        rx = int(px // 512)
        rz = int(pz // 512)
        target_region_file = f"r.{rx}.{rz}.mca"
        
        self.log(f"Ricerca file regione per il giocatore: {target_region_file}...")
        
        # Case-insensitive combobox matching loop
        index = -1
        for i in range(self.region_select.count()):
            if self.region_select.itemText(i).lower() == target_region_file.lower():
                index = i
                break
                
        if index >= 0:
            self.region_select.setCurrentIndex(index)
            local_x = px - rx * 512
            local_z = pz - rz * 512
            
            from PyQt6.QtCore import QPointF
            self.map_viewer.pan_offset = QPointF(256 - local_x, 256 - local_z)
            self.map_viewer.update()
            self.log(f"Mappa centrata sul giocatore a coordinate relative ({local_x:.1f}, {local_z:.1f})")
        else:
            self.log(f"Il file di regione {target_region_file} non esiste in questo mondo!")

    # Local structures management
    def load_local_templates(self):
        self.local_list.clear()
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir, exist_ok=True)
            
        files = [f for f in os.listdir(self.templates_dir) if f.endswith(('.nbt', '.schem', '.schematic'))]
        for f in files:
            self.local_list.addItem(f)

    def import_custom_structure(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Apri file struttura", "", "Minecraft Structure (*.nbt *.schem *.schematic)")
        if file_path:
            # Copy to templates dir
            dest = os.path.join(self.templates_dir, os.path.basename(file_path))
            try:
                shutil.copy2(file_path, dest)
                self.load_local_templates()
                # Find and select the imported item
                for i in range(self.local_list.count()):
                    if self.local_list.item(i).text() == os.path.basename(file_path):
                        self.local_list.setCurrentRow(i)
                        break
                self.log(f"Importato {os.path.basename(file_path)} con successo.")
            except Exception as e:
                self.log(f"Impossibile importare il file: {e}")

    def local_structure_selected(self):
        selected_items = self.local_list.selectedItems()
        if not selected_items:
            return
            
        filename = selected_items[0].text()
        file_path = os.path.join(self.templates_dir, filename)
        
        self.load_structure_file(file_path, filename)

    def load_structure_file(self, file_path, name):
        try:
            self.selected_structure = Structure.load(file_path)
            self.selected_structure_name = name
            self.map_viewer.set_selected_structure(self.selected_structure)
            
            self.update_structure_info()
            self.log(f"Caricata struttura {name} ({self.selected_structure.width}x{self.selected_structure.length}). R per ruotare.")

            modded = self.selected_structure.modded_blocks()
            if modded:
                total = sum(modded.values())
                self.log(f"Avviso: {total} blocchi di mod ({', '.join(sorted(modded))}). "
                         f"In un mondo vanilla verranno saltati.")
            if self.selected_structure.is_pre_flattening():
                self.log(f"Errore: {name} usa il formato pre-1.13 (DataVersion {self.selected_structure.data_version}) "
                         f"e non puo' essere iniettato. Caricalo con uno structure block e risalvalo.")

            # Update check box status
            self.check_injection_readiness()
        except Exception as e:
            self.log(f"Errore nel caricamento della struttura: {e}")
            self.selected_structure = None
            self.map_viewer.set_selected_structure(None)
            self.struct_info_box.setText("Errore di caricamento.")

    # Online search and download
    def search_online(self):
        query = self.search_input.text().strip()
        if not query:
            return
            
        self.log(f"Ricerca online per '{query}'...")
        self.online_list.clear()
        
        # Run scraper search
        results = search_minecraft_schematics(query)
        for r in results:
            item = QListWidgetItem(f"{r['title']} [{r['category']}]")
            # Store metadata in item custom user role
            item.setData(Qt.ItemDataRole.UserRole, r)
            self.online_list.addItem(item)
            
        self.log(f"Trovati {len(results)} risultati.")

    def online_structure_selected(self):
        selected_items = self.online_list.selectedItems()
        if not selected_items:
            self.download_btn.setEnabled(False)
            return
            
        metadata = selected_items[0].data(Qt.ItemDataRole.UserRole)
        self.download_btn.setEnabled(True)
        
        info = (
            f"<b>Nome:</b> {metadata['title']}<br>"
            f"<b>Categoria:</b> {metadata['category']}<br>"
            f"<b>Autore:</b> {metadata['author']}<br>"
            f"<b>Sorgente:</b> {metadata['source']}<br>"
            f"<b>Descrizione:</b> {metadata['description']}"
        )
        self.struct_info_box.setText(info)

    def download_selected_structure(self):
        selected_items = self.online_list.selectedItems()
        if not selected_items:
            return
            
        metadata = selected_items[0].data(Qt.ItemDataRole.UserRole)
        dl_url = metadata["download_url"]
        
        # Decide file name
        ext = ".schematic"
        if "medieval/tower" in dl_url:
            ext = ".schematic"
        elif ".nbt" in dl_url or dl_url.startswith("local:"):
            ext = ".nbt"
            
        filename = metadata["title"].replace(" ", "_").lower() + ext
        dest_path = os.path.join(self.templates_dir, filename)
        
        self.log(f"Download in corso: {metadata['title']}...")
        self.download_btn.setEnabled(False)
        QApplication.processEvents() # Refresh UI
        
        success = download_structure(dl_url, dest_path, self.templates_dir)
        self.download_btn.setEnabled(True)
        
        if success:
            self.log(f"Download completato: salvato come {filename}")
            self.load_local_templates()
            # Switch tab to local and select it
            self.tabs.setCurrentIndex(0)
            for i in range(self.local_list.count()):
                if self.local_list.item(i).text() == filename:
                    self.local_list.setCurrentRow(i)
                    break
        else:
            self.log("Errore nel download. Il link potrebbe richiedere l'accesso al sito web.")

    # UI updates and placement handles
    def update_hover_coordinates(self, world_x, world_z, height_y):
        reg_file = self.region_select.currentText() or "--"
        self.coord_status.setText(f"Coordinate Globali: X: {world_x}, Z: {world_z} | Altezza Y terreno: {height_y} | Regione: {reg_file}")
        
        # Snap y spinbox to terrain height if not locked yet
        if not self.locked_placement:
            if hasattr(self, 'auto_y_checkbox') and self.auto_y_checkbox.isChecked():
                grid_x = self.map_viewer.preview_grid_x
                grid_z = self.map_viewer.preview_grid_z
                avg_h = self.get_average_footprint_height(grid_x, grid_z)
                self.y_spinbox.setValue(avg_h)
            else:
                # The structure's first layer goes on the block above the terrain
                self.y_spinbox.setValue(height_y + 1)

    def lock_placement_coordinate(self, grid_x, grid_z):
        self.locked_placement = (grid_x, grid_z)
        # Snap Spinbox to average footprint height or individual coordinate height
        if hasattr(self, 'auto_y_checkbox') and self.auto_y_checkbox.isChecked():
            avg_h = self.get_average_footprint_height(grid_x, grid_z)
            self.y_spinbox.setValue(avg_h)
        else:
            cx = grid_x // 16
            cz = grid_z // 16
            bx = grid_x % 16
            bz = grid_z % 16
            
            heights = self.map_viewer.get_chunk_heightmap(cx, cz) if 0 <= grid_x < 512 and 0 <= grid_z < 512 else None
            if heights:
                self.y_spinbox.setValue(heights[bz * 16 + bx] + 1)
            
        world_x = self.current_region.rx * 512 + grid_x
        world_z = self.current_region.rz * 512 + grid_z
        self.lock_feedback_lbl.setText(f"Iniezione bloccata a X: {world_x}, Z: {world_z}")
        self.lock_feedback_lbl.setStyleSheet("color: #2ecc71; font-weight: bold; font-size: 11px;")
        self.check_injection_readiness()

    def stage_placement(self):
        if not self.current_region or not self.selected_structure or not self.locked_placement:
            return
            
        grid_x, grid_z = self.locked_placement
        y_val = self.y_spinbox.value()
        
        # Create a display name
        s_name = self.selected_structure_name
        item_x = self.current_region.rx * 512 + grid_x
        item_z = self.current_region.rz * 512 + grid_z
        display_name = f"{s_name} ({item_x}, {y_val}, {item_z})"
        
        # Copy the structure object so it is frozen in its current state
        import copy
        structure_copy = copy.copy(self.selected_structure)
        
        item_data = {
            "structure": structure_copy,
            "world_x": item_x,
            "world_z": item_z,
            "y_coord": y_val,
            "name": s_name,
            "preview_pixmap": self.map_viewer.structure_preview_pixmap
        }
        
        self.staged_placements.append(item_data)
        
        # Add to UI list widget
        self.staged_list.addItem(display_name)
        
        # Update map_viewer list of staged placements
        self.map_viewer.staged_placements = self.staged_placements
        self.map_viewer.update()
        
        self.log(f"Aggiunta in coda: {display_name}")
        
        # Reset current locked placement to let them choose next location/structure
        self.locked_placement = None
        self.map_viewer.is_locked = False
        self.lock_feedback_lbl.setText("Fai clic sulla mappa per posizionare.")
        self.lock_feedback_lbl.setStyleSheet("color: #e67e22; font-weight: bold; font-size: 11px;")
        
        self.check_injection_readiness()

    def remove_selected_staged(self):
        selected_rows = [self.staged_list.row(item) for item in self.staged_list.selectedItems()]
        if not selected_rows:
            return
            
        for row in sorted(selected_rows, reverse=True):
            removed = self.staged_placements.pop(row)
            self.staged_list.takeItem(row)
            self.log(f"Rimossa dalla coda: {removed['name']}")
            
        self.map_viewer.staged_placements = self.staged_placements
        self.map_viewer.update()
        self.check_injection_readiness()

    def clear_all_staged(self):
        self.staged_placements.clear()
        self.staged_list.clear()
        self.map_viewer.staged_placements = []
        self.map_viewer.update()
        self.log("Coda di iniezione svuotata.")
        self.check_injection_readiness()

    def staged_list_selection_changed(self):
        has_selection = len(self.staged_list.selectedItems()) > 0
        self.remove_staged_btn.setEnabled(has_selection)

    def check_injection_readiness(self):
        # Stage button is active if there is an active locked structure
        if self.current_region and self.selected_structure and self.locked_placement is not None:
            self.stage_btn.setEnabled(True)
        else:
            self.stage_btn.setEnabled(False)
            
        self.clear_staged_btn.setEnabled(len(self.staged_placements) > 0)
        
        # Apply button is active if we have staged items OR an active selection locked
        if len(self.staged_placements) > 0:
            self.apply_btn.setEnabled(True)
            self.apply_btn.setText(f"Inietta Strutture nel Mondo ({len(self.staged_placements)})")
        elif self.current_region and self.selected_structure and self.locked_placement is not None:
            self.apply_btn.setEnabled(True)
            self.apply_btn.setText("Inietta Struttura Selezionata")
        else:
            self.apply_btn.setEnabled(False)
            self.apply_btn.setText("Inietta Struttura nel Mondo")
            
        if hasattr(self, 'suggest_pos_btn'):
            self.suggest_pos_btn.setEnabled(self.current_region is not None and self.selected_structure is not None)

    def get_average_footprint_height(self, grid_x, grid_z):
        """Suggested Y for the structure's first layer: one above the average terrain top."""
        if not self.current_region or not self.selected_structure or not hasattr(self.map_viewer, 'region_heights'):
            return 64
        sw = self.selected_structure.width
        sl = self.selected_structure.length
        
        total_height = 0
        count = 0
        for bz in range(sl):
            for bx in range(sw):
                gx = grid_x + bx
                gz = grid_z + bz
                if 0 <= gx < 512 and 0 <= gz < 512:
                    total_height += self.map_viewer.region_heights[gz][gx]
                    count += 1
        if count > 0:
            return int(round(total_height / count)) + 1
        return 64

    def suggest_optimal_position(self):
        if not self.current_region or not self.selected_structure:
            return
            
        sw = self.selected_structure.width
        sl = self.selected_structure.length
        
        self.log("Ricerca posizione ottimale in corso (minimizzazione dislivello)...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        
        best_gx = self.map_viewer.preview_grid_x
        best_gz = self.map_viewer.preview_grid_z
        best_score = float('inf')
        
        current_gx = self.map_viewer.preview_grid_x
        current_gz = self.map_viewer.preview_grid_z
        
        # Scan region for flatest spot nearby with step=4
        for gz in range(0, 512 - sl, 4):
            for gx in range(0, 512 - sw, 4):
                # Sample heights at corners and center
                x_coords = [gx, gx + sw - 1, gx, gx + sw - 1, gx + sw // 2]
                z_coords = [gz, gz, gz + sl - 1, gz + sl - 1, gz + sl // 2]
                
                heights = []
                for x, z in zip(x_coords, z_coords):
                    heights.append(self.map_viewer.region_heights[z][x])
                    
                h_min = min(heights)
                h_max = max(heights)
                
                # Variance of sample
                avg = sum(heights) / len(heights)
                variance = sum((h - avg) ** 2 for h in heights) / len(heights)
                
                # Distance penalty from current position
                dist = ((gx - current_gx) ** 2 + (gz - current_gz) ** 2) ** 0.5
                
                # Score (variance + proximity weight)
                score = variance + (dist * 0.05)
                
                # Avoid water or extreme heights
                avg_h = int(round(avg)) + 1
                if avg_h < 60:
                    score += 500  # ocean penalty
                elif avg_h > 150:
                    score += 100  # peak penalty
                    
                if score < best_score:
                    best_score = score
                    best_gx = gx
                    best_gz = gz
                    
        QApplication.restoreOverrideCursor()
        
        # Apply optimal coordinates
        self.map_viewer.preview_grid_x = best_gx
        self.map_viewer.preview_grid_z = best_gz
        self.locked_placement = (best_gx, best_gz)
        self.map_viewer.is_locked = True
        
        # Set height to average terrain height at new footprint
        avg_h = self.get_average_footprint_height(best_gx, best_gz)
        self.y_spinbox.setValue(avg_h)
        
        self.map_viewer.update()
        self.lock_feedback_lbl.setText(f"Iniezione bloccata a X: {self.current_region.rx * 512 + best_gx}, Z: {self.current_region.rz * 512 + best_gz}")
        self.lock_feedback_lbl.setStyleSheet("color: #2ecc71; font-weight: bold; font-size: 11px;")
        self.check_injection_readiness()
        
        self.log(f"Posizione ottimale trovata a X: {self.current_region.rx * 512 + best_gx}, Z: {self.current_region.rz * 512 + best_gz} (Altezza media consigliata: Y: {avg_h}).")

    def update_structure_info(self):
        s = self.selected_structure
        if not s:
            return
        modded = s.modded_blocks()
        info = (
            f"<b>Nome:</b> {self.selected_structure_name}<br>"
            f"<b>Larghezza (X):</b> {s.width}<br>"
            f"<b>Altezza (Y):</b> {s.height}<br>"
            f"<b>Lunghezza (Z):</b> {s.length}<br>"
            f"<b>Blocchi totali:</b> {len(s.blocks)}<br>"
            f"<b>Formato:</b> {os.path.splitext(self.selected_structure_name)[1].upper()}"
        )
        if s.data_version is not None:
            info += f"<br><b>DataVersion:</b> {s.data_version}"
        if modded:
            info += f"<br><span style='color:#e67e22;'><b>Blocchi di mod:</b> {sum(modded.values())} ({', '.join(sorted(modded))})</span>"
        self.struct_info_box.setText(info)

    def rotate_current_structure(self):
        if self.selected_structure:
            self.selected_structure = self.selected_structure.rotate(90)
            # Keep the locked position: rotating should not move the placement
            self.map_viewer.set_selected_structure(self.selected_structure, keep_lock=self.locked_placement is not None)
            self.log("Struttura ruotata di 90° in senso orario.")
            self.update_structure_info()

    def apply_structure_to_world(self):
        if not self.current_region:
            return
            
        # Check if the specific world is open (locked) or if Minecraft/Java is active
        minecraft_active = is_minecraft_running()
        world_locked = False
        if self.current_world_path:
            lock_path = os.path.join(self.current_world_path, "session.lock")
            if os.path.exists(lock_path):
                try:
                    f = open(lock_path, "r+")
                    f.close()
                except IOError:
                    world_locked = True
                    
        if world_locked or minecraft_active:
            msg = ""
            if world_locked:
                msg += "Il mondo selezionato risulta attualmente APERTO in Minecraft (file session.lock bloccato).\n\n"
            else:
                msg += "Rilevato Minecraft o processo Java (javaw.exe) in esecuzione in background.\n\n"
                
            msg += "Se inietti le strutture mentre il gioco è aperto sul mondo, le modifiche verranno annullate dal gioco stesso e rischi di corrompere il salvataggio.\n\nVuoi procedere comunque?"
            
            reply = QMessageBox.warning(
                self, 
                "Attenzione: Mondo o Gioco attivo",
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                self.log("Iniezione annullata per motivi di sicurezza.")
                return
            
        # Determine items to inject
        placements_to_inject = []
        if self.staged_placements:
            placements_to_inject = list(self.staged_placements)
        elif self.selected_structure and self.locked_placement is not None:
            grid_x, grid_z = self.locked_placement
            y_coord = self.y_spinbox.value()
            placements_to_inject = [{
                "structure": self.selected_structure,
                "world_x": self.current_region.rx * 512 + grid_x,
                "world_z": self.current_region.rz * 512 + grid_z,
                "y_coord": y_coord,
                "name": self.selected_structure_name
            }]
            
        if not placements_to_inject:
            self.log("Nessuna struttura posizionata o in coda da iniettare.")
            return
            
        old_format = [p["name"] for p in placements_to_inject if p["structure"].is_pre_flattening()]
        if old_format:
            QMessageBox.critical(
                self, "Formato non supportato",
                "Queste strutture usano il formato pre-1.13 e i loro blocchi non esistono piu' nel gioco:\n\n"
                + "\n".join(old_format)
                + "\n\nCaricale con uno structure block in Minecraft e risalvale prima di iniettarle."
            )
            return

        # The backup of every modified region is made by World.save()

        self.log(f"Iniezione di {len(placements_to_inject)} strutture avviata in background...")
        
        # Disable UI during thread run
        self.apply_btn.setEnabled(False)
        self.go_to_player_btn.setEnabled(False)
        self.stage_btn.setEnabled(False)
        self.remove_staged_btn.setEnabled(False)
        self.clear_staged_btn.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        # Structures crossing the region border are written to the neighbouring regions too
        world = World(self.get_region_dir(), preloaded=[self.current_region])
        self.last_injected = placements_to_inject

        # Instantiate and start the worker thread
        self.injection_thread = InjectionWorker(
            world,
            placements_to_inject,
            fill_foundations=self.fill_foundation_checkbox.isChecked(),
            clear_terrain=self.clear_terrain_checkbox.isChecked(),
            skip_modded=self.skip_modded_checkbox.isChecked()
        )
        self.injection_thread.progress.connect(self.log)
        self.injection_thread.success.connect(self.on_injection_success)
        self.injection_thread.permission_error.connect(self.on_injection_permission_error)
        self.injection_thread.error.connect(self.on_injection_error)
        self.injection_thread.finished.connect(self.on_injection_finished)
        self.injection_thread.start()

    def on_injection_success(self):
        self.log("Tutte le strutture sono state iniettate con successo!")
        
        # Clear queue after successful write
        if self.staged_placements:
            self.clear_all_staged()
            
        # Refresh map viewer
        self.map_viewer.heights_cache.clear()
        self.map_viewer.render_map()
        self.map_viewer.update()
        self.show_injection_summary()

    def teleport_command(self, item):
        """/tp command that puts the player just south of a placed structure, looking at it."""
        s = item["structure"]
        x = item["world_x"] + s.width // 2
        z = item["world_z"] + s.length + 3
        y = item["y_coord"]
        if self.current_region:
            gx, gz = x - self.current_region.rx * 512, z - self.current_region.rz * 512
            if 0 <= gx < 512 and 0 <= gz < 512:
                y = max(y, self.map_viewer.region_heights[gz][gx] + 1)
        return f"/tp @s {x} {y} {z} 180 10"

    def show_injection_summary(self):
        """Tells the user exactly where to find the structures in the game."""
        items = getattr(self, "last_injected", None) or []
        stats = getattr(getattr(self, "injection_thread", None), "stats", None) or {}
        if not items:
            return
        world = os.path.basename(self.current_world_path or "")
        dim = self.dim_select.currentText() or "Overworld"
        if stats and stats.get("placed", 0) == 0:
            QMessageBox.warning(
                self, "Nessun blocco inserito",
                "Nessun blocco e' stato scritto: l'area scelta non e' ancora generata (o e' in un formato vecchio).\n"
                "Esplora quella zona in gioco, chiudi il mondo e riprova.")
            return
        cmd = self.teleport_command(items[0])
        QApplication.clipboard().setText(cmd)
        lines = [f"- {it['name']}: X {it['world_x']}, Y {it['y_coord']}, Z {it['world_z']}" for it in items[:8]]
        if len(items) > 8:
            lines.append(f"... e altre {len(items) - 8}")
        self.log(f"Per vederle in gioco: Giocatore singolo -> '{world}', poi {cmd} (copiato negli appunti).")
        QMessageBox.information(
            self, "Strutture inserite",
            f"Strutture inserite nel mondo \"{world}\" ({dim}):\n" + "\n".join(lines) +
            f"\n\nPer vederle: apri Minecraft -> Giocatore singolo -> \"{world}\".\n"
            f"Per arrivarci subito scrivi in chat (con i trucchi attivi):\n{cmd}\n"
            "Il comando e' gia' copiato negli appunti: premi T e poi Ctrl+V.\n\n"
            "Nota: l'app modifica solo i mondi salvati su questo PC; i server multiplayer non cambiano.")

    def on_injection_permission_error(self, err_msg):
        self.log(f"ERRORE DI PERMESSO (Accesso Negato): {err_msg}")
        self.log("Se hai già chiuso il gioco, Windows potrebbe bloccare la scrittura. Risolvi così:")
        self.log("  - Apri Gestione Attività (Ctrl+Shift+Esc), cerca 'javaw.exe' o 'Minecraft' e clicca su 'Termina Attività'.")
        self.log("  - Avvia l'app come amministratore con:  py -3 main.py --admin")
        self.log("  - Verifica che la cartella del salvataggio non sia impostata su 'Solo Lettura'.")

    def on_injection_error(self, err_msg):
        self.log(f"Errore grave durante l'iniezione: {err_msg}")

    def on_injection_finished(self):
        QApplication.restoreOverrideCursor()
        self.check_injection_readiness()
        self.update_player_info_display()
        # Clean up thread
        self.injection_thread = None


def _path_from_args(args):
    """World path from the command line: --world PATH, --saves-dir PATH or a bare path."""
    for i, arg in enumerate(args):
        if arg in ("--world", "--saves-dir") and i + 1 < len(args):
            return args[i + 1].strip('"')
        if arg.startswith("--saves-dir "):
            return arg.split(" ", 1)[1].strip('"')
    for arg in args:
        if not arg.startswith("-") and os.path.exists(arg.strip('"')):
            return arg.strip('"')
    return None


def is_minecraft_running():
    try:
        # Java Edition runs as javaw.exe. Minecraft.exe is only the launcher (it stays open
        # while the game is closed), so it must not trigger the warning; an open world is
        # detected reliably through its session.lock anyway.
        output = subprocess.check_output('tasklist /FI "IMAGENAME eq javaw.exe" /NH', shell=True).decode('utf-8', errors='ignore')
        if "javaw.exe" in output:
            return True
    except:
        pass
    return False


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin():
    if not is_admin():
        script = os.path.abspath(sys.argv[0])
        # Find the non-elevated saves dir
        saves_dir = os.path.expandvars(r"%appdata%\.minecraft\saves")
        if not os.path.exists(saves_dir):
            saves_dir = os.path.join(os.path.dirname(script), "saves")
            
        args = sys.argv[1:]
        if not any(arg.startswith("--saves-dir") for arg in args) and os.path.exists(saves_dir):
            args.append(f'--saves-dir "{saves_dir}"')
            
        params = " ".join([f'"{x}"' if not x.startswith('--saves-dir') else x for x in args])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', os.path.dirname(script), 1)
        sys.exit(0)


def main():
    # Administrator rights are not needed to edit saves in %APPDATA%: elevate only on request
    if sys.platform == "win32" and "--admin" in sys.argv:
        sys.argv.remove("--admin")
        run_as_admin()

    app = QApplication(sys.argv)
    window = MinecraftBuilderApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
