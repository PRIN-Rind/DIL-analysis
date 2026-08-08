#!/usr/bin/env python3
"""
Annotazione DIL - Gemini 3.5 Flash via Google Gen AI SDK (google-genai)
Esperimento V2: 3 prompt × 1000 blocchi testuali

Nota: questo script usa la libreria 'google-genai' (non 'google-generativeai',
che è deprecata). Installazione: pip install google-genai

Uso:
    python annotate_gemini_v2.py --prompt A
    python annotate_gemini_v2.py --prompt all

Le API key vengono lette dal file .keys.env nella stessa cartella dello script.
Output: 03_llm_annotated_csv/gemini35flash_prompt[A|B|C]_annotated.csv
"""

import os
import json
import time
import argparse
import logging
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    raise SystemExit(
        "Libreria google-genai non trovata.\n"
        "Installa con: pip install google-genai"
    )

# ---------------------------------------------------------------------------
# Caricamento API key da file esterno (.keys.env)
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).parent
load_dotenv(_SCRIPT_DIR / ".keys.env")

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

# ---------------------------------------------------------------------------
# Percorsi
# ---------------------------------------------------------------------------
BASE_DIR   = _SCRIPT_DIR.parent
PROMPT_DIR = _SCRIPT_DIR / "prompts"
CSV_DIR    = BASE_DIR / "data"
OUT_DIR    = BASE_DIR / "annotations"
LOG_DIR    = BASE_DIR / "logs"

OUT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

SAMPLE_FILE = CSV_DIR / "corpus_trigrams_1000_test_sample.csv"

PROMPT_FILES = {
    "A": PROMPT_DIR / "prompt_A_zeroshot_minimal.txt",
    "B": PROMPT_DIR / "prompt_B_zeroshot_theoretical.txt",
    "C": PROMPT_DIR / "prompt_C_fewshot.txt",
}

MODEL          = "gemini-3.5-flash"   # GA da maggio 2026; aggiorna se necessario
MAX_TOKENS     = 2048  # budget ampio: include il thought summary + la risposta finale

# Rate limiting prudenziale: Gemini 3.5 Flash ha limiti generosi,
# ma un piccolo delay evita errori 429 su sessioni lunghe.
REQUESTS_PER_MINUTE = 60
MAX_RETRIES         = 3
CHECKPOINT_EVERY    = 50  # salva checkpoint ogni N blocchi testuali
RETRY_BASE_WAIT     = 10   # secondi (moltiplicato per il numero del tentativo)

SYSTEM_INSTRUCTION = (
    "Sei un annotatore di testi letterari italiani. "
    "Rispondi ESCLUSIVAMENTE con due parole inglesi separate da uno spazio: "
    "prima 'yes' o 'no', poi il livello di confidenza 'high', 'medium' o 'low'. "
    "Esempi di risposta corretta: 'yes high'  'no low'  'yes medium'. "
    "Nessun altro testo, nessuna spiegazione, nessuna punteggiatura."
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "gemini_v2.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_prompt(prompt_id: str) -> str:
    return PROMPT_FILES[prompt_id].read_text(encoding="utf-8")


def parse_result(result_text) -> tuple[str, str]:
    """Estrae label e confidence dalla risposta plain-text di Gemini.

    Formato atteso: due parole separate da spazio, es. "yes high" o "no low".
    Se il modello risponde con più testo, si cercano comunque i token corretti.
    """
    if result_text is None:
        log.warning("response.text è None (risposta bloccata o vuota dal safety filter)")
        return "error", "unknown"
    tokens = result_text.strip().lower().split()
    label = "error"
    conf  = "unknown"
    for tok in tokens:
        if tok in ("yes", "no") and label == "error":
            label = tok
        if tok in ("high", "medium", "low") and conf == "unknown":
            conf = tok
    if label == "error":
        log.warning(f"Parsing fallito: nessun yes/no trovato | risposta: {result_text[:150]}")
    return label, conf


def call_gemini(client: genai.Client, prompt: str) -> tuple[str, str]:
    """Chiama Gemini con retry esponenziale in caso di errore temporaneo.

    thinking_budget=0 disabilita esplicitamente il thinking di Gemini 3.5 Flash,
    che è attivo per default e causa la comparsa di frammenti del testo in input
    all'interno di response.text al posto della risposta effettiva.
    """
    config = genai_types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        max_output_tokens=MAX_TOKENS,
        temperature=0.0,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=1024),
    )
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=config,
            )
            return parse_result(response.text)
        except Exception as e:
            log.warning(f"Tentativo {attempt}/{MAX_RETRIES} fallito: {e}")
            if attempt < MAX_RETRIES:
                wait = RETRY_BASE_WAIT * attempt
                log.info(f"Attendo {wait}s prima di riprovare…")
                time.sleep(wait)
    return "error", "unknown"


def run_prompt(client: genai.Client, df: pd.DataFrame, prompt_id: str, out_path: Path) -> pd.DataFrame:
    lbl_col  = f"DIL_gemini35flash_prompt{prompt_id}"
    conf_col = f"confidence_gemini35flash_prompt{prompt_id}"
    partial  = out_path.with_suffix(".partial.csv")
    total    = len(df)
    delay    = 60.0 / REQUESTS_PER_MINUTE

    # Riprendi da checkpoint se esiste
    if partial.exists():
        done   = pd.read_csv(partial)
        n_done = min(len(done), total)
        labels = list(done[lbl_col])[:n_done]
        confs  = list(done[conf_col])[:n_done]
        log.info(f"Checkpoint trovato: {n_done}/{total} già completati, riprendo da lì")
    else:
        labels, confs, n_done = [], [], 0

    template  = load_prompt(prompt_id)
    remaining = df.iloc[n_done:]
    log.info(f"=== Inizio prompt {prompt_id} ({total - n_done} blocchi testuali rimanenti) ===")

    for i, (_, row) in enumerate(remaining.iterrows(), start=n_done + 1):
        text = str(row["text"]).strip()
        label, confidence = call_gemini(client, template.replace("{TEXT}", text))
        labels.append(label)
        confs.append(confidence)

        if len(labels) % CHECKPOINT_EVERY == 0 or i == total:
            ckpt = df.iloc[:n_done + len(labels)].copy()
            ckpt[lbl_col]  = labels
            ckpt[conf_col] = confs
            ckpt.to_csv(partial, index=False)
            log.info(f"  [{i}/{total}] completati | errori: {labels.count('error')} | checkpoint salvato")

        time.sleep(delay)

    out = df.copy()
    out[lbl_col]  = labels
    out[conf_col] = confs
    partial.unlink(missing_ok=True)
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Annotazione DIL con Gemini 3.5 Flash (Google Gen AI SDK)"
    )
    parser.add_argument(
        "--prompt",
        choices=["A", "B", "C", "all"],
        default="all",
        help="Quale prompt eseguire (default: all)",
    )
    args = parser.parse_args()

    if not GOOGLE_API_KEY:
        raise SystemExit(
            "GOOGLE_API_KEY non trovata.\n"
            "Crea il file 04_scripts/.keys.env partendo da .keys.env.template."
        )

    client = genai.Client(api_key=GOOGLE_API_KEY)

    df = pd.read_csv(SAMPLE_FILE)
    log.info(f"Dataset caricato: {len(df)} blocchi testuali da {SAMPLE_FILE.name}")

    prompts_to_run = ["A", "B", "C"] if args.prompt == "all" else [args.prompt]

    for pid in prompts_to_run:
        out_path = OUT_DIR / f"gemini35flash_prompt{pid}_annotated.csv"
        if out_path.exists():
            log.info(f"File già esistente, skip: {out_path.name}")
            continue
        result_df = run_prompt(client, df, pid, out_path)
        result_df.to_csv(out_path, index=False)
        log.info(f"Salvato: {out_path}")

    log.info("Completato.")


if __name__ == "__main__":
    main()
