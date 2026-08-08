# Sentence Tokenization of a Diachronic Italian Literary Corpus (1830–1930)

**Project type:** NLP pre-processing pipeline
**Date:** February 2026
**Author:** Fabio Ciotti

---

## 1. Corpus Description

The corpus consists of 500 plain-text files corresponding to Italian novels
published between 1830 and 1930. The total size is approximately **177 MB**,
amounting to roughly **30 million tokens**. The texts span a full century of
Italian literary prose, from the Romantic period through Verismo and the early
twentieth-century novel, and exhibit considerable variation in style, register,
and typographic conventions.

---

## 2. Objective

The goal of this task was to produce, for each source text, a **sentence-tokenized
CSV file** with the following structure:

| Column | Content |
|---|---|
| `filename` | Name of the source file (without extension) |
| `sentence` | Text of the extracted sentence |

Output files are named using the convention `<original_name>_sent.csv` and
collected in a dedicated subdirectory (`TESTI/sentence/`).

---

## 3. Linguistic Challenges

The texts present several features that complicate automatic sentence
segmentation:

**Complex periodic structure.** 19th-century Italian literary prose is
characterised by long, heavily subordinated sentences articulated through
semicolons and colons. These punctuation marks function as intra-sentential
coordinators rather than sentence boundaries.

**Historical orthographic and typographic conventions.** The corpus contains
period-specific abbreviations (`sig.`, `cav.`, `S.`), archaic spellings
(`perciocchè`, `perchè` without accent), and anonymised proper names rendered
as sequences of dots (`D....`, `C.....`). These elements introduce periods that
do not mark sentence boundaries and therefore constitute potential sources of
segmentation error.

**Direct speech.** Reported dialogue — delimited by guillemets (`«»`),
quotation marks, or em-dashes — may contain multiple graphic sentences within
a single turn, or be interrupted by narrator incises, generating structurally
ambiguous cases.

---

## 4. Evaluation of Sentence Tokenizers

Four main tools were evaluated against the requirements of the corpus:

### 4.1 NLTK Punkt *(selected)*

Punkt (Kiss & Strunk, 2006) is an **unsupervised** algorithm that learns, from
the data itself, a statistical model of abbreviation types, sentence-starting
word types, and orthographic context features. The key advantage for this
project is that the model can be **retrained on the target corpus**, allowing it
to adapt to 19th-century Italian conventions without annotated data. The
algorithm is deterministic and computationally lightweight.

### 4.2 Stanza

Stanza (Qi et al., 2020) offers a neural sentence segmenter for Italian trained
on Universal Dependencies treebanks (ISDT, PoSTWITA). Its accuracy on
contemporary Italian is high, but the training data (predominantly journalistic
and social-media text) is substantially different from literary historical prose.
Computational cost is also significantly higher than Punkt.

### 4.3 spaCy

spaCy provides both a dependency-parser-based sentencizer and a rule-based
component. The former degrades on non-contemporary syntax; the latter is
efficient but offers no domain-adaptation mechanisms comparable to Punkt.

### 4.4 SaT (Segment any Text)

SaT (Minixhofer et al., 2023) is a recent transformer-based approach designed
for robust cross-domain multilingual segmentation. It is potentially the most
accurate option, but its performance on historical Italian literary prose is not
documented in the literature, and it requires GPU resources for efficient
large-scale processing.

---

## 5. Methodological Choices

### Tokenizer

**NLTK Punkt, retrained on the full corpus.** Training on 30 million tokens
provides a statistically robust basis for learning the period's abbreviation
patterns. The unsupervised nature of the algorithm makes it intrinsically
suited to diachronic corpora, where pre-trained models for contemporary language
cannot be assumed to generalise.

### Semicolon treatment

Semicolons are **not** treated as sentence boundaries. In 19th-century Italian
literary prose the semicolon predominantly conjoins closely related independent
clauses within a single rhetorical unit. Punkt's default behaviour excludes
semicolons from boundary detection, requiring no additional configuration.

### Paragraph boundaries

The raw text is first split into paragraph blocks (delimited by empty lines).
Punkt is applied to each block independently, preventing spurious merging of
the last sentence of one paragraph with the first of the next.

### Numeric chapter titles

Lines consisting exclusively of Arabic or Roman numerals — optionally preceded
by the keywords `CAPITOLO`, `PARTE`, or `CAP.` — are excluded from the output.
Chapter titles with lexical content (e.g. *CAPITOLO PRIMO*) are retained,
since they cannot be reliably distinguished from short narrative sentences
without full syntactic analysis.

### Direct speech

No dedicated dialogue-handling layer is applied. Reported speech is segmented
according to its internal punctuation, which is the best approximation
achievable without a specialised dialogue-aware segmentation component.

---

## 6. Implementation

The pipeline is implemented as a single Python script (`sentence_tokenizer.py`)
with the following structure:

```
train_punkt(corpus_dir)
    └── PunktTrainer.train()  × 500 files
    └── PunktTrainer.finalize_training()
    └── returns PunktSentenceTokenizer

tokenize_file(tokenizer, filepath, output_dir)
    └── read_file()           — UTF-8 / Latin-1 / CP-1252 fallback
    └── line-level filtering  — numeric chapter titles removed
    └── paragraph blocking    — empty lines as block separators
    └── tokenizer.tokenize()  — Punkt applied per block
    └── CSV export            — QUOTE_ALL, UTF-8
```

Usage:

```bash
# Inspect a single example file first
python sentence_tokenizer.py --example

# Process the full corpus
python sentence_tokenizer.py
```

**Dependency:** `nltk` (install with `pip install nltk`).
Set `CORPUS_DIR` at the top of the script to the path of your `TESTI` folder.

---

## 7. Results

| Metric | Value |
|---|---|
| Source files processed | 500 |
| Total sentences extracted | 1,609,559 |
| Output directory size | 251 MB |
| Punkt training time | ~68 s |
| Tokenization time (500 files) | ~29 s |
| Abbreviation types learned | 400 |

---

## 8. Limitations

No systematic quantitative evaluation of segmentation quality was performed,
as no manually annotated gold standard exists for historical Italian literary
prose. Qualitative inspection identified two residual problem areas:

1. **Multi-sentence direct speech** — a single dialogue turn containing
   multiple graphic sentences is segmented at internal punctuation boundaries,
   which may not align with the intended rhetorical units.
2. **Anonymised proper names** — sequences such as `D....` or `C.....` are
   occasionally misanalysed as sentence-ending periods followed by a new
   sentence, though the Punkt training on the corpus substantially mitigates
   this issue.

A precision/recall evaluation on a manually annotated sample would be a
valuable next step for assessing and further improving the pipeline.

---

## 9. References

Kiss, T. and Strunk, J. (2006). Unsupervised Multilingual Sentence Boundary
Detection. *Computational Linguistics*, 32(4), 485–525.

Minixhofer, B., Paischer, F. and Navarro, J. (2023). Where Does the Period Go?
Machine Learning Approaches to Sentence Boundary Detection. *Proceedings of the
61st Annual Meeting of the Association for Computational Linguistics*,
pp. 10774–10789.

Qi, P., Zhang, Y., Zhang, Y., Bolton, J. and Manning, C. D. (2020). Stanza:
A Python Natural Language Processing Toolkit for Many Human Languages.
*Proceedings of the 58th Annual Meeting of the Association for Computational
Linguistics: System Demonstrations*, pp. 101–108.
