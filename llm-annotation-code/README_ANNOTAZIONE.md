# Sistema di Annotazione DIL (Discorso Indiretto Libero)

Sistema automatico per annotazione di corpus letterario italiano usando Claude Sonnet 4.5.

## File forniti

```
annotate_dil.py         # Script principale per annotazione completa
test_annotate.py        # Script di test su campione ridotto
config.json             # File di configurazione (da completare)
README_ANNOTAZIONE.md   # Questa guida
```

## Setup iniziale

### 1. Configura API key

Apri `config.json` e sostituisci `YOUR_API_KEY_HERE` con la tua chiave API Anthropic:

```json
{
  "anthropic_api_key": "sk-ant-api03-...",
  ...
}
```

### 2. Installa dipendenze

```bash
pip install aiohttp --break-system-packages
```

(Il flag `--break-system-packages` è necessario nell'ambiente VM)

### 3. Verifica configurazione

Controlla che i percorsi in `config.json` siano corretti:
- `input_dir`: cartella con file `*_chunk.csv`
- `output_dir`: cartella per file annotati (verrà creata automaticamente)

## Workflow consigliato

### Fase 1: Test iniziale

**Testa con 50-100 chunk per verificare:**
- Connessione API funzionante
- Qualità delle annotazioni
- Costi effettivi
- Velocità di elaborazione

```bash
python3 test_annotate.py
```

Lo script ti chiederà quanti chunk testare e fornirà:
- Distribuzione annotazioni (YES/NO)
- Esempi di risposte
- Costi effettivi
- Stima costo totale corpus
- Throughput (chunk/min)

**Validazione manuale**: Controlla alcuni esempi per verificare che il modello annoti correttamente.

### Fase 2: Annotazione completa

Una volta validato il test, avvia l'annotazione completa:

```bash
python3 annotate_dil.py
```

Lo script:
1. Mostra riepilogo configurazione
2. Chiede conferma prima di iniziare
3. Processa tutti i file in `chunk/`
4. Salva risultati in `chunk_annotated/`
5. Crea checkpoint automatici ogni 1000 chunk
6. Log dettagliato in `annotation.log`

## Funzionalità di resilienza

### Checkpoint automatici

Lo script salva stato ogni 1000 chunk in `annotation_state.json`. Include:
- Numero chunk processati
- File completati
- Costo totale corrente
- Timestamp

### Resume automatico

Se lo script si interrompe (errore, rate limit, connessione):
1. Riavvia semplicemente `python3 annotate_dil.py`
2. Lo script rileverà il checkpoint
3. Riprenderà dal punto esatto di interruzione

### Retry automatico

- Ogni richiesta API fallita viene ritentata fino a 3 volte
- Gestione automatica dei rate limit (error 429)
- Exponential backoff per errori temporanei

## Monitoring durante l'esecuzione

### Log in tempo reale

```bash
tail -f annotation.log
```

Mostra:
- Progresso (X/Y chunk, %)
- Velocità (chunk/s)
- ETA (tempo stimato rimanente)
- Costo corrente

### Stato corrente

```bash
cat annotation_state.json
```

Mostra snapshot completo dello stato.

## Configurazione parametri

### Rate limiting

In `config.json`, parametro `max_concurrent_requests`:
- **5** (default): Conservativo, per tier bassi o test
- **10-15**: Standard, per tier 2-3
- **20+**: Aggressivo, solo per tier 4+ o enterprise

### Checkpoint interval

`checkpoint_interval: 1000`: Frequenza salvataggio stato
- Valori più bassi: checkpoint più frequenti ma più overhead I/O
- Valori più alti: meno overhead ma più chunk da rifare in caso di crash

## Struttura output

I file annotati in `chunk_annotated/` hanno la stessa struttura degli input più il campo `DIL`:

```csv
"filename","nome","titolo","anno","chunk","DIL"
"Autore-Titolo-Anno","Autore","Titolo","1890","Testo del chunk...","YES"
```

Valori possibili per `DIL`:
- `YES`: Discorso indiretto libero presente
- `NO`: Discorso indiretto libero assente
- `UNCLEAR`: Risposta ambigua dal modello (raro)
- `ERROR`: Errore API dopo tutti i retry (da riprocessare)

## Stima costi e tempi

### Con $5 di credito

Per test conservativo:
- ~50-100 chunk: $0.02-0.10
- ~1.000 chunk: $0.40-0.50
- ~5.000 chunk: $2.00-2.50

Per corpus completo (536.676 chunk):
- Costo stimato: ~$225
- Tempo (tier 2, 5 concurrent): ~180 ore (~7.5 giorni)
- Tempo (tier 3, 15 concurrent): ~60 ore (~2.5 giorni)

### Upgrade tier

Per ottenere tier più alti e velocizzare:
1. Usa API per alcune settimane
2. Spendi soglie progressive ($100, $500, $1000)
3. Oppure contatta Anthropic sales per upgrade immediato

## Troubleshooting

### Errore: "API key non configurata"
→ Completa `config.json` con la tua chiave API

### Errore: "Rate limit exceeded" continuo
→ Riduci `max_concurrent_requests` in `config.json`

### Molte annotazioni "UNCLEAR"
→ Il prompt potrebbe necessitare calibrazione. Verifica esempi in test.

### Script si blocca senza errori
→ Controlla `annotation.log` per dettagli. Possibile issue di rete.

### File già processati riprocessati
→ Assicurati che `annotation_state.json` non sia corrotto

## Esecuzione su cloud VM (raccomandato)

Per run continuativi di giorni, usa VM cloud:

```bash
# Su VM GCP/AWS
screen -S dil_annotation
python3 annotate_dil.py

# Detach: Ctrl+A, poi D
# Logout tranquillo dalla VM

# Riconnetti dopo
screen -r dil_annotation
```

## Note finali

- **Backup**: I file originali in `chunk/` non vengono modificati
- **Incrementale**: Puoi interrompere e riprendere in qualsiasi momento
- **Parallelizzazione**: Lo script usa async per massimizzare throughput
- **Logging**: Tutti gli eventi sono tracciati in `annotation.log`

## Supporto

In caso di problemi, controlla:
1. `annotation.log` per errori dettagliati
2. `annotation_state.json` per stato corrente
3. Documentazione API Anthropic: https://docs.anthropic.com
