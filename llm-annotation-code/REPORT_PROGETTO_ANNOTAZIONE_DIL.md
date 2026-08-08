# Report Tecnico: Sistema di Annotazione Automatica del Discorso Indiretto Libero in un Corpus Letterario Italiano (1830–1930)

## 1. Introduzione

Il presente documento descrive lo sviluppo e il deployment di un sistema automatico di annotazione linguistica per l'identificazione del Discorso Indiretto Libero (DIL) in un corpus di testi letterari italiani. Il progetto si inscrive nell'ambito della linguistica computazionale applicata agli studi letterari e rappresenta un tentativo di scalare metodologie di analisi stilistica attraverso l'impiego di modelli linguistici di grandi dimensioni (LLM).

### 1.1 Contesto della ricerca

Il Discorso Indiretto Libero costituisce un fenomeno narratologico e stilistico di particolare rilevanza per l'analisi del romanzo moderno. La sua identificazione manuale richiede competenze specialistiche e risulta estremamente onerosa in termini di tempo quando applicata a corpora di dimensioni significative. L'impiego di sistemi automatici basati su LLM rappresenta una soluzione metodologica al problema della scalabilità, aprendo prospettive di analisi finora impraticabili per vincoli di risorse umane.

### 1.2 Obiettivi del progetto

Gli obiettivi specifici del progetto sono stati:

1. Strutturare un corpus testuale preesistente in unità di analisi appropriate per il task di annotazione
2. Sviluppare un sistema automatico di annotazione basato su Claude Sonnet 4.5
3. Implementare meccanismi di robustezza (checkpointing, error handling, resume capability)
4. Eseguire il deployment su infrastruttura cloud per processing batch di lunga durata
5. Ottimizzare i costi di elaborazione rispetto ai vincoli di budget disponibili

---

## 2. Caratteristiche del Corpus

### 2.1 Composizione

Il corpus oggetto di analisi presenta le seguenti caratteristiche quantitative:

| Parametro | Valore |
|---|---|
| Periodo temporale | 1830–1930 |
| Numero di opere | 500 |
| Unità testuali base | 1.609.559 frasi |
| Formato dati | CSV (UTF-8) |

### 2.2 Struttura originale dei dati

I dati erano organizzati in 500 file CSV, ciascuno corrispondente a un'opera letteraria. Ogni file presentava una struttura tabulare con metadati bibliografici e il testo delle singole frasi estratte.

---

## 3. Pre-processing: Generazione delle Unità di Analisi (Chunking)

### 3.1 Motivazione teorica

L'identificazione del DIL richiede un contesto testuale sufficientemente ampio per cogliere gli indicatori stilistici e pragmatici del fenomeno. Una singola frase risulta un'unità di analisi inadeguata, mentre sequenze troppo lunghe introducono rumore informativo e incrementano i costi computazionali. La scelta di aggregare 3 frasi consecutive rappresenta un compromesso operativamente motivato.

### 3.2 Strategia di chunking

- **Dimensione del chunk**: 3 frasi consecutive
- **Sovrapposizione**: nessuna (chunking non-overlapping)
- **Gestione residui**: i chunk incompleti (meno di 3 frasi) sono stati mantenuti

### 3.3 Risultati

Lo script `create_chunks.py` ha prodotto:

| Parametro | Valore |
|---|---|
| File di output | 500 CSV (uno per opera) |
| Totale chunk generati | 536.676 |
| Riduzione dimensionale | da 1.609.559 a 536.676 unità (~67%) |

Ogni file CSV derivato mantiene i metadati bibliografici originali e aggiunge un campo `chunk` contenente la concatenazione di tre frasi consecutive.

---

## 4. Sistema di Annotazione Automatica

### 4.1 Architettura generale

Il sistema è implementato come applicazione Python asincrona. I componenti principali sono:

**Modello linguistico**
- Modello: Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
- Provider: Anthropic API
- Formato output: classificazione binaria (YES / NO)

**Pipeline di elaborazione**

```
Input CSV → Lettura righe (DictReader) → Estrazione campo 'chunk'
→ Annotazione asincrona con rate limiting
→ Aggiunta campo 'DIL' → Output CSV (DictWriter)
```

### 4.2 Prompt engineering

Il prompt di sistema fornisce: definizione teorica del DIL, caratteristiche linguistiche distintive, istruzioni esplicite per output binario ed esempi positivi e negativi. La scelta di un output binario (YES/NO) anziché esplicativo ha ridotto i costi stimati da $604 a $225 (−62%).

### 4.3 Gestione della concorrenza

- **Paradigma**: `asyncio` (Python async/await)
- **Semaforo**: massimo 5 richieste concorrenti
- **Sessione HTTP**: connessione persistente con connection pooling via `aiohttp`

### 4.4 Robustezza e fault tolerance

**Checkpointing automatico** ogni 1.000 chunk processati:
- Stato persistito in `checkpoint.json`
- Ripresa automatica da ultimo checkpoint in caso di interruzione

**Error handling multilivello**:
- Errori di rete: retry con backoff esponenziale
- Errori API: marcatura chunk come `ERROR` senza fallimento dell'intero processo
- Errori I/O: logging dettagliato per debugging post-hoc

**Logging**:
- File: `logs/annotation.log`
- Livelli: INFO per progressi, ERROR per eccezioni

### 4.5 Implementazione: metodo `_process_file()`

Nucleo della pipeline (script `annotate_dil.py`, righe 179–228):

```python
# Lettura CSV (preserva struttura colonne)
rows = []
with open(csv_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# Creazione task asincroni
tasks = []
for row in rows:
    chunk_text = row['chunk']
    tasks.append(self._annotate_chunk(session, semaphore, chunk_text))

# Esecuzione parallela con rate limiting
annotations = await asyncio.gather(*tasks)

# Aggiunta annotazione a ogni riga
for row, annotation in zip(rows, annotations):
    row['DIL'] = annotation if annotation else 'ERROR'

# Scrittura output (tutte le colonne originali + DIL)
with open(output_file, 'w', encoding='utf-8', newline='') as f:
    fieldnames = list(rows[0].keys())
    writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(rows)
```

---

## 5. Deployment su Infrastruttura Cloud (AWS EC2)

### 5.1 Motivazione

Il processing completo del corpus richiede un tempo stimato di 2–7 giorni di elaborazione continua, rendendo necessaria un'infrastruttura cloud con capacità di esecuzione persistente.

### 5.2 Specifiche istanza

| Parametro | Valore |
|---|---|
| Tipo istanza | t3.micro |
| Sistema operativo | Ubuntu 22.04 LTS |
| Regione AWS | eu-central-1 (Frankfurt) |
| Indirizzo IP | 15.160.196.188 |
| Autenticazione | SSH key-pair |

La scelta di t3.micro è motivata dalla natura del workload: il task è I/O-bound e API-bound, non richiede capacità computazionale significativa, e la t3.micro offre il miglior rapporto costo-efficacia.

### 5.3 Struttura directory su VM

```
/home/ubuntu/dil_project/
├── annotate_dil.py       # Script principale
├── config.json           # Configurazione
├── chunk/                # Input: 500 CSV chunk
├── chunk_annotated/      # Output: CSV annotati
├── logs/                 # Log di sistema
└── checkpoint.json       # Stato elaborazione
```

### 5.4 Automazione deployment

Due script bash hanno automatizzato il processo:

- **`deploy_to_vm.sh`**: creazione directory, upload files, esecuzione setup remoto, adattamento path in `config.json`
- **`setup_vm.sh`**: installazione dipendenze Python, configurazione screen

### 5.5 Gestione processo persistente (GNU Screen)

```bash
screen -S dil_annotation    # Crea sessione nominata
python3 annotate_dil.py     # Avvio annotazione
# Ctrl+A, D                  # Detach (processo resta attivo)
screen -r dil_annotation    # Riattacco alla sessione
```

### 5.6 Problemi risolti durante il deployment

| Problema | Causa | Soluzione |
|---|---|---|
| "command not found" in bash | CRLF line endings (Windows) | `sed -i '' 's/\r$//'` sui file .sh |
| pip externally-managed-environment | PEP 668 su Ubuntu 22.04 | Flag `--break-system-packages` |
| Path hardcoded nello script | Path assoluto di sviluppo | Sostituzione con path relativo `config.json` |
| Upload fallito | Directory non ancora create | Aggiunta `mkdir -p` prima dell'upload |

---

## 6. Analisi dei Costi

### 6.1 Costi API Anthropic

| Parametro | Valore |
|---|---|
| Input tokens (stima per chunk) | ~300 tokens |
| Output tokens (risposta binaria) | ~5 tokens |
| Prezzo input | $3 / 1M tokens |
| Prezzo output | $15 / 1M tokens |
| **Costo totale stimato** | **~$225** |

### 6.2 Costi infrastruttura AWS

| Componente | Costo |
|---|---|
| t3.micro (7 giorni) | ~$1.75 |
| Storage / Bandwidth | trascurabile |
| **Totale AWS** | **~$2** |

**Costo complessivo stimato: ~$227**

### 6.3 Vincoli e strategia adottata

L'account Anthropic in uso è classificato come Tier 1, con limite mensile di $100, insufficiente a coprire l'intero corpus ($225 stimati). Sono state adottate due strategie parallele:

1. **Richiesta upgrade tier** al supporto Anthropic (passaggio a Tier 2, limite $1.000/mese)
2. **Processing parziale**: avvio annotazione con $100 disponibili, coprendo ~44% del corpus (~236.000 chunk su 536.676). Il sistema di checkpoint garantisce ripresa seamless dopo upgrade o reset mensile (1° marzo 2026).

---

## 7. Testing e Validazione

### 7.1 Strategia di test incrementale

| Script | Scope | Finalità |
|---|---|---|
| `test_local.py` | 5 chunk | Validazione API e autenticazione |
| `test_annotate.py` | 50–100 chunk | Verifica throughput e rate limiting |
| `test_complete.py` | File completo | Test end-to-end con scrittura CSV |

Tutti i test hanno prodotto risultati attesi prima del deployment in produzione.

### 7.2 Sanity check pre-lancio

Prima del lancio definitivo è stato effettuato un sanity check completo della logica `_process_file()`, verificando: correttezza della lettura con `DictReader`, preservazione della struttura colonne, aggiunta del campo `DIL` come ultima colonna, integrità dell'output con `DictWriter`.

---

## 8. Risultati Attesi e Prospettive

### 8.1 Output del progetto

Al termine dell'elaborazione sarà disponibile:
- 536.676 chunk con classificazione DIL (YES / NO / ERROR)
- 500 file CSV annotati in `chunk_annotated/`
- Log completi e statistiche di elaborazione

### 8.2 Possibili utilizzi

I dati prodotti consentiranno analisi diacroniche sull'evoluzione del DIL nel periodo 1830–1930, analisi stilometriche per l'identificazione di fingerprint autoriali, validazione di ipotesi narratologiche su larga scala, e la costituzione di un dataset annotato per il fine-tuning di modelli specializzati.

### 8.3 Limitazioni metodologiche

È necessario esplicitare le seguenti limitazioni:

- **Assenza di gold standard**: nessuna validazione sistematica rispetto ad annotazioni manuali di riferimento
- **Bias del modello**: possibili bias nella concettualizzazione del DIL incorporata nel LLM
- **Granularità**: il chunking a 3 frasi potrebbe non catturare fenomeni più estesi o distribuiti
- **Contesto ridotto**: perdita di informazioni derivanti dal macrocontesto narrativo
- **Ambiguità intrinseca**: il DIL presenta zone grigie teoricamente dibattute nella letteratura specialistica

---

## 9. Conclusioni

Il progetto ha dimostrato la fattibilità tecnica dell'annotazione automatica di fenomeni stilistici complessi su corpora di dimensioni significative mediante LLM di nuova generazione. L'architettura sviluppata presenta caratteristiche di robustezza, scalabilità e cost-effectiveness che la rendono potenzialmente applicabile ad altri task di annotazione linguistica in ambito digital humanities.

Le principali innovazioni metodologiche includono: la pipeline completamente automatizzata (da raw text a annotazioni strutturate), il fault tolerance tramite checkpoint system per elaborazioni multi-giorno, l'ottimizzazione dei costi tramite output binario (−62%), e il deployment cloud-native su infrastruttura minimale.

I vincoli incontrati — in particolare la limitazione del tier API — rappresentano condizioni contingenti che non inficiano la validità metodologica dell'approccio. La capacità di ripresa tramite checkpoint ne attesta la resilienza operativa.

---

## Appendice: Specifiche Tecniche

### A.1 Versioni software

| Software | Versione |
|---|---|
| Python | 3.10+ |
| aiohttp | 3.9+ |
| Ubuntu | 22.04 LTS |
| GNU Screen | 4.9.0 |

### A.2 Comandi deployment principali

```bash
# Upload script corretto
scp -i dil-annotation-key.pem annotate_dil.py ubuntu@15.160.196.188:~/dil_project/

# Connessione SSH
ssh -i dil-annotation-key.pem ubuntu@15.160.196.188

# Avvio annotazione con screen
screen -S dil_annotation
python3 annotate_dil.py

# Monitoraggio da remoto
ssh -i dil-annotation-key.pem ubuntu@15.160.196.188 'tail -20 ~/dil_project/logs/annotation.log'
```

---

*Data compilazione: 21 febbraio 2026 — Versione documento: 1.1 — Status: Deployment completato, annotazione in corso*
