# 🏰 MINECRAFT BUILDER

**Minecraft Auto-Builder & Map Editor** è un'applicazione desktop moderna e performante sviluppata in **Python** e **PyQt6**, progettata per caricare mondi di Minecraft (file Anvil `.mca`), tracciare la posizione in tempo reale del giocatore, visualizzare l'anteprima 2D/3D di strutture (`.nbt`, `.schem`, `.schematic`) e iniettarle direttamente nel mondo con integrazione intelligente al terreno e ai biomi circostanti.

---

## ✨ Funzionalità Principali

- 🗺️ **Visualizzatore Mappa Anvil (.mca)**:
  - Rendering topografico ad alta velocità con hillshading e colori distinti per altimetria e biomi.
  - Zoom incentrato sul cursore del mouse e navigazione Pan fluida.
  - HUD fluttuante in stile glassmorphism con coordinate globali, coordinate del chunk, altezza Y e bioma stimato.
- 📍 **Rilevamento e Tracciamento Giocatore**:
  - Localizzazione automatica delle ultime coordinate del giocatore dai file di salvataggio (`level.dat`, `playerdata`, `players`).
  - Animazione radar circolare pulsante sul marker del giocatore.
  - Pulsante per centrare istantaneamente la visuale sulla regione del personaggio.
- 🏗️ **Gestione e Posizionamento Strutture**:
  - Libreria integrata con strutture dettagliate da mod rinomate (*Ice and Fire*, *Better Strongholds*, *Create Astral*).
  - Browser per cercare e scaricare schemi online.
  - Anteprima grafica top-down 2D dei blocchi reali con trasparenza per allineamento preciso.
  - Rotazione a 90° oraria (`R`) e drag-and-drop con click-to-place.
  - Sistema di code a posizionamenti multipli (Staging) per iniettare più strutture contemporaneamente.
- 🌱 **Integrazione Intelligente col Terreno**:
  - **Adattamento Altezza**: Calcolo automatico della quota media dell'ingombro della struttura.
  - **Fondamenta Naturali**: Rilevamento del bioma superficiale (erba/terra, sabbia/arenaria, neve, roccia) e riempimento automatico dei vuoti sottostanti.
  - **Scavo Terreno**: Rimozione automatica di ostacoli (terra, pietra) per i volumi interni d'aria.
  - **Consiglio Posizione Ottimale**: Scanner euristico per individuare la zona più pianeggiante nelle vicinanze.
- ⚡ **Architettura Asincrona & Sicurezza**:
  - Iniezione blocchi gestita in un thread dedicato in background (`QThread`) senza bloccare l'interfaccia utente.
  - Backup automatico di sicurezza dei file `.mca` prima di ogni modifica.
  - Rilevamento dello stato di blocco del mondo (`session.lock`) per prevenire corruzioni di dati.
  - Elevazione automatica dei privilegi Amministratore (UAC) su Windows.
  - Console di log high-tech con colorazione sintattica HTML delle operazioni.

---

## 🚀 Requisiti e Installazione

### Prerequisiti
- **Python 3.10+**
- **Git**

### Installazione

1. Clona il repository:
   ```bash
   git clone https://github.com/mescalistan/MINECRAFT-BUILDER.git
   cd MINECRAFT-BUILDER
   ```

2. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```

3. Avvia l'applicazione:
   ```bash
   python main.py
   ```

---

## 📦 Struttura del Progetto

```
.
├── main.py                 # Finestra principale, controller GUI, worker thread asincrono
├── map_viewer.py           # Canvas interattivo della mappa, rendering e HUD
├── mca_codec.py            # Parser e scrittore Anvil (.mca), gestione blocchi e heightmap
├── nbt_codec.py            # Codec puro Python per la lettura/scrittura di file NBT
├── structure_manager.py    # Caricatore di strutture (.nbt/.schem) e trasformazioni 3D
├── scraper.py              # Catalogo schemi online e downloader
├── templates/              # Cartella schemi e strutture preinstallate
└── requirements.txt        # Dipendenze Python
```

---

## 🛡️ Note di Sicurezza
Prima di iniettare strutture in un mondo di Minecraft, assicurarsi che il mondo non sia attualmente aperto nel gioco. Il programma creerà automaticamente una copia di backup (`.bak`) del file di regione nella cartella dei salvataggi prima di applicare le modifiche.

---

## 📄 Licenza
Rilasciato sotto licenza MIT.
