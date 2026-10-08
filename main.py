import os
import re
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
    QMessageBox, QCheckBox, QTreeWidget, QTreeWidgetItem, QDialog, QDialogButtonBox, QFormLayout,
    QScrollArea, QFrame
)
from PyQt6.QtGui import QFont, QIcon, QColor
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QSettings, QTimer

from nbt_codec import load_nbt
from mca_codec import MCARegion, UnsupportedChunkFormat
from structure_manager import Structure
from world_editor import World, inject_structures
import world_locator
import game_link
import json
import catalog
import structure_generators as sgen
import village_generator as vgen
import walls
import roads
import world_extractor
from world_editor import WorldTerrain, RecordedTerrain, footprint, footprint_to_text, footprint_from_text
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
QWidget#sidebar, QFrame#sidebar {
    background-color: #1b1b1f;
    border-right: 1px solid #27272a;
}
QTabWidget::pane {
    border: 1px solid #27272a;
    background: #1b1b1f;
    border-radius: 8px;
}
QScrollArea#panel_scroll, QScrollArea#panel_scroll > QWidget#qt_scrollarea_viewport, QWidget#panel_page {
    background-color: #1b1b1f;
    border: none;
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
QTreeWidget {
    background-color: #0f0f11;
    alternate-background-color: #0f0f11;
    border: 1px solid #27272a;
    border-radius: 6px;
    padding: 4px;
    color: #e0e0e8;
    font-size: 12px;
    outline: 0;
    show-decoration-selected: 0;
}
QTreeWidget::item {
    padding: 5px 4px;
    border-radius: 4px;
    color: #e0e0e8;
}
QTreeWidget::item:hover {
    background-color: #27272a;
    color: #2ecc71;
}
QTreeWidget::item:selected {
    background-color: #2ecc71;
    color: #141416;
}
QTreeWidget::branch {
    background: transparent;
    border-image: none;
    image: none;
}
QTreeWidget::branch:selected, QTreeWidget::branch:hover {
    background: transparent;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar::handle:vertical {
    min-height: 24px;
}
QAbstractItemView {
    background-color: #1b1b1f;
    color: #e0e0e8;
    selection-background-color: #2ecc71;
    selection-color: #141416;
    border: 1px solid #27272a;
}
QToolTip {
    background-color: #1b1b1f;
    color: #e0e0e8;
    border: 1px solid #2ecc71;
    padding: 4px;
}
QTabBar QToolButton {
    background-color: #27272a;
    border: 1px solid #3f3f46;
    color: #ffffff;
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
QScrollBar:horizontal {
    border: none;
    background: #141416;
    height: 8px;
}
QScrollBar::handle:horizontal {
    background: #27272a;
    border-radius: 4px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover {
    background: #2ecc71;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
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

    def __init__(self, world, placements_to_inject, fill_foundations=True, clear_terrain=True, skip_modded=True,
                 blend=True):
        super().__init__()
        self.world = world
        self.placements_to_inject = placements_to_inject
        self.fill_foundations = fill_foundations
        self.clear_terrain = clear_terrain
        self.skip_modded = skip_modded
        self.blend = blend
        self.stats = None

    def run(self):
        try:
            t0 = time.perf_counter()
            stats = inject_structures(
                self.world,
                self.placements_to_inject,
                fill_foundations=self.fill_foundations,
                clear_terrain=self.clear_terrain,
                blend=self.blend,
                skip_modded=self.skip_modded,
                log=self.progress.emit,
            )
            self.stats = stats
            self.progress.emit(
                f"Blocchi piazzati: {stats['placed']}, scavati: {stats['cleared']}, fondamenta: {stats['foundation']}, "
                f"terreno raccordato: {stats['blend']} | blocchi naturali rimossi: {stats['destroyed']}"
            )
            if stats["skipped_missing"]:
                reasons = sorted(set(self.world.skipped_chunks.values()))
                self.progress.emit(
                    f"Avviso: {stats['skipped_missing']} blocchi saltati in {len(self.world.skipped_chunks)} chunk "
                    f"({', '.join(reasons)}). Esplora l'area in gioco e riprova."
                )
            if stats.get("entities") or stats.get("block_data"):
                self.progress.emit(f"Entita' aggiunte: {stats.get('entities', 0)}, contenitori riempiti: "
                                   f"{stats.get('block_data', 0)}.")
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
    WALL_HELP = ("Suggerisci il perimetro: le mura vengono proposte intorno alle tue costruzioni vicino al "
                 "giocatore, con la porta dove passa una strada o dove il terreno e' libero e piano. Oppure "
                 "disegnale: clic sui vertici (linee a 0/45/90 gradi, Shift per linee libere), clic sul primo punto "
                 "o Invio per chiudere (C chiude allineato), doppio clic per un tratto aperto, Backspace toglie "
                 "l'ultimo punto, Esc annulla.")
    ROAD_HELP = ("Clicca i punti del tracciato (linee a 0/45/90 gradi, Shift per linee libere), Invio o doppio "
                 "clic per finire, Backspace toglie l'ultimo punto. Vicino a una strada esistente il punto si "
                 "aggancia da solo (cerchio azzurro): le strade fatte col programma e i sentieri o le strade "
                 "lastricate gia' presenti nel mondo. Le estremita' entro 8 blocchi da una strada vengono "
                 "collegate a quella.")

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
        tabs_add = self.tabs.addTab

        def add_scrolling_tab(widget, name):
            """Every tab scrolls: on small screens the buttons keep their size instead of being squashed."""
            area = QScrollArea()
            area.setObjectName("panel_scroll")      # dark background (the system default is light grey)
            area.setWidgetResizable(True)
            area.setFrameShape(QFrame.Shape.NoFrame)
            widget.setObjectName("panel_page")
            area.setWidget(widget)
            return tabs_add(area, name)
        self.tabs.addTab = add_scrolling_tab
        
        # Tab 1: Local structures list
        local_tab = QWidget()
        local_layout = QVBoxLayout(local_tab)
        local_layout.setContentsMargins(4, 4, 4, 4)
        
        self.library_search = QLineEdit()
        self.library_search.setPlaceholderText("Cerca struttura (nome, categoria...)")
        self.library_search.textChanged.connect(self.filter_library)
        local_layout.addWidget(self.library_search)

        self.local_list = QTreeWidget()
        self.local_list.setHeaderHidden(True)
        self.local_list.setIndentation(14)
        self.local_list.itemSelectionChanged.connect(self.local_structure_selected)
        self.local_list.setRootIsDecorated(False)
        # a single click on a category opens or closes it; the arrow is part of the label
        self.local_list.itemClicked.connect(
            lambda item, _col: item.setExpanded(not item.isExpanded()) if item.childCount() else None)
        self.local_list.itemExpanded.connect(self._update_category_label)
        self.local_list.itemCollapsed.connect(self._update_category_label)
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

        def hint(text):
            lbl = QLabel(text)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("font-size: 11px; color: #a0a0b0;")
            return lbl

        # Tab 3: bridges
        bridge_tab = QWidget()
        bl = QVBoxLayout(bridge_tab)
        bl.setContentsMargins(6, 6, 6, 6)
        bl.addWidget(QLabel("Stile del ponte:"))
        self.bridge_style = QComboBox()
        for key, spec in sgen.BRIDGE_STYLES.items():
            self.bridge_style.addItem(spec["title"], key)
        bl.addWidget(self.bridge_style)
        self.bridge_integrate = QCheckBox("Integra con l'ambiente")
        self.bridge_integrate.setChecked(True)
        self.bridge_integrate.setToolTip(
            "Rampe dolci fino alle sponde (anche se sono ad altezze diverse), arco abbastanza alto "
            "sull'acqua per far passare le barche, il ponte scavalca le colline invece di scavarle e "
            "usa i materiali del posto: arenaria nel deserto, fango nelle paludi, il legno degli alberi vicini.")
        bl.addWidget(self.bridge_integrate)
        self.draw_bridge_btn = QPushButton("Disegna ponte tra due sponde")
        self.draw_bridge_btn.clicked.connect(self.start_bridge_mode)
        bl.addWidget(self.draw_bridge_btn)
        bl.addWidget(hint("Clicca sulla mappa la prima sponda e poi la seconda (il ponte e' dritto e parte dal "
                          "primo clic): lunghezza, altezza, piloni e rampe vengono calcolati da soli. Se parti vicino alla fine di un ponte gia' presente (in coda o "
                          "costruito prima), il nuovo lo prosegue senza interruzioni, nello stesso stile e alla "
                          "stessa altezza. Esc per annullare."))
        length_row = QHBoxLayout()
        length_row.addWidget(QLabel("Lunghezza:"))
        self.bridge_length = QSpinBox()
        self.bridge_length.setRange(7, 500)
        self.bridge_length.setValue(25)
        length_row.addWidget(self.bridge_length)
        self.apply_length_btn = QPushButton("Applica")
        self.apply_length_btn.setEnabled(False)
        self.apply_length_btn.clicked.connect(self.apply_bridge_length)
        length_row.addWidget(self.apply_length_btn)
        bl.addLayout(length_row)
        self.bridge_info = hint("Seleziona un ponte dall'elenco (categoria Ponti) per allungarlo o accorciarlo "
                                "mantenendo lo stesso stile.")
        bl.addWidget(self.bridge_info)
        bl.addStretch()
        self.tabs.addTab(bridge_tab, "Ponti")

        # Tab 4: villages
        village_tab = QWidget()
        vl = QVBoxLayout(village_tab)
        vl.setContentsMargins(6, 6, 6, 6)
        vl.addWidget(QLabel("Tipo di villaggio:"))
        self.village_style = QComboBox()
        for key, spec in vgen.STYLES.items():
            self.village_style.addItem(spec["title"], key)
        vl.addWidget(self.village_style)
        vl.addWidget(QLabel("Dimensione:"))
        self.village_size = QComboBox()
        for key in vgen.SIZES:
            self.village_size.addItem(f"{key.capitalize()} ({vgen.SIZES[key][0]} edifici)", key)
        self.village_size.setCurrentIndex(1)
        vl.addWidget(self.village_size)
        self.village_best_btn = QPushButton("Consiglia posizione migliore")
        self.village_best_btn.setObjectName("action_btn")
        self.village_best_btn.clicked.connect(self.suggest_village_site)
        vl.addWidget(self.village_best_btn)
        self.village_btn = QPushButton("Scegli il centro sulla mappa")
        self.village_btn.clicked.connect(self.start_village_mode)
        vl.addWidget(self.village_btn)
        vl.addWidget(hint("Clicca il punto centrale: il villaggio crea piazza, strade, case con la porta verso "
                          "la strada, fattorie e lampioni, evitando acqua e pendii. Ogni edificio si appoggia al "
                          "terreno. Il villaggio va in coda come un'unica voce: controllalo sulla mappa e poi "
                          "premi Inietta."))
        vl.addStretch()
        self.tabs.addTab(village_tab, "Villaggio")

        # Tab: defensive walls
        wall_tab = QWidget()
        wl = QVBoxLayout(wall_tab)
        wl.setContentsMargins(6, 6, 6, 6)
        wl.addWidget(QLabel("Stile delle mura:"))
        self.wall_style = QComboBox()
        for key, spec in walls.WALL_STYLES.items():
            self.wall_style.addItem(spec["title"], key)
        wl.addWidget(self.wall_style)
        row = QHBoxLayout()
        row.addWidget(QLabel("Altezza:"))
        self.wall_height = QSpinBox()
        self.wall_height.setRange(5, 20)
        self.wall_height.setValue(9)
        row.addWidget(self.wall_height)
        self.wall_towers = QCheckBox("Torri ogni")
        self.wall_towers.setChecked(True)
        row.addWidget(self.wall_towers)
        self.wall_spacing = QSpinBox()
        self.wall_spacing.setRange(16, 80)
        self.wall_spacing.setValue(32)
        self.wall_spacing.setSuffix(" blocchi")
        row.addWidget(self.wall_spacing)
        wl.addLayout(row)
        wl.addWidget(QLabel("Porte:"))
        self.wall_gate_type = QComboBox()
        for key, title in walls.GATE_TYPES.items():
            self.wall_gate_type.addItem(title, key)
        self.wall_gate_type.setCurrentIndex(2)
        wl.addWidget(self.wall_gate_type)
        self.wall_lights = QCheckBox("Luci automatiche (sensori di movimento e lampade notturne)")
        self.wall_lights.setChecked(True)
        wl.addWidget(self.wall_lights)
        self.wall_suggest_btn = QPushButton("Suggerisci il perimetro")
        self.wall_suggest_btn.setObjectName("action_btn")
        self.wall_suggest_btn.clicked.connect(self.suggest_walls)
        wl.addWidget(self.wall_suggest_btn)
        self.wall_draw_btn = QPushButton("Disegna il perimetro sulla mappa")
        self.wall_draw_btn.clicked.connect(self.start_wall_mode)
        wl.addWidget(self.wall_draw_btn)
        gate_row = QHBoxLayout()
        self.wall_gate_btn = QPushButton("Aggiungi porta")
        self.wall_gate_btn.clicked.connect(self.start_gate_mode)
        gate_row.addWidget(self.wall_gate_btn)
        self.wall_gate_clear_btn = QPushButton("Togli porte")
        self.wall_gate_clear_btn.clicked.connect(self.clear_wall_gates)
        gate_row.addWidget(self.wall_gate_clear_btn)
        wl.addLayout(gate_row)
        self.wall_edit_btn = QPushButton("Modifica il perimetro (trascina i punti)")
        self.wall_edit_btn.setEnabled(False)
        self.wall_edit_btn.clicked.connect(lambda: self.start_line_edit("walls"))
        wl.addWidget(self.wall_edit_btn)
        self.wall_stage_btn = QPushButton("Metti in coda le mura")
        self.wall_stage_btn.setEnabled(False)
        self.wall_stage_btn.clicked.connect(self.stage_walls)
        wl.addWidget(self.wall_stage_btn)
        wl.addWidget(QLabel("Mura gia' costruite:"))
        self.built_walls_combo = QComboBox()
        wl.addWidget(self.built_walls_combo)
        built_row = QHBoxLayout()
        self.built_walls_edit_btn = QPushButton("Modifica")
        self.built_walls_edit_btn.clicked.connect(lambda: self.edit_built_line("walls"))
        built_row.addWidget(self.built_walls_edit_btn)
        self.built_walls_demolish_btn = QPushButton("Demolisci")
        self.built_walls_demolish_btn.clicked.connect(lambda: self.demolish_built_line("walls"))
        built_row.addWidget(self.built_walls_demolish_btn)
        wl.addLayout(built_row)
        self.wall_info = hint(self.WALL_HELP)
        wl.addWidget(self.wall_info)
        self.wall_gate_type.setToolTip(
            "Leve: il portone e il ponte levatoio hanno una leva dentro, sul muro del corpo di guardia accanto "
            "al passaggio, e una leva nascosta fuori, in un cespuglio a destra della strada d'arrivo. Ogni scatto "
            "di una delle due apre o chiude la porta: apri da fuori, entri e richiudi da dentro.\n"
            "Ponte levatoio: davanti alla porta c'e' un fossato; i sensori sculk sotto la strada fanno emergere "
            "il ponte quando qualcuno si avvicina, la leva lo tiene alzato.\n"
            "Luci: nel passaggio si accendono al movimento, sulle torri di notte. Sulle mura oblique il tratto "
            "vicino alla porta viene raddrizzato; una porta su un angolo viene spostata sul lato piu' lungo.")
        wl.addWidget(hint("Passa il mouse sul tipo di porta per sapere come funzionano leve, sensori e luci."))
        self.wall_plan_input = None
        wl.addStretch()
        self.tabs.addTab(wall_tab, "Mura")

        # Tab: roads
        road_tab = QWidget()
        rl = QVBoxLayout(road_tab)
        rl.setContentsMargins(6, 6, 6, 6)
        rl.addWidget(QLabel("Stile della strada:"))
        self.road_style = QComboBox()
        for key, spec in roads.ROAD_STYLES.items():
            self.road_style.addItem(spec["title"], key)
        self.road_style.setCurrentIndex(1)
        rl.addWidget(self.road_style)
        row = QHBoxLayout()
        row.addWidget(QLabel("Larghezza:"))
        self.road_width = QSpinBox()
        self.road_width.setRange(1, 9)
        self.road_width.setValue(3)
        self.road_width.setSuffix(" blocchi")
        row.addWidget(self.road_width)
        row.addStretch()
        rl.addLayout(row)
        row = QHBoxLayout()
        self.road_lamps = QCheckBox("Lampioni ogni")
        self.road_lamps.setChecked(True)
        row.addWidget(self.road_lamps)
        self.road_lamp_spacing = QSpinBox()
        self.road_lamp_spacing.setRange(6, 48)
        self.road_lamp_spacing.setValue(12)
        self.road_lamp_spacing.setSuffix(" blocchi")
        row.addWidget(self.road_lamp_spacing)
        row.addStretch()
        rl.addLayout(row)
        self.road_kerbs = QCheckBox("Cordoli ai lati (strade larghe almeno 3)")
        self.road_kerbs.setChecked(True)
        rl.addWidget(self.road_kerbs)
        self.road_draw_btn = QPushButton("Disegna la strada sulla mappa")
        self.road_draw_btn.setObjectName("action_btn")
        self.road_draw_btn.clicked.connect(self.start_road_mode)
        rl.addWidget(self.road_draw_btn)
        self.road_edit_btn = QPushButton("Modifica il tracciato (trascina i punti)")
        self.road_edit_btn.setEnabled(False)
        self.road_edit_btn.clicked.connect(lambda: self.start_line_edit("roads"))
        rl.addWidget(self.road_edit_btn)
        self.road_stage_btn = QPushButton("Metti in coda la strada")
        self.road_stage_btn.setEnabled(False)
        self.road_stage_btn.clicked.connect(self.stage_road)
        rl.addWidget(self.road_stage_btn)
        self.road_info = hint(self.ROAD_HELP)
        rl.addWidget(self.road_info)
        rl.addWidget(QLabel("Strade gia' costruite:"))
        self.built_roads_combo = QComboBox()
        rl.addWidget(self.built_roads_combo)
        built_row = QHBoxLayout()
        self.built_roads_edit_btn = QPushButton("Modifica")
        self.built_roads_edit_btn.clicked.connect(lambda: self.edit_built_line("roads"))
        built_row.addWidget(self.built_roads_edit_btn)
        self.built_roads_demolish_btn = QPushButton("Demolisci")
        self.built_roads_demolish_btn.clicked.connect(lambda: self.demolish_built_line("roads"))
        built_row.addWidget(self.built_roads_demolish_btn)
        rl.addLayout(built_row)
        rl.addWidget(hint("Modifica: il tracciato o il perimetro tornano sulla mappa con i punti azzurri; "
                          "trascinali, doppio clic su un tratto aggiunge un punto, clic destro su un punto lo "
                          "toglie. In coda vanno la demolizione della versione vecchia (il terreno torna com'era "
                          "prima) e la costruzione della nuova: premi Inietta. Demolisci toglie e basta."))
        self.road_plan_input = None
        rl.addStretch()
        self.tabs.addTab(road_tab, "Strade")

        # Tab 5: cut an area of a world as a structure
        cut_tab = QWidget()
        cl = QVBoxLayout(cut_tab)
        cl.setContentsMargins(6, 6, 6, 6)
        self.cut_thread = None
        self.cut_btn = QPushButton("Seleziona l'area da ritagliare")
        self.cut_btn.clicked.connect(self.start_cut_mode)
        cl.addWidget(self.cut_btn)
        cl.addWidget(hint("Trascina un rettangolo sulla mappa del mondo da cui copiare. La zona viene salvata "
                          "come struttura nella categoria Ritagli. Con 'Solo costruzioni' il terreno originale "
                          "non viene copiato: quando la incolli su un'altra mappa si appoggia al nuovo terreno "
                          "(cantine comprese) e le fondamenta riempiono i vuoti. Con 'Tutto' viene copiata "
                          "anche la terra."))
        cl.addStretch()
        self.tabs.addTab(cut_tab, "Ritagli")
        
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
        self.map_viewer.bridge_requested.connect(self.on_bridge_requested)
        self.map_viewer.area_selected.connect(self.on_area_selected)
        self.map_viewer.point_selected.connect(self.on_map_point)
        self.map_viewer.polygon_finished.connect(self.on_polygon_finished)
        self.map_viewer.preview_edited.connect(self.on_preview_edited)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.map_viewer.mode_cancelled.connect(
            lambda mode: self.log("Modifica terminata: ora puoi mettere in coda." if mode == "edit_poly"
                                  else "Operazione annullata."))
        self.map_viewer.unlocked.connect(self.unlock_placement)
        self.map_viewer.game_structures_changed.connect(self.update_structure_jump_list)
        self.map_viewer.staged_selected.connect(self.on_staged_selected)
        self.map_viewer.staged_moved.connect(self.move_staged)
        self.map_viewer.staged_action.connect(self.on_staged_action)

        # Map toolbar: overlays and quick navigation
        map_bar = QHBoxLayout()
        map_bar.setContentsMargins(8, 6, 8, 2)
        self.show_placed_cb = QCheckBox("Strutture piazzate")
        self.show_game_cb = QCheckBox("Strutture del gioco")
        self.show_chunks_cb = QCheckBox("Griglia chunk")
        for cb, attr in ((self.show_placed_cb, "show_placed_structures"), (self.show_game_cb, "show_game_structures"),
                         (self.show_chunks_cb, "show_chunk_grid")):
            cb.setChecked(True)
            cb.toggled.connect(lambda on, a=attr: (setattr(self.map_viewer, a, on), self.map_viewer.update()))
            map_bar.addWidget(cb)
        self.show_placed_cb.setToolTip("Le strutture iniettate con questo programma, colorate per categoria.")
        self.show_game_cb.setToolTip("Villaggi, templi, portali e altre strutture generate da Minecraft.")
        map_bar.addStretch()
        # second row: on narrow screens the overlays and the navigation never overlap
        nav_bar = QHBoxLayout()
        nav_bar.setContentsMargins(8, 0, 8, 2)
        self.structure_jump = QComboBox()
        self.structure_jump.setMinimumWidth(160)
        self.structure_jump.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.structure_jump.setMinimumContentsLength(18)
        self.structure_jump.activated.connect(self.jump_to_structure)
        nav_bar.addWidget(self.structure_jump, 1)
        whole_btn = QPushButton("Tutto il mondo")
        whole_btn.setToolTip("Rimpicciolisce la mappa per mostrare tutte le regioni del mondo.")
        whole_btn.clicked.connect(self.map_viewer.show_whole_world)
        nav_bar.addWidget(whole_btn)
        here_btn = QPushButton("Giocatore")
        here_btn.clicked.connect(self.go_to_player_region)
        nav_bar.addWidget(here_btn)
        self.live_btn = QPushButton("Live")
        self.live_btn.setCheckable(True)
        self.live_btn.setToolTip(
            "Mappa dal vivo mentre giochi: la posizione del giocatore e il terreno si aggiornano\n"
            "quando Minecraft salva (salvataggio automatico ogni 5 minuti circa, o 'Salva ed esci').\n"
            "Per aggiornare la posizione SUBITO premi F3+C nel gioco: il programma legge le coordinate copiate.")
        self.live_btn.toggled.connect(self.set_live_mode)
        nav_bar.addWidget(self.live_btn)
        self.follow_cb = QCheckBox("Segui")
        self.follow_cb.setToolTip("In modalita' Live centra la mappa sul giocatore a ogni spostamento.")
        self.follow_cb.setChecked(True)
        self.follow_cb.setEnabled(False)
        nav_bar.addWidget(self.follow_cb)
        self.auto_pos_cb = QCheckBox("Posizione continua")
        self.auto_pos_cb.setToolTip(
            "Minecraft scrive la posizione su disco solo quando salva, e salva quando va in pausa: se la mappa\n"
            "e' su un altro schermo il gioco non va mai in pausa. Con questa opzione, mentre giochi (Minecraft in\n"
            "primo piano, nessuna chat o inventario aperti) il programma preme per te F3+C ogni 2 secondi e legge le\n"
            "coordinate; poi rimette negli appunti quello che c'era. Nella chat del gioco compare il messaggio di F3+C.")
        self.auto_pos_cb.setChecked(game_link.IS_WINDOWS)
        self.auto_pos_cb.setEnabled(False)
        self.auto_pos_cb.setVisible(game_link.IS_WINDOWS)
        nav_bar.addWidget(self.auto_pos_cb)
        self.live_timer = QTimer(self)
        self.live_timer.setInterval(2000)
        self.live_timer.timeout.connect(self.live_tick)
        self.auto_pos_timer = QTimer(self)
        self.auto_pos_timer.setInterval(2000)
        self.auto_pos_timer.timeout.connect(self.auto_locate)
        self._auto_pending = None       # (time the keys were sent, clipboard contents to put back)
        self._auto_misses = 0
        self._live_stamp = None
        self._live_info = ""
        self._live_other_dim = None
        center_layout.addLayout(map_bar)
        center_layout.addLayout(nav_bar)
        center_layout.addWidget(self.map_viewer, 1)
        self.update_structure_jump_list()
        
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
        
        terrain_row = QHBoxLayout()
        terrain_row.addWidget(QLabel("Terreno intorno:"))
        self.terrain_combo = QComboBox()
        self.terrain_combo.addItem("Paesaggio naturale", "natural")
        self.terrain_combo.addItem("Solo pendio di terra", "blend")
        self.terrain_combo.addItem("Lascia com'e'", "none")
        self.terrain_combo.setToolTip(
            "Paesaggio naturale: se la struttura sta piu' in alto del terreno sale una collina con i materiali\n"
            "del bioma (erba, sabbia, neve, roccia dove e' ripido, fiori, massi, alberelli) e una scalinata\n"
            "nel materiale della struttura scende dalle porte; su un pendio il terreno davanti viene\n"
            "terrazzato; sull'acqua nasce un'isola con la spiaggia (o la struttura galleggia, vedi sotto).\n"
            "Solo pendio di terra: qualche blocco di terra a scivolo intorno agli edifici rialzati.")
        terrain_row.addWidget(self.terrain_combo, 1)
        inspector_layout.addLayout(terrain_row)

        water_row = QHBoxLayout()
        water_row.addWidget(QLabel("Sull'acqua:"))
        self.water_combo = QComboBox()
        self.water_combo.addItem("Isola con spiaggia", "island")
        self.water_combo.addItem("Galleggia (barche, basi sottomarine)", "float")
        self.water_combo.setToolTip(
            "Cosa succede se la metti sull'acqua: un'isola di sabbia su cui appoggiarla, oppure la struttura\n"
            "galleggia immersa di quanti blocchi vuoi (l'acqua rimasta dentro lo scafo viene tolta).\n"
            "La scelta viene ricordata per ogni struttura.")
        water_row.addWidget(self.water_combo, 1)
        inspector_layout.addLayout(water_row)
        depth_row = QHBoxLayout()
        depth_row.addWidget(QLabel("Immersione:"))
        self.depth_spin = QSpinBox()
        self.depth_spin.setRange(0, 160)
        self.depth_spin.setSuffix(" blocchi sotto il pelo dell'acqua")
        self.depth_spin.setToolTip("Quanti strati della struttura stanno sott'acqua (una barca: 2-4; una base "
                                   "sottomarina: la sua altezza o di piu'). Ricordata per ogni struttura.")
        depth_row.addWidget(self.depth_spin, 1)
        inspector_layout.addLayout(depth_row)
        self._loading_water = False
        self.water_combo.currentIndexChanged.connect(self.on_water_settings_changed)
        self.depth_spin.valueChanged.connect(self.on_water_settings_changed)
        self.depth_spin.setEnabled(False)

        self.clear_terrain_checkbox = QCheckBox("Scava ostacoli di terreno (Aria)")
        self.clear_terrain_checkbox.setChecked(True)
        inspector_layout.addWidget(self.clear_terrain_checkbox)

        self.skip_modded_checkbox = QCheckBox("Salta blocchi di mod (mondo vanilla)")
        self.skip_modded_checkbox.setChecked(True)
        self.skip_modded_checkbox.setToolTip(
            "In un mondo senza mod, un blocco sconosciuto fa scartare al gioco l'intera sezione 16x16x16."
        )
        inspector_layout.addWidget(self.skip_modded_checkbox)
        scope_lbl = QLabel("Queste opzioni valgono per tutto cio' che inietti (anche la coda); l'altezza Y vale "
                           "per la struttura che stai posizionando.")
        scope_lbl.setWordWrap(True)
        scope_lbl.setStyleSheet("color: #888896; font-size: 10px;")
        inspector_layout.addWidget(scope_lbl)

        # Suggest Position Button
        self.suggest_pos_btn = QPushButton("Consiglia Posizione Ottimale")
        self.suggest_pos_btn.setEnabled(False)
        self.suggest_pos_btn.clicked.connect(self.suggest_optimal_position)
        inspector_layout.addWidget(self.suggest_pos_btn)
        
        # Rotations shortcuts
        rot_layout = QHBoxLayout()
        self.rotate_btn = rotate_btn = QPushButton("Ruota 90° (R)")
        rotate_btn.setEnabled(False)
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
        self.stage_btn = QPushButton("Metti in coda")
        self.stage_btn.setEnabled(False)
        self.stage_btn.clicked.connect(self.stage_placement)
        inspector_layout.addWidget(self.stage_btn)
        
        # Queue Header
        queue_title = QLabel("Strutture in Coda:")
        queue_title.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        inspector_layout.addWidget(queue_title)
        
        # Queue List Widget
        self.staged_list = QListWidget()
        self.staged_list.setMinimumHeight(130)
        self.staged_list.setWordWrap(True)
        self.staged_list.setToolTip("Canc toglie gli elementi selezionati dalla coda.")
        from PyQt6.QtGui import QShortcut, QKeySequence
        QShortcut(QKeySequence(Qt.Key.Key_Delete), self.staged_list, activated=self.remove_selected_staged)
        self.staged_list.itemSelectionChanged.connect(self.on_staged_list_selection)
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
        self.clear_staged_btn.clicked.connect(self.confirm_clear_staged)
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

        self.undo_btn = QPushButton("Annulla ultima iniezione")
        self.undo_btn.setToolTip("Rimette le regioni del mondo com'erano prima dell'ultima iniezione, usando i backup "
                                 "creati automaticamente. Si puo' ripetere per annullare anche le precedenti.")
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self.undo_last_injection)
        inspector_layout.addWidget(self.undo_btn)
        
        # Console output
        log_lbl = QLabel("Registro Operazioni:")
        log_lbl.setStyleSheet("font-size: 11px; color: #888896;")
        inspector_layout.addWidget(log_lbl)
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMinimumHeight(140)
        inspector_layout.addWidget(self.console)

        inspector_scroll = QScrollArea()
        inspector_scroll.setObjectName("panel_scroll")
        inspector_scroll.setWidgetResizable(True)
        inspector_scroll.setFrameShape(QFrame.Shape.NoFrame)
        inspector_scroll.setWidget(inspector)
        main_splitter.addWidget(inspector_scroll)

        # The map gets the free space; side panels keep a usable width
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)
        main_splitter.setStretchFactor(2, 0)
        sidebar.setMinimumWidth(300)
        inspector_scroll.setMinimumWidth(290)
        main_splitter.setCollapsible(0, False)
        main_splitter.setCollapsible(2, False)
        self.main_splitter = main_splitter
        QTimer.singleShot(0, self._initial_splitter_sizes)

    def _initial_splitter_sizes(self):
        w = max(self.width(), 1100)
        side, insp = max(320, int(w * 0.26)), max(290, int(w * 0.22))
        self.main_splitter.setSizes([side, max(300, w - side - insp), insp])

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

    def _confirm_discard_queue(self):
        """Switching world or dimension discards the queue and the plans (they belong to this world)."""
        if getattr(self, "injection_thread", None) is not None:
            QMessageBox.information(self, "Iniezione in corso", "Aspetta la fine dell'iniezione prima di cambiare "
                                    "mondo o dimensione.")
            return False
        pending = len(self.staged_placements)
        if pending and QMessageBox.question(
                self, "Coda da svuotare",
                f"In coda ci sono {pending} elementi preparati per questo mondo: cambiando mondo o dimensione "
                f"verranno scartati. Continuare?") != QMessageBox.StandardButton.Yes:
            return False
        if pending:
            self.clear_all_staged()
        self.wall_plan_input = None
        self.road_plan_input = None
        self.locked_placement = None
        if hasattr(self, "map_viewer"):
            self.map_viewer.wall_preview = None
        return True

    def world_changed(self):
        world_name = self.world_select.currentText()
        if self.current_world_path and world_name != os.path.basename(self.current_world_path) \
                and not self._confirm_discard_queue():
            self.world_select.blockSignals(True)
            self.world_select.setCurrentText(os.path.basename(self.current_world_path))
            self.world_select.blockSignals(False)
            return
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
        self._shown_dimension = self.dim_select.currentText()
        self.dim_select.blockSignals(False)
        self.update_player_info_display()
        self.scan_regions()

        # Centering player region automatically on world load after a small delay to let UI settle
        QTimer.singleShot(50, self.go_to_player_region)

    def dimension_changed(self):
        shown = getattr(self, "_shown_dimension", None)
        if shown is not None and shown != self.dim_select.currentText() and not self._confirm_discard_queue():
            self.dim_select.blockSignals(True)
            self.dim_select.setCurrentText(shown)
            self.dim_select.blockSignals(False)
            return
        self._shown_dimension = self.dim_select.currentText()
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
        old = self.current_region
        locked_world = None
        if old is not None and self.locked_placement is not None:
            locked_world = (old.rx * 512 + self.locked_placement[0], old.rz * 512 + self.locked_placement[1])
        
        try:
            self.current_region = MCARegion(region_path)
            self.terrain = None
            self.map_viewer.set_region(self.current_region)
            if locked_world is not None:
                # grid coordinates are relative to the region shown: the locked spot must not move
                gx = locked_world[0] - self.current_region.rx * 512
                gz = locked_world[1] - self.current_region.rz * 512
                self.locked_placement = (gx, gz)
                self.map_viewer.preview_grid_x, self.map_viewer.preview_grid_z = gx, gz
            if getattr(self, "wall_plan_input", None):
                self.update_wall_preview()
            if getattr(self, "road_plan_input", None):
                self.update_road_preview()
            self.refresh_placed_structures()
            self.update_undo_button()
            self.log(f"Regione {region_file} caricata correttamente! (r.{self.current_region.rx}.{self.current_region.rz})")
            
            # Load player coordinates from world saves
            player_pos = self.load_player_position()
            if player_pos and self.player_dimension not in (None, self.current_dimension_id()):
                player_pos = None
            if player_pos:
                px, py, pz = player_pos
                self.map_viewer.set_player_position(px, pz, getattr(self, "player_yaw", None))
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

    @staticmethod
    def _yaw_of(nbt):
        rot = nbt.get("Rotation") or []
        try:
            return float(rot[0]) if len(rot) >= 1 else None
        except (TypeError, ValueError):
            return None

    def _load_player_position(self):
        self.player_dimension = None
        self.player_yaw = None
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
                        self.player_yaw = self._yaw_of(player)
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
                                    self.player_yaw = self._yaw_of(p_nbt)
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
                                self.player_yaw = self._yaw_of(p_nbt)
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

    # ------------------------------------------------------------------
    # Live view: follow the player while playing
    # ------------------------------------------------------------------
    # F3+C in the game copies e.g. "/execute in minecraft:overworld run tp @s 12.50 64.00 -3.20 91.5 12.0"
    _F3C_RE = re.compile(r"/execute in (\S+) run tp @s (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?")

    def set_live_mode(self, on):
        clipboard = QApplication.clipboard()
        self.follow_cb.setEnabled(on)
        self.auto_pos_cb.setEnabled(on)
        if on:
            self._live_stamp = None
            self._live_info = "in attesa di un salvataggio del gioco o di F3+C"
            self._auto_misses = 0
            clipboard.dataChanged.connect(self.on_clipboard_changed)
            self.live_timer.start()
            self.auto_pos_timer.start()
            if self.auto_pos_cb.isChecked():
                self.log("Live attivo: mentre giochi la tua posizione si aggiorna ogni 2 secondi (F3+C automatico); "
                         "il terreno nuovo compare quando Minecraft salva il mondo.")
            else:
                self.log("Live attivo: la mappa si aggiorna quando Minecraft salva il mondo (ogni 5 minuti circa). "
                         "Per aggiornare subito la tua posizione premi F3+C nel gioco.")
            self.live_tick()
        else:
            self.live_timer.stop()
            self.auto_pos_timer.stop()
            self._auto_pending = None
            try:
                clipboard.dataChanged.disconnect(self.on_clipboard_changed)
            except TypeError:
                pass
            self.map_viewer.live_status = ""
            self.map_viewer.update()

    def _live_status_text(self):
        tail = ("posizione continua attiva mentre giochi" if self.auto_pos_cb.isChecked()
                else "F3+C nel gioco = posizione subito")
        return f"LIVE  -  {self._live_info}  ({tail})"

    def _player_files_stamp(self):
        """Modification times of the files the player position is read from (changed when the game saves)."""
        out = []
        world = self.current_world_path or ""
        for d in (world, os.path.join(world, "playerdata"), os.path.join(world, "players"),
                  os.path.join(world, "players", "data")):
            try:
                with os.scandir(d) as it:
                    for e in it:
                        if e.name == "level.dat" or (d != world and e.name.endswith(".dat")):
                            out.append((e.path, e.stat().st_mtime_ns))
            except OSError:
                continue
        return tuple(sorted(out))

    def live_tick(self):
        if not self.current_world_path:
            return
        stamp = self._player_files_stamp()
        if stamp != self._live_stamp:
            first = self._live_stamp is None
            self._live_stamp = stamp
            pos = self.load_player_position(quiet=True)
            if pos and self.player_dimension in (None, self.current_dimension_id()):
                self._apply_live_position(pos[0], pos[1], pos[2], getattr(self, "player_yaw", None),
                                          "dal salvataggio del gioco", announce=not first)
        changed = self.map_viewer.refresh_changed_regions()
        if changed:
            self._live_info = f"{self._live_info.split('  |')[0]}  |  terreno aggiornato alle {time.strftime('%H:%M:%S')}"
        self.map_viewer.live_status = self._live_status_text()
        self.map_viewer.update()

    def auto_locate(self):
        """Live + continuous position: F3+C pressed for the player while they are in game."""
        pending = self._auto_pending
        if pending is not None:
            if time.time() - pending[0] < 1.5:
                return                      # still waiting for the game to copy the position
            self._auto_pending = None       # no answer (e.g. reduced debug info): keys sent for nothing
            self._auto_misses += 1
            if self._auto_misses == 3:
                self.log("Posizione continua: il gioco non risponde a F3+C (forse le informazioni di debug "
                         "ridotte sono attive nel mondo). La posizione si aggiornera' ai salvataggi.")
        if not self.auto_pos_cb.isChecked() or not self.current_world_path or not game_link.player_in_game():
            return
        # waiting before the keys go out: the game may copy the position before press_f3_c returns
        self._auto_pending = (time.time(), self._clipboard_copy())
        if not game_link.press_f3_c():
            self._auto_pending = None

    @staticmethod
    def _clipboard_copy():
        """Copy of what is in the clipboard now (all formats), to put back after an automatic F3+C."""
        from PyQt6.QtCore import QMimeData
        md = QApplication.clipboard().mimeData()
        if md is None:
            return None
        out = QMimeData()
        try:
            for fmt in md.formats():
                out.setData(fmt, md.data(fmt))
        except Exception:
            return None
        return out

    def on_clipboard_changed(self):
        text = QApplication.clipboard().text() or ""
        restored = getattr(self, "_clip_restored", None)
        if restored is not None and time.time() < restored[0] and text == restored[1]:
            return                          # our own restore of the player's clipboard, not a new position
        m = self._F3C_RE.search(text[:300])
        if not m or not self.current_world_path:
            return
        auto = self._auto_pending is not None and time.time() - self._auto_pending[0] < 3
        if auto:
            backup = self._auto_pending[1]
            self._auto_pending = None
            self._auto_misses = 0
            if backup is not None:
                # the player's clipboard back as it was (after this handler: not inside the change signal)
                self._clip_restored = (time.time() + 3, backup.text() if backup.hasText() else "")
                QTimer.singleShot(0, lambda: QApplication.clipboard().setMimeData(backup))
        dim = self._dimension_id(m.group(1))
        x, y, z = float(m.group(2)), float(m.group(3)), float(m.group(4))
        yaw = float(m.group(5)) if m.group(5) else None
        if dim != self.current_dimension_id():
            if dim != self._live_other_dim:
                self.log(f"F3+C: sei in un'altra dimensione ({dim}) rispetto a quella mostrata.")
            self._live_other_dim = dim
            return
        self._live_other_dim = None
        self._apply_live_position(x, y, z, yaw, "in tempo reale" if auto else "da F3+C", announce=not auto)

    def _apply_live_position(self, x, y, z, yaw, source, announce=True):
        self.map_viewer.set_player_position(x, z, yaw)
        self.player_info_lbl.setText(f"Giocatore: X: {x:.1f}, Y: {y:.1f}, Z: {z:.1f}\n"
                                     f"Regione: r.{int(x // 512)}.{int(z // 512)}.mca")
        self.go_to_player_btn.setEnabled(True)
        self._live_info = f"posizione {source} alle {time.strftime('%H:%M:%S')}"
        self.map_viewer.live_status = self._live_status_text()
        mv = self.map_viewer
        if self.follow_cb.isChecked() and not (mv.is_panning or mv.is_dragging_structure or mv.edit_drag is not None):
            mv.center_on_world(x, z)
        if announce:
            self.log(f"Live: giocatore a X {x:.0f}, Y {y:.0f}, Z {z:.0f} ({source}).")
        mv.update()

    # Local structures management
    def load_local_templates(self, select=None):
        """Fills the library tree, grouped by category."""
        self.local_list.blockSignals(True)
        self.local_list.clear()
        os.makedirs(self.templates_dir, exist_ok=True)
        groups = {}
        self.catalog_titles = {}
        for entry in catalog.load_catalog(self.templates_dir):
            self.catalog_titles[entry["file"]] = entry["title"]
            cat = entry["category"]
            if cat not in groups:
                top = QTreeWidgetItem([cat])
                top.setFlags(top.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                font = top.font(0)
                font.setBold(True)
                top.setFont(0, font)
                top.setForeground(0, QColor("#2ecc71"))
                top.setData(0, Qt.ItemDataRole.UserRole + 1, cat)
                self.local_list.addTopLevelItem(top)
                groups[cat] = top
            child = QTreeWidgetItem([entry["title"]])
            child.setData(0, Qt.ItemDataRole.UserRole, entry)
            child.setToolTip(0, f"{entry['file']}\n{entry.get('description', '')}")
            groups[cat].addChild(child)
        for top in groups.values():
            top.setData(0, Qt.ItemDataRole.UserRole + 1, f"{top.text(0)} ({top.childCount()})")
            self._update_category_label(top)
        self.local_list.blockSignals(False)
        self.filter_library(self.library_search.text())
        if select:
            self.select_template_file(select)

    @staticmethod
    def _update_category_label(item):
        label = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if label:
            item.setText(0, ("▾  " if item.isExpanded() else "▸  ") + label)

    def library_items(self):
        for i in range(self.local_list.topLevelItemCount()):
            top = self.local_list.topLevelItem(i)
            for j in range(top.childCount()):
                yield top, top.child(j)

    def select_template_file(self, filename):
        for top, child in self.library_items():
            if child.data(0, Qt.ItemDataRole.UserRole)["file"] == filename:
                top.setExpanded(True)
                self.local_list.setCurrentItem(child)
                return True
        return False

    def filter_library(self, text):
        query = text.strip().lower()
        visible = {}
        for top, child in self.library_items():
            e = child.data(0, Qt.ItemDataRole.UserRole)
            hay = " ".join((e["title"], e["file"], e.get("description", ""), e["category"])).lower()
            match = not query or query in hay
            child.setHidden(not match)
            visible[id(top)] = visible.get(id(top), 0) + int(match)
        for i in range(self.local_list.topLevelItemCount()):
            top = self.local_list.topLevelItem(i)
            top.setHidden(visible.get(id(top), 0) == 0)
            top.setExpanded(bool(query) and visible.get(id(top), 0) > 0)

    def import_custom_structure(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Apri file struttura", "", "Minecraft Structure (*.nbt *.schem *.schematic)")
        if file_path:
            # Copy to templates dir
            dest = os.path.join(self.templates_dir, os.path.basename(file_path))
            try:
                shutil.copy2(file_path, dest)
                self.load_local_templates(select=os.path.basename(file_path))
                self.log(f"Importato {os.path.basename(file_path)} con successo.")
            except Exception as e:
                self.log(f"Impossibile importare il file: {e}")

    def local_structure_selected(self):
        selected_items = self.local_list.selectedItems()
        if not selected_items:
            return
        entry = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        if not entry:
            return
        self.selected_entry = entry
        self.load_structure_file(os.path.join(self.templates_dir, entry["file"]), entry["file"])

    def load_structure_file(self, file_path, name):
        try:
            big = os.path.getsize(file_path) > 15 * 2 ** 20
        except OSError:
            big = False
        if not big:
            try:
                structure = Structure.load(file_path)
            except Exception as e:
                self._structure_load_failed(str(e))
                return
            self._structure_loaded(structure, name)
            return
        if getattr(self, "load_task", None) is not None:
            return
        # very large cuts: read and preview in the background, the window stays responsive
        self.log(f"Caricamento di {name}: struttura molto grande, qualche secondo...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        def job():
            structure = Structure.load(file_path)
            if getattr(structure.blocks, "packed", False):
                self.map_viewer.packed_preview_image(structure)      # QImage only: fine off the GUI thread
            return structure
        self.load_task = BackgroundTask(job)
        self.load_task.done.connect(lambda st: self._structure_loaded(st, name))
        self.load_task.failed.connect(self._structure_load_failed)
        self.load_task.finished.connect(self._structure_load_finished)
        self.load_task.start()

    def _structure_load_finished(self):
        self.load_task = None
        QApplication.restoreOverrideCursor()

    def _structure_load_failed(self, msg):
        self.log(f"Errore nel caricamento della struttura: {msg}")
        self.selected_structure = None
        self.map_viewer.set_selected_structure(None)
        self.struct_info_box.setText("Errore di caricamento.")

    def _structure_loaded(self, structure, name):
        try:
            self.selected_structure = structure
            self.selected_structure_name = name
            self.selected_rotation = 0
            self.map_viewer.set_selected_structure(self.selected_structure)
            
            self.update_structure_info()
            self.load_water_settings()
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
            self.update_bridge_controls()
        except Exception as e:
            self.log(f"Errore nel caricamento della struttura: {e}")
            self.selected_structure = None
            self.map_viewer.set_selected_structure(None)
            self.struct_info_box.setText("Errore di caricamento.")

    # Online search and download
    def search_online(self):
        query = self.search_input.text().strip()
        if not query or getattr(self, "online_task", None) is not None:
            return
        self.log(f"Ricerca online per '{query}'...")
        self.online_list.clear()
        errors = []
        self.online_task = BackgroundTask(lambda: search_minecraft_schematics(query, errors))
        self.online_task.done.connect(lambda results: self.on_search_done(results, errors))
        self.online_task.failed.connect(lambda msg: self.log(f"Ricerca non riuscita: {msg}"))
        self.online_task.finished.connect(lambda: setattr(self, "online_task", None))
        self.online_task.start()

    def on_search_done(self, results, errors):
        for r in results:
            item = QListWidgetItem(f"{r['title']} [{r['category']}]")
            item.setData(Qt.ItemDataRole.UserRole, r)
            self.online_list.addItem(item)
        if errors:
            self.log(f"Il sito minecraft-schematics.com non risponde ({errors[0][:80]}): mostro solo i "
                     f"{len(results)} risultati del catalogo integrato.")
        else:
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
            
        safe = re.sub(r"[^a-z0-9_-]+", "_", metadata["title"].lower()).strip("_") or "struttura"
        filename = safe[:60] + ext
        dest_path = os.path.join(self.templates_dir, filename)
        
        if dl_url.startswith("local:") and os.path.exists(os.path.join(self.templates_dir, dl_url[6:])):
            # built-in structure: it is already in the library, no duplicate
            self.log(f"'{metadata['title']}' e' gia' nella libreria: la seleziono.")
            self.tabs.setCurrentIndex(0)
            self.load_local_templates(select=dl_url[6:])
            return
        if getattr(self, "download_task", None) is not None:
            return
        self.log(f"Download in corso: {metadata['title']}...")
        self.download_btn.setEnabled(False)
        self.download_task = BackgroundTask(lambda: download_structure(dl_url, dest_path, self.templates_dir))
        self.download_task.done.connect(lambda ok: self.on_download_done(ok, filename))
        self.download_task.failed.connect(lambda msg: self.on_download_done(False, filename))
        self.download_task.finished.connect(lambda: setattr(self, "download_task", None))
        self.download_task.start()

    def on_download_done(self, success, filename):
        self.download_btn.setEnabled(True)
        if success:
            self.log(f"Download completato: salvato come {filename}")
            self.tabs.setCurrentIndex(0)
            self.load_local_templates(select=filename)
        else:
            self.log("Errore nel download. Il link potrebbe richiedere l'accesso al sito web.")

    # UI updates and placement handles
    def update_hover_coordinates(self, world_x, world_z, height_y):
        reg_file = f"r.{world_x // 512}.{world_z // 512}.mca"
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
                self.y_spinbox.setValue(height_y + 1 - self._ground_offset())

    def unlock_placement(self):
        """Right click on the map: the structure follows the mouse again, nothing is fixed."""
        self.locked_placement = None
        self.lock_feedback_lbl.setText("Fai clic sulla mappa per posizionare.")
        self.lock_feedback_lbl.setStyleSheet("color: #e67e22; font-weight: bold; font-size: 11px;")
        self.check_injection_readiness()

    def lock_placement_coordinate(self, grid_x, grid_z):
        self.locked_placement = (grid_x, grid_z)
        # Snap Spinbox to average footprint height or individual coordinate height
        if hasattr(self, 'auto_y_checkbox') and self.auto_y_checkbox.isChecked():
            avg_h = self.integrated_height(grid_x, grid_z)
            self.y_spinbox.setValue(avg_h)
        else:
            h = self.map_viewer.height_at(grid_x, grid_z)
            if h is not None:
                self.y_spinbox.setValue(h + 1 - self._ground_offset())
            
        world_x = self.current_region.rx * 512 + grid_x
        world_z = self.current_region.rz * 512 + grid_z
        self.lock_feedback_lbl.setText(f"Posizione fissata a X: {world_x}, Z: {world_z} "
                                       f"(clic destro per spostarla)")
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
        title = getattr(self, "catalog_titles", {}).get(s_name, s_name)
        display_name = f"{title} (X {item_x}, Y {y_val}, Z {item_z})"
        
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
        item_data["terrain"] = self.terrain_combo.currentData()
        item_data["water_mode"] = self.water_combo.currentData()
        if getattr(structure_copy, "bridge", None) or self.bridge_style_of_selection():
            item_data["extend_columns"] = True  # bridge piers go down to the bottom
        self.add_staged(item_data, display_name)
        
        # Reset current locked placement to let them choose next location/structure
        self.locked_placement = None
        self.map_viewer.is_locked = False
        self.lock_feedback_lbl.setText("Fai clic sulla mappa per posizionare.")
        self.lock_feedback_lbl.setStyleSheet("color: #e67e22; font-weight: bold; font-size: 11px;")
        
        self.check_injection_readiness()

    @staticmethod
    def _entry_boxes(entry):
        boxes = []
        for it in (entry["items"] if entry.get("kind") == "group" else [entry]):
            s = it.get("structure")
            if s is not None and it.get("name") != "lampione":
                boxes.append((it["world_x"], it["world_z"], it["world_x"] + s.width - 1, it["world_z"] + s.length - 1))
        return boxes

    def _overlapping_entries(self, item):
        """Titles of queued entries whose structures overlap the new one by a good part of its area."""
        new_boxes = self._entry_boxes(item)
        found = []
        for row, entry in enumerate(self.staged_placements):
            overlap = 0
            for ax1, az1, ax2, az2 in new_boxes:
                for bx1, bz1, bx2, bz2 in self._entry_boxes(entry):
                    w = min(ax2, bx2) - max(ax1, bx1) + 1
                    l = min(az2, bz2) - max(az1, bz1) + 1
                    if w > 0 and l > 0:
                        overlap += w * l
            area = sum((x2 - x1 + 1) * (z2 - z1 + 1) for x1, z1, x2, z2 in new_boxes) or 1
            if overlap >= max(9, area * 0.1):
                found.append(self.staged_list.item(row).text() if self.staged_list.item(row) else entry.get("name", ""))
        return found

    def add_staged(self, item, display_name, quiet=False):
        """Adds a placement (or a group of placements) to the injection queue."""
        overlaps = self._overlapping_entries(item)
        if overlaps:
            self.log(f"Attenzione: '{display_name}' si sovrappone a {', '.join(overlaps[:3])} gia' in coda: "
                     f"la struttura messa in coda dopo coprira' quella prima.")
        self.staged_placements.append(item)
        self.staged_list.addItem(display_name)
        self.map_viewer.staged_placements = self.staged_placements
        self.map_viewer.update()
        if not quiet:
            self.log(f"Aggiunta in coda: {display_name}")
        self.check_injection_readiness()

    @staticmethod
    def flatten_placements(items):
        flat = []
        for item in items:
            if item.get("kind") == "group":
                flat.extend(item["items"])
            else:
                flat.append(item)
        return flat

    BOAT_WORDS = ("ship", "boat", "nave", "navi", "barca", "galeon", "galleon", "yacht", "submarine", "sottomarin",
                  "vessel", "caravel", "caravella", "longship", "drakkar", "pirate", "pirat", "gondola", "zattera",
                  "raft", "ferry", "traghetto", "veliero", "battleship", "titanic")

    def _water_key(self):
        return "water/" + os.path.basename(self.selected_structure_name or "")

    def load_water_settings(self):
        """What the selected structure does on water: saved per structure, boats float by default."""
        name = os.path.basename(self.selected_structure_name or "")
        raw = self.settings.value(self._water_key(), None) if name else None
        mode, depth = None, 0
        if raw:
            mode, _, d = str(raw).partition(":")
            try:
                depth = int(d or 0)
            except ValueError:
                depth = 0
        if mode not in ("island", "float"):
            stem = os.path.splitext(name)[0]
            low = (stem + " " + getattr(self, "catalog_titles", {}).get(name, "")).lower()
            boat = catalog.category_for(stem) == "Navi" or any(w in low for w in self.BOAT_WORDS)
            mode = "float" if boat else "island"
            s = self.selected_structure
            depth = (2 if s is None or s.height <= 12 else 3) if boat else 0
        self._loading_water = True
        self.water_combo.setCurrentIndex(max(0, self.water_combo.findData(mode)))
        self.depth_spin.setValue(depth)
        self.depth_spin.setEnabled(mode == "float")
        self._loading_water = False

    def on_water_settings_changed(self):
        mode = self.water_combo.currentData()
        self.depth_spin.setEnabled(mode == "float")
        if self._loading_water:
            return
        if self.selected_structure_name:
            self.settings.setValue(self._water_key(), f"{mode}:{self.depth_spin.value()}")
        if self.locked_placement and self.auto_y_checkbox.isChecked() and self.selected_structure:
            self.y_spinbox.setValue(self.integrated_height(*self.locked_placement))

    def _ground_offset(self):
        return getattr(self.selected_structure, "ground_offset", 0) if self.selected_structure else 0

    def _world_of(self, grid_x, grid_z):
        return self.current_region.rx * 512 + grid_x, self.current_region.rz * 512 + grid_z

    def _edit_world(self):
        return World(self.get_region_dir(), preloaded=[self.current_region])

    # ---- Bridges ----
    def bridge_style_of_selection(self):
        s = self.selected_structure
        if s is None:
            return None
        if getattr(s, "bridge", None):
            return s.bridge["style"]
        entry = getattr(self, "selected_entry", None)
        if entry and entry.get("bridge_style") and entry["file"] == self.selected_structure_name:
            return entry["bridge_style"]
        return None

    def update_bridge_controls(self):
        style = self.bridge_style_of_selection()
        self.apply_length_btn.setEnabled(style is not None)
        if style:
            s = self.selected_structure
            length = s.bridge["length"] if getattr(s, "bridge", None) else max(s.width, s.length)
            self.bridge_length.setValue(length)
            idx = self.bridge_style.findData(style)
            if idx >= 0:
                self.bridge_style.setCurrentIndex(idx)
            self.bridge_info.setText(f"Ponte selezionato: {sgen.BRIDGE_STYLES[style]['title']}, {length} blocchi. "
                                     "Cambia la lunghezza e premi Applica: lo stile resta lo stesso.")
        else:
            self.bridge_info.setText("Seleziona un ponte dall'elenco (categoria Ponti) per allungarlo o accorciarlo "
                                     "mantenendo lo stesso stile.")

    def apply_bridge_length(self):
        style = self.bridge_style_of_selection()
        if not style:
            return
        s = sgen.make_bridge(style, self.bridge_length.value())
        steps = getattr(self, "selected_rotation", 0) % 4
        if steps:
            s = s.rotate(90 * steps)
        self.selected_structure = s
        self.selected_structure_name = f"{sgen.BRIDGE_STYLES[style]['title']} ({s.bridge['length']} blocchi)"
        self.map_viewer.set_selected_structure(s, keep_lock=self.locked_placement is not None)
        self.update_structure_info()
        self.update_bridge_controls()
        self.check_injection_readiness()
        self.log(f"Ponte ridimensionato a {s.bridge['length']} blocchi nello stile '{sgen.BRIDGE_STYLES[style]['title']}'.")

    def start_bridge_mode(self):
        if not self.current_region:
            self.log("Apri prima un mondo.")
            return
        self.map_viewer.set_mode("bridge")
        self.map_viewer.setFocus()
        self.log("Ponte: clicca sulla mappa la prima sponda, poi la seconda (Esc per annullare).")

    @staticmethod
    def bank_height(world, x, z):
        top = world.surface_y(x, z)
        if top is None:
            return None
        name = world.get_block_name(x, top, z) or ""
        if "water" in name or "lava" in name:
            return top
        ground = world.ground_y(x, z, top)
        return ground if ground is not None else top

    def bridges_file(self):
        return os.path.join(self.current_world_path, "minecraft_builder.json") if self.current_world_path else None

    def known_bridges(self):
        path = self.bridges_file()
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError, TypeError):
            return []
        return data.get("bridges", {}).get(self.current_dimension_id(), [])

    # ---- Undo ----
    def _read_registry(self):
        try:
            with open(self.bridges_file(), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError, TypeError):
            return {}

    def _write_registry(self, data):
        with open(self.bridges_file(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1, ensure_ascii=False)

    def _registry_sizes(self):
        data = self._read_registry()
        dim = self.current_dimension_id()
        return {key: len(data.get(key, {}).get(dim, [])) for key in ("bridges", "structures", "walls", "roads")}

    def push_undo(self, backups, before, names):
        """Remembers the backups of an injection (in the world folder, so undo works after a restart)."""
        if not backups or not self.bridges_file():
            self.update_undo_button()
            return
        data = self._read_registry()
        labels = [os.path.splitext(n)[0] for n in names if n and n != "lampione"]
        label = ", ".join(sorted(set(labels))[:4]) + ("..." if len(set(labels)) > 4 else "")
        data.setdefault("history", []).append({
            "time": time.strftime("%Y-%m-%d %H:%M:%S"), "dimension": self.current_dimension_id(),
            "label": label or "iniezione", "backups": [[r, b] for r, b in backups], "before": before})
        data["history"] = data["history"][-20:]
        try:
            self._write_registry(data)
        except OSError as e:
            self.log(f"Avviso: impossibile salvare la cronologia per l'annullamento: {e}")
        self.update_undo_button()

    def update_undo_button(self):
        if not hasattr(self, "undo_btn"):
            return
        history = self._read_registry().get("history", []) if self.current_world_path else []
        last = history[-1] if history else None
        self.undo_btn.setEnabled(bool(last) and getattr(self, "injection_thread", None) is None)
        self.undo_btn.setText(f"Annulla ultima iniezione ({last['time'][11:16]})" if last else
                              "Annulla ultima iniezione")

    def undo_last_injection(self):
        data = self._read_registry()
        history = data.get("history", [])
        if not history:
            self.log("Non c'e' nessuna iniezione da annullare.")
            return
        last = history[-1]
        missing = [b for _, b in last["backups"] if b and not os.path.exists(b)]
        if missing:
            QMessageBox.warning(self, "Annulla", "I backup di questa iniezione non ci sono piu': impossibile annullarla.")
            history.pop()
            self._write_registry(data)
            self.update_undo_button()
            return
        regions = [os.path.basename(r) for r, _ in last["backups"]]
        msg = (f"Annullare l'iniezione del {last['time']} ({last['label']})?\n\n"
               f"Le regioni {', '.join(regions)} torneranno com'erano prima. Anche quello che hai costruito "
               f"in gioco in queste regioni dopo l'iniezione verra' perso.")
        if is_minecraft_running() or self.check_world_locked():
            msg += "\n\nAttenzione: Minecraft sembra aperto. Chiudi il mondo prima di continuare."
        if QMessageBox.question(self, "Annulla ultima iniezione", msg) != QMessageBox.StandardButton.Yes:
            return
        try:
            for region, backup in last["backups"]:
                if backup:
                    shutil.copy2(backup, region)
                elif os.path.exists(region):
                    os.remove(region)          # file created by the injection (entities)
        except OSError as e:
            QMessageBox.critical(self, "Annulla", f"Impossibile ripristinare le regioni: {e}")
            return
        dim = last.get("dimension", self.current_dimension_id())
        before = last.get("before", {})
        for key in ("bridges", "structures", "walls", "roads"):
            lst = data.get(key, {}).get(dim)
            if lst is not None and key in before:
                del lst[before[key]:]
        token = before.get("token")
        for key in ("walls", "roads", "structures"):   # builds that this injection replaced stand again
            for r in data.get(key, {}).get(dim, []):
                if token and r.get("removed") == token:
                    del r["removed"]
        history.pop()
        self._write_registry(data)
        self.log(f"Iniezione del {last['time']} annullata: ripristinate {len(regions)} regioni dai backup.")
        self.region_changed()
        self.map_viewer.invalidate()
        self.refresh_placed_structures()
        self.update_undo_button()

    def record_bridges(self, items):
        bridges = [i["bridge"] for i in items if i.get("bridge")]
        path = self.bridges_file()
        if not bridges or not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = {}
        data.setdefault("bridges", {}).setdefault(self.current_dimension_id(), []).extend(bridges)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1)

    # ---- Structures placed in the world (drawn on the map) ----
    def placed_structures(self):
        path = self.bridges_file()
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError, TypeError):
            return []
        return [s for s in data.get("structures", {}).get(self.current_dimension_id(), []) if not s.get("removed")]

    def refresh_placed_structures(self):
        self.map_viewer.set_placed_structures(self.placed_structures())
        self.update_structure_jump_list()
        if hasattr(self, "built_roads_combo"):
            self.refresh_built_lines()

    def record_structures(self, items):
        """Remembers what was injected and where, so the map can show it."""
        path = self.bridges_file()
        if not path:
            return
        info = {e["file"]: e for e in catalog.load_catalog(self.templates_dir)}
        new = []
        for i in items:
            s = i.get("structure")
            name = i.get("name", "")
            if s is None or name == "lampione" or name.startswith(("Mura - ", "Strada - ")):
                continue  # the whole wall is shown by the map itself, the gates are listed
            entry = info.get(name, {})
            stem = os.path.splitext(name)[0]
            if i.get("bridge"):
                category = "Ponti"
            elif i.get("group") == "villaggio":
                category = "Villaggio"
            elif i.get("group") == "mura":
                category = "Castelli e fortezze"
            else:
                category = entry.get("category") or catalog.category_for(stem)
            title = entry.get("title") or (stem.replace("_", " ").title() if name.endswith(".nbt") else name)
            new.append({"name": name, "title": title, "category": category,
                        "x": int(i["world_x"]), "y": int(i["y_coord"]), "z": int(i["world_z"]),
                        "w": s.width, "h": s.height, "l": s.length, "date": time.strftime("%Y-%m-%d %H:%M")})
            if i.get("line_id"):
                new[-1]["line"] = i["line_id"]
        if not new:
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = {}
        data.setdefault("structures", {}).setdefault(self.current_dimension_id(), []).extend(new)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=1, ensure_ascii=False)
        except OSError as e:
            self.log(f"Avviso: impossibile salvare l'elenco delle strutture: {e}")
        self.refresh_placed_structures()

    def update_structure_jump_list(self):
        """Fills the 'go to structure' menu with the placed and the game structures."""
        if not hasattr(self, "structure_jump"):
            return
        self.structure_jump.blockSignals(True)
        self.structure_jump.clear()
        self.structure_jump.addItem("Vai a una struttura...", None)
        for s in sorted(self.map_viewer.placed_structures, key=lambda s: (s.get("category", ""), s.get("title", ""))):
            self.structure_jump.addItem(f"{s.get('title', s.get('name'))}  ({s['x']}, {s['z']})",
                                        (s["x"] + s["w"] // 2, s["z"] + s["l"] // 2))
        for label, x1, z1, x2, z2 in sorted(self.map_viewer.game_structures()):
            self.structure_jump.addItem(f"[gioco] {label}  ({x1}, {z1})", ((x1 + x2) // 2, (z1 + z2) // 2))
        self.structure_jump.blockSignals(False)

    def jump_to_structure(self, index):
        target = self.structure_jump.itemData(index)
        self.structure_jump.setCurrentIndex(0)
        if not target or not self.current_region:
            return
        x, z = target
        self.map_viewer.center_on_grid(x - self.current_region.rx * 512, z - self.current_region.rz * 512,
                                       max(self.map_viewer.zoom_level, 3.0))
        self.log(f"Mappa centrata su X: {x}, Z: {z}")

    def on_bridge_requested(self, ax, az, bx, bz):
        self.map_viewer.set_mode("place")
        world = self._edit_world()
        a, b = self._world_of(ax, az), self._world_of(bx, bz)
        existing = self.known_bridges() + [p["bridge"] for p in self.flatten_placements(self.staged_placements)
                                           if p.get("bridge")]
        integrate = self.bridge_integrate.isChecked()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            plan = sgen.plan_bridge(self.bridge_style.currentData(), a, b, WorldTerrain(world), existing,
                                    integrate=integrate, world=world)
        finally:
            QApplication.restoreOverrideCursor()
        if plan is None:
            self.log("Errore: una delle due sponde e' in una zona non generata (o in formato vecchio).")
            return
        info = plan["bridge"]
        heights = f"piano da Y {info.get('deck_a', info['deck'])} a Y {info.get('deck_b', info['deck'])}"
        label = f"{plan['name']} (X {plan['world_x']}, Z {plan['world_z']}, {heights})"
        if plan.get("ramps"):
            self.add_staged({"kind": "group", "items": [plan] + plan.pop("ramps"), "name": plan["name"]}, label)
        else:
            self.add_staged(plan, label)
        if plan["snapped"]:
            self.log("Il nuovo ponte prosegue quello esistente: stesso stile, stesso asse e stessa altezza.")
        if integrate:
            self.log("Ponte integrato: rampe dolci fino alle sponde, arco alto sull'acqua e materiali presi "
                     "dall'ambiente circostante.")

    # ---- Villages ----
    def start_village_mode(self):
        if not self.current_region:
            self.log("Apri prima un mondo.")
            return
        self.point_action = "village"
        self.map_viewer.set_mode("point")
        self.map_viewer.setFocus()
        self.log("Villaggio: clicca sulla mappa il punto centrale (Esc per annullare).")

    def on_map_point(self, grid_x, grid_z):
        """A single click in 'point' mode: village centre or new gate, depending on what was asked."""
        action, self.point_action = getattr(self, "point_action", "village"), "village"
        if action == "gate":
            if self.add_wall_gate(grid_x, grid_z):
                self.map_viewer.set_mode("place")
            else:
                self.point_action = "gate"       # stay in gate mode until a good click or Esc
        else:
            self.on_village_center(grid_x, grid_z)

    # ---- Walls ----
    def _reference_point(self):
        pos = self.load_player_position(quiet=True)
        if pos and self.player_dimension in (None, self.current_dimension_id()):
            return int(pos[0]), int(pos[2])
        return self.current_region.rx * 512 + 256, self.current_region.rz * 512 + 256

    def start_wall_mode(self):
        if not self.current_region:
            self.log("Apri prima un mondo.")
            return
        self.poly_purpose = "walls"
        self.map_viewer.wall_preview = None
        self.map_viewer.poly_closable = True
        self.map_viewer.snap_targets = []
        self.map_viewer.set_mode("polygon")
        self.map_viewer.setFocus()
        self.log("Mura: clicca i vertici del perimetro. Clic sul primo punto o Invio per chiudere, doppio clic "
                 "per un tratto aperto, Backspace toglie l'ultimo punto, Esc annulla.")

    def on_polygon_finished(self, pts, closed):
        if getattr(self, "poly_purpose", "walls") == "roads":
            self.on_road_finished(pts)
            return
        world_pts = [self._world_of(x, z) for x, z in pts]
        ref = self._reference_point()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            gates = walls.best_gates(self._edit_world(), world_pts, closed, outside_ref=ref)
        finally:
            QApplication.restoreOverrideCursor()
        self.wall_plan_input = {"points": world_pts, "closed": closed, "gates": gates}
        self.update_wall_preview()
        self.log(f"Perimetro disegnato ({len(world_pts)} punti, {'chiuso' if closed else 'aperto'}). "
                 f"Porta consigliata: {', '.join(f'X {x} Z {z}' for x, z in gates) or 'nessuna'}.")

    def suggest_walls(self):
        if not self.current_region:
            self.log("Apri prima un mondo.")
            return
        center = self._reference_point()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            pts, gates, msg = walls.suggest_perimeter(self._edit_world(), center,
                                                      placed=self.map_viewer.placed_structures)
        finally:
            QApplication.restoreOverrideCursor()
        self.wall_plan_input = {"points": pts, "closed": True, "gates": gates}
        self.update_wall_preview()
        self.center_map_on(*center)
        self.log(msg + " Controlla la proposta sulla mappa: puoi aggiungere porte o ridisegnarla.")

    def start_gate_mode(self):
        if not self.wall_plan_input:
            self.log("Prima disegna o fatti suggerire il perimetro delle mura.")
            return
        self.point_action = "gate"
        self.map_viewer.set_mode("point")
        self.map_viewer.setFocus()
        self.log("Clicca sul perimetro dove vuoi una porta (Esc per annullare).")

    def add_wall_gate(self, grid_x, grid_z):
        if not self.wall_plan_input:
            return
        x, z = self._world_of(grid_x, grid_z)
        path = walls.Path(self.wall_plan_input["points"], self.wall_plan_input["closed"])
        dist, s, _ = path.project(x, z)
        if dist > 12:
            self.log("Clicca piu' vicino alle mura per mettere la porta (Esc per rinunciare).")
            return False
        px, pz, _, _ = path.at(s)
        self.wall_plan_input["gates"].append((int(round(px)), int(round(pz))))
        self.update_wall_preview()
        self.log(f"Porta aggiunta a X {int(round(px))}, Z {int(round(pz))}.")
        return True

    def clear_wall_gates(self):
        if self.wall_plan_input:
            n = len(self.wall_plan_input["gates"])
            self.wall_plan_input["gates"] = []
            self.update_wall_preview()
            self.log(f"Tolte {n} porte dal perimetro." if n else "Il perimetro non ha porte.")

    def update_wall_preview(self):
        inp = self.wall_plan_input
        self.wall_edit_btn.setEnabled(bool(inp))
        self.wall_gate_btn.setEnabled(bool(inp))
        self.wall_gate_clear_btn.setEnabled(bool(inp and inp.get("gates")))
        if not inp:
            self.wall_info.setText(self.WALL_HELP)
        if not inp or not self.current_region:
            if getattr(self, "preview_owner", None) in (None, "walls"):
                self.map_viewer.wall_preview = None
            self.wall_stage_btn.setEnabled(False)
            self.map_viewer.update()
            return
        self.preview_owner = "walls"
        ox, oz = self.current_region.rx * 512, self.current_region.rz * 512
        self.map_viewer.wall_preview = {
            "points": [(x - ox, z - oz) for x, z in inp["points"]], "closed": inp["closed"],
            "gates": [(x - ox, z - oz) for x, z in inp["gates"]]}
        length = walls.Path(inp["points"], inp["closed"]).length
        self.wall_info.setText((f"Modifica di mura gia' costruite. " if inp.get("replaces") else "")
                               + f"Perimetro: {length:.0f} blocchi, {len(inp['points'])} vertici, "
                               f"{len(inp['gates'])} porte. Premi 'Metti in coda le mura' quando va bene.")
        self.wall_stage_btn.setEnabled(True)
        self.map_viewer.update()

    def stage_walls(self):
        inp = self.wall_plan_input
        if not inp:
            return
        old = self._built_record("walls", inp.get("replaces"))
        settings = {"style": self.wall_style.currentData(), "height": self.wall_height.value(),
                    "towers": self.wall_towers.isChecked(), "spacing": self.wall_spacing.value(),
                    "gate_type": self.wall_gate_type.currentData(), "lights": self.wall_lights.isChecked()}
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            terrain = self._planning_terrain(old)
            plan = walls.plan_walls(
                inp["points"], inp["closed"], settings["style"], settings["height"], terrain,
                towers=settings["towers"], tower_spacing=settings["spacing"], gates=inp["gates"],
                gate_type=settings["gate_type"], lights=settings["lights"], outside_ref=self._reference_point())
            fp = footprint(plan["placements"], terrain) if plan["placements"] else None
        finally:
            QApplication.restoreOverrideCursor()
        self.log(plan["report"])
        if not plan["placements"]:
            QMessageBox.warning(self, "Mura", plan["report"])
            return
        record = {"id": f"mura-{time.time_ns()}", "date": time.strftime("%Y-%m-%d %H:%M"),
                  "title": walls.WALL_STYLES[settings["style"]]["title"],
                  "points": [list(p) for p in inp["points"]], "closed": inp["closed"],
                  "gates": [list(g) for g in inp["gates"]], "settings": settings, "footprint": footprint_to_text(fp)}
        self._stage_line("walls", "Mura", plan["placements"], record, old, plan["report"])
        self.wall_plan_input = None
        self.update_wall_preview()

    # ---- Roads ----
    def _grid_lines(self, kind, exclude=None):
        ox, oz = self.current_region.rx * 512, self.current_region.rz * 512
        return [[(x - ox, z - oz) for x, z in r["points"]] for r in self.built_lines(kind) if r.get("id") != exclude]

    def start_road_mode(self):
        if not self.current_region:
            self.log("Apri prima un mondo.")
            return
        self.poly_purpose = "roads"
        self.road_plan_input = None
        self.update_road_preview()
        self.map_viewer.poly_closable = False
        self.map_viewer.snap_targets = self._grid_lines("roads")
        self.map_viewer.set_mode("polygon")
        self.map_viewer.setFocus()
        self.log("Strada: clicca i punti del tracciato, Invio o doppio clic per finire, Backspace toglie "
                 "l'ultimo punto, Esc annulla. Vicino a una strada esistente il punto si aggancia da solo.")

    def on_road_finished(self, pts):
        world_pts = [self._world_of(x, z) for x, z in pts]
        existing = [r["points"] for r in self.built_lines("roads")]
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            world_pts, msgs = roads.snap_endpoints(world_pts, existing, self._edit_world())
        finally:
            QApplication.restoreOverrideCursor()
        self.road_plan_input = {"points": world_pts}
        self.update_road_preview()
        for m in msgs:
            self.log(m)
        self.log(f"Tracciato disegnato ({len(world_pts)} punti). Puoi modificarlo o metterlo in coda.")

    def update_road_preview(self):
        inp = self.road_plan_input
        self.road_edit_btn.setEnabled(bool(inp))
        self.road_stage_btn.setEnabled(bool(inp))
        if not inp:
            self.road_info.setText(self.ROAD_HELP)
        if not inp or not self.current_region:
            if getattr(self, "preview_owner", None) == "roads":
                self.map_viewer.wall_preview = None
            self.map_viewer.update()
            return
        self.preview_owner = "roads"
        ox, oz = self.current_region.rx * 512, self.current_region.rz * 512
        self.map_viewer.wall_preview = {"points": [(x - ox, z - oz) for x, z in inp["points"]],
                                        "closed": False, "gates": []}
        length = walls.Path(inp["points"], False).length
        self.road_info.setText((f"Modifica di una strada gia' costruita. " if inp.get("replaces") else "")
                               + f"Strada: {length:.0f} blocchi, {len(inp['points'])} punti. Premi 'Metti in "
                               f"coda la strada' quando va bene.")
        self.map_viewer.update()

    def stage_road(self):
        inp = self.road_plan_input
        if not inp:
            return
        old = self._built_record("roads", inp.get("replaces"))
        settings = {"style": self.road_style.currentData(), "width": self.road_width.value(),
                    "lamps": self.road_lamps.isChecked(), "lamp_spacing": self.road_lamp_spacing.value(),
                    "kerbs": self.road_kerbs.isChecked()}
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            terrain = self._planning_terrain(old)
            plan = roads.plan_road(inp["points"], settings["style"], settings["width"], terrain,
                                   lamps=settings["lamps"], lamp_spacing=settings["lamp_spacing"],
                                   kerbs=settings["kerbs"])
            fp = footprint(plan["placements"], terrain) if plan["placements"] else None
        finally:
            QApplication.restoreOverrideCursor()
        self.log(plan["report"])
        if not plan["placements"]:
            QMessageBox.warning(self, "Strade", plan["report"])
            return
        record = {"id": f"strada-{time.time_ns()}", "date": time.strftime("%Y-%m-%d %H:%M"),
                  "title": roads.ROAD_STYLES[settings["style"]]["title"],
                  "points": [list(p) for p in inp["points"]], "settings": settings,
                  "footprint": footprint_to_text(fp)}
        self._stage_line("roads", "Strada", plan["placements"], record, old, plan["report"])
        self.road_plan_input = None
        self.update_road_preview()

    # ---- Walls and roads already built: edit, demolish ----
    def built_lines(self, kind):
        """Walls ('walls') or roads ('roads') built with the program in this dimension, still standing."""
        if not self.current_world_path:
            return []
        return [r for r in self._read_registry().get(kind, {}).get(self.current_dimension_id(), [])
                if not r.get("removed")]

    def _built_record(self, kind, rec_id):
        if not rec_id:
            return None
        return next((r for r in self.built_lines(kind) if r.get("id") == rec_id), None)

    def _planning_terrain(self, old_record):
        """Terrain for the planner; inside an old build that is being replaced, its original ground."""
        base = WorldTerrain(self._edit_world())
        if old_record is None:
            return base
        return RecordedTerrain(base, [footprint_from_text(old_record.get("footprint"))])

    def _queued_on(self, rec_id):
        """True if the queue already holds a modification or a demolition of this built wall/road."""
        for entry in self.staged_placements:
            for it in (entry["items"] if entry.get("kind") == "group" else [entry]):
                lr = it.get("line_record")
                if lr and lr[2] == rec_id:
                    return True
        return False

    def _stage_line(self, kind, label, placements, record, old, report):
        """Queues a wall/road: the demolition of the version it replaces first, then the new one."""
        if old is not None and self._queued_on(old["id"]):
            QMessageBox.warning(self, "Gia' in coda", "In coda c'e' gia' una modifica o una demolizione di "
                                "quest'opera: inietta o togli quella dalla coda prima di prepararne un'altra.")
            return
        items = []
        if old is not None:
            items.append({"kind": "demolish", "name": f"{label} precedente",
                          "footprint": footprint_from_text(old.get("footprint"))})
        placements[0]["line_record"] = (kind, record, old.get("id") if old else None)
        for p in placements:
            p["line_id"] = record["id"]          # gates & co. disappear from the map with their wall
        items.extend(placements)
        title = f"{label} ({record['title']})" + (" - modifica" if old else "")
        self.add_staged({"kind": "group", "items": items, "name": title}, title)
        self.log(report)

    def _selected_built(self, kind):
        combo = self.built_walls_combo if kind == "walls" else self.built_roads_combo
        rec_id = combo.currentData()
        rec = self._built_record(kind, rec_id)
        if rec is None:
            self.log("Non ci sono " + ("mura" if kind == "walls" else "strade") + " costruite col programma "
                     "in questa dimensione.")
        return rec

    def edit_built_line(self, kind):
        rec = self._selected_built(kind)
        if rec is None:
            return
        st = rec.get("settings", {})
        pts = [tuple(p) for p in rec["points"]]
        if kind == "walls":
            self._set_combo(self.wall_style, st.get("style"))
            self.wall_height.setValue(st.get("height", self.wall_height.value()))
            self.wall_towers.setChecked(st.get("towers", True))
            self.wall_spacing.setValue(st.get("spacing", self.wall_spacing.value()))
            self._set_combo(self.wall_gate_type, st.get("gate_type"))
            self.wall_lights.setChecked(st.get("lights", True))
            self.wall_plan_input = {"points": pts, "closed": rec.get("closed", True),
                                    "gates": [tuple(g) for g in rec.get("gates", [])], "replaces": rec["id"]}
            self.update_wall_preview()
        else:
            self._set_combo(self.road_style, st.get("style"))
            self.road_width.setValue(st.get("width", self.road_width.value()))
            self.road_lamps.setChecked(st.get("lamps", True))
            self.road_lamp_spacing.setValue(st.get("lamp_spacing", self.road_lamp_spacing.value()))
            self.road_kerbs.setChecked(st.get("kerbs", True))
            self.road_plan_input = {"points": pts, "replaces": rec["id"]}
            self.update_road_preview()
        xs, zs = [p[0] for p in pts], [p[1] for p in pts]
        self.center_map_on((min(xs) + max(xs)) // 2, (min(zs) + max(zs)) // 2)
        self.start_line_edit(kind)

    def demolish_built_line(self, kind):
        rec = self._selected_built(kind)
        if rec is None:
            return
        if self._queued_on(rec["id"]):
            QMessageBox.warning(self, "Gia' in coda", "In coda c'e' gia' una modifica o una demolizione di "
                                "quest'opera: inietta o togli quella dalla coda prima.")
            return
        what = "le mura" if kind == "walls" else "la strada"
        if QMessageBox.question(self, "Demolisci", f"Demolire {what} '{rec['title']}' del {rec['date']}? Il "
                                f"terreno torna com'era prima della costruzione (la demolizione va in coda: "
                                f"premi Inietta).") != QMessageBox.StandardButton.Yes:
            return
        item = {"kind": "demolish", "name": f"Demolizione {rec['title']}",
                "footprint": footprint_from_text(rec.get("footprint")), "line_record": (kind, None, rec["id"])}
        self.add_staged({"kind": "group", "items": [item], "name": item["name"]}, item["name"])

    @staticmethod
    def _set_combo(combo, data):
        idx = combo.findData(data)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def start_line_edit(self, kind):
        inp = self.wall_plan_input if kind == "walls" else self.road_plan_input
        if not inp:
            return
        self.edit_target = kind
        if kind == "walls":
            self.update_wall_preview()
            self.map_viewer.snap_targets = []
        else:
            self.update_road_preview()
            self.map_viewer.snap_targets = self._grid_lines("roads", exclude=inp.get("replaces"))
        self.map_viewer.set_mode("edit_poly")
        self.map_viewer.setFocus()
        self.log("Modifica: trascina i punti azzurri, doppio clic su un tratto aggiunge un punto, clic destro "
                 "su un punto lo toglie, Esc per finire. Poi metti in coda.")

    def on_preview_edited(self, pts):
        world_pts = [self._world_of(x, z) for x, z in pts]
        if getattr(self, "edit_target", "walls") == "roads":
            if self.road_plan_input is not None:
                self.road_plan_input["points"] = world_pts
                self.update_road_preview()
            return
        inp = self.wall_plan_input
        if inp is None:
            return
        inp["points"] = world_pts
        path = walls.Path(world_pts, inp["closed"])
        kept = []
        for gx, gz in inp["gates"]:
            dist, sp, _ = path.project(gx, gz)
            if dist <= 12:
                px, pz, _, _ = path.at(sp)
                kept.append((int(round(px)), int(round(pz))))
        if len(kept) < len(inp["gates"]):
            self.log("Una porta era troppo lontana dal nuovo perimetro ed e' stata tolta: aggiungila di nuovo.")
        inp["gates"] = kept
        self.update_wall_preview()

    def on_tab_changed(self, index):
        name = self.tabs.tabText(index)
        if name == "Mura" and self.wall_plan_input:
            self.update_wall_preview()
        elif name == "Strade" and self.road_plan_input:
            self.update_road_preview()

    def refresh_built_lines(self):
        """Built walls and roads: drawn on the map and listed in the two tabs."""
        lines = []
        for kind, combo in (("walls", self.built_walls_combo), ("roads", self.built_roads_combo)):
            combo.clear()
            recs = self.built_lines(kind)
            for r in recs:
                xs = [p[0] for p in r["points"]]
                zs = [p[1] for p in r["points"]]
                combo.addItem(f"{r['title']} - {r['date']} (X {sum(xs) // len(xs)}, Z {sum(zs) // len(zs)})",
                              r["id"])
                lines.append({"kind": kind, "points": [tuple(p) for p in r["points"]],
                              "closed": r.get("closed", False), "title": r["title"]})
            if not recs:
                combo.addItem("Nessuna", None)
        for kind, btns in (("walls", (self.built_walls_edit_btn, self.built_walls_demolish_btn)),
                           ("roads", (self.built_roads_edit_btn, self.built_roads_demolish_btn))):
            for b in btns:
                b.setEnabled(bool(self.built_lines(kind)))
        self.map_viewer.built_lines = lines
        self.map_viewer.update()

    def record_lines(self, items, token):
        """Remembers the walls/roads just built (and marks the ones they replaced or demolished)."""
        records = [i["line_record"] for i in items if i.get("line_record")]
        if not records or not self.bridges_file():
            return
        data = self._read_registry()
        dim = self.current_dimension_id()
        for kind, rec, replaces in records:
            lst = data.setdefault(kind, {}).setdefault(dim, [])
            if replaces:
                for r in lst:
                    if r.get("id") == replaces and not r.get("removed"):
                        r["removed"] = token
                for st in data.get("structures", {}).get(dim, []):
                    if st.get("line") == replaces and not st.get("removed"):
                        st["removed"] = token
            if rec:
                lst.append(rec)
        try:
            self._write_registry(data)
        except OSError as e:
            self.log(f"Avviso: impossibile salvare l'elenco di mura e strade: {e}")
        self.refresh_placed_structures()

    def on_village_center(self, grid_x, grid_z):
        self.map_viewer.set_mode("place")
        terrain = WorldTerrain(self._edit_world())
        style, size = self.village_style.currentData(), self.village_size.currentData()

        def load(name):
            return Structure.load(os.path.join(self.templates_dir, name + ".nbt"))

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = vgen.generate_village(self._world_of(grid_x, grid_z), style, size, terrain, load)
        finally:
            QApplication.restoreOverrideCursor()
        self.stage_village(result, style)

    def suggest_village_site(self):
        """Finds the flattest, driest, least wooded area near the player and plans the village there."""
        if not self.current_region:
            self.log("Apri prima un mondo.")
            return
        pos = self.load_player_position(quiet=True)
        if pos and self.player_dimension in (None, self.current_dimension_id()):
            around = (int(pos[0]), int(pos[2]))
        else:
            around = (self.current_region.rx * 512 + 256, self.current_region.rz * 512 + 256)
        style, size = self.village_style.currentData(), self.village_size.currentData()
        self.log(f"Ricerca della zona migliore per il villaggio intorno a X {around[0]}, Z {around[1]}...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            center, result = vgen.find_best_site(
                WorldTerrain(self._edit_world()), around, style, size,
                lambda n: Structure.load(os.path.join(self.templates_dir, n + ".nbt")), log=self.log)
        finally:
            QApplication.restoreOverrideCursor()
        if center is None:
            self.log(result)
            QMessageBox.warning(self, "Villaggio", result)
            return
        self.log(f"Posizione consigliata: X {center[0]}, Z {center[1]}.")
        self.stage_village(result, style)
        self.center_map_on(center[0], center[1])

    def center_map_on(self, x, z):
        from PyQt6.QtCore import QPointF
        rx, rz = x // 512, z // 512
        name = f"r.{rx}.{rz}.mca"
        for i in range(self.region_select.count()):
            if self.region_select.itemText(i) == name:
                self.region_select.setCurrentIndex(i)
                break
        self.map_viewer.pan_offset = QPointF(256 - (x - rx * 512), 256 - (z - rz * 512))
        self.map_viewer.update()

    def stage_village(self, result, style):
        self.log(result["report"])
        if len(result["placements"]) <= 1:      # only the square: no building fits here
            QMessageBox.warning(self, "Villaggio", result["report"] + "\n\nNessun edificio ci sta: scegli una "
                                "zona piu' pianeggiante o asciutta.")
            return
        items = list(result["placements"])
        if result["path_cells"]:
            items.append({"kind": "path", "cells": result["path_cells"], "block": result["path_block"],
                          "name": "strade del villaggio"})
        lamp = sgen.lamp_post(result["lamp_wood"])
        for x, z, y in result["lamps"]:
            items.append({"structure": lamp, "world_x": x, "world_z": z, "y_coord": y, "name": "lampione"})
        title = vgen.STYLES[style]["title"]
        self.add_staged({"kind": "group", "items": items, "name": title},
                        f"{title}: {len(result['placements'])} costruzioni (piazza compresa), strade e lampioni")

    # ---- Cut an area ----
    def start_cut_mode(self):
        if not self.current_region:
            self.log("Apri prima il mondo da cui ritagliare.")
            return
        self.map_viewer.set_mode("select")
        self.map_viewer.setFocus()
        self.log("Ritaglio: trascina sulla mappa un rettangolo intorno alla zona da copiare (Esc per annullare).")

    def on_area_selected(self, x1, z1, x2, z2):
        self.map_viewer.set_mode("place")
        wx1, wz1 = self._world_of(x1, z1)
        wx2, wz2 = self._world_of(x2, z2)
        world_name = os.path.basename(self.current_world_path or "mondo")
        dlg = CutDialog(self, f"Ritaglio {world_name} {wx1} {wz1}", wx2 - wx1 + 1, wz2 - wz1 + 1)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            self.log("Ritaglio annullato.")
            return
        title, mode, trees, ambiguous, enclosures = dlg.values()
        if getattr(self, "cut_thread", None) is not None:
            self.log("Un ritaglio e' gia' in corso: attendi che finisca.")
            return
        path = world_extractor.unique_path(self.templates_dir, title)
        area = (wx2 - wx1 + 1) * (wz2 - wz1 + 1)
        self.log(f"Ritaglio di {wx2 - wx1 + 1}x{wz2 - wz1 + 1} blocchi in corso in background"
                 + (" (area grande: ci vuole qualche decina di secondi)..." if area > 256 * 256 else "..."))
        self.cut_btn.setEnabled(False)
        self.cut_thread = CutWorker(self.get_region_dir(), (wx1, wz1, wx2, wz2), mode, (trees, ambiguous, enclosures), path,
                                    {"source": world_name, "mode": mode, "area": f"{wx1},{wz1} {wx2},{wz2}"})
        self.cut_thread.progress.connect(self.on_cut_progress)
        self.cut_thread.done.connect(lambda info: self.on_cut_done(info, title, world_name, mode, path,
                                                                   (wx1, wz1, wx2, wz2)))
        self.cut_thread.failed.connect(self.on_cut_failed)
        self.cut_thread.finished.connect(self.on_cut_finished)
        self.cut_last_report = -1
        self.cut_thread.start()

    def on_cut_progress(self, done, total):
        pct = int(done * 100 / max(total, 1))
        if pct // 10 != self.cut_last_report // 10 or done == total:
            self.cut_last_report = pct
            self.log(f"Ritaglio: {pct}% ({done}/{total} chunk letti)")

    def on_cut_done(self, info, title, world_name, mode, path, box):
        wx1, wz1, wx2, wz2 = box
        desc = (f"Ritaglio da '{world_name}' (X {wx1}..{wx2}, Z {wz1}..{wz2}): {info['blocks']} blocchi"
                + (", terreno compreso." if mode == "tutto" else ", solo costruzioni."))
        catalog.add_user_entry(os.path.basename(path), title, "Ritagli", desc)
        w, h, l = info["size"]
        self.log(f"Ritaglio salvato: {os.path.basename(path)} ({w}x{h}x{l}, {info['blocks']} blocchi). "
                 f"Lo trovi nella categoria Ritagli.")
        if info["missing_columns"]:
            self.log(f"Avviso: {info['missing_columns']} colonne dell'area non erano generate e sono state saltate.")
        self.tabs.setCurrentIndex(0)
        self.load_local_templates(select=os.path.basename(path))

    def on_cut_failed(self, message):
        self.log(f"Ritaglio non riuscito: {message}")
        QMessageBox.warning(self, "Ritaglio", message)

    def on_cut_finished(self):
        self.cut_btn.setEnabled(True)
        self.cut_thread = None

    # ------------------------------------------------------------------
    # Queued structures edited on the map: select, move, rotate, duplicate, remove
    # ------------------------------------------------------------------
    def on_staged_selected(self, row):
        self.staged_list.blockSignals(True)
        self.staged_list.clearSelection()
        if 0 <= row < self.staged_list.count():
            self.staged_list.setCurrentRow(row)
            self.staged_list.scrollToItem(self.staged_list.item(row))
            if not getattr(self, "_staged_hint_shown", False):
                self._staged_hint_shown = True
                self.log("Struttura in coda selezionata: trascinala per spostarla, R per ruotarla, Canc per "
                         "toglierla, Ctrl+D per metterne un'altra (anche col tasto destro). Esc per deselezionare.")
        self.staged_list.blockSignals(False)

    def on_staged_list_selection(self):
        rows = [self.staged_list.row(i) for i in self.staged_list.selectedItems()]
        entry = self.staged_placements[rows[0]] if len(rows) == 1 and rows[0] < len(self.staged_placements) else None
        self.map_viewer.select_staged(entry, emit=False)

    @staticmethod
    def _movable(entry):
        """None if a queued entry can be moved on the map, else why not."""
        items = entry["items"] if entry.get("kind") == "group" else [entry]
        if any(it.get("line_record") or it.get("line_id") for it in items):
            return "mura e strade si cambiano con 'Modifica' nelle loro schede"
        if any(it.get("extend_columns") or it.get("bridge") or it.get("kind") == "demolish" for it in items):
            return "ponti e demolizioni dipendono dal punto in cui sono stati disegnati"
        return None

    def _staged_label(self, entry):
        if entry.get("kind") == "group":
            return entry.get("name", "")
        title = getattr(self, "catalog_titles", {}).get(entry["name"], entry["name"])
        return f"{title} (X {entry['world_x']}, Y {entry['y_coord']}, Z {entry['world_z']})"

    def _height_for(self, structure, wx, wz):
        """Y that fits a structure at a world position (same rules as the placement)."""
        saved = self.selected_structure
        try:
            self.selected_structure = structure
            return self.integrated_height(wx - self.current_region.rx * 512, wz - self.current_region.rz * 512)
        finally:
            self.selected_structure = saved

    def _refresh_staged(self, row, select=True):
        entry = self.staged_placements[row]
        item = self.staged_list.item(row)
        if item is not None:
            item.setText(self._staged_label(entry))
        self.map_viewer.staged_placements = self.staged_placements
        if select:
            self.map_viewer.select_staged(entry)
        self.map_viewer.update()

    def move_staged(self, row, dx, dz):
        if not 0 <= row < len(self.staged_placements):
            return
        entry = self.staged_placements[row]
        why = self._movable(entry)
        if why:
            self.log(f"Non si sposta trascinando: {why}.")
            return
        items = entry["items"] if entry.get("kind") == "group" else [entry]
        follow = self.auto_y_checkbox.isChecked() and self.current_region is not None
        for it in items:
            if it.get("kind") == "path":
                it["cells"] = [(x + dx, z + dz) for x, z in it.get("cells", ())]
                continue
            if "world_x" not in it:
                continue
            it["world_x"] += dx
            it["world_z"] += dz
            if follow and it.get("structure") is not None and it.get("name") != "lampione":
                it["y_coord"] = self._height_for(it["structure"], it["world_x"], it["world_z"])
        self._refresh_staged(row)
        self.log(f"Spostata in coda: {self._staged_label(entry)}")

    def on_staged_action(self, row, action):
        if not 0 <= row < len(self.staged_placements):
            return
        entry = self.staged_placements[row]
        if action == "remove":
            self.staged_placements.pop(row)
            self.staged_list.takeItem(row)
            self.map_viewer.staged_placements = self.staged_placements
            self.map_viewer.select_staged(None, emit=False)
            self.log(f"Rimossa dalla coda: {entry.get('name', '')}")
            self.check_injection_readiness()
            return
        if action == "rotate":
            if entry.get("kind") == "group" or entry.get("structure") is None or self._movable(entry):
                self.log("Si possono ruotare solo le singole strutture in coda.")
                return
            old = entry["structure"]
            new = old.rotate(90)
            # turn around the centre, so the structure stays where it was
            cx, cz = entry["world_x"] + old.width / 2, entry["world_z"] + old.length / 2
            entry["structure"] = new
            entry["world_x"] = int(round(cx - new.width / 2))
            entry["world_z"] = int(round(cz - new.length / 2))
            entry["preview_pixmap"] = None
            if self.auto_y_checkbox.isChecked() and self.current_region is not None:
                entry["y_coord"] = self._height_for(new, entry["world_x"], entry["world_z"])
            self._refresh_staged(row)
            self.log(f"Ruotata in coda: {self._staged_label(entry)}")
            return
        if action == "duplicate":
            import copy
            why = self._movable(entry)
            if why:
                self.log(f"Non si duplica: {why}.")
                return
            twin = copy.copy(entry)
            if entry.get("kind") == "group":
                twin["items"] = [copy.copy(it) for it in entry["items"]]
            items = twin["items"] if twin.get("kind") == "group" else [twin]
            boxes = [(it["world_x"], it["world_x"] + it["structure"].width) for it in items
                     if it.get("structure") is not None]
            shift = (max(b for _, b in boxes) - min(a for a, _ in boxes) + 3) if boxes else 8
            for it in items:
                if it.get("kind") == "path":
                    it["cells"] = [(x + shift, z) for x, z in it.get("cells", ())]
                elif "world_x" in it:
                    it["world_x"] += shift
                    if it.get("structure") is not None and self.auto_y_checkbox.isChecked() and it.get(
                            "name") != "lampione":
                        it["y_coord"] = self._height_for(it["structure"], it["world_x"], it["world_z"])
            self.add_staged(twin, self._staged_label(twin), quiet=True)
            self._refresh_staged(len(self.staged_placements) - 1)
            self.on_staged_selected(len(self.staged_placements) - 1)
            self.log(f"Messa in coda un'altra copia: {self._staged_label(twin)} (trascinala dove vuoi).")

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

    def _remove_injected_from_queue(self):
        """Removes from the queue only what was injected (items added meanwhile stay)."""
        done = {id(e) for e in getattr(self, "injecting_entries", [])}
        for row in range(len(self.staged_placements) - 1, -1, -1):
            if id(self.staged_placements[row]) in done:
                self.staged_placements.pop(row)
                self.staged_list.takeItem(row)
        self.injecting_entries = []
        self.map_viewer.staged_placements = self.staged_placements
        self.map_viewer.update()

    def confirm_clear_staged(self):
        n = len(self.staged_placements)
        if n and QMessageBox.question(self, "Svuota la coda", f"Togliere dalla coda tutti i {n} elementi?") \
                == QMessageBox.StandardButton.Yes:
            self.clear_all_staged()

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
        if getattr(self, "injection_thread", None) is not None:
            for w in (self.apply_btn, self.clear_staged_btn, self.remove_staged_btn):
                w.setEnabled(False)
            self.stage_btn.setEnabled(bool(self.current_region and self.selected_structure
                                           and self.locked_placement is not None))
            self.apply_btn.setText("Iniezione in corso...")
            return
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
        if hasattr(self, "rotate_btn"):
            self.rotate_btn.setEnabled(self.selected_structure is not None)

    def integrated_height(self, grid_x, grid_z):
        """
        Y that integrates the structure with the land: real ground (trees ignored), floor at the
        75th percentile so that the footprint is mostly filled instead of dug.
        """
        if not self.current_region or not self.selected_structure:
            return 64
        if getattr(self, "terrain", None) is None:
            self.terrain = WorldTerrain(self._edit_world())
        s = self.selected_structure
        if s.width * s.length > 256 * 256:
            # very large structures (big cuts): a few thousand samples of the map heights, no chunk decoding
            step = max(1, int((s.width * s.length / 4000) ** 0.5))
            heights = sorted(h for h in (self.map_viewer.height_at(grid_x + bx, grid_z + bz)
                                         for bx in range(0, s.width, step) for bz in range(0, s.length, step))
                             if h is not None)
            if not heights:
                return 64
            return heights[min(len(heights) - 1, (len(heights) * 3) // 4)] + 1 - self._ground_offset()
        x1, z1 = self._world_of(grid_x, grid_z)
        heights, water = [], []
        step = 2 if max(s.width, s.length) > 16 else 1
        for x in range(x1, x1 + s.width, step):
            for z in range(z1, z1 + s.length, step):
                h = self.terrain.height(x, z)
                if h is None:
                    continue
                (water if self.terrain.is_water(x, z) else heights).append(h)
        if water and len(water) >= 0.3 * (len(water) + len(heights)):
            # on water: a boat floats with its chosen draught, anything else sits on a dry island
            level = max(set(water), key=water.count)
            if self.water_combo.currentData() == "float":
                return level + 1 - self.depth_spin.value()
            return level + 2 - self._ground_offset()
        if not heights:
            return self.get_average_footprint_height(grid_x, grid_z)
        heights.sort()
        return heights[min(len(heights) - 1, (len(heights) * 3) // 4)] + 1 - self._ground_offset()

    def get_average_footprint_height(self, grid_x, grid_z):
        """Suggested Y for the structure's first layer: one above the average terrain top."""
        if not self.current_region or not self.selected_structure:
            return 64
        sw = self.selected_structure.width
        sl = self.selected_structure.length

        total_height = 0
        count = 0
        step = max(1, int((sw * sl / 400) ** 0.5))     # big cuts: sample, the UI must stay responsive
        for bz in range(0, sl, step):
            for bx in range(0, sw, step):
                h = self.map_viewer.height_at(grid_x + bx, grid_z + bz)
                if h is not None:
                    total_height += h
                    count += 1
        if count > 0:
            return int(round(total_height / count)) + 1 - self._ground_offset()
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
        
        # Scan the area around the current position (also across the region borders) with step=4
        height_at = self.map_viewer.height_at
        for gz in range(current_gz - 192, current_gz + 192, 4):
            for gx in range(current_gx - 192, current_gx + 192, 4):
                # Sample heights at corners and center
                x_coords = [gx, gx + sw - 1, gx, gx + sw - 1, gx + sw // 2]
                z_coords = [gz, gz, gz + sl - 1, gz + sl - 1, gz + sl // 2]

                heights = [height_at(x, z) for x, z in zip(x_coords, z_coords)]
                if None in heights:
                    continue  # not generated

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
        self.lock_feedback_lbl.setText(f"Posizione fissata a X: {self.current_region.rx * 512 + best_gx}, "
                                       f"Z: {self.current_region.rz * 512 + best_gz}")
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
            self.selected_rotation = getattr(self, "selected_rotation", 0) + 1
            # Keep the locked position: rotating should not move the placement
            self.map_viewer.set_selected_structure(self.selected_structure, keep_lock=self.locked_placement is not None)
            self.log("Struttura ruotata di 90° in senso orario.")
            self.update_structure_info()

    def check_world_locked(self):
        """True if Minecraft has the world open (its session.lock cannot be written)."""
        if not self.current_world_path:
            return False
        lock_path = os.path.join(self.current_world_path, "session.lock")
        if os.path.exists(lock_path):
            try:
                with open(lock_path, "r+"):
                    pass
            except IOError:
                return True
        return False

    def apply_structure_to_world(self):
        if not self.current_region or getattr(self, "injection_thread", None) is not None:
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
            placements_to_inject = self.flatten_placements(self.staged_placements)
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
        self.injecting_entries = list(self.staged_placements)     # what leaves the queue when done
        self.injecting_direct = not self.staged_placements
            
        old_format = [p["name"] for p in placements_to_inject
                      if "structure" in p and p["structure"].is_pre_flattening()]
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
        self.map_viewer.pause_loading(True)  # the map must not read region files while they are rewritten

        # Instantiate and start the worker thread
        self.injection_thread = InjectionWorker(
            world,
            placements_to_inject,
            fill_foundations=self.fill_foundation_checkbox.isChecked(),
            clear_terrain=self.clear_terrain_checkbox.isChecked(),
            blend=self.terrain_combo.currentData(),
            skip_modded=self.skip_modded_checkbox.isChecked()
        )
        self.injection_thread.progress.connect(self.log)
        self.injection_thread.success.connect(self.on_injection_success)
        self.injection_thread.permission_error.connect(self.on_injection_permission_error)
        self.injection_thread.error.connect(self.on_injection_error)
        self.injection_thread.finished.connect(self.on_injection_finished)
        self.injection_thread.start()
        for w in (self.world_select, self.dim_select, self.region_select):
            w.setEnabled(False)
        self.check_injection_readiness()

    def on_injection_success(self):
        self.terrain = None
        stats = getattr(self.injection_thread, "stats", None) or {}
        wrote = any(stats.get(k, 0) for k in ("placed", "cleared", "foundation", "demolished", "path", "entities"))
        self._remove_injected_from_queue()
        if stats and not wrote:
            self.log("Nessun blocco e' stato scritto: l'area non e' ancora generata. Niente e' stato registrato.")
            self.map_viewer.pause_loading(False)
            self.show_injection_summary()
            return
        self.log("Tutte le strutture sono state iniettate con successo!")
        before = self._registry_sizes()
        before["token"] = str(time.time_ns())
        self.record_bridges(getattr(self, "last_injected", None) or [])
        self.record_structures(getattr(self, "last_injected", None) or [])
        self.record_lines(getattr(self, "last_injected", None) or [], before["token"])
        world = getattr(self.injection_thread, "world", None)
        self.push_undo(getattr(world, "last_backups", []), before,
                       [i.get("name", "") for i in (getattr(self, "last_injected", None) or []) if "structure" in i])
        
        if getattr(self, "injecting_direct", False):
            self.unlock_placement()            # a direct injection must not be repeated by mistake

        # Refresh map viewer (the modified regions are rendered again)
        self.map_viewer.pause_loading(False)
        self.map_viewer.invalidate()
        self.show_injection_summary()

    def teleport_command(self, item):
        """/tp command that puts the player just south of a placed structure, looking at it."""
        s = item["structure"]
        x = item["world_x"] + s.width // 2
        z = item["world_z"] + s.length + 3
        y = item["y_coord"]
        if self.current_region:
            h = self.map_viewer.height_at(x - self.current_region.rx * 512, z - self.current_region.rz * 512)
            if h is not None:
                y = max(y, h + 1)
        return f"/tp @s {x} {y} {z} 180 10"

    def show_injection_summary(self):
        """Tells the user exactly where to find the structures in the game."""
        items = [i for i in (getattr(self, "last_injected", None) or []) if "structure" in i and i.get("name") != "lampione"]
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
        self.injecting_entries = []           # nothing written: the queue stays as it is
        QMessageBox.critical(
            self, "Accesso negato",
            f"Windows non permette di scrivere il mondo:\n{err_msg}\n\nDi solito Minecraft e' ancora aperto: "
            "chiudilo del tutto (anche javaw.exe in Gestione attivita') e riprova. Controlla anche che la "
            "cartella del mondo non sia in sola lettura. La coda non e' stata svuotata.")
        self.log(f"ERRORE DI PERMESSO (Accesso Negato): {err_msg}")
        self.log("Se hai già chiuso il gioco, Windows potrebbe bloccare la scrittura. Risolvi così:")
        self.log("  - Apri Gestione Attività (Ctrl+Shift+Esc), cerca 'javaw.exe' o 'Minecraft' e clicca su 'Termina Attività'.")
        self.log("  - Avvia l'app come amministratore con:  py -3 main.py --admin")
        self.log("  - Verifica che la cartella del salvataggio non sia impostata su 'Solo Lettura'.")

    def on_injection_error(self, err_msg):
        self.injecting_entries = []
        self.log(f"Errore grave durante l'iniezione: {err_msg}")
        QMessageBox.critical(self, "Errore durante l'iniezione",
                             f"L'iniezione si e' interrotta:\n{err_msg}\n\nIl mondo non e' stato modificato "
                             "(i file vengono scritti solo alla fine). La coda non e' stata svuotata.")

    def on_injection_finished(self):
        for w in (self.world_select, self.dim_select, self.region_select):
            w.setEnabled(True)
        self.map_viewer.pause_loading(False)
        QApplication.restoreOverrideCursor()
        QApplication.processEvents()
        self.check_injection_readiness()
        self.update_player_info_display()
        # Clean up thread
        self.injection_thread = None
        self.check_injection_readiness()
        self.update_undo_button()

    def closeEvent(self, event):
        self.live_timer.stop()
        self.map_viewer.shutdown()
        super().closeEvent(event)


class BackgroundTask(QThread):
    """Runs a function outside the GUI thread (network searches and downloads)."""
    done = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            self.done.emit(self.fn())
        except Exception as e:
            self.failed.emit(str(e))


class CutWorker(QThread):
    """Cuts and saves an area of any size in the background."""
    progress = pyqtSignal(int, int)
    done = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, region_dir, box, mode, trees, path, extra):
        super().__init__()
        self.region_dir, self.box, self.mode = region_dir, box, mode
        opts = tuple(trees) if isinstance(trees, tuple) else (trees,)
        self.trees, self.ambiguous, self.enclosures = (opts + (False, False, True)[len(opts):])[:3]
        self.path, self.extra = path, extra

    def run(self):
        try:
            # a World of its own: the chunks are released while reading, the map is not affected
            world = World(self.region_dir)
            struct, info = world_extractor.extract_area(
                world, *self.box, mode=self.mode, include_trees=self.trees, keep_ambiguous=self.ambiguous,
                enclosures=self.enclosures,
                progress=lambda d, t: self.progress.emit(d, t), cancelled=self.isInterruptionRequested)
            del world
            world_extractor.save_structure(struct, self.path, self.extra)
            info["size"] = (struct.width, struct.height, struct.length)
            self.done.emit(info)
        except ValueError as e:
            self.failed.emit(str(e))
        except MemoryError:
            self.failed.emit("Memoria insufficiente per un'area cosi' grande: prova con 'Solo costruzioni' "
                             "o dividi l'area in piu' ritagli.")
        except Exception as e:
            self.failed.emit(f"Errore durante il ritaglio: {e}")


class CutDialog(QDialog):
    """Name and options of a cut area."""

    def __init__(self, parent, default_title, width, length):
        super().__init__(parent)
        self.setWindowTitle("Salva la zona come struttura")
        form = QFormLayout(self)
        form.addRow(QLabel(f"Area selezionata: {width} x {length} blocchi"))
        self.title_edit = QLineEdit(default_title)
        form.addRow("Nome:", self.title_edit)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Solo costruzioni (si adatta al nuovo terreno)", "costruzioni")
        self.mode_combo.addItem("Tutto, terreno compreso", "tutto")
        form.addRow("Cosa copiare:", self.mode_combo)
        self.trees_check = QCheckBox("Includi gli alberi")
        form.addRow("", self.trees_check)
        self.enclosure_check = QCheckBox("Tieni il terreno racchiuso dalla costruzione (cortili, campi, giardini)")
        self.enclosure_check.setChecked(True)
        self.enclosure_check.setToolTip(
            "Il prato di un cortile, il campo di uno stadio, l'aiuola di un giardino chiuso da mura o recinti vengono "
            "copiati con la costruzione (solo lo strato in superficie, con fiori e alberi). Fuori dalla costruzione "
            "il terreno resta quello della nuova mappa.")
        form.addRow("", self.enclosure_check)
        self.ambiguous_check = QCheckBox("Tieni anche neve compatta, terracotta e ghiaccio")
        self.ambiguous_check.setToolTip(
            "Questi blocchi sono anche il terreno naturale di alcuni biomi (cime innevate, badlands): di solito "
            "vengono lasciati fuori, a meno che non poggino sulla costruzione o ne facciano da soffitto. Spunta se "
            "la costruzione e' fatta di questi blocchi (igloo, case di terracotta): vengono tenuti quelli che "
            "poggiano sul terreno, quindi in quei biomi verra' copiato anche un po' di terreno.")
        form.addRow("", self.ambiguous_check)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        return (self.title_edit.text().strip() or "Ritaglio", self.mode_combo.currentData(),
                self.trees_check.isChecked(), self.ambiguous_check.isChecked(), self.enclosure_check.isChecked())


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
    install_error_handler(window)
    window.show()
    sys.exit(app.exec())


def install_error_handler(window):
    """
    PyQt6 closes the application when an exception escapes from a button or map click.
    Report it instead (log panel, crash.log and a message box) and keep the app running.
    """
    import traceback
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash.log")

    def handler(exc_type, exc, tb):
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n{text}\n")
        except OSError:
            pass
        try:
            QApplication.restoreOverrideCursor()
            window.map_viewer.set_mode("place")
            window.log(f"Errore imprevisto: {exc}")
            QMessageBox.critical(
                window, "Errore imprevisto",
                f"Si e' verificato un errore, ma l'app resta aperta e il mondo non e' stato modificato.\n\n"
                f"{exc_type.__name__}: {exc}\n\nDettagli salvati in: {log_path}")
        except Exception:
            sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = handler


if __name__ == "__main__":
    main()
