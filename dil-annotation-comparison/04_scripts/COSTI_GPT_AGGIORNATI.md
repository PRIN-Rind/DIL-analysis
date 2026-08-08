# Costi Aggiornati per Annotazione GPT

**Data aggiornamento**: Febbraio 2026
**Prezzi GPT-4o/5.2**: $1.75/1M input, $14.00/1M output

---

## Riepilogo Costi per 500 Trigrammi

| Modello | Input | Output | **Totale** | Rapporto Qualità/Prezzo |
|---------|-------|--------|------------|------------------------|
| **GPT-4o/5.2** | $0.78 | $0.07 | **$0.85** | ⭐⭐⭐⭐⭐ **Consigliato** |
| GPT-4 Turbo | $4.45 | $0.15 | $4.60 | ⭐⭐⭐ OK |
| GPT-4 (legacy) | $13.35 | $0.30 | $13.65 | ⭐⭐ Costoso |
| GPT-3.5 Turbo | $0.22 | $0.01 | $0.23 | ⭐⭐⭐ Economico ma qualità ↓ |

## Dettaglio Token per 500 Trigrammi

```
Input tokens:  445,000 (~890 per trigramma)
  ├─ Prompt sistema:     ~50 tokens
  ├─ Prompt utente:      ~150 tokens
  ├─ Testo trigramma:    ~600 tokens
  └─ Overhead:           ~90 tokens

Output tokens: 5,000 (~10 per trigramma)
  └─ Risposta yes/no:    ~10 tokens

Totale:        450,000 tokens
```

## Costi per Corpus Completo (29,293 trigrammi)

| Modello | Costo Totale | Costo per 1,000 | Tempo Stimato |
|---------|--------------|-----------------|---------------|
| **GPT-4o/5.2** | **$49.72** | $1.70 | ~26 ore |
| GPT-4 Turbo | $269.49 | $9.20 | ~26 ore |
| GPT-4 (legacy) | $799.60 | $27.30 | ~26 ore |
| GPT-3.5 Turbo | $13.48 | $0.46 | ~26 ore |

### Risparmio con GPT-4o/5.2

- **vs GPT-4**: $749.88 risparmiati (93.8% meno)
- **vs GPT-4 Turbo**: $219.77 risparmiati (81.5% meno)
- **vs GPT-3.5**: -$36.24 (costo maggiore ma qualità superiore)

## Raccomandazioni

### ✅ Scenario 1: Ricerca Accademica (Budget Limitato)

**Modello consigliato**: GPT-4o/5.2

**Motivi**:
- Costo contenuto ($0.85 per 500, $49.72 per corpus completo)
- Qualità paragonabile a GPT-4
- Migliore rapporto qualità/prezzo

**Comando**:
```bash
python annotate_dil_gpt_500.py \
    --api-key YOUR_KEY \
    --model gpt-4o \
    --eval --compare
```

### ⚠️ Scenario 2: Test Pilota (Validazione Approccio)

**Modello consigliato**: GPT-3.5 Turbo

**Motivi**:
- Costo minimo ($0.23 per 500)
- Sufficiente per validare pipeline
- Performance attesa ~45-55% accuracy

**Comando**:
```bash
python annotate_dil_gpt_500.py \
    --api-key YOUR_KEY \
    --model gpt-3.5-turbo \
    --eval --compare
```

### 🔬 Scenario 3: Pubblicazione Scientifica (Massima Qualità)

**Modello consigliato**: GPT-4o/5.2

**Motivi**:
- Qualità elevata mantenendo costi accessibili
- Risultati comparabili con Claude Sonnet
- Credibilità per pubblicazione

**Comando**:
```bash
# Test su 500 sample
python annotate_dil_gpt_500.py \
    --api-key YOUR_KEY \
    --model gpt-4o \
    --eval --compare

# Se soddisfatti, annotare corpus completo
python annotate_dil_gpt_500.py \
    --api-key YOUR_KEY \
    --model gpt-4o \
    --input-file corpus_labelled-trigrams.csv \
    --output-file corpus_labelled-trigrams_FULL_DUAL_annotated.csv \
    --eval --compare
```

## Confronto Performance Attese

| Modello | Accuracy (stimata) | Precision | Recall | F1-Score | Costo |
|---------|-------------------|-----------|--------|----------|-------|
| Claude Sonnet 4.5 | 56.4% | 57.0% | 52.4% | 54.6% | Incluso |
| **GPT-4o/5.2** | **60-70%** | **65-75%** | **55-65%** | **60-70%** | **$0.85** |
| GPT-4 Turbo | 58-68% | 63-73% | 53-63% | 58-68% | $4.60 |
| GPT-3.5 Turbo | 45-55% | 50-60% | 40-50% | 45-55% | $0.23 |

**Nota**: Le stime sono basate su performance tipiche di questi modelli in task di analisi linguistica simili. I risultati effettivi possono variare.

## Budget Planning

### Budget Minimo (Test)
- **500 trigrammi**: $0.85 (GPT-4o)
- **Obiettivo**: Validare approccio e stimare performance

### Budget Medio (Ricerca)
- **2,000 trigrammi**: $3.40 (GPT-4o)
- **Obiettivo**: Campione rappresentativo per paper

### Budget Completo (Pubblicazione)
- **29,293 trigrammi**: $49.72 (GPT-4o)
- **Obiettivo**: Annotazione completa corpus

## Tempo di Esecuzione

### Fattori che influenzano il tempo:
1. **Rate limiting**: 10 richieste/minuto (tipico)
2. **Latenza API**: ~1-2 secondi per richiesta
3. **Retry su errori**: Aggiunge ~5-10% tempo

### Stima realistica:
- **500 trigrammi**: 45-60 minuti
- **2,000 trigrammi**: 3-4 ore
- **29,293 trigrammi**: 24-30 ore

### Ottimizzazioni possibili:
```bash
# Aumentare batch size (se rate limit lo permette)
--batch-size 100

# Ridurre delay tra richieste (attenzione al rate limit!)
# Modificare nello script: time.sleep(0.05) invece di 0.1
```

## Checklist Pre-Esecuzione

- [ ] Chiave API OpenAI valida e attiva
- [ ] Credito sufficiente nell'account OpenAI
- [ ] File di input presente e verificato
- [ ] Backup del file di input (se si modifica in-place)
- [ ] Connessione internet stabile per task lunghi
- [ ] Spazio disco sufficiente per file output

## Contatti

- **Progetto**: RIND - PRIN 2022
- **Task**: Identificazione automatica DIL
- **Corpus**: Romanzi italiani 1850-1929

---

**Ultimo aggiornamento**: 10 Febbraio 2026
**Versione script**: 2.0
