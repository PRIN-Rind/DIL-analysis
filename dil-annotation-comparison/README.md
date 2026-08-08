# RIND — Riconoscimento automatico del discorso Indiretto libero nella Narrativa italiana del Decadentismo

Corpus e esperimenti di narratologia computazionale per l'identificazione del **Discorso Indiretto Libero (DIL)** nella narrativa italiana del periodo 1850–1929.

## Descrizione

Il progetto confronta le prestazioni di annotatori umani e Large Language Models (LLMs) nell'identificazione del DIL su un corpus di 36 opere narrative italiane (87.841 frasi). L'esperimento include quattro sistemi di annotazione automatica:

- **Pattern matching rule-based** (baseline)
- **Claude Sonnet 4.5 v1** (configurazione conservativa)
- **Claude Sonnet 4.5 v2** (configurazione liberale/multi-criterio)
- **GPT-5.2** con *reasoning effort* LOW

## Struttura del repository

```
├── 01_original_annotated_files/   # File xlsx e csv con annotazioni umane originali per autore
├── 02_experiment_csv_base/        # Corpus in formato trigrammi, chunks e testi sorgente
├── 03_llm_annotated_csv/          # CSV con annotazioni LLM, metriche e confusion matrix
├── 04_scripts/                    # Script Python e bash per la conduzione degli esperimenti
├── capitolo_esperimento_DIL_LLM.md  # Capitolo scientifico con metodi e risultati
├── REPORT_ANNOTAZIONE_DIL_Sonnet_v2.md
└── Report_Esperimento_500_Sample.md
```

## Risultati principali

| Sistema | Accuracy | F1-Score | Cohen's κ |
|---|---|---|---|
| Pattern matching (baseline) | 69,0% | — | +0,38 |
| Claude Sonnet v1 | 56,4% | 54,6% | +0,128 |
| Claude Sonnet v2 | 58,8% | 65,8% | +0,176 |
| **GPT-5.2 (reasoning low)** | **77,0%** | **76,3%** | **+0,540** |

Campione: 500 trigrammi stratificati (250 DIL=yes / 250 DIL=no) — gold standard annotato manualmente.

## Scripts

### Annotazione con GPT-5.2 (OpenAI Responses API)

```bash
# Configura la chiave API in annotate_dil_gpt_500_v2.py
python 04_scripts/annotate_dil_gpt_500_v2.py
```

### Annotazione con Claude (Anthropic Batches API)

```bash
# 1. Copia e configura il file di esempio
cp 04_scripts/api_config.json api_config.json
# 2. Inserisci la tua chiave API Anthropic in api_config.json
# 3. Esegui lo script
python 04_scripts/annotate_dil_claude_api.py
```

> ⚠️ **Non committare mai `api_config.json`** — il file è incluso nel `.gitignore`.

## Dipendenze

```bash
pip install anthropic openai pandas scikit-learn tqdm
```

## Corpus

Il corpus comprende 36 opere di narrativa italiana (1850–1929), pre-processate con tokenizzazione a livello di frase. I file di corpus di grandi dimensioni (`corpus_labelled.csv`, `corpus_labelled-trigrams.csv`, `corpus_labelled-chunks.csv`) sono disponibili su richiesta.

## Autore

Fabio Ciotti — fabio.ciotti@gmail.com

## Licenza

I dati di annotazione e gli script sono rilasciati per uso accademico e di ricerca.
