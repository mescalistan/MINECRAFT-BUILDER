# Hub sotterraneo e iron farm

Primo task del prompt [PROMPT_ARCHITETTO.md](PROMPT_ARCHITETTO.md). Il codice è in
[`tools/templates/hub_farm.py`](../tools/templates/hub_farm.py) e i test in
[`tests/test_hub_farm.py`](../tests/test_hub_farm.py) e [`tests/test_entities.py`](../tests/test_entities.py).

Cosa è verificato e cosa no:

- **Verificato da codice**: entrambi i modelli passano `validate_templates` con 0 errori.
- **Verificato dal simulatore** (`AnalogSim` in `tests/redstone_sim.py`): i circuiti, cioè lo smistatore fetta per fetta e il pistone della farm di giorno e di notte, con la leva accesa e spenta.
- **Verificato dalle regole del gioco**: dove possono nascere i golem e la linea di vista tra villager e zombie. I test le ricostruiscono dal codice di Minecraft Java 1.21.
- **Da provare in gioco**: tempi, flussi d'acqua, rese, comportamento dei mob. Vedi le checklist in fondo.

---

## 1. Catalogo modulare

Nel catalogo ci sono due nuove categorie, **Hub e magazzini** e **Farm automatiche**. I moduli si compongono così:

| Modulo | Dove sta | Come si aggancia |
|---|---|---|
| Hub sotterraneo (`underground_hub`) | 22 blocchi sotto terra, chiosco in superficie | Due **porte di servizio**, a est e a ovest. Sono corridoi larghi 3 e alti 4 al livello del pavimento dell'hub, al centro del lato, e finiscono con un muro di mattoni d'ardesia incrinati con un blocco cesellato al centro: basta scavarlo e prolungare il corridoio verso il modulo. |
| Iron farm (`iron_farm`) | In superficie | Si raggiunge a piedi dal chiosco dell'hub. Il ferro va portato al **Deposito** dell'hub, che lo smista nel barile *Ferro* (e i papaveri in *Papaveri*). |
| Moduli futuri, non ancora costruiti | Sotterranei, agganciati alle porte E/O | Un secondo braccio di smistatore, la stazione dei binari e le farm di colture. Useranno la stessa larghezza di corridoio e la stessa quota del pavimento. |

## 2. Funzioni aggiunte all'app (prerequisiti)

| Funzione | Dove | Note |
|---|---|---|
| **Entità** (villager, zombie, qualunque mob) | `Builder.entity/villager/mob`, `World.add_entity` | Le entità vengono scritte nella cartella `entities/` del mondo, nel chunk giusto, con un UUID nuovo. Hanno `PersistenceRequired`, cioè non spariscono mai. La rotazione della struttura ruota anche la posizione e lo sguardo. Se il file delle entità non c'era, *Annulla ultima iniezione* lo cancella. |
| **Contenuto dei contenitori** | `Builder.contents`, `ChunkEditor.set_block_data` | Gli oggetti sono nel formato 1.20.5+ (`id`, `count`). I nomi (`CustomName` e `custom_name` degli oggetti) sono scritti come testo per i mondi 1.21.5+ e convertiti in JSON per quelli più vecchi. |
| **Strutture interrate** | `Builder.ground_offset` → `MinecraftBuilder.groundOffset` | La quota proposta dall'app tiene conto degli strati sotto il terreno. Anche il validatore ne tiene conto: sotto il livello del suolo le celle non impostate sono roccia. |
| **Aree tecniche sigillate** | `Builder.technical_area` | Il validatore non pretende che siano raggiungibili i blocchi interattivi nascosti apposta, come i letti della capsula dei villager. |
| Dispenser, dropper, crafter, colonne di bolle, cartelli | `tools/blockinfo.py` | Aggiunte le proprietà e i nomi che mancavano. |
| Polvere sui lati dei comparatori | `Builder.connect_redstone` | Come nel gioco, la polvere si collega a un comparatore da ogni lato (ingresso laterale). |
| Simulatore analogico | `tests/redstone_sim.py` (`AnalogSim`) | Simula il segnale che cala lungo la polvere, i comparatori in confronto e sottrazione che leggono i contenitori con la formula ⌊1 + 14 × riempimento⌋, le torce (anche a muro), le leve, i sensori di luce, i pistoni con quasi-connettività e il blocco delle tramogge. Se il circuito oscilla, lo segnala. |
| Spaccato nei render | `render_templates.py --cut=N` | Mostra solo gli strati fino a y=N, per guardare dentro le strutture interrate. |

---

## 3. Hub sotterraneo esagonale con magazzino (`underground_hub`)

### Scheda tecnica

- **Ingombro**: 39 × 38 × 57 blocchi (X × Y × Z).
- **Quota**: 22 strati sotto il terreno. Il pavimento della sala è 22 blocchi sotto la superficie e il chiosco esce sopra.
- **Ambienti**:
  - sala esagonale con raggio 15 e cupola a costoloni alta 18 blocchi;
  - galleria-magazzino a nord, larga 35 blocchi;
  - torre con scala a chiocciola e ascensore a bolle;
  - chiosco in superficie, 11 × 11.
- **Resa dello smistatore**: limitata dalle tramogge, 2,5 oggetti al secondo (una tramoggia sposta un oggetto ogni 8 tick). Il deposito accetta quindi circa 9000 oggetti all'ora, che percorrono la catena a 2,5 blocchi al secondo.
- **Capacità**: 9 categorie da 27 slot (1728 oggetti ciascuna) più il baule di troppo pieno.
- **Mob cap**: nessun impatto. Tutti gli spazi aperti sono illuminati: il validatore non trova punti bui. Ogni cella vuota sotto il suolo confina solo con blocchi messi dal modello, così grotte o falde vicine non possono allagare l'hub.
- **Distanza dal giocatore**: il magazzino funziona solo nei chunk caricati, cioè quando il giocatore è entro la simulation distance.

### Distinta materiali (contata dal modello)

- **Strutturali**:
  - 3688 mattoni d'ardesia (deepslate bricks) e 200 incrinati;
  - 1839 piastrelle d'ardesia (deepslate tiles) e 13 incrinate;
  - 1022 ardesia levigata (polished deepslate);
  - 883 mattoni di tufo (tuff bricks) e 158 tufo levigato (polished tuff);
  - 725 mattoni di pietranera levigata (polished blackstone bricks) e 81 pietranera levigata cesellata (chiseled polished blackstone);
  - 189 vetri;
  - 154 pietrisco d'ardesia (cobbled deepslate);
  - 120 scale di piastrelle e 59 di ardesia levigata;
  - 20 librerie.
- **Redstone e meccanica**: 52 tramogge, 9 comparatori, 27 polveri di redstone, 9 torce di redstone a muro, 10 barili, 2 bauli, 1 sabbia delle anime e la colonna di bolle.
- **Entità**: nessuna.
- **Contenuti scritti dall'app**:
  - in ogni tramoggia filtro, **41 oggetti bersaglio** e **4 bastoni rinominati "Filtro"**;
  - in totale: 41 lingotti di ferro, d'oro e di rame, 41 di redstone, carbone, lapislazzuli, pietrisco, pietrisco d'ardesia e papaveri, più 36 bastoni "Filtro";
  - nomi sui barili (*Ferro*, *Oro*...), sul baule *Deposito* e sul baule *Troppo pieno*.

### Circuito: smistatore anti-overflow (schema tipo ImpulseSV)

La catena **H** è fatta di tramogge al livello y=3, nella fila z=9, con il beccuccio a est. Parte dal baule *Deposito* (x=4), che H svuota da sotto, e dal canale d'acqua del podio, che porta gli oggetti sopra la tramoggia in x=6. Finisce in x=35, dove tre tramogge scendono nel baule *Troppo pieno*.

Ci sono 9 **fette**, una ogni 3 blocchi a x = 8, 11, …, 32. Questa è la fetta a x = X, in coordinate del `Builder`:

| Pezzo | Posizione | Orientamento / stato |
|---|---|---|
| F, tramoggia filtro | (X, 2, 9) | Beccuccio a **ovest**, verso un blocco pieno, così F non spinge mai in L. Contiene 41 bersagli + 4 "Filtro". |
| L, tramoggia bloccata | (X, 1, 9) | Beccuccio a **sud**, nel barile (X, 1, 10). `enabled=false`. |
| C, comparatore | (X, 2, 8) | `facing=south` (legge F), modalità **confronto**. |
| Polvere 1, 2, 3 | (X, 2, 7), (X+1, 2, 7), (X+1, 2, 8) | La terza poggia su S. |
| S, blocco | (X+1, 1, 8) | Blocco pieno. |
| T, torcia a muro | (X+1, 1, 9) | `facing=south`, attaccata a S, accesa. Blocca L, che le sta accanto. |
| Vetro | (X+1, 2, 9) | Sopra T: la torcia non alimenta niente sopra di sé. |

Funzionamento:

- **Segnale a riposo**: con 41 bersagli e 4 riempitivi il riempimento è (41/64 + 4/64)/5 e il segnale vale ⌊1 + 14 × 0,1406⌋ = **2**. Lungo la polvere scende a 2 → 1 → 0, quindi S non è alimentato, T resta accesa e L resta bloccato.
- **Arriva un oggetto**:
  1. con il 42° bersaglio il segnale sale a **3**, la terza polvere vale 1 e alimenta S;
  2. T si spegne e L si sblocca;
  3. L preleva un oggetto da F e lo spinge nel barile;
  4. F torna a 41 e T si riaccende.
- **Ingresso laterale**: la terza polvere si collega anche al lato del comparatore. In modalità confronto 3 ≥ 1, quindi l'uscita resta 3 e non oscilla. In sottrazione oscillerebbe: per questo il comparatore è in confronto.
- **Anti-overflow**: se un barile è pieno, L si ferma e F si riempie. A quel punto F non preleva più da H e gli oggetti di quel tipo proseguono fino al *Troppo pieno*: la catena non si blocca mai.
- **Isolamento**: tra una fetta e l'altra c'è una colonna piena, quindi le polveri di fette vicine non si toccano. Il test `test_one_more_item_unlocks_only_its_slice` lo verifica: ogni fetta si sblocca da sola.
- **Mappa per livelli**:
  - y=0: pavimento;
  - y=1: L, S, T, i barili e i supporti;
  - y=2: F, C, la polvere e il vetro;
  - y=3: la catena H;
  - y=4: il pavimento del podio, con il baule *Deposito* in (4,4,9) e il canale d'acqua da (6,4,13) a (6,4,9).

  Tutto il meccanismo, da z=6 a z=9, è murato dietro i barili: dalla galleria non si vede redstone.

### Estetica

- **Palette**: ardesia (mattoni, piastrelle, levigata), pietranera levigata per lo scheletro (costoloni, pilastri ai vertici), tufo nella parte alta delle pareti e accenti di rame ossidato cerato.
- **Tre livelli di rilievo**:
  - lo zoccolo e i pilastri ai vertici sporgono;
  - la cornice a y=10 ha una corona di 12 lanterne;
  - i costoloni scendono di un blocco sotto la volta e proseguono nel pavimento come raggi scuri.
- **Gradienti**: il pavimento ha fasce concentriche e verso le pareti diventa più consumato (pietrisco d'ardesia); le pareti passano da ardesia levigata a mattoni d'ardesia, con qualche incrinato, e poi a tufo.
- **Arredo**:
  - quattro stazioni: incanti (20 librerie, livello massimo), alchimia, officina e fonderia con canna fumaria in rame;
  - un lampadario a catena al centro e sei lampioni intorno al medaglione.

### Checklist in gioco (hub)

1. Inietta l'hub. L'app propone la quota giusta: il chiosco esce al livello del terreno.
2. **Ascensore**:
   1. scendi dalla scala a chiocciola fino alla sala e torna alla torre;
   2. apri la porta a nord del tubo di vetro ed entra nell'acqua: devi salire fino al chiosco;
   3. esci dalla porta a sud.
   - Se le bolle non ti spingono, rompi e rimetti la sabbia delle anime alla base: le colonne di bolle scritte dall'app sono ferme finché un blocco vicino non viene aggiornato.
3. **Canale d'acqua del podio**: è scritto già con i livelli di flusso giusti. Se un oggetto buttato nel canale non scorre verso il muro, metti e togli un blocco accanto alla sorgente in fondo al canale.
4. **Smistamento**:
   1. metti 1 lingotto di ferro nel baule *Deposito*: dopo qualche secondo deve comparire nel barile *Ferro*;
   2. metti 64 lingotti di ferro: devono arrivare tutti in *Ferro*;
   3. metti un oggetto non previsto, per esempio della terra: deve finire nel *Troppo pieno*.
5. **Filtri**: dopo le prove ogni tramoggia filtro deve avere ancora 41 oggetti nel primo slot. Per controllarla rompi il blocco sopra il barile della fetta e poi rimettilo.
6. **Mondi 1.21.1-1.21.4**: i nomi dei bastoni "Filtro" vengono convertiti in JSON. Controlla che i bastoni nei filtri siano rinominati. Se non lo sono, sostituiscili con 4 bastoni rinominati all'incudine.

---

## 4. Iron farm compatta 1.21+ (`iron_farm`, "Fonderia del ferro")

### Scheda tecnica

- **Ingombro**: 18 × 29 × 18 blocchi. L'edificio occupa 16 × 16, con un blocco di margine per lesene, zoccolo e gronda.
- **Quota**: si appoggia sul terreno, senza parti interrate.
- **Livelli**:
  - piano terra (y 1-7): bauli, pozzo e leva;
  - piattaforma d'acqua: y=9;
  - letti dei villager: y=14;
  - sottotetto tecnico: y 18-19;
  - tetto: y=20, con il tetto a padiglione e il camino sopra.
- **Meccanica**, dal codice Java 1.21:
  - ogni 100 tick un villager in panico prova a evocare un golem, se almeno 3 villager vicini lo "vogliono";
  - per volerlo devono aver dormito nelle ultime 24000 tick e non aver visto un golem nelle ultime 600;
  - il golem nasce con 10 tentativi entro ±8 blocchi in orizzontale e ±6 in verticale.

  Il test `test_golems_can_only_spawn_on_the_platform` ricostruisce questi tentativi. Nel raggio, l'unica superficie dove un golem può nascere e starci è la piattaforma d'acqua: tutto il resto è vetro, vetro colorato, coperto, oppure fuori quota. Per questo le pareti esterne sono lisce tra y=7 e y=20.
- **Resa, ragionata**:
  - **Giorno**: dopo ogni golem i villager aspettano 600 tick. Il golem muore nella lava in circa 10-15 secondi, poi al tentativo successivo, ogni 100 tick, ne nasce un altro. Il ciclo è quindi di circa 35-45 secondi, cioè circa 80-100 golem all'ora con lo zombie visibile. Con 3-5 lingotti per golem (media 4) fanno circa **320-400 lingotti all'ora**, più 0-2 papaveri per golem.
  - **Media sulle 24 ore**: lo zombie è nascosto di notte, quindi la farm funziona circa metà del tempo e la media scende a circa **160-220 all'ora**.

  Sono stime ragionate, non misurate: vanno confermate in gioco.
- **Mob cap**: villager e golem non contano nel limite dei mostri. Lo zombie occupa al massimo 1 dei 70 posti.
- **Requisiti**:
  - il giocatore deve stare entro la simulation distance;
  - sopra y=8 non devono esserci alberi o costruzioni entro 9 blocchi dall'edificio, perché un golem potrebbe nascere sopra;
  - in pianura non serve altro.
- **Bordi dei chunk**: i circuiti sono statici, senza clock né impulsi, quindi a cavallo di un chunk non si rompono. Conviene comunque far coincidere l'edificio (x, z da 1 a 16 del modello) con un chunk, perché si carichi tutto insieme. L'aggancio automatico ai chunk non è ancora nell'app.

### Distinta materiali (contata dal modello)

- **Strutturali**:
  - 1171 ardesia levigata e 968 mattoni d'ardesia;
  - 628 mattoni di pietranera levigata;
  - 618 mattoni, 63 granito e 31 mattoni di fango;
  - 311 scale di piastrelle e 301 piastrelle d'ardesia;
  - 259 vetri, 192 pannelli di vetro nero e 12 pannelli trasparenti;
  - 106 pietra liscia (smooth stone);
  - 64 ardesia cesellata (chiseled deepslate).
- **Redstone e meccanica**: 1 pistone appiccicoso, 1 sensore di luce diurna (normale), 1 torcia a muro, 8 torce di redstone e 8 blocchi di pietra liscia (la torre di torce), 8 polveri, 1 leva, 4 tramogge, 4 bauli, 8 cartelli di quercia a muro, 4 lava, 96 acqua e 6 letti (3 letti doppi).
- **Entità** (le scrive l'app):
  - 3 villager adulti senza professione, sui letti;
  - 1 zombie adulto e persistente sulla lastra della sua cella.
- **Contenuti**: nessuno.

### Circuito e orientamenti

Le coordinate sono quelle del `Builder`; V = 14 è la quota dei letti.

- **Feritoia**:
  - i villager stanno sui letti in (8..10, 14, 6), con la testa a nord;
  - lo zombie sta su una lastra in (9, 14, 10);
  - tra loro c'è una feritoia orizzontale alta 1 blocco a y=16: (8..10, 16, 6..8) più l'apertura (9, 16, 9);
  - sotto la feritoia ci sono vetro e ardesia, sopra il soffitto di vetro.
- **Linea di vista**: l'occhio dei villager sta a 16,18 e quello dello zombie a 16,24, quindi la linea passa tutta nella feritoia. Il test `test_villagers_see_the_zombie_only_through_the_open_slot` la ricostruisce: è libera a feritoia aperta e chiusa quando il blocco è spinto giù. La distanza dallo zombie è al massimo 4,1 blocchi, sotto il limite di 8.
- **Pistone**: un pistone appiccicoso in (9, 18, 9), con `facing=down`, spinge il blocco di pietra liscia (9, 17, 9) dentro l'apertura (9, 16, 9).
- **Giorno e notte**:
  - il sensore di luce diurna (normale) in (10, 19, 11) sta sotto un lucernario di vetro;
  - una polvere in (9, 19, 11) poggia sul blocco S3 in (9, 18, 11);
  - una torcia a muro in (9, 18, 10), `facing=north`, è attaccata a S3 e accanto al pistone.

  Di giorno il sensore dà un segnale ≥ 1, S3 è alimentato, la torcia si spegne e il pistone si ritrae: lo zombie è visibile. Di notte il sensore dà 0, la torcia si accende, il pistone si estende e la feritoia è chiusa: i villager possono dormire.
- **Flush & lock**: la leva è nella nicchia del muro ovest in (3, 4, 9), `face=wall`, `facing=east`. Il segnale sale da lì al sottotetto passando per una torre di torce nel muro:
  - B0 in (2, 4, 9), poi T1 a y=5, B1 a y=6, e così via fino a T8 in (2, 19, 9);
  - ogni torcia inverte il segnale e le inversioni sono 8, un numero pari: a leva accesa T8 è accesa;
  - da T8 parte una linea di 7 polveri a y=19, da (3,19,9) a (9,19,9), sopra il pistone, che arriva con forza 9.

  A **leva accesa** la feritoia resta chiusa giorno e notte e non nascono più golem. I golem già nel pozzo muoiono comunque nella lava e le tramogge restano libere.
- **Simulazione**: i test simulano tutte e quattro le combinazioni, giorno e notte con la leva accesa e spenta, più l'alba con il sensore a 1.
- **Pozzo di uccisione**, al centro (8..9, 8..9):

  | y | Contenuto |
  |---|---|
  | 1 | 4 bauli |
  | 2 | 4 tramogge con `facing=down` |
  | 3 | spazio del golem |
  | 4 | cartelli a muro, che reggono la lava |
  | 5 | **lama di lava**: tocca il golem (alto 2,7) all'altezza della testa |
  | 6 | cartelli a muro, che fermano l'acqua che scende |
  | 7-9 | foro attraverso il pavimento della piattaforma |

  L'acqua e la lava non si toccano mai: tra loro c'è sempre uno strato di cartelli. La lava non arriva agli oggetti, che restano sulle tramogge.
- **Piattaforma**, 10 × 10 da x, z = 4 a 13: le sorgenti stanno sul bordo e il livello dell'acqua cresce di 1 a ogni anello verso il centro. La corrente spinge sempre verso il foro 2 × 2.

### Estetica

- **Palette**: "fonderia" in mattoni rossi con granito e qualche mattone di fango, su uno zoccolo di pietranera.
- **Struttura**:
  - lesene di ardesia levigata sporgenti, che salgono fino alla gronda;
  - fasce di pietranera a y=7 e sotto il tetto;
  - finestroni alti di vetro nero in ogni campata;
  - tetto a padiglione di piastrelle d'ardesia con un camino di mattoni e un fuoco da campo che fuma.
- **Vincolo**: tra y=7 e y=20 la facciata è liscia. Ogni cornice sporgente sarebbe un punto dove un golem può nascere fuori dall'edificio: il rilievo è dato dalle lesene, che arrivano fino alla gronda, e dalle fasce di materiale.
- **Pozzo**: ha finestre di vetro al piano terra, così si vede la lava.

### Checklist in gioco (iron farm)

1. Inietta la farm di **giorno**, in un'area pianeggiante e senza alberi alti vicino. Entra dalla doppia porta a sud: al centro c'è il pozzo con la lava dietro i vetri, ai lati i 4 bauli.
2. **Villager e zombie**: guarda in alto attraverso i vetri del pozzo, oppure sali in creativo. I 3 villager devono essere sui letti e lo zombie nella sua cella.
3. **Notte**:
   - la feritoia si deve chiudere: il blocco di pietra liscia scende;
   - i villager devono **dormire**, con i letti occupati. È indispensabile: senza aver dormito non evocano golem, quindi **i primi golem arrivano solo il giorno dopo la prima notte**.
4. **Giorno**:
   - la feritoia si riapre;
   - nel giro di 1-2 minuti un golem deve nascere sull'acqua, essere spinto nel foro e morire nella lava;
   - il ferro deve arrivare nei bauli.
5. **Leva** accanto al pozzo:
   - accesa: la feritoia si chiude anche di giorno e non nascono golem;
   - spenta: si torna al ciclo giorno/notte.
6. **Se qualcosa non va**:

   | Sintomo | Cosa fare |
   |---|---|
   | L'acqua della piattaforma sembra ferma | La direzione della corrente è già scritta nei livelli. Se i golem non si muovono, metti e togli un blocco sul bordo. |
   | Nessun golem dopo 2 giorni | Controlla che i villager dormano. Se uno è uscito dal letto, rimettilo con un'esca (pane). |
   | Un golem nasce fuori dall'edificio | C'è una superficie solida sopra y=8 entro 9 blocchi, per esempio un albero o una collina: toglila. |

7. **Da confermare**:
   - la resa effettiva all'ora;
   - che i cartelli reggano la lava e fermino l'acqua anche in 26.x (lo fanno da molte versioni);
   - che i villager si prendano i letti su cui stanno.
