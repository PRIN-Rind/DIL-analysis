#!/usr/bin/env python3
"""
Sentence tokenization of a diachronic Italian literary corpus (1830-1930).

Approach: NLTK Punkt tokenizer retrained on the target corpus itself, so that
the model learns the abbreviation conventions and sentence-boundary patterns
specific to 19th- and early 20th-century Italian prose, without requiring
manually annotated data.

Output: one CSV file per source text, with columns [filename, sentence].
"""

import os
import re
import csv
import time
import glob
import nltk
from nltk.tokenize.punkt import PunktSentenceTokenizer, PunktTrainer


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CORPUS_DIR = "/path/to/TESTI"               # directory containing source .txt files
OUTPUT_DIR = os.path.join(CORPUS_DIR, "sentence")  # output directory for CSV files


# ---------------------------------------------------------------------------
# Patterns for filtering numeric-only chapter titles
# ---------------------------------------------------------------------------

# Matches lines consisting only of Roman numerals, optionally preceded by
# "CAPITOLO", "PARTE", or "CAP." (case-insensitive).
# Examples that will be excluded: "I", "IV", "CAPITOLO III", "PARTE II"
ROMAN_RE = re.compile(
    r'^\s*(CAPITOLO|PARTE|CAP\.?)?\s*[IVXLCDM]+\.?\s*$',
    re.IGNORECASE
)

# Matches lines consisting only of Arabic numerals, optionally preceded by
# the same section keywords.
# Examples that will be excluded: "1", "23.", "CAPITOLO 3"
ARABIC_RE = re.compile(
    r'^\s*(CAPITOLO|PARTE|CAP\.?)?\s*\d+\.?\s*$',
    re.IGNORECASE
)


def is_numeric_chapter_title(line: str) -> bool:
    """
    Return True if a line is a numeric-only chapter heading that should
    be excluded from the sentence output.

    Lines consisting exclusively of Roman or Arabic numerals (with optional
    section keyword prefix) are treated as structural markers, not content.
    Chapter titles with lexical content (e.g. "CAPITOLO PRIMO") are retained,
    since they cannot be reliably distinguished from short prose sentences
    without full syntactic analysis.
    """
    stripped = line.strip()
    if not stripped:
        return False
    return bool(ROMAN_RE.match(stripped)) or bool(ARABIC_RE.match(stripped))


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def read_file(filepath: str) -> str:
    """
    Read a plain-text file, attempting UTF-8 first, then Latin-1 and CP-1252
    as fallbacks, to handle the encoding variation common in digitised
    historical corpora.
    """
    for encoding in ('utf-8', 'latin-1', 'cp1252'):
        try:
            with open(filepath, 'r', encoding=encoding) as fh:
                return fh.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"Cannot decode file with any supported encoding: {filepath}")


# ---------------------------------------------------------------------------
# Punkt training
# ---------------------------------------------------------------------------

def train_punkt(corpus_dir: str) -> PunktSentenceTokenizer:
    """
    Train a Punkt sentence tokenizer on all .txt files found in corpus_dir.

    Punkt (Kiss & Strunk, 2006) is an unsupervised algorithm that learns:
      - abbreviation types  (tokens frequently followed by a period in
        non-sentence-final position)
      - sentence-starter types  (tokens that frequently begin sentences)
      - orthographic context features

    By training on the target corpus rather than using a pre-trained Italian
    model, the tokenizer adapts to the specific abbreviation conventions and
    distributional patterns of 19th- and early 20th-century Italian prose
    without requiring any manually annotated data.

    Parameters
    ----------
    corpus_dir : str
        Path to the directory containing source .txt files.

    Returns
    -------
    PunktSentenceTokenizer
        A tokenizer initialised with the parameters learned from the corpus.
    """
    print("=== Training Punkt on the corpus ===")
    trainer = PunktTrainer()

    txt_files = sorted(glob.glob(os.path.join(corpus_dir, "*.txt")))
    print(f"Found {len(txt_files)} text files.")

    t0 = time.time()
    for i, fpath in enumerate(txt_files):
        text = read_file(fpath)
        # finalize=False defers the final parameter estimation until all
        # documents have been fed to the trainer, which yields better
        # abbreviation statistics than incremental finalisation.
        trainer.train(text, finalize=False, verbose=False)
        if (i + 1) % 50 == 0:
            print(f"  Trained on {i + 1}/{len(txt_files)} files...")

    # Compute final log-likelihood scores and classify abbreviation candidates.
    trainer.finalize_training(verbose=False)
    elapsed = time.time() - t0
    print(f"Training completed in {elapsed:.1f} s.")

    params = trainer.get_params()
    abbrevs = sorted(params.abbrev_types)
    print(f"Learned {len(abbrevs)} abbreviation types "
          f"(first 50): {', '.join(abbrevs[:50])}")

    return PunktSentenceTokenizer(params)


# ---------------------------------------------------------------------------
# Sentence tokenization and CSV export
# ---------------------------------------------------------------------------

def clean_sentence(sent: str) -> str:
    """
    Normalise a sentence string: strip leading/trailing whitespace and
    collapse any internal runs of whitespace to a single space.
    """
    return re.sub(r'\s+', ' ', sent).strip()


def tokenize_file(
    tokenizer: PunktSentenceTokenizer,
    filepath: str,
    output_dir: str
) -> tuple[str, int]:
    """
    Tokenize a single source file into sentences and write the results to a
    CSV file.

    Pre-processing pipeline
    -----------------------
    1. Split the raw text into lines.
    2. Drop lines identified as numeric-only chapter titles (see
       is_numeric_chapter_title). Chapter titles with lexical content are
       retained because they cannot be reliably distinguished from short
       narrative sentences without full syntactic analysis.
    3. Reassemble consecutive non-empty lines into paragraph blocks
       (an empty line signals a paragraph boundary). This ensures that Punkt
       does not attempt to segment across paragraph breaks, which would risk
       merging the last sentence of one paragraph with the first sentence of
       the next.
    4. Apply the Punkt tokenizer to each paragraph block independently.

    Semicolon treatment
    -------------------
    Semicolons are deliberately NOT treated as sentence boundaries. In
    19th-century Italian literary prose the semicolon typically conjoins
    closely related independent clauses within a single rhetorical unit.
    Punkt's default behaviour already excludes semicolons from its boundary
    detection, so no additional configuration is required.

    Direct speech
    -------------
    No special handling beyond Punkt's default rules is applied to direct
    speech. Reported speech delimited by guillemets (« »), quotation marks,
    or em-dashes is segmented according to the internal punctuation it
    contains. This is the best achievable approximation without a dedicated
    dialogue-aware segmentation layer.

    Parameters
    ----------
    tokenizer : PunktSentenceTokenizer
        A trained Punkt tokenizer.
    filepath : str
        Absolute path to the source .txt file.
    output_dir : str
        Directory in which the output CSV will be written.

    Returns
    -------
    tuple[str, int]
        The path to the CSV file written, and the number of sentences it
        contains.
    """
    basename      = os.path.basename(filepath)
    name_no_ext   = os.path.splitext(basename)[0]
    text          = read_file(filepath)

    # --- Step 1 & 2: line-level filtering ---
    lines = text.split('\n')
    filtered_blocks: list[str] = []
    current_block:   list[str] = []

    for line in lines:
        if is_numeric_chapter_title(line):
            # Flush any accumulated block and discard this line.
            if current_block:
                filtered_blocks.append(' '.join(current_block))
                current_block = []
            continue

        stripped = line.strip()
        if not stripped:
            # Empty line marks a paragraph boundary.
            if current_block:
                filtered_blocks.append(' '.join(current_block))
                current_block = []
        else:
            current_block.append(stripped)

    if current_block:
        filtered_blocks.append(' '.join(current_block))

    # --- Step 3 & 4: sentence tokenization ---
    all_sentences: list[str] = []
    for block in filtered_blocks:
        for sent in tokenizer.tokenize(block):
            cleaned = clean_sentence(sent)
            # Discard empty strings and single-character residues
            # (punctuation marks detached from their context, OCR noise, etc.)
            if len(cleaned) > 1:
                all_sentences.append(cleaned)

    # --- CSV export ---
    csv_filename = f"{name_no_ext}_sent.csv"
    csv_path     = os.path.join(output_dir, csv_filename)

    with open(csv_path, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.writer(fh, quoting=csv.QUOTE_ALL)
        writer.writerow(['filename', 'sentence'])   # header row
        for sent in all_sentences:
            writer.writerow([name_no_ext, sent])

    return csv_path, len(all_sentences)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    import sys

    # Train Punkt on the full corpus.
    tokenizer = train_punkt(CORPUS_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if '--example' in sys.argv:
        # Process a single file for inspection before committing to the full run.
        example_file = sorted(glob.glob(os.path.join(CORPUS_DIR, "*.txt")))[0]
        csv_path, n = tokenize_file(tokenizer, example_file, OUTPUT_DIR)
        print(f"\nExample output: {csv_path}  ({n} sentences)")

    else:
        # Process all files in the corpus.
        txt_files   = sorted(glob.glob(os.path.join(CORPUS_DIR, "*.txt")))
        total_sents = 0
        t0          = time.time()

        print(f"\n=== Processing all {len(txt_files)} files ===")
        for i, fpath in enumerate(txt_files):
            _, n = tokenize_file(tokenizer, fpath, OUTPUT_DIR)
            total_sents += n
            if (i + 1) % 50 == 0:
                print(f"  Processed {i + 1}/{len(txt_files)} files...")

        elapsed = time.time() - t0
        print(f"\nCompleted: {len(txt_files)} files | "
              f"{total_sents:,} sentences | "
              f"{elapsed:.1f} s")
        print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
