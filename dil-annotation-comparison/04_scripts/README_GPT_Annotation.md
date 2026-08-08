# Annotazione DIL con GPT - 500 Trigrammi

## Descrizione

Script Python per annotare automaticamente 500 trigrammi con GPT-4, aggiungendo i risultati in una colonna separata accanto alle annotazioni di Claude Sonnet per confronto diretto.

## File

- **Script**: `annotate_dil_gpt_500.py`
- **Input**: `corpus_labelled-trigrams_500_LLM_annotated.csv` (con colonna `DIL_Sonnet`)
- **Output**: `corpus_labelled-trigrams_500_DUAL_annotated.csv` (con colonne `DIL_Sonnet` e `DIL_gpt_4`)

## Requisiti

### Librerie Python

```bash
pip install pandas openai tqdm
```

### Chiave API OpenAI

Necessaria una chiave API OpenAI valida. Ottienila da: https://platform.openai.com/api-keys

## Utilizzo

### 1. Annotazione Base

```bash
python annotate_dil_gpt_500.py \
    --api-key YOUR_API_KEY \
    --model gpt-4
```

### 2. Annotazione con Valutazione

```bash
python annotate_dil_gpt_500.py \
    --api-key YOUR_API_KEY \
    --model gpt-4 \
    --eval
```

Calcola automaticamente le metriche vs annotazioni umane (colonna `DIL`):
- Accuracy, Precision, Recall, F1-Score
- Matrice di confusione
- Salva metriche in JSON

### 3. Annotazione con Confronto LLM

```bash
python annotate_dil_gpt_500.py \
    --api-key YOUR_API_KEY \
    --model gpt-4 \
    --eval \
    --compare
```

Confronta le annotazioni di Claude Sonnet vs GPT:
- Tasso di accordo inter-annotatore
- Distribuzione dei disaccordi
- Salva statistiche di confronto in JSON

### 4. Opzioni Avanzate

```bash
python annotate_dil_gpt_500.py \
    --api-key YOUR_API_KEY \
    --model gpt-4-turbo \
    --batch-size 25 \
    --input-file custom_input.csv \
    --output-file custom_output.csv
```

## Parametri

| Parametro | Default | Descrizione |
|-----------|---------|-------------|
| `--api-key` | *required* | Chiave API OpenAI |
| `--model` | `gpt-4` | Modello GPT (`gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo`) |
| `--batch-size` | `50` | Righe processate prima di salvare |
| `--input-file` | `corpus_labelled-trigrams_500_LLM_annotated.csv` | File CSV di input |
| `--output-file` | `corpus_labelled-trigrams_500_DUAL_annotated.csv` | File CSV di output |
| `--text-column` | `text` | Nome colonna con il testo |
| `--no-resume` | `False` | Non riprendere da file esistente |
| `--eval` | `False` | Calcola metriche vs gold standard |
| `--compare` | `False` | Confronta Sonnet vs GPT |

## Funzionalità

### Resume Automatico

Lo script supporta la ripresa automatica in caso di interruzione:
- Salva progressivamente ogni batch
- Rileva annotazioni già completate
- Riprende dal punto di interruzione

```bash
# Prima esecuzione (interrotta)
python annotate_dil_gpt_500.py --api-key KEY --model gpt-4
# Interrotto dopo 200 righe

# Seconda esecuzione (riprende da 200)
python annotate_dil_gpt_500.py --api-key KEY --model gpt-4
# Continua da dove si era fermato
```

### Gestione Errori

- **Rate Limiting**: Attesa esponenziale con retry automatici
- **Errori API**: 3 tentativi con delay incrementale
- **Risposte Ambigue**: Normalizzazione automatica (default: 'no')

### Salvataggio Progressivo

Il file di output viene salvato dopo ogni batch per prevenire perdita di dati.

## Stima Costi

### GPT-4o / GPT-5.2 (Consigliato - Migliore rapporto qualità/prezzo)

| Item | Quantità | Costo per 1M tokens | Totale |
|------|----------|---------------------|--------|
| Input tokens | ~445,000 | $1.75 | **$0.78** |
| Output tokens | ~5,000 | $14.00 | **$0.07** |
| **TOTALE GPT-4o/5.2** | | | **~$0.85** |

### GPT-4 Turbo

| Item | Quantità | Costo per 1M tokens | Totale |
|------|----------|---------------------|--------|
| Input tokens | ~445,000 | $10.00 | **$4.45** |
| Output tokens | ~5,000 | $30.00 | **$0.15** |
| **TOTALE GPT-4 Turbo** | | | **~$4.60** |

### GPT-3.5 Turbo (Più economico, qualità inferiore)

| Item | Quantità | Costo per 1M tokens | Totale |
|------|----------|---------------------|--------|
| Input tokens | ~445,000 | $0.50 | **$0.22** |
| Output tokens | ~5,000 | $1.50 | **$0.01** |
| **TOTALE GPT-3.5** | | | **~$0.23** |

### Corpus Completo (29,293 trigrammi)

| Modello | Costo 500 | Costo Completo | Note |
|---------|-----------|----------------|------|
| **GPT-4o/5.2** | **$0.85** | **$49.72** | ✅ **Migliore scelta** |
| GPT-4 Turbo | $4.60 | $269.49 | 5.4× più costoso |
| GPT-3.5 Turbo | $0.23 | $13.48 | Qualità inferiore |

**Nota**: I costi sono stime basate su ~890 tokens per trigramma (prompt + testo + overhead). Prezzi aggiornati a febbraio 2026.

## Tempo di Esecuzione Stimato

- **GPT-4**: ~45-60 minuti (con delay 0.1s per rate limiting)
- **GPT-4 Turbo**: ~45-60 minuti
- **GPT-3.5 Turbo**: ~45-60 minuti

Il tempo dipende principalmente dal rate limiting e dalla latenza di rete, non dal modello.

## Output

### File CSV

Il file di output contiene tutte le colonne originali più la nuova colonna GPT:

```csv
author,work,year,doc_id,text,DIL,DIL_Sonnet,DIL_gpt_4
Deledda,Stella d'oriente,1890,doc_1,"...",yes,yes,no
Capuana,Giacinta,1879,doc_2,"...",no,no,no
...
```

### File Metriche (con --eval)

File JSON con metriche di performance:

```json
{
  "total": 500,
  "accuracy": 0.652,
  "precision": 0.681,
  "recall": 0.584,
  "specificity": 0.720,
  "f1_score": 0.629,
  "true_positives": 146,
  "true_negatives": 180,
  "false_positives": 70,
  "false_negatives": 104
}
```

### File Confronto (con --compare)

File JSON con confronto tra annotatori:

```json
{
  "total_compared": 500,
  "agreement": 345,
  "agreement_rate": 0.69,
  "both_yes": 115,
  "both_no": 230,
  "sonnet_yes_gpt_no": 25,
  "sonnet_no_gpt_yes": 130
}
```

## Esempio Completo

```bash
# 1. Installare dipendenze
pip install pandas openai tqdm

# 2. Eseguire annotazione con valutazione e confronto
python annotate_dil_gpt_500.py \
    --api-key sk-proj-XXXXXXXXXXXXXXXX \
    --model gpt-4 \
    --batch-size 50 \
    --eval \
    --compare

# Output atteso:
# ======================================================================
# ANNOTAZIONE AUTOMATICA DISCORSO INDIRETTO LIBERO
# Esperimento 500 Trigrammi: Claude Sonnet vs GPT
# ======================================================================
# Modello GPT: gpt-4
# Input: corpus_labelled-trigrams_500_LLM_annotated.csv
# Output: corpus_labelled-trigrams_500_DUAL_annotated.csv
# Batch size: 50
# ======================================================================
#
# Corpus caricato: 500 righe
# Righe da processare: 500
#
# [Progress bars...]
#
# ✓ Annotazione completata!
#
# ======================================================================
# VALUTAZIONE PERFORMANCE vs GOLD STANDARD
# ======================================================================
#
# Righe valutate: 500
# Accuracy:    65.2%
# Precision:   68.1%
# Recall:      58.4%
# F1-Score:    62.9%
#
# ======================================================================
# CONFRONTO ANNOTATORI: Claude Sonnet vs GPT
# ======================================================================
#
# Accordo totale: 345 (69.0%)
```

## Troubleshooting

### Errore: "Rate limit reached"

Aumentare il delay tra richieste modificando lo script (riga ~120):
```python
time.sleep(0.5)  # Aumentare da 0.1 a 0.5
```

### Errore: "Invalid API key"

Verificare che la chiave API sia valida e attiva su https://platform.openai.com/

### Errore: "Model not found"

Verificare di avere accesso al modello richiesto nel proprio account OpenAI.

### Output non salvato

Usare sempre percorsi assoluti per --output-file se si lavora da directory diverse.

## Confronto Claude vs GPT

Risultati attesi basati su esperimenti precedenti:

| Metrica | Claude Sonnet 4.5 | GPT-4 (stimato) | GPT-4 Turbo |
|---------|-------------------|-----------------|-------------|
| Accuracy | 56.4% | 60-70% | 55-65% |
| Precision | 57.0% | 65-75% | 60-70% |
| Recall | 52.4% | 55-65% | 50-60% |
| F1-Score | 54.6% | 60-70% | 55-65% |
| Costo | Incluso | ~$13.65 | ~$4.60 |

**Nota**: Le stime GPT sono basate su performance tipiche di GPT-4 in task di analisi linguistica comparabile. I risultati effettivi potrebbero variare.

## Contatto e Supporto

Per problemi o domande sull'esperimento:
- Progetto: RIND - PRIN 2022
- Corpus: Romanzi italiani 1850-1929
- Task: Identificazione automatica DIL

## Changelog

### v2.0 (2024-02-10)
- Aggiornato per 500 trigrammi (da 100)
- Aggiunta colonna separata per GPT (non sovrascrive Sonnet)
- Aggiunto confronto inter-annotatore (--compare)
- Migliorata gestione errori e resume
- Ridotto batch_size default a 50 per stabilità

### v1.0 (2024-02-07)
- Versione iniziale per 100 trigrammi
