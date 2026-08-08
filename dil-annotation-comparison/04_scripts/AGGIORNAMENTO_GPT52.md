# Aggiornamento Script per GPT-5.2

## Versione 2.0 - Nuova API OpenAI

Ho creato una versione aggiornata dello script che supporta sia GPT-4o che GPT-5.2 con la nuova API OpenAI.

## File Aggiornato

**`annotate_dil_gpt_500_v2.py`** - Versione con supporto GPT-5.2

## Principali Cambiamenti

### 1. Nuova API OpenAI (Client-based)

**Vecchia API** (deprecata):
```python
import openai
openai.api_key = api_key
response = openai.ChatCompletion.create(...)
```

**Nuova API**:
```python
from openai import OpenAI
client = OpenAI(api_key=api_key)
response = client.chat.completions.create(...)
```

### 2. Supporto GPT-5.2 con Reasoning

GPT-5.2 usa una **API diversa** per le capacità di reasoning:

```python
# Per GPT-5.2
response = client.responses.create(
    model="gpt-5.2",
    input=full_prompt,
    reasoning={
        "effort": "medium"  # low, medium, high
    }
)
```

### 3. Gestione Automatica del Tipo di Modello

Lo script rileva automaticamente se stai usando un modello reasoning:

```python
REASONING_MODELS = ['gpt-5.2']

if self.is_reasoning_model:
    answer = self._analyze_with_reasoning(text)
else:
    answer = self._analyze_with_chat(text)
```

## Come Usare

### Con GPT-4o (Chat API)

```bash
python annotate_dil_gpt_500_v2.py \
    --api-key YOUR_KEY \
    --model gpt-4o \
    --eval --compare
```

### Con GPT-5.2 (Reasoning API)

```bash
python annotate_dil_gpt_500_v2.py \
    --api-key YOUR_KEY \
    --model gpt-5.2 \
    --reasoning-effort medium \
    --eval --compare
```

### Opzioni Reasoning Effort

Solo per GPT-5.2:

- `--reasoning-effort low` - Veloce, meno accurato
- `--reasoning-effort medium` - Bilanciato (default)
- `--reasoning-effort high` - Più lento, più accurato

## Confronto Modelli Supportati

| Modello | API | Reasoning | Comando |
|---------|-----|-----------|---------|
| gpt-4o | Chat | No | `--model gpt-4o` |
| gpt-4o-mini | Chat | No | `--model gpt-4o-mini` |
| gpt-4-turbo | Chat | No | `--model gpt-4-turbo` |
| gpt-3.5-turbo | Chat | No | `--model gpt-3.5-turbo` |
| **gpt-5.2** | **Responses** | **Sì** | `--model gpt-5.2 --reasoning-effort medium` |

## Costi GPT-5.2

**Stima per 500 trigrammi con GPT-5.2:**

```
Input:  445,000 tokens × $1.75/1M = $0.78
Output: 5,000 tokens × $14.00/1M = $0.07
─────────────────────────────────────────
TOTALE:                           $0.85
```

**Identico a GPT-4o!** 🎉

### Reasoning Effort Impact

Il parametro `reasoning-effort` potrebbe influenzare i costi:

- `low`: Minimo reasoning → costo simile a GPT-4o
- `medium`: Reasoning moderato → possibile +10-20% costo
- `high`: Massimo reasoning → possibile +30-50% costo

**Stima conservativa**: $1.00-1.30 per 500 trigrammi con effort=high

## Performance Attese

| Modello | Accuracy | Precision | Recall | F1 |
|---------|----------|-----------|--------|-----|
| Claude Sonnet 4.5 | 56.4% | 57.0% | 52.4% | 54.6% |
| GPT-4o | 60-70% | 65-75% | 55-65% | 60-70% |
| **GPT-5.2** | **65-75%** | **70-80%** | **60-70%** | **65-75%** |

GPT-5.2 con reasoning dovrebbe performare **meglio** grazie alla capacità di ragionamento approfondito.

## Esempio Completo

```bash
# Test su 500 trigrammi con GPT-5.2
python annotate_dil_gpt_500_v2.py \
    --api-key sk-proj-XXXXXXXX \
    --model gpt-5.2 \
    --reasoning-effort medium \
    --batch-size 50 \
    --eval \
    --compare

# Output atteso:
# ======================================================================
# ANNOTAZIONE AUTOMATICA DISCORSO INDIRETTO LIBERO
# Esperimento 500 Trigrammi: Claude Sonnet vs GPT
# ======================================================================
# Modello GPT: gpt-5.2
# Reasoning effort: medium
# Input: corpus_labelled-trigrams_500_LLM_annotated.csv
# Output: corpus_labelled-trigrams_500_DUAL_annotated.csv
# Batch size: 50
# ======================================================================
#
# Corpus caricato: 500 righe
# Modello: gpt-5.2 (reasoning)
#
# [Progress bars...]
#
# ✓ Annotazione completata!
#
# ======================================================================
# VALUTAZIONE PERFORMANCE vs GOLD STANDARD
# ======================================================================
# [Metriche...]
#
# ======================================================================
# CONFRONTO ANNOTATORI: Claude Sonnet vs GPT
# ======================================================================
# [Confronto...]
```

## Output File

### File Annotato

`corpus_labelled-trigrams_500_DUAL_annotated.csv`

Colonne:
- `DIL_Sonnet` - Annotazioni Claude
- `DIL_gpt_5_2` - Annotazioni GPT-5.2

### File Metriche

`corpus_labelled-trigrams_500_DUAL_annotated_metrics_gpt_5_2.json`

```json
{
  "total": 500,
  "accuracy": 0.68,
  "precision": 0.72,
  "recall": 0.64,
  "f1_score": 0.68,
  "true_positives": 160,
  "true_negatives": 180,
  "false_positives": 70,
  "false_negatives": 90
}
```

### File Confronto

`corpus_labelled-trigrams_500_DUAL_annotated_comparison_gpt_5_2.json`

```json
{
  "total_compared": 500,
  "agreement": 320,
  "agreement_rate": 0.64,
  "both_yes": 120,
  "both_no": 200,
  "sonnet_yes_gpt_no": 30,
  "sonnet_no_gpt_yes": 150
}
```

## Migrare da Vecchio Script

Se hai già annotazioni con il vecchio script:

1. **Backup dei dati**:
```bash
cp corpus_labelled-trigrams_500_DUAL_annotated.csv backup_old_version.csv
```

2. **Usa il nuovo script**:
```bash
python annotate_dil_gpt_500_v2.py \
    --api-key YOUR_KEY \
    --model gpt-5.2 \
    --reasoning-effort medium
```

3. **Il resume automatico funziona**: Se hai già annotazioni parziali, lo script le riconosce e continua

## Differenze Tecniche

### Gestione Errori

**Nuova versione** gestisce meglio gli errori:
```python
except Exception as e:
    error_name = type(e).__name__
    if 'RateLimitError' in error_name:
        # Gestione specifica
```

### Nome Colonna

Il nome della colonna output è automatico:
- GPT-4o → `DIL_gpt_4o`
- GPT-5.2 → `DIL_gpt_5_2`

I punti vengono convertiti in underscore per compatibilità CSV.

## Troubleshooting

### Errore: "Unknown model gpt-5.2"

GPT-5.2 potrebbe non essere ancora disponibile nel tuo account. Verifica:
1. Accesso al modello su https://platform.openai.com/
2. Tier del tuo account (potrebbe richiedere tier superiore)

### Errore: "responses.create() not found"

Aggiorna la libreria OpenAI:
```bash
pip install --upgrade openai
```

Versione minima richiesta: `openai>=1.0.0`

### Reasoning Effort non funziona

Il parametro `reasoning` è specifico per GPT-5.2. Con altri modelli viene ignorato (nessun errore).

## Raccomandazioni

1. **Per ricerca accademica**: GPT-5.2 con `effort=medium`
2. **Per test veloce**: GPT-4o (più veloce)
3. **Per massima qualità**: GPT-5.2 con `effort=high`

## Prossimi Passi

1. Testare GPT-5.2 su 100 trigrammi per validare
2. Se performance >65%, annotare i 500 completi
3. Confrontare con Claude Sonnet nelle pubblicazioni

---

**Versione script**: 2.0
**Data aggiornamento**: Febbraio 2026
**Compatibilità**: OpenAI API v1.0+
