# DIL-analysis

Code and derived datasets for the computational study of **free indirect discourse** (*discorso indiretto libero*, DIL) in Italian narrative prose, 1830–1930.

Produced within the research project **"Reading the Italian Novel at a Distance (1830-1930)" (RIND)**, funded under the PRIN 2022 programme of the Italian Ministry of University and Research (MUR). The general aim of the project is to employ computational and quantitative methods in order to reassess the traditional periodisation of Italian literature between the nineteenth and the early twentieth century, and to validate it against empirical evidence.

The primary texts are not held here. They live in the companion repository [PRIN-Rind/corpus](https://github.com/PRIN-Rind/corpus), which documents the corpus, its metadata schema and its file naming convention.

## Contents

| directory | what it holds |
|---|---|
| [`dil-llm-annotation/`](dil-llm-annotation/) | Replication package for the multi-model, multi-prompt evaluation: five LLM systems × three prompting strategies, against a human expert baseline on a balanced sample of 1,000 text blocks. Self-contained: data, annotations, results, scripts. |
| [`dil-annotation-comparison/`](dil-annotation-comparison/) | Earlier comparison between human annotators and LLM annotation, with the experimental CSV bases and the reports produced along the way. |
| [`llm-annotation-code/`](llm-annotation-code/) | Annotation pipeline for the full corpus, with the deployment scripts for the remote machine. |
| [`chunk_annotated/`](chunk_annotated/) | Per-text annotated chunks, one CSV per work. |

`dil-llm-annotation/` is the most recent and the best documented of the four; start there.

## Known issues

These are recorded openly rather than left implicit.

**`chunk_annotated/` is out of step with the corpus.** Its 500 CSV files carry the file naming convention that preceded the corpus revision, and they correspond to a sampling that has since changed: they include chunks for three works no longer in the corpus, and lack chunks for six works added to it. They need to be regenerated, or renamed and reconciled, before being used alongside the current corpus.

**The annotation code exists in several parallel versions.** Ten scripts across three directories implement variants of the same procedure, differing mainly in the API client. Sequence comparison puts most pairs above 0.85 similarity. A correction applied to one leaves the others untouched. Consolidation into a single module, with the client as a parameter, is pending.

**Some files are versioned by filename rather than by git**, `_v1` and `_v2` suffixes sitting side by side. Where both were committed together, git offers no way to tell which supersedes which.

## Licence

Two regimes apply, and the distinction is not cosmetic.

**Code** — the scripts under `*/scripts/` and the annotation pipelines — is released under the MIT licence. See [LICENSE](LICENSE).

**Derived data** — annotated chunks, labelled CSV bases, model outputs — is released under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/), not by preference but by inheritance: these datasets contain passages of the corpus, itself released under that licence, whose share-alike clause propagates to derivative material. See [LICENSE-DATA](LICENSE-DATA).

## Security note

API keys must never be committed. Scripts read them from an untracked `.keys.env`; only the template is versioned. The repository `.gitignore` excludes `*.env` while retaining `*.env.template`.

## Citation

If you use this material, please cite the corpus (see [PRIN-Rind/corpus](https://github.com/PRIN-Rind/corpus)) together with the publication accompanying the relevant experiment, indicated in the README of each directory.
