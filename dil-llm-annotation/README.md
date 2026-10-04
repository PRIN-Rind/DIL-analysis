# DIL-LLM Annotation: replication package

Data, annotations and code for:

> Ciotti, Fabio, Anna Chiara Corradino, e Aurora Argenzio. "Usare i Large Language Model per l'analisi del discorso indiretto libero: una analisi comparativa su testi della narrativa italiana 1830-1930." *Umanistica Digitale* (forthcoming).

The experiment compares the annotation of free indirect discourse (FID, Italian *discorso indiretto libero*, DIL) produced by five Large Language Models with an expert annotation, using three prompting strategies, on a sample of Italian novels published between 1830 and 1930. It is part of the PRIN 2022 project RIND, *Leggere il romanzo italiano a distanza (1830-1930)*.

## Contents

```
data/
  corpus_labelled-trigrams.csv          35 novels, 29,293 text blocks with expert labels
  corpus_trigrams_1000_test_sample.csv  test sample: 1,000 blocks (500 DIL, 500 non-DIL) from 34 novels
  metadata_romanzi.csv                  author, title and year of the 35 novels
annotations/                            15 files: 5 models x 3 prompts
scripts/
  prompts/                              the three prompts, as sent to the models
  annotate_*_v2.py                      annotation scripts, one per model
  compute_metrics_v2.py                 metrics for the 15 conditions (Table A1, Figure 1)
  analisi_revisione.py                  inferential and stability analyses (Tables A2-A7)
results/                                outputs of compute_metrics_v2.py
results/revisione/                      outputs of analisi_revisione.py
```

## Data

A text block is a sequence of three consecutive sentences. Each novel was annotated sentence by sentence by one of two expert annotators; a block is labelled `yes` if at least one of its sentences was labelled as DIL. Each novel was annotated by a single expert, so no inter-annotator agreement is available: the labels are a conventional expert reference, not a gold standard. In the full corpus 865 blocks (2.95%) are positive.

Columns: `author`, `work`, `year` (derived from `doc_id`), `doc_id` (file name of the novel), `text`, `DIL` (`yes`/`no`); the test sample also has `split` (`V1` = blocks of the pilot experiment, `V2_new` = new blocks). Annotation files add the model label (`DIL_<model>_prompt<X>`) and the self-reported confidence (`confidence_<model>_prompt<X>`).

## Models and parameters

| Model | Access | Temperature | top_p / top_k | Reasoning | Max output tokens |
|---|---|---|---|---|---|
| Claude Sonnet 4.6 | Anthropic Batch API | provider default | not set | off (not requested) | 64 |
| GPT-5.5 | OpenAI Responses API | provider default | not set | effort = none | 256 |
| Gemini 3.5 Flash | Google Gen AI SDK | 0 | not set | thinking budget 1,024 tokens | 2,048 |
| Qwen3-35B-A3B | LM Studio, Q8_0 | 0.6 | 0.95 / 20 | on (cannot be disabled via API) | 8,192 |
| GPT-OSS-120B | LM Studio, MXFP4 | 0.6 | 0.95 / 20 | model default | 8,192 |

Each condition was run once. A sixth model, Minerva-7B, labelled almost every block as positive and was excluded from the analysis; its outputs are not included. For GPT-OSS-120B with Prompt B, six requests returned no valid answer and are excluded (14,994 valid outputs in total).

## Prompts

- **A**, minimal zero-shot: task description only.
- **B**, theoretical zero-shot: adds an operational definition of DIL with four indicators.
- **C**, few-shot: definition plus six annotated examples (four positive, two negative) with short explanations.

The files reproduce the prompts as sent. They call the block *trigramma* and give the period as 1850-1929; the article uses *blocco testuale* and covers 1830-1930. For the models run in LM Studio the system message avoids the word "JSON"; Gemini returns label and confidence as plain text.

## Reproducing the results

```
pip install -r scripts/requirements.txt
python scripts/compute_metrics_v2.py   # metrics, Table A1
python scripts/analisi_revisione.py    # Tables A2-A7
```

Confidence intervals are obtained by resampling novels (2,000 bootstrap samples, seed 42), since blocks from the same novel are not independent.

To rerun the annotation, copy `scripts/.keys.env.template` to `scripts/.keys.env`, add your API keys (the file is excluded from version control), start LM Studio for the local models, and run `python scripts/annotate_<model>_v2.py --prompt all`. Because four of the five models use stochastic decoding and commercial models change over time, new runs will not reproduce the archived outputs exactly.

## License

Code: MIT (see [LICENSE](../LICENSE)). Data and annotations: CC BY-NC-SA 4.0, inherited from the source corpus (see [LICENSE-DATA](../LICENSE-DATA)).

## Contact

Fabio Ciotti, Università di Roma Tor Vergata (fabio.ciotti@gmail.com)
