# DIL-LLM Annotation: Replication Package

> **Companion data and code** for:
> Ciotti, F. (2026). *LLM-Based Annotation of Free Indirect Discourse in Italian Literary Prose: A Multi-Model, Multi-Prompt Evaluation*. RIND Project.

---

## Overview

This repository contains the data, annotation outputs, evaluation scripts, and pre-computed results for an experiment comparing five Large Language Model (LLM) systems against a human expert baseline on the task of annotating **Free Indirect Discourse** (FID, *Discorso Indiretto Libero*, DIL) in Italian literary prose from the period 1830–1930.

The experiment varies both the model (5 systems) and the prompting strategy (3 prompt types), yielding 15 conditions evaluated against a balanced test set of 1,000 text blocks drawn from the RIND corpus.

---

## Repository Structure

```
dil-llm-annotation/
├── data/
│   ├── corpus_labelled-trigrams.csv          # Full RIND corpus (29,293 text blocks, human labels)
│   └── corpus_trigrams_1000_test_sample.csv  # Balanced test set (500 pos + 500 neg, seed=42)
├── annotations/                               # LLM outputs: 5 models × 3 prompts = 15 files
│   ├── claude_sonnet46_prompt{A,B,C}_annotated.csv
│   ├── gemini35flash_prompt{A,B,C}_annotated.csv
│   ├── gpt55_prompt{A,B,C}_annotated.csv
│   ├── gpt_oss_120b_prompt{A,B,C}_annotated.csv
│   └── qwen3_35b_prompt{A,B,C}_annotated.csv
├── results/                                   # Pre-computed evaluation outputs
│   ├── metrics_v2_summary.csv / .json
│   ├── inter_session_agreement_v2.csv
│   ├── alignment_ranking_v2.json
│   └── *.png  (heatmaps, confusion matrices)
└── scripts/
    ├── prompts/
    │   ├── prompt_A_zeroshot_minimal.txt
    │   ├── prompt_B_zeroshot_theoretical.txt
    │   └── prompt_C_fewshot.txt
    ├── annotate_claude_v2.py     # Claude Sonnet 4.6 (Batch API)
    ├── annotate_gemini_v2.py     # Gemini 3.5 Flash (google-genai SDK)
    ├── annotate_gpt_v2.py        # GPT-5.5 (OpenAI Responses API)
    ├── annotate_gptoss_v2.py     # GPT-OSS-120B via LM Studio
    ├── annotate_qwen_v2.py       # Qwen3-35B-A3B via LM Studio
    ├── compute_metrics_v2.py     # Evaluation: metrics, heatmaps, confusion matrices
    ├── api_config_v2.json        # Model configuration (no secrets)
    ├── .keys.env.template        # API key template — copy to .keys.env
    └── requirements.txt
```

---

## Data

### corpus_labelled-trigrams.csv

The full RIND corpus of Italian narrative prose (1830–1930), segmented into **text blocks** of three consecutive sentences. Each block carries a human expert annotation for the presence or absence of Free Indirect Discourse.

| Column    | Description |
|-----------|-------------|
| `author`  | Author surname |
| `work`    | Work title |
| `year`    | Publication year |
| `doc_id`  | Unique document identifier |
| `text`    | Text block (three consecutive sentences) |
| `DIL`     | Human annotation: `yes` / `no` |

Distribution: 865 positive (2.95%) — 28,428 negative (97.05%) — total 29,293 blocks.

### corpus_trigrams_1000_test_sample.csv

A stratified, balanced sample of 1,000 text blocks (500 DIL=yes / 500 DIL=no, drawn with `random_state=42`) used as the evaluation set. Includes an additional `split` column indicating whether the block was also present in a prior experiment (`V1`) or is new (`V2_new`).

**Design rationale.** The test set is deliberately balanced (50/50) rather than naturalistic (3/97). With a heavily imbalanced natural distribution, a classifier that always predicts "no" achieves ~97% accuracy with zero discriminative power (the *class imbalance bias* described in Davis & Goadrich, 2006). The balanced set ensures that recall and specificity are estimated independently and that Cohen's κ measures genuine agreement beyond chance, with expected random-agreement probability P_e = 0.5 in both classes.

---

## Models

| Model | Type | Script |
|-------|------|--------|
| Claude Sonnet 4.6 | API (Anthropic Batch API) | `annotate_claude_v2.py` |
| GPT-5.5 | API (OpenAI Responses API) | `annotate_gpt_v2.py` |
| Gemini 3.5 Flash | API (Google AI) | `annotate_gemini_v2.py` |
| Qwen3-35B-A3B | Local via LM Studio | `annotate_qwen_v2.py` |
| GPT-OSS-120B | Local via LM Studio | `annotate_gptoss_v2.py` |

All models were evaluated with three prompting strategies (A, B, C — see `scripts/prompts/`).

---

## Prompts

Three prompting strategies were tested systematically across all models:

- **Prompt A** (`prompt_A_zeroshot_minimal.txt`): Zero-shot, minimal instruction. The model receives the text block and a bare labelling directive with no theoretical background.
- **Prompt B** (`prompt_B_zeroshot_theoretical.txt`): Zero-shot, theoretical. The model receives a formal definition of FID together with its key syntactic-stylistic markers before the text.
- **Prompt C** (`prompt_C_fewshot.txt`): Few-shot with five annotated examples. The model is shown five labelled text blocks before the target, covering both positive and negative cases with brief explanations.

All prompts request a structured JSON response: `{"label": "yes"|"no", "confidence": "high"|"medium"|"low"}`.

---

## Reproducing the Results

### Option A — verify pre-computed results only

Pre-computed annotation files (15 CSVs) and evaluation outputs are included in `annotations/` and `results/`. To re-run only the evaluation step:

```bash
cd scripts
pip install -r requirements.txt
python compute_metrics_v2.py
```

This reads the annotation CSVs and overwrites `results/` with fresh metrics, heatmaps and confusion matrices.

### Option B — re-run the full annotation pipeline

**1. Install dependencies**

```bash
pip install -r scripts/requirements.txt
```

> Note: the Gemini client library is `google-genai` (not the deprecated `google-generativeai`).

**2. Set up API keys**

```bash
cp scripts/.keys.env.template scripts/.keys.env
# Edit .keys.env and insert your actual API keys
```

The `.keys.env` file is listed in `.gitignore` and must never be committed.

**3. Run annotation scripts**

Each script accepts `--prompt A`, `--prompt B`, `--prompt C`, or `--prompt all`.

```bash
# API models (require keys in .keys.env)
python scripts/annotate_claude_v2.py  --prompt all
python scripts/annotate_gpt_v2.py    --prompt all
python scripts/annotate_gemini_v2.py --prompt all

# Local models (require LM Studio running on localhost:1234 with the model loaded)
python scripts/annotate_qwen_v2.py   --prompt all
python scripts/annotate_gptoss_v2.py --prompt all
```

Each script writes checkpoint files (`*.partial.csv`) that allow resuming interrupted runs, and produces final `annotations/{model}_prompt{X}_annotated.csv` files.

**4. Compute metrics**

```bash
python scripts/compute_metrics_v2.py
```

---

## Key Results Summary

Cohen's κ with human expert baseline, best prompting condition (Prompt C, few-shot) for each model:

| Model | κ (best) | Prompt | Recall (FID) | Specificity |
|-------|----------|--------|--------------|-------------|
| Claude Sonnet 4.6 | **0.570** | C | 0.786 | 0.784 |
| GPT-5.5 | 0.558 | C | 0.766 | 0.792 |
| Gemini 3.5 Flash | 0.556 | C | 0.662 | 0.894 |
| Qwen3-35B-A3B | 0.502 | C | 0.752 | 0.750 |
| GPT-OSS-120B | 0.346 | C | 0.512 | 0.834 |

Full results in `results/metrics_v2_summary.csv`.

---

## Reproducibility Notes

- **LLM non-determinism.** All API calls use `temperature=0`; local models also use `temperature=0`. Re-running the annotation scripts should produce outputs close but not necessarily identical to those archived here, due to possible model version updates and backend non-determinism at very low temperatures.
- **Test set reproducibility.** The balanced test set was drawn with `random_state=42` (scikit-learn `train_test_split`). The exact sample is included in `data/corpus_trigrams_1000_test_sample.csv`.
- **Human baseline.** The column `DIL` in the corpus CSV reflects the output of two expert human annotators following an additive protocol. No inter-annotator agreement measure is available for the baseline; the annotation should be interpreted as an expert consensus estimate rather than a verified gold standard.

---

## Citation

If you use this dataset or code, please cite:

```bibtex
@misc{ciotti2026dil,
  author    = {Ciotti, Fabio},
  title     = {LLM-Based Annotation of Free Indirect Discourse in Italian Literary Prose},
  year      = {2026},
  note      = {RIND Project — replication package},
  url       = {https://github.com/[to-be-added]}
}
```

---

## License

- **Code** (`scripts/`): MIT License
- **Corpus data** (`data/`): The literary texts are in the public domain (authors deceased before 1956, works published before 1930). Annotations are released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

---

## Contact

Fabio Ciotti — fabio.ciotti@gmail.com
RIND Project — Rappresentazione del pensiero nella narrativa italiana del secondo Ottocento
Università di Roma Tor Vergata / AIUCD
