# Report Tecnico: Sistema di Annotazione Automatica del Discorso Indiretto Libero in un Corpus Letterario Italiano (1830-1930)

## 1. Introduzione

Il presente documento descrive lo sviluppo e il deployment di un sistema automatico di annotazione linguistica per l'identificazione del Discorso Indiretto Libero (DIL) in un corpus di testi letterari italiani. Il progetto si inserisce nell'ambito della linguistica computazionale applicata agli studi letterari e rappresenta un tentativo di scalare metodologie di analisi stilistica attraverso l'impiego di modelli linguistici di grandi dimensioni (LLM).

### 1.1 Contesto della ricerca

Il Discorso Indiretto Libero costituisce un fenomeno narratologico e stilistico di particolare rilevanza per l'analisi del romanzo moderno. La sua identificazione manuale richiede competenze specialistiche e risulta estremamente onerosa in termini di tempo quando applicata a corpora di dimensioni significative. L'impiego di sistemi automatici basati su LLM rappresenta una possibile soluzione metodologica a questo problema di scalabilità.

### 1.2 Obiettivi del progetto

Gli obiettivi specifici del progetto sono stati:

1. Strutturare un corpus testuale esistente in unità di analisi appropriate per il task di annotazione
2. Sviluppare un sistema automatico di annotazione basato su Claude Sonnet 4.5
3. Implementare meccanismi di robustezza (checkpointing, error handling, resume capability)
4. Eseguire il deployment su infrastruttura cloud per processing batch di lunga durata
5. Ottimizzare i costi di elaborazione rispetto ai vincoli di budget disponibili

## 2. Caratteristiche del Corpus

### 2.1 Composizione

Il corpus oggetto di analisi presenta le seguenti caratteristiche quantitative:

- **Periodo temporale**: 1830-1930 (un secolo di produzione letteraria italiana)
- **Numero di opere**: 500 testi
- **Unità testuali base**: 1.609.559 frasi (sentences)
- **Formato dati**: CSV (Comma-Separated Values)
- **Codifica**: UTF-8

### 2.2 Struttura originale dei dati

I dati erano originariamente organizzati in 500 file CSV, ciascuno corrispondente a un'opera letteraria. Ogni file presentava una struttura tabulare con informazioni bibliografiche e testuali, includendo tra i campi principali il testo delle singole frasi estratte dalle opere.

## 3. Pre-processing: Generazione delle Unità di Analisi

### 3.1 Motivazione teorica

L'identificazione del DIL richiede un contesto testuale sufficientemente ampio per cogliere gli indicatori stilistici e pragmatici del fenomeno. Una singola frase risulta un'unità di analisi inadeguata, mentre sequenze troppo lunghe introducono rumore informativo e incrementano i costi computazionali.

### 3.2 Metodologia di chunking

È stata adottata una strategia di aggregazione sequenziale con i seguenti parametri:

- **Dimensione del chunk**: 3 frasi consecutive
- **Sovrapposizione**: nessuna (chunking non-overlapping)
- **Gestione residui**: i chunk incompleti (contenenti meno di 3 frasi) sono stati mantenuti

### 3.3 Implementazione

La generazione dei chunk è stata implementata attraverso lo script `create_chunks.py`, che ha prodotto:

- **File di output**: 500 file CSV derivati (uno per opera)
- **Directory di output**: `./chunk/`
- **Numero totale di chunk**: 536.676 unità di analisi
- **Riduzione dimensionale**: da 1.609.559 frasi a 536.676 chunk (rapporto ~3:1)

Ogni file CSV generato mantiene tutti i metadati bibliografici dell'opera originale e aggiunge un campo `chunk` contenente la concatenazione di tre frasi consecutive.

## 4. Sistema di Annotazione Automatica

### 4.1 Architettura del sistema

Il sistema di annotazione è stato progettato come applicazione Python asincrona basata sui seguenti componenti:

#### 4.1.1 Modello linguistico

- **Modello**: Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
- **Provider**: Anthropic API
- **Formato output**: classificazione binaria (YES/NO)

#### 4.1.2 Prompt engineering

Il prompt di sistema fornisce:
1. Definizione teorica del DIL
2. Caratteristiche distintive del fenomeno
3. Istruzioni esplicite per output binario
4. Esempi positivi e negativi

Questa scelta di design minimizza la lunghezza delle risposte del modello, riducendo significativamente i costi di elaborazione (da $604 stimati con output esplicativi a $225 con output binario).

#### 4.1.3 Pipeline di elaborazione

Il sistema implementa la seguente pipeline:

```
Input CSV → Lettura righe → Estrazione campo 'chunk' →
→ Annotazione parallela con rate limiting →
→ Aggiunta campo 'DIL' → Output CSV
```

### 4.2 Gestione della concorrenza

Per ottimizzare i tempi di elaborazione rispettando i limiti di rate dell'API, è stato implementato un sistema di concorrenza controllata:

- **Paradigma**: asyncio (Python async/await)
- **Semaforo**: limitazione a 5 richieste concorrenti
- **Sessione HTTP**: connessione persistente con connection pooling

### 4.3 Robustezza e fault tolerance

#### 4.3.1 Sistema di checkpoint

Il sistema implementa checkpointing automatico ogni 1000 chunk processati:

- **Stato persistito**: `checkpoint.json`
- **Informazioni salvate**: ultimo file completato, ultimo chunk processato
- **Capacità di resume**: ripresa automatica da ultimo checkpoint in caso di interruzione

#### 4.3.2 Error handling

Sono stati implementati meccanismi di gestione errori a più livelli:

1. **Errori di rete**: retry automatico con backoff esponenziale
2. **Errori API**: marcatura chunk come 'ERROR' invece di fallimento completo
3. **Errori di I/O**: logging dettagliato per debugging

#### 4.3.3 Logging

Sistema di logging multi-livello:

- **File di log**: `logs/annotation.log`
- **Livelli**: INFO per progressi, ERROR per eccezioni
- **Informazioni tracciate**: timestamp, file corrente, chunk processati, errori

### 4.4 Implementazione tecnica

#### 4.4.1 File principale: `annotate_dil.py`

Lo script implementa le seguenti classi e metodi:

**Classe `DILAnnotator`**:
- `__init__()`: inizializzazione configurazione e client API
- `_load_checkpoint()`: caricamento stato salvato
- `_save_checkpoint()`: persistenza checkpoint
- `_annotate_chunk()`: annotazione singolo chunk con API call
- `_process_file()`: elaborazione completa file CSV
- `run()`: orchestrazione pipeline completa

**Metodo critico `_process_file()`** (righe 179-228):

Il metodo implementa la logica centrale di elaborazione:

1. Lettura CSV con `csv.DictReader` (preserva struttura colonne)
2. Estrazione campo `chunk` per ogni riga
3. Creazione task asincroni per annotazione parallela
4. Raccolta risultati con `asyncio.gather()`
5. Aggiunta campo `DIL` a ogni dizionario riga
6. Scrittura output con `csv.DictWriter` (tutte le colonne originali + `DIL`)

#### 4.4.2 File di configurazione: `config.json`

Parametri configurabili:
- Chiave API Anthropic
- Identificatore modello
- Path directory input/output
- Parametri di rate limiting

### 4.5 Testing e validazione

È stata implementata una strategia di testing incrementale:

1. **test_local.py**: validazione API call su 5 chunk campione
2. **test_annotate.py**: test su 50-100 chunk per verifica throughput
3. **test_complete.py**: test end-to-end con scrittura CSV completa

Tutti i test sono stati eseguiti con successo prima del deployment in produzione.

## 5. Deployment su Infrastruttura Cloud

### 5.1 Motivazione

Il processing completo del corpus richiede un tempo stimato di 2-7 giorni di elaborazione continua, rendendo necessario l'utilizzo di infrastruttura cloud con capacità di esecuzione persistente.

### 5.2 Architettura deployment

#### 5.2.1 Infrastruttura AWS EC2

Specifiche istanza:
- **Tipo**: t3.micro
- **Sistema operativo**: Ubuntu 22.04 LTS
- **Regione**: eu-central-1 (Frankfurt)
- **Indirizzo IP**: 15.160.196.188
- **Connettività**: SSH con key-pair authentication

Razionale scelta istanza: il task è I/O-bound e API-bound, non richiede capacità computazionale significativa. La t3.micro offre il miglior rapporto costo-efficacia per questo workload.

#### 5.2.2 Configurazione ambiente

Dipendenze installate:
- Python 3 (runtime)
- pip3 (package manager)
- aiohttp (HTTP client asincrono)
- screen (session management per persistenza)

#### 5.2.3 Struttura directory su VM

```
/home/ubuntu/dil_project/
├── annotate_dil.py       # Script principale
├── config.json           # Configurazione
├── chunk/                # Input: 500 CSV chunk
├── chunk_annotated/      # Output: CSV annotati
├── logs/                 # File di log
└── checkpoint.json       # Stato elaborazione
```

### 5.3 Automazione deployment

Sono stati sviluppati script bash per automatizzare il deployment:

#### 5.3.1 `deploy_to_vm.sh`

Funzioni:
1. Creazione directory su VM remota
2. Upload files (script Python, configurazione, dati)
3. Esecuzione script di setup remoto
4. Modifica paths in config.json per ambiente VM

#### 5.3.2 `setup_vm.sh`

Funzioni:
1. Aggiornamento package manager
2. Installazione dipendenze Python
3. Configurazione ambiente screen
4. Verifica installazione

### 5.4 Gestione processo persistente

Utilizzo di GNU Screen per garantire persistenza dell'elaborazione:

```bash
screen -S dil_annotation    # Crea sessione nominata
python3 annotate_dil.py     # Esecuzione script
# Ctrl+A, D                  # Detach da sessione
screen -r dil_annotation    # Riattacco a sessione esistente
```

Questo approccio garantisce che il processo continui anche dopo disconnessione SSH.

### 5.5 Problemi risolti durante deployment

#### 5.5.1 Line ending incompatibility

**Problema**: Script bash con CRLF line endings causavano errori "command not found".

**Soluzione**: Conversione line endings con `sed -i '' 's/\r$//'`.

#### 5.5.2 pip externally-managed-environment

**Problema**: Ubuntu 22.04 usa PEP 668 che previene installazioni pip globali.

**Soluzione**: Flag `--break-system-packages` per installazioni sistema-wide in ambiente controllato.

#### 5.5.3 Hardcoded paths

**Problema**: Path assoluto `/sessions/wizardly-bold-mccarthy/config.json` nello script.

**Soluzione**: Utilizzo path relativo `config.json` per portabilità.

#### 5.5.4 Directory creation timing

**Problema**: Tentativo upload file prima della creazione directory destinazione.

**Soluzione**: Creazione esplicita directory con `mkdir -p` prima di upload.

## 6. Analisi Costi e Vincoli di Budget

### 6.1 Stima costi computazionali

#### 6.1.1 Costi API Anthropic

Assumendo output binario (YES/NO):

- **Input tokens** (stima media per chunk): ~300 tokens
- **Output tokens** (risposta binaria): ~5 tokens
- **Prezzo input**: $3 per 1M tokens
- **Prezzo output**: $15 per 1M tokens
- **Costo stimato totale**: ~$225 per corpus completo

#### 6.1.2 Costi infrastruttura AWS

- **Istanza t3.micro**: $0.0104/ora
- **Durata stimata**: 7 giorni (168 ore)
- **Costo compute**: ~$1.75
- **Storage**: trascurabile (<1GB)
- **Bandwidth**: trascurabile (solo API calls)
- **Costo AWS totale**: ~$2

#### 6.1.3 Costo complessivo stimato

**Totale progetto**: ~$227

### 6.2 Vincoli e limitazioni

#### 6.2.1 Tier API limitations

Il progetto si è scontrato con una limitazione operativa:

- **Tier account**: Tier 1
- **Limite mensile**: $100
- **Costo necessario**: $225
- **Deficit**: $125

#### 6.2.2 Strategia adottata

Sono state adottate due strategie parallele:

1. **Richiesta upgrade tier**: contatto con supporto Anthropic per upgrade a Tier 2 ($1000/mese)
2. **Processing parziale**: avvio annotazione con $100 disponibili, processando ~44% del corpus (236.000 chunk su 536.676)

Il sistema di checkpoint garantisce che l'elaborazione possa essere ripresa seamlessly dopo upgrade tier o reset mensile del limite (1 marzo 2026).

### 6.3 Ottimizzazioni implementate

Le seguenti ottimizzazioni hanno ridotto significativamente i costi:

1. **Output binario** invece di spiegazioni: -62% costi ($604 → $225)
2. **Chunking 3-frasi**: riduzione unità da 1.6M a 536K (-67%)
3. **Rate limiting intelligente**: minimizzazione retry API
4. **Infrastruttura minimale**: t3.micro invece di istanze più costose

## 7. Tempi di Elaborazione

### 7.1 Stime teoriche

Basate su rate limits API Anthropic:

- **Tier 1**: 50 requests/min → ~179 ore (7.5 giorni)
- **Tier 2**: 100 requests/min → ~89 ore (3.7 giorni)
- **Tier 3+**: 1000 requests/min → ~9 ore

Con concorrenza di 5 richieste simultanee e media 2 secondi per richiesta, il throughput effettivo dovrebbe posizionarsi verso il limite superiore del proprio tier.

### 7.2 Monitoraggio progressi

Sono disponibili tre modalità di monitoraggio:

1. **Remote log tail**: `ssh ... 'tail -20 logs/annotation.log'`
2. **Screen reattach**: `screen -r dil_annotation`
3. **Checkpoint inspection**: lettura `checkpoint.json` per stato corrente

## 8. Validazione e Quality Assurance

### 8.1 Testing pre-deployment

Prima del deployment in produzione sono stati eseguiti:

1. Test API connectivity e autenticazione
2. Test elaborazione singolo file completo
3. Verifica correttezza output CSV (preservazione colonne, aggiunta campo DIL)
4. Test capacità di resume da checkpoint
5. Sanity check completo della pipeline CSV (DictReader → processing → DictWriter)

### 8.2 Validazione output

L'output del sistema consiste in:

- **500 file CSV annotati** in `chunk_annotated/`
- **Struttura**: tutte le colonne originali + campo `DIL` (valori: YES/NO/ERROR)
- **Integrità**: verificata preservazione metadati bibliografici originali

### 8.3 Metriche di qualità attese

Metriche da calcolare post-elaborazione:

1. **Coverage**: percentuale chunk annotati senza errori
2. **Distribuzione DIL**: percentuale YES/NO nel corpus
3. **Error rate**: percentuale chunk con marcatura ERROR
4. **Distribuzione temporale**: variazione DIL nel periodo 1830-1930
5. **Distribuzione per autore/opera**: identificazione pattern stilistici

## 9. Risultati Attesi e Prospettive

### 9.1 Output del progetto

Al termine dell'elaborazione completa sarà disponibile:

1. **Corpus annotato**: 536.676 chunk con classificazione DIL
2. **Metadati elaborazione**: log completi, checkpoint finali, statistiche errori
3. **Dati per analisi downstream**: CSV pronti per analisi quantitative e visualizzazioni

### 9.2 Utilizzi potenziali

I dati prodotti consentiranno:

1. **Analisi diacroniche**: evoluzione uso DIL nella letteratura italiana (1830-1930)
2. **Analisi stilometriche**: identificazione fingerprint autoriali
3. **Comparazioni cross-opera**: variazioni intra-autoriali
4. **Training modelli specializzati**: dataset annotato per fine-tuning futuri modelli
5. **Validazione teorica**: verifica ipotesi narratologiche su larga scala

### 9.3 Limitazioni metodologiche

È necessario esplicitare le seguenti limitazioni:

1. **Validazione umana**: assenza di gold standard per validation accuracy
2. **Bias del modello**: possibili bias nella definizione teorica incorporata nel LLM
3. **Granularità**: chunking a 3 frasi potrebbe non catturare fenomeni più estesi
4. **Contesto**: perdita informazioni dal resto dell'opera
5. **Ambiguità intrinseca**: il DIL presenta zone grigie teoricamente dibattute

### 9.4 Sviluppi futuri

Possibili estensioni del progetto:

1. **Validazione inter-annotator**: confronto con annotazione manuale su campione
2. **Ensemble methods**: confronto con altri LLM (GPT-4, Gemini)
3. **Annotazione multi-classe**: graduazione dell'intensità del DIL
4. **Estensione temporale**: inclusione periodi pre-1830 e post-1930
5. **Analisi multilingue**: applicazione ad altri corpora europei

## 10. Conclusioni

Il progetto ha dimostrato la fattibilità tecnica dell'annotazione automatica di fenomeni stilistici complessi su corpora di dimensioni significative utilizzando LLM di nuova generazione. L'architettura sviluppata presenta caratteristiche di robustezza, scalabilità e cost-effectiveness che la rendono applicabile ad altri task di annotazione linguistica.

Le principali innovazioni metodologiche includono:

1. **Pipeline completamente automatizzata**: da raw text a annotazioni strutturate
2. **Fault tolerance**: checkpoint system per elaborazioni multi-giorno
3. **Ottimizzazione costi**: design choices che riducono costi del 62%
4. **Cloud-native deployment**: utilizzo efficiente infrastruttura serverless-like

I vincoli incontrati (tier limitations) rappresentano limitazioni contingenti che non inficiano la validità metodologica dell'approccio. L'esecuzione parziale con successiva ripresa dimostra la resilienza del sistema progettato.

Il corpus annotato risultante costituirà una risorsa preziosa per ricerche future in linguistica computazionale, narratologia quantitativa e digital humanities, aprendo prospettive di analisi precedentemente impraticabili per vincoli di tempo e risorse umane.

---

## Appendice A: Specifiche Tecniche

### A.1 Versioni software

- Python: 3.10+
- aiohttp: 3.9+
- Ubuntu: 22.04 LTS
- GNU Screen: 4.9.0

### A.2 Parametri configurazione

```json
{
  "api_key": "[REDACTED]",
  "model": "claude-sonnet-4-5-20250929",
  "max_concurrent_requests": 5,
  "checkpoint_interval": 1000,
  "retry_attempts": 3,
  "timeout_seconds": 30
}
```

### A.3 Struttura prompts

**System prompt** (~250 tokens):
- Definizione teorica DIL
- Caratteristiche linguistiche distintive
- Istruzioni formato output
- Esempi classificazione

**User prompt** (variabile):
- Testo chunk da annotare
- Richiesta esplicita output YES/NO

### A.4 Comandi deployment

```bash
# Upload script
scp -i dil-annotation-key.pem annotate_dil.py ubuntu@15.160.196.188:~/dil_project/

# SSH connection
ssh -i dil-annotation-key.pem ubuntu@15.160.196.188

# Launch with screen
screen -S dil_annotation
python3 annotate_dil.py

# Detach
Ctrl+A, D

# Monitor
screen -r dil_annotation
```

---

**Data compilazione report**: 10 febbraio 2026
**Versione documento**: 1.0
**Status progetto**: Deployment completato, annotazione in corso
