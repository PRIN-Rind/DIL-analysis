# Guida all'uso — Script di Annotazione DIL tramite API Claude

**Script**: `annotate_dil_claude_api.py`
**Versione**: 1.0 — Febbraio 2026
**Autore**: Fabio Ciotti

---

## Indice

1. [Panoramica](#1-panoramica)
2. [Prerequisiti](#2-prerequisiti)
3. [Configurazione](#3-configurazione)
4. [Utilizzo](#4-utilizzo)
5. [Output prodotti](#5-output-prodotti)
6. [Stima dei costi](#6-stima-dei-costi)
7. [Risoluzione dei problemi](#7-risoluzione-dei-problemi)
8. [Architettura tecnica](#8-architettura-tecnica)
9. [Note di sicurezza](#9-note-di-sicurezza)

---

## 1. Panoramica

Lo script automatizza l'annotazione del **Discorso Indiretto Libero (DIL)** su un corpus di 500 trigrammi di narrativa italiana, inviando ogni testo alle API ufficiali di Anthropic (Claude) e raccogliendo una valutazione linguistica strutturata.

A differenza della versione precedente (`dil_cognitive_analyzer.py`) basata su regole programmatiche, questo script sfrutta le capacità di ragionamento del modello LLM per produrre annotazioni che tengono conto del contesto narrativo, dello stile dell'autore e delle sfumature teoriche del DIL.

### Cosa fa lo script

```
Dataset CSV (500 trigrammi)
        │
        ▼
Prepara 500 richieste API con prompt linguistico + schema JSON
        │
        ▼
Invia il batch all'API Anthropic (Batches API)
        │
        ▼
Attende il completamento (polling ciclico)
        │
        ▼
Raccoglie le risposte (decisione + ragionamento + marcatori)
        │
        ▼
Salva CSV annotato + log JSONL + metriche
```

---

## 2. Prerequisiti

### Python

Versione minima: **Python 3.10** (richiesta per la sintassi `match/case` usata internamente dall'SDK Anthropic).

Verificare la versione installata:

```bash
python3 --version
```

### Dipendenze

Installare le librerie necessarie:

```bash
pip install anthropic pandas scikit-learn
```

| Libreria | Versione minima | Scopo |
|---|---|---|
| `anthropic` | ≥ 0.40 | SDK ufficiale per le API Anthropic |
| `pandas` | ≥ 1.5 | Caricamento e gestione del dataset CSV |
| `scikit-learn` | ≥ 1.0 | Calcolo metriche (accuracy, F1, kappa) |

### Chiave API Anthropic

È necessaria una chiave API Anthropic attiva. La chiave si ottiene dalla console Anthropic all'indirizzo `console.anthropic.com`. La chiave ha il formato `sk-ant-api03-...`.

---

## 3. Configurazione

Tutta la configurazione è concentrata nel file `api_config.json`. Lo script non contiene parametri hardcoded: questo permette di modificare il comportamento senza toccare il codice.

### Passo obbligatorio: inserire la chiave API

Aprire `api_config.json` e sostituire il placeholder con la propria chiave:

```json
{
  "api_key": "sk-ant-api03-XXXXXXXXXXXXXXXXXXXX",
  ...
}
```

### Parametri configurabili

| Parametro | Default | Descrizione |
|---|---|---|
| `api_key` | *(placeholder)* | Chiave API Anthropic — **obbligatorio** |
| `modello` | `claude-opus-4-6` | Modello da usare (vedi sezione [Scelta del modello](#scelta-del-modello)) |
| `max_tokens` | `512` | Token massimi per la risposta del modello |
| `usa_thinking_adattivo` | `false` | Attiva il ragionamento adattivo (solo Opus 4.6) |
| `percorso_input` | `corpus_labelled-trigrams_500_LLM_annotated.csv` | File CSV di input |
| `percorso_output` | `corpus_labelled-trigrams_500_Sonnet_API_annotated.csv` | File CSV di output |
| `percorso_log_batch` | `batch_ids_log.json` | Log degli ID dei batch inviati |
| `percorso_log_ragionamenti` | `DIL_API_reasoning_log.jsonl` | Log dettagliato dei ragionamenti |
| `percorso_metriche` | `metrics_API_vs_gold.csv` | Tabella metriche in formato CSV |
| `pausa_polling_secondi` | `60` | Secondi tra un controllo e l'altro dello stato del batch |
| `max_tentativi_polling` | `60` | Numero massimo di cicli di polling (60 × 60s = 1 ora max) |
| `colonna_annotazione_nuova` | `DIL_Claude_API` | Nome della nuova colonna nel CSV di output |
| `salva_ragionamento` | `true` | Se salvare il ragionamento per ogni trigramma |

### Scelta del modello

I tre modelli disponibili presentano un trade-off qualità/costo:

| Modello | Qualità | Costo (input/output per 1M token) | Consigliato per |
|---|---|---|---|
| `claude-opus-4-6` | ★★★ Massima | $5 / $25 | Annotazione di ricerca, massima accuratezza |
| `claude-sonnet-4-6` | ★★☆ Elevata | $3 / $15 | Buon compromesso, validazione rapida |
| `claude-haiku-4-5` | ★☆☆ Buona | $1 / $5 | Pre-screening, test preliminari |

Per ricerca accademica sul DIL si raccomanda `claude-opus-4-6`.

---

## 4. Utilizzo

### Modalità standard — Batches API (consigliata)

Esegue l'annotazione completa usando il Batches API di Anthropic. Tutte le 500 richieste vengono inviate in un unico batch, con elaborazione asincrona e 50% di riduzione dei costi.

```bash
python annotate_dil_claude_api.py
```

Lo script stampa il progresso e registra i messaggi anche nel file `annotazione_dil.log`.

### Modalità sequenziale

Esegue una richiesta alla volta, con feedback immediato sul risultato di ogni trigramma. Più lenta ma utile per test su campioni ridotti o quando si vuole monitorare la qualità in tempo reale.

```bash
python annotate_dil_claude_api.py --mode sequential
```

### Riprendere un batch interrotto

Se lo script viene interrotto durante il polling (interruzione di rete, chiusura del terminale, ecc.), il batch continua ad essere elaborato da Anthropic. Per riprendere il polling senza re-inviare le richieste:

```bash
python annotate_dil_claude_api.py --resume msgbatch_01abc123xyz
```

L'ID del batch è reperibile nel file `batch_ids_log.json`, generato automaticamente all'invio.

### File di configurazione alternativo

```bash
python annotate_dil_claude_api.py --config percorso/alla/mia_config.json
```

### Riepilogo argomenti da riga di comando

| Argomento | Valori | Default | Descrizione |
|---|---|---|---|
| `--config` | percorso file | `api_config.json` | File di configurazione JSON |
| `--mode` | `batch`, `sequential` | `batch` | Modalità di annotazione |
| `--resume` | ID batch | — | Riprende il polling di un batch esistente |

---

## 5. Output prodotti

Al termine dell'esecuzione, lo script produce quattro file:

### `corpus_labelled-trigrams_500_Sonnet_API_annotated.csv`

Il dataset originale con l'aggiunta della colonna `DIL_Claude_API`. I valori possibili nella nuova colonna sono:

| Valore | Significato |
|---|---|
| `yes` | DIL presente nel trigramma |
| `no` | DIL assente nel trigramma |
| `api_error` | La richiesta API è fallita per errore server |
| `parse_error` | La risposta non era un JSON valido |
| `expired` | La richiesta è scaduta (batch oltre 24 ore) |
| `non_annotato` | La riga non è stata processata |

### `DIL_API_reasoning_log.jsonl`

Log in formato JSON Lines (una riga per trigramma) con il ragionamento completo del modello. Ogni riga ha la struttura:

```json
{
  "index": 42,
  "timestamp": "2026-02-23T14:30:00",
  "testo_anteprima": "Mario guardò l'orologio...",
  "decisione": "yes",
  "confidenza": "alta",
  "gold_standard": "yes",
  "annotazione_precedente": "no",
  "ragionamento": "Il testo presenta esclamazione emotiva 'Sempre in ritardo!' priva di verbo dichiarativo...",
  "marcatori": ["esclamazione_emotiva", "assenza_verbo_dichiarativo"],
  "tokens_input": 348,
  "tokens_output": 89
}
```

### `batch_ids_log.json`

Log degli ID dei batch inviati, utile per riprendere operazioni interrotte.

### `metrics_API_vs_gold.csv`

Tabella riassuntiva delle metriche (accuracy, precision, recall, F1) confrontate con il gold standard e con l'annotazione precedente.

Le metriche vengono stampate anche su console al termine dell'esecuzione:

```
======================================================================
METRICHE DI VALUTAZIONE — DIL_Claude_API
Richieste valide: 500/500
======================================================================

[1] PERFORMANCE VS GOLD STANDARD (Annotatori Umani)
──────────────────────────────────────────────────────────────────────

  Accuracy:  XX.XX%
  Precision: XX.XX%
  Recall:    XX.XX%
  F1-Score:  XX.XX%
  ...
```

---

## 6. Stima dei costi

Il costo dipende dalla lunghezza dei testi e dal modello scelto. Per 500 trigrammi del corpus utilizzato (lunghezza media ~350 token per testo):

| Modello | Token input stimati | Token output stimati | Costo stimato (senza batch) | Costo stimato (con Batches API) |
|---|---|---|---|---|
| `claude-opus-4-6` | ~180.000 | ~45.000 | ~$2.00 | **~$1.00** |
| `claude-sonnet-4-6` | ~180.000 | ~45.000 | ~$1.21 | **~$0.60** |
| `claude-haiku-4-5` | ~180.000 | ~45.000 | ~$0.40 | **~$0.20** |

Il **Batches API** riduce il costo del 50% rispetto alle chiamate singole sequenziali. La stima assume ~360 token di input per trigramma (system prompt + contesto bibliografico + testo) e ~90 token di output (JSON con decisione + ragionamento breve).

Per calcolare il costo esatto prima dell'invio, è possibile usare la funzione di token counting dell'SDK:

```python
import anthropic
client = anthropic.Anthropic(api_key="...")
count = client.messages.count_tokens(
    model="claude-opus-4-6",
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": prompt_utente}]
)
print(f"Token di input stimati: {count.input_tokens}")
```

---

## 7. Risoluzione dei problemi

### Errore: "La chiave API non è stata impostata"

Aprire `api_config.json` e sostituire il placeholder `INSERISCI_QUI_LA_TUA_CHIAVE_ANTHROPIC` con la propria chiave. Verificare che non ci siano spazi aggiuntivi attorno alla chiave.

### Errore: `ModuleNotFoundError: No module named 'anthropic'`

Installare le dipendenze:
```bash
pip install anthropic pandas scikit-learn
```

### Errore: `AuthenticationError` (HTTP 401)

La chiave API non è valida o è scaduta. Verificare la chiave nella console Anthropic (`console.anthropic.com`).

### Errore: `RateLimitError` (HTTP 429)

Il limite di richieste per minuto è stato raggiunto. In modalità batch questo non si verifica normalmente; in modalità sequenziale lo script gestisce automaticamente l'attesa. Se persiste, ridurre il carico o passare alla modalità batch.

### Il polling si blocca o supera il timeout

Il batch impiega più di 60 minuti (impostazione predefinita). Due opzioni:

1. Aumentare `max_tentativi_polling` in `api_config.json` (es. `120` per 2 ore).
2. Annotare l'ID del batch dal file `batch_ids_log.json` e riprendere in seguito con `--resume`.

### Errori di parsing JSON (`parse_error`)

Con i Structured Outputs il parsing non dovrebbe fallire. Se si verificano errori sistematici, verificare che il modello selezionato sia compatibile con `output_config.format` (tutti i modelli correnti lo supportano).

### Il file di input non viene trovato

Lo script cerca il file CSV nella stessa directory da cui viene eseguito. Specificare il percorso completo nel campo `percorso_input` di `api_config.json`, oppure eseguire lo script dalla cartella che contiene il CSV:

```bash
cd /percorso/alla/cartella/dataset
python /percorso/allo/script/annotate_dil_claude_api.py
```

---

## 8. Architettura tecnica

### Struttura del sistema prompt

Il system prompt inviato a Claude a ogni richiesta contiene:

- La definizione teorica del DIL (Discorso Indiretto Libero)
- I criteri diagnostici (assenza verbi dichiarativi, terza persona, soggettività, ecc.)
- Le distinzioni critiche da altri tipi di discorso riportato
- La gestione dei casi dubbi
- Il formato JSON obbligatorio per la risposta

Il prompt utente aggiunge il contesto bibliografico (autore, opera, anno) e il testo da analizzare.

### Structured Outputs

La risposta del modello è vincolata a un JSON schema con `"strict": true`:

```json
{
  "dil": "yes" | "no",
  "confidenza": "alta" | "media" | "bassa",
  "ragionamento": "stringa",
  "marcatori": ["array", "di", "stringhe"]
}
```

Lo schema garantisce che ogni risposta sia parsable senza logica di fallback.

### Batches API vs chiamate sequenziali

| Aspetto | Batches API | Chiamate sequenziali |
|---|---|---|
| Costo | 50% ridotto | Pieno |
| Velocità | Asincrona (~15-60 min) | Sincrona (~20-30 min per 500 testi) |
| Rate limiting | Gestito automaticamente | Richede gestione manuale |
| Ripristino | ID batch salvato, riprende senza re-inviare | Checkpoint ogni 50 righe |
| Visibilità | Solo al completamento | Tempo reale |

### Flusso di gestione degli errori

```
Richiesta API
    │
    ├─ Successo ──► Parsing JSON ──► Annota riga
    │
    ├─ RateLimitError (429) ──► Attesa 60s ──► Riprova
    │
    ├─ ServerError (5xx) ──► Attesa 30s ──► Riprova
    │
    ├─ ClientError (4xx) ──► Annota come 'api_error' ──► Prosegui
    │
    └─ JSONDecodeError ──► Annota come 'parse_error' ──► Log ──► Prosegui
```

---

## 9. Note di sicurezza

### Protezione della chiave API

La chiave API non deve mai apparire nel codice sorgente o in file committati su repository pubblici o condivisi.

Aggiungere il file di configurazione al `.gitignore` del progetto:

```
# File di configurazione con chiave API — NON committare
api_config.json
batch_ids_log.json
annotazione_dil.log
```

In alternativa alla configurazione via file JSON, è possibile impostare la variabile d'ambiente `ANTHROPIC_API_KEY` e modificare l'inizializzazione del client nello script:

```python
# Sostituisce: client = anthropic.Anthropic(api_key=config["api_key"])
client = anthropic.Anthropic()  # Legge automaticamente ANTHROPIC_API_KEY
```

Per impostare la variabile d'ambiente (sessione corrente):

```bash
# Linux/macOS
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-api03-..."
```

### Dati nel batch

Il contenuto dei trigrammi viene inviato ai server Anthropic per l'elaborazione. Verificare la conformità con la politica sulla privacy dei dati del proprio progetto di ricerca prima di inviare testi soggetti a restrizioni.

---

## File correlati

| File | Tipo | Descrizione |
|---|---|---|
| `annotate_dil_claude_api.py` | Script Python | Script principale di annotazione |
| `api_config.json` | Configurazione | Parametri e chiave API |
| `dil_cognitive_analyzer.py` | Script Python | Versione precedente (regole programmatiche) |
| `REPORT_ANNOTAZIONE_DIL_Sonnet_v2.md` | Report | Risultati e metriche dell'annotazione precedente |
| `corpus_labelled-trigrams_500_LLM_annotated.csv` | Dataset | Input: 500 trigrammi con annotazioni esistenti |

---

*Documentazione generata: febbraio 2026*
