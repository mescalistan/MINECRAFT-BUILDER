# 🏰 MINECRAFT BUILDER

**Minecraft Auto-Builder & Map Editor** è un'applicazione desktop moderna e performante sviluppata in **Python** e **PyQt6**, progettata per caricare mondi di Minecraft (file Anvil `.mca`), tracciare la posizione in tempo reale del giocatore, visualizzare l'anteprima 2D/3D di strutture (`.nbt`, `.schem`, `.schematic`) e iniettarle direttamente nel mondo con integrazione intelligente al terreno e ai biomi circostanti.

---

## ✨ Funzionalità Principali

- 🗺️ **Visualizzatore Mappa Anvil (.mca)**:
  - Rendering topografico ad alta velocità con hillshading e colori distinti per altimetria e biomi.
  - Zoom incentrato sul cursore del mouse e navigazione Pan fluida.
  - HUD fluttuante in stile glassmorphism con coordinate globali, coordinate del chunk, altezza Y e bioma stimato.
- 📂 **Apertura automatica del mondo**:
  - Basta indicare un qualsiasi percorso legato al mondo: la cartella del mondo, una sua sottocartella (`region`, `DIM-1`, `playerdata`...), `level.dat`, un file `.mca`, la cartella `saves` o `.minecraft`. L'app ricava da sola cartella dei salvataggi, mondo e dimensione.
  - Il percorso si può scegliere con *Sfoglia...*, incollare nel campo (Invio) o trascinare sulla finestra; da riga di comando: `py -3 main.py "percorso"`.
  - Selettore Overworld / Nether / End, elenco dei soli mondi validi (dal più recente) e ripresa automatica dell'ultimo mondo aperto.
- 🗂️ **Libreria per categorie**: Case, Castelli e fortezze, Torri, Ponti, Monumenti, Templi e luoghi sacri, Fattorie e animali, Piazze e decorazioni, Utilità e magia, Navi, Rovine e portali, Fantascienza e Ritagli, con ricerca per nome/descrizione.
- 🌉 **Ponti su misura** (scheda *Ponti*): quattro stili (pietra ad archi, legno, mattoni del Nether, sospeso) di qualsiasi lunghezza.
  - *Disegna ponte tra due sponde*: due clic sulla mappa e il ponte viene calcolato con lunghezza, direzione e altezza giuste (sempre sopra il livello dell'acqua); i piloni scendono fino al fondo nello stesso materiale.
  - Se il nuovo ponte parte vicino alla fine di un ponte esistente (in coda o costruito in precedenza, memorizzato nel mondo) lo prosegue senza interruzioni, nello stesso stile e alla stessa altezza.
  - I ponti della libreria si possono allungare o accorciare mantenendo lo stile.
- 🏘️ **Generatore di villaggi** (scheda *Villaggio*): pianura, borgo medievale o nordico, in tre dimensioni. Crea piazza, strade a croce che seguono il terreno, edifici con la porta rivolta verso la strada, fattorie, sentieri e lampioni, evitando acqua, pendii e zone non generate.
- ✂️ **Ritagli** (scheda *Ritagli*): trascina un rettangolo sulla mappa per salvare una zona di un mondo come struttura. In modalità *Solo costruzioni* terreno, piante e alberi naturali non vengono copiati e viene memorizzata la quota d'appoggio, così incollandola su un'altra mappa si adatta al nuovo terreno (cantine comprese); in modalità *Tutto* viene copiato anche il terreno.
- 📍 **Rilevamento e Tracciamento Giocatore**:
  - Localizzazione automatica delle ultime coordinate del giocatore dai file di salvataggio (`level.dat`, `playerdata`, `players`).
  - Animazione radar circolare pulsante sul marker del giocatore.
  - Pulsante per centrare istantaneamente la visuale sulla regione del personaggio.
- 🏗️ **Gestione e Posizionamento Strutture**:
  - Libreria integrata di 65 modelli vanilla giocabili (monumenti famosi, classici di Minecraft, castelli, case, fattorie) più le strutture da mod originali (*Ice and Fire*, *Better Strongholds*, *Create Astral*).
  - Browser per cercare e scaricare schemi online.
  - Anteprima grafica top-down 2D dei blocchi reali con trasparenza per allineamento preciso.
  - Rotazione a 90° oraria (`R`) e drag-and-drop con click-to-place.
  - Sistema di code a posizionamenti multipli (Staging) per iniettare più strutture contemporaneamente.
- 🌱 **Integrazione Intelligente col Terreno**:
  - **Adattamento Altezza**: Calcolo automatico della quota media dell'ingombro della struttura.
  - **Fondamenta Naturali**: Rilevamento del terreno reale sotto la struttura (erba/terra, sabbia/arenaria, neve, roccia) e riempimento dei vuoti sottostanti. Archi e ponti mantengono lo spazio vuoto sotto le campate.
  - **Scavo Terreno**: Rimozione automatica di ostacoli (terra, pietra, alberi) per i volumi interni d'aria.
  - **Strutture a cavallo delle regioni**: i blocchi oltre il bordo del file `.mca` vengono scritti nelle regioni vicine.
  - **Rotazione completa**: oltre a `facing`/`axis` ruotano anche recinti, vetri, muretti, cartelli, stendardi e binari.
  - **Consiglio Posizione Ottimale**: Scanner euristico per individuare la zona più pianeggiante nelle vicinanze.
- ⚡ **Architettura Asincrona & Sicurezza**:
  - Iniezione blocchi gestita in un thread dedicato in background (`QThread`) senza bloccare l'interfaccia utente.
  - Modifica per sezioni (ogni sezione 16×16×16 viene decodificata e ricodificata una sola volta): migliaia di volte più veloce dell'approccio blocco per blocco.
  - Regioni caricate in modo lazy: la mappa legge solo le heightmap e il salvataggio riscrive solo i chunk modificati, copiando gli altri byte per byte.
  - Scrittura atomica e backup automatico di ogni file `.mca` modificato.
  - Luce e heightmap dei chunk modificati invalidate: Minecraft le ricalcola al caricamento.
  - I chunk non generati vengono saltati (mai creati vuoti) e i blocchi di mod vengono saltati nei mondi vanilla.
  - Compatibile con i mondi dalla 1.18 a Minecraft 26.x: legge e scrive sia il formato classico dei blocchi (`{Name, Properties}`) sia quello nuovo (stringhe e `{id, properties}`), e aggiorna i nomi dei blocchi rinominati (es. `chain` → `iron_chain`, `grass` → `short_grass`) in base alla versione del mondo.
  - Le fondamenta riempiono solo vuoti piccoli (fino a 10 blocchi) e mai sotto strutture appoggiate sull'acqua: le costruzioni sospese restano sospese; i piloni dei ponti scendono fino al fondo.
  - Rilevamento dello stato di blocco del mondo (`session.lock`) per prevenire corruzioni di dati.
  - Elevazione a Amministratore (UAC) solo su richiesta con `py -3 main.py --admin`.
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
   - **Windows**: doppio clic su `avvia.bat` (installa le dipendenze al primo avvio), oppure
     ```bash
     py -3 main.py
     ```
   - **Altri sistemi**:
     ```bash
     python3 main.py
     ```

   > Se compare `No module named 'PyQt6'`, il comando `python` sta aprendo un interprete diverso da quello in cui `pip` ha installato le dipendenze (ad esempio un Python di MSYS2 nel PATH). Usa `avvia.bat` o `py -3 main.py`.

---

## 📦 Struttura del Progetto

```
.
├── main.py                 # Finestra principale, controller GUI, worker thread asincrono
├── map_viewer.py           # Canvas interattivo della mappa, rendering e HUD
├── mca_codec.py            # Parser e scrittore Anvil (.mca) lazy, ChunkEditor per sezioni, heightmap
├── world_editor.py         # Accesso al mondo in coordinate globali (multi-regione), iniezione, sentieri
├── world_locator.py        # Riconosce mondo/saves/dimensione da qualsiasi percorso
├── catalog.py              # Catalogo delle strutture con categorie in italiano
├── structure_generators.py # Ponti parametrici, ponte tra due sponde con aggancio, lampioni
├── village_generator.py    # Generatore di villaggi
├── world_extractor.py      # Ritaglio di zone di mondo come strutture
├── nbt_codec.py            # Codec puro Python per la lettura/scrittura di file NBT
├── structure_manager.py    # Caricatore di strutture (.nbt/.schem) e trasformazioni 3D
├── scraper.py              # Catalogo schemi online e downloader
├── templates/              # Cartella schemi e strutture preinstallate
├── tools/
│   ├── template_builder.py # Mini-DSL per creare strutture .nbt (stanze, cupole, archi, tetti...)
│   ├── templates/          # Definizioni dei template, un modulo per categoria
│   ├── build_templates.py  # Genera i template vanilla 1.21 e templates/catalog.json
│   ├── validate_templates.py # Validatore di giocabilita' dei template
│   ├── render_templates.py # Render isometrici e gallerie in docs/
│   └── blockinfo.py        # Conoscenza dei blocchi vanilla (nomi, proprieta', luce, colori)
├── docs/                   # Gallerie e render dei template
├── tests/                  # Test automatici su mondi sintetici: python -m unittest discover -s tests
└── requirements.txt        # Dipendenze Python
```

### 🧱 Libreria di template vanilla (65 modelli)

Tutti generati da codice con `python tools/build_templates.py` (solo blocchi vanilla, DataVersion 3955 / MC 1.21.1), validati automaticamente per la giocabilità e testati con iniezione in un mondo. Il livello y=0 di ogni modello è il primo strato sopra il terreno.


#### 🌍 Monumenti famosi (23)

![Landmark](docs/gallery_landmark.png)

| Modello | File | Dimensioni (X×Y×Z) | Descrizione |
|---|---|---|---|
| Arc de Triomphe | `arc_de_triomphe.nbt` | 17×19×11 | Arco di Trionfo di Parigi con fornice principale, archi laterali, rilievi e terrazza panoramica. |
| Big Ben (Elizabeth Tower) | `big_ben.nbt` | 11×52×11 | Torre dell'orologio di Londra con quadranti, cella campanaria, guglia e scala interna. |
| Colosseum | `colosseum.nbt` | 41×17×33 | Colosseo di Roma: anello ellittico a quattro ordini di arcate, gradinate, arena e un lato in rovina. |
| Dutch Windmill | `dutch_windmill.nbt` | 17×26×17 | Mulino a vento olandese di Kinderdijk: base ottagonale in mattoni, ballatoio, cappello e pale in tela. |
| Eiffel Tower | `eiffel_tower.nbt` | 25×60×25 | Torre Eiffel in scala: quattro gambe ad arco, due piattaforme panoramiche e scala a pioli centrale. |
| El Castillo (Chichen Itza) | `el_castillo.nbt` | 45×25×45 | Piramide maya di Kukulkan: nove terrazze, scalinate sui quattro lati e tempio sulla cima. |
| Five-Storey Pagoda | `five_storey_pagoda.nbt` | 17×38×17 | Pagoda giapponese a cinque piani con gronde ricurve, pilastro centrale e guglia sorin. |
| Gothic Cathedral | `gothic_cathedral.nbt` | 23×42×47 | Cattedrale gotica ispirata a Notre-Dame: navata alta, archi rampanti, rosone, vetrate colorate e due torri. |
| Great Pyramid of Giza | `great_pyramid.nbt` | 39×21×39 | Grande Piramide con facce lisce, corridoio d'ingresso illuminato e camera del re con il tesoro. |
| Great Wall Segment | `great_wall.nbt` | 11×17×45 | Tratto della Grande Muraglia cinese con camminamento merlato e torre di guardia abitabile. |
| Leaning Tower of Pisa | `leaning_tower_pisa.nbt` | 15×40×15 | Torre di Pisa pendente in marmo con logge a colonne, cella campanaria e scala interna. |
| Moai of Easter Island | `moai_heads.nbt` | 19×13×8 | Tre statue Moai dell'Isola di Pasqua su un ahu di pietra, una con il pukao rosso. |
| Obelisk | `obelisk.nbt` | 13×38×13 | Obelisco in marmo bianco in stile Washington Monument, su piazza a gradini con lanterne. |
| Onion Dome Cathedral | `onion_dome_cathedral.nbt` | 21×34×21 | Cattedrale a cupole a cipolla ispirata a San Basilio: torre centrale a tenda e cappelle con cupole colorate a strisce. |
| Pantheon | `pantheon.nbt` | 25×24×33 | Pantheon di Roma: rotonda con cupola e oculo, pavimento a scacchi e pronao a colonne con frontone. |
| Parthenon | `parthenon.nbt` | 19×18×33 | Partenone di Atene: stilobate a gradini, peristilio di colonne doriche, frontoni e cella con statua. |
| Space Needle | `space_needle.nbt` | 23×56×23 | Torre panoramica ispirata allo Space Needle di Seattle: gambe a clessidra, disco ristorante vetrato e guglia. |
| Stonehenge | `stonehenge.nbt` | 27×8×27 | Cerchio megalitico di Stonehenge con architravi, triliti interni, pietre cadute e altare. |
| Suspension Bridge | `suspension_bridge.nbt` | 71×36×9 | Ponte sospeso rosso ispirato al Golden Gate: due torri con traversi, cavi parabolici, tiranti e carreggiata. |
| Taj Mahal | `taj_mahal.nbt` | 41×36×57 | Taj Mahal in marmo bianco: piattaforma, iwan ad arco, cupola a cipolla, quattro minareti e vasca riflettente. |
| Temple of Heaven | `temple_of_heaven.nbt` | 25×28×25 | Tempio del Cielo di Pechino: tre terrazze di marmo con balaustre, sala rotonda rossa e tre tetti blu con pinnacolo d'oro. |
| Torii Gate | `torii_gate.nbt` | 15×11×7 | Portale torii rosso in stile Itsukushima con architrave nera ricurva e lanterne di pietra. |
| Tower Bridge | `tower_bridge.nbt` | 49×36×9 | Tower Bridge di Londra: due torri gotiche, passerelle alte vetrate, catene blu e carreggiata. |

#### ⛏️ Classici di Minecraft (11)

![Minecraft Classic](docs/gallery_minecraft_classic.png)

| Modello | File | Dimensioni (X×Y×Z) | Descrizione |
|---|---|---|---|
| Ancient City Portal | `ancient_city_portal.nbt` | 27×19×11 | Il grande portale della citta' antica in ardesia rinforzata, con sculk, lanterne dell'anima e casse. |
| Desert Temple | `desert_temple.nbt` | 21×16×21 | Tempio del deserto con torri decorate in terracotta, sala centrale a mosaico e quattro casse del tesoro. |
| Desert Well | `desert_well.nbt` | 5×5×5 | Il classico pozzo del deserto in arenaria con acqua al centro e tettoia su quattro pilastri. |
| End City Tower | `end_city_tower.nbt` | 15×38×15 | Torre della citta' dell'End in purpur, con stanze sporgenti, verghe dell'End e vetrate magenta. |
| Igloo | `igloo.nbt` | 11×6×14 | Igloo di neve con tunnel d'ingresso, letto, fornace, banco da lavoro e tappeti. |
| Jungle Temple | `jungle_temple.nbt` | 14×12×17 | Tempio della giungla in pietrisco muschioso su due livelli, con viticci, scalinata e cassa. |
| Nether Fortress Bridge | `nether_fortress_bridge.nbt` | 7×11×31 | Ponte della fortezza del Nether in mattoni infernali con archi, ringhiere e giardino di verruche. |
| Pillager Outpost | `pillager_outpost.nbt` | 15×24×15 | Avamposto dei predoni in quercia scura e betulla, con piani collegati da scale e terrazza di vedetta. |
| Plains Village House | `plains_village_house.nbt` | 11×10×9 | Casa del villaggio delle pianure: fondamenta in pietrisco, travi di quercia, fioriere e arredamento. |
| Ruined Portal | `ruined_portal.nbt` | 13×10×9 | Portale in rovina con cornice di ossidiana spezzata, netherrack, magma, oro e cassa del bottino. |
| Witch Hut | `witch_hut.nbt` | 9×14×10 | Capanna della strega su palafitte in abete con calderone, vaso con fungo e scala d'accesso. |

#### 🏰 Medievale (6)

![Medieval](docs/gallery_medieval.png)

| Modello | File | Dimensioni (X×Y×Z) | Descrizione |
|---|---|---|---|
| Castle Gatehouse | `castle_gatehouse.nbt` | 21×22×15 | Corpo di guardia con saracinesca, due torri cilindriche, ponte levatoio e camminamento merlato. |
| Castle Keep | `castle_keep.nbt` | 23×33×23 | Mastio normanno a quattro piani con torrette angolari, sala del trono, camere, armeria e camminamento. |
| Medieval Tavern | `medieval_tavern.nbt` | 17×15×15 | Taverna su due piani: bancone, botti, tavoli, focolare con camino e stanze per gli ospiti al piano di sopra. |
| Medieval Watchtower | `watchtower.nbt` | 9×16×9 | Torre di guardia 7x7 alta 16 blocchi con scala a pioli, piano intermedio e merli. |
| Viking Longhouse | `viking_longhouse.nbt` | 13×12×27 | Casa lunga vichinga a forma di scafo con focolare centrale, panche, letti e teste di drago sul tetto. |
| Village Chapel | `village_chapel.nbt` | 11×22×21 | Cappella di villaggio con campanile, campana, panche, altare con candele e vetrate. |

#### 🧙 Fantasy (5)

![Fantasy](docs/gallery_fantasy.png)

| Modello | File | Dimensioni (X×Y×Z) | Descrizione |
|---|---|---|---|
| Fairytale Castle | `fairytale_castle.nbt` | 35×44×29 | Castello da fiaba ispirato a Neuschwanstein: mura bianche, torri con tetti conici blu, cortile e sale illuminate. |
| Hobbit Hole | `hobbit_hole.nbt` | 19×10×19 | Casa hobbit scavata in una collina erbosa: porta rotonda, finestre tonde, camere, cucina e giardino fiorito. |
| Pirate Ship | `pirate_ship.nbt` | 13×30×39 | Galeone pirata con scafo in quercia scura, due alberi con vele, coffa, cabina del capitano, cannoni e stiva. |
| Treehouse | `treehouse.nbt` | 19×27×19 | Casa sull'albero: grande quercia scura, piattaforma con capanna, ringhiera, scala a pioli e chioma folta. |
| Wizard Tower | `wizard_tower.nbt` | 15×38×15 | Torre del mago in ardesia con tetto conico di ametista, biblioteca con tavolo da incantamento, alchimia e alloggio. |

#### 🏠 Case (5)

![House](docs/gallery_house.png)

| Modello | File | Dimensioni (X×Y×Z) | Descrizione |
|---|---|---|---|
| Blacksmith Forge | `blacksmith_forge.nbt` | 9×11×9 | Fucina aperta con altoforno, incudine, banco da forgiatura e camino fumante. |
| Modern Villa | `modern_villa.nbt` | 23×10×20 | Villa moderna in cemento bianco e vetro: volume superiore a sbalzo, terrazza, piscina, scala interna e giardino. |
| Skyscraper | `skyscraper.nbt` | 15×64×15 | Grattacielo di 15 piani con facciata in vetro, atrio, uffici illuminati, scala a pioli nel nucleo ed eliporto. |
| Starter Cottage | `starter_cottage.nbt` | 11×10×11 | Casetta 9x9 in quercia con tetto a capanna, letto, forno, cassa e illuminazione. |
| Tudor House | `tudor_house.nbt` | 13×17×13 | Casa Tudor a graticcio con piano superiore sporgente, tetto ripido, camino e due piani arredati. |

#### 🌾 Fattorie (5)

![Farm](docs/gallery_farm.png)

| Modello | File | Dimensioni (X×Y×Z) | Descrizione |
|---|---|---|---|
| Animal Pen | `animal_pen.nbt` | 11×4×11 | Recinto per animali con riparo, fieno, compostiera e abbeveratoi. |
| Crop Farm (Mixed) | `crop_farm.nbt` | 11×3×15 | Campo idratato con grano, carote, patate e barbabietole, recintato. |
| Greenhouse | `greenhouse.nbt` | 11×12×15 | Serra in vetro con struttura in quercia: aiuole coltivate e irrigate, fiori, compostiera e banco. |
| Horse Stable | `horse_stable.nbt` | 15×14×13 | Scuderia in abete con sei box, cancelli, fieno, abbeveratoi, cassa per selle e tetto a capanna. |
| Sugar Cane Farm | `sugar_cane_farm.nbt` | 13×4×13 | Piantagione di canna da zucchero: file di sabbia irrigate, recinto con cancello e lampioni. |

#### 🛠️ Utilità (6)

![Utility](docs/gallery_utility.png)

| Modello | File | Dimensioni (X×Y×Z) | Descrizione |
|---|---|---|---|
| Beacon Pyramid | `beacon_pyramid.nbt` | 9×6×9 | Piramide completa a quattro livelli in ferro e oro con faro attivo sulla cima. |
| Enchanting Room | `enchanting_room.nbt` | 9×11×9 | Stanza dell'incantamento al livello massimo (15 librerie), con leggio, incudine, cassa e tappeto. |
| Lighthouse | `lighthouse.nbt` | 11×28×11 | Faro a strisce bianche e rosse con galleria panoramica e lanterna in vetro. |
| Nether Portal Shrine | `nether_portal_shrine.nbt` | 8×7×5 | Portale del Nether gia' acceso su piattaforma in pietranera con lanterne dell'anima. |
| Stone Bridge | `stone_bridge.nbt` | 5×7×25 | Ponte in pietra 5x25 a tre pile con archi, parapetti e lanterne. |
| Villager Trading Hall | `villager_trading_hall.nbt` | 23×13×11 | Sala degli scambi con 20 celle per villici, ognuna con il proprio blocco professione (porta i tuoi villici). |

#### ⛲ Decorazioni (4)

![Decoration](docs/gallery_decoration.png)

| Modello | File | Dimensioni (X×Y×Z) | Descrizione |
|---|---|---|---|
| Fountain Plaza | `fountain_plaza.nbt` | 17×8×17 | Piazza con fontana a tre vasche, panchine, aiuole fiorite e lampioni. |
| Market Stall | `market_stall.nbt` | 5×5×5 | Bancarella con tendone a righe, bancone, barili e lanterna. |
| Village Well | `village_well.nbt` | 6×9×6 | Pozzo da villaggio con acqua, tettoia in pietra e lanterne. |
| Zen Garden | `zen_garden.nbt` | 19×9×19 | Giardino zen giapponese con ghiaia, laghetto con ninfee, ponticello, ciliegi in fiore, bambu' e lanterne di pietra. |

### 🧰 Strumenti per i template

```bash
python tools/build_templates.py            # rigenera tutti i template e templates/catalog.json
python tools/build_templates.py --list     # elenco per categoria
python tools/validate_templates.py         # controllo di giocabilità (0 errori richiesti)
python tools/render_templates.py --gallery # render isometrici in docs/ (richiede requirements-dev.txt)
python -m unittest discover -s tests -v    # test automatici
```

Il validatore controlla: nomi e proprietà dei blocchi vanilla, supporti (torce, scale a pioli, lanterne, colture, porte, blocchi con gravità), letti e porte completi, raggiungibilità a piedi di ogni blocco interattivo (letti, casse, banchi da lavoro...) partendo dall'esterno, porte non murate, zone interne buie dove nascono mob, fluidi che possono fuoriuscire e foglie che si seccano.

Per creare un nuovo modello aggiungi una funzione decorata con `@template(...)` in uno dei moduli di `tools/templates/`: la mini-DSL di `tools/template_builder.py` offre stanze, muri, cilindri, cupole, coni, piramidi, archi, tetti a capanna/padiglione/pagoda, porte con gradino, letti, scale a pioli e alberi, e calcola da sola connessioni di recinti/pannelli/muretti e forma delle scale.

---

## 🛡️ Note di Sicurezza
Prima di iniettare strutture in un mondo di Minecraft, assicurarsi che il mondo non sia attualmente aperto nel gioco. Il programma creerà automaticamente una copia di backup (`.bak`) di ogni file di regione modificato nella cartella `region/backups` prima di applicare le modifiche.

Il mondo deve essere in formato 1.18 o successivo. Le strutture salvate prima della 1.13 (DataVersion < 1451) vanno ricaricate con uno structure block e risalvate prima di poterle iniettare.

---

## 📄 Licenza
Rilasciato sotto licenza MIT.
