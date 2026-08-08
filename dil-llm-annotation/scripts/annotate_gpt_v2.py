#!/usr/bin/env python3
"""
Annotazione DIL - GPT-5.5 via OpenAI Responses API (chiamate sincrone)
Esperimento V2: 3 prompt × 1000 blocchi testuali

Nota: GPT-5.5 è progettato per la Responses API (/v1/responses), non per
la legacy Chat Completions API. Le chiamate vengono eseguite in modo
sincrono con rate limiting, analogamente a quanto fatto per Gemini.

Uso:
    python annotate_gpt_v2.py --prompt A
    python annotate_gpt_v2.py --prompt all

Le API key vengono lette dal file .keys.env nella stessa cartella dello script.
Output: 03_llm_annotated_csv/gpt55_prompt[A|B|C]_annotated.csv
"""

import os
import json
import time
import argparse
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# ---------------------------------------------------------------------------
# Caricamento API key da file esterno (.keys.env)
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).parent
load_dotenv(_SCRIPT_DIR / ".keys.env")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

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

MODEL         = "gpt-5.5"
MAX_TOKENS    = 256   # senza reasoning interno (effort=none), sufficiente per il JSON
CALL_DELAY    = 1.0   # secondi tra una chiamata e l'altra (60 RPM di sicurezza)
RETRY_WAIT    = 15    # secondi prima di riprovare in caso di errore transitorio
MAX_RETRIES   = 3
CHECKPOINT_EVERY = 50  # salva checkpoint ogni N blocchi testuali (resume in caso di interruzione)

# System instruction: costringe l'output in formato JSON puro
SYSTEM_INSTRUCTION = (
    "Sei un annotatore di testi letterari italiani. "
    "Rispondi ESCLUSIVAMENTE con un oggetto JSON valido, senza nessun testo prima o dopo. "
    'Formato richiesto: {"label": "yes", "confidence": "high"} '
    'oppure {"label": "no", "confidence": "low"}. '
    "I valori ammessi per label sono solo 'yes' o 'no'. "
    "I valori ammessi per confidence sono solo 'high', 'medium' o 'low'."
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "gpt_v2.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_prompt(prompt_id: str) -> str:
    return PROMPT_FILES[prompt_id].read_text(encoding="utf-8")


def parse_result(result_text: str) -> tuple[str, str]:
    try:
        text  = result_text.strip()
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("Nessun blocco JSON trovato nella risposta")
        obj        = json.loads(text[start:end])
        label      = str(obj.get("label", "")).lower().strip()
        confidence = str(obj.get("confidence", "")).lower().strip()
        if label not in ("yes", "no"):
            raise ValueError(f"Label non valido: '{label}'")
        if confidence not in ("high", "medium", "low"):
            confidence = "unknown"
        return label, confidence
    except Exception as e:
        log.warning(f"Parsing fallito: {e} | risposta: {result_text[:150]}")
        return "error", "unknown"


def call_gpt(client: OpenAI, prompt: str) -> tuple[str, str]:
    """Chiama GPT-5.5 via Responses API con retry esponenziale."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.responses.create(
                model=MODEL,
                instructions=SYSTEM_INSTRUCTION,
                input=prompt,
                max_output_tokens=MAX_TOKENS,
                reasoning={"effort": "none"},
            )
            return parse_result(response.output_text)
        except Exception as e:
            log.warning(f"Tentativo {attempt}/{MAX_RETRIES} fallito: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_WAIT * attempt)
    return "error", "unknown"


def run_prompt(client: OpenAI, df: pd.DataFrame, prompt_id: str, out_path: Path) -> pd.DataFrame:
    lbl_col  = f"DIL_gpt55_prompt{prompt_id}"
    conf_col = f"confidence_gpt55_prompt{prompt_id}"
    partial  = out_path.with_suffix(".partial.csv")
    total    = len(df)

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
        lbl, conf = call_gpt(client, template.replace("{TEXT}", text))
        labels.append(lbl)
        confs.append(conf)

        # Checkpoint periodico e a fine run
        if len(labels) % CHECKPOINT_EVERY == 0 or i == total:
            ckpt = df.iloc[:n_done + len(labels)].copy()
            ckpt[lbl_col]  = labels
            ckpt[conf_col] = confs
            ckpt.to_csv(partial, index=False)
            log.info(f"  [{i}/{total}] completati | errori: {labels.count('error')} | checkpoint salvato")

        time.sleep(CALL_DELAY)

    # Finalizza: scrivi file definitivo e rimuovi checkpoint
    out = df.copy()
    out[lbl_col]  = labels
    out[conf_col] = confs
    partial.unlink(missing_ok=True)

    err_count = labels.count("error")
    log.info(f"=== Prompt {prompt_id} completato: {total - err_count}/{total} ok, {err_count} errori ===")
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Annotazione DIL con GPT-5.5 (Responses API, sincrono)"
    )
    parser.add_argument(
        "--prompt",
        choices=["A", "B", "C", "all"],
        default="all",
        help="Quale prompt eseguire (default: all)",
    )
    args = parser.parse_args()

    if not OPENAI_API_KEY:
        raise SystemExit(
            "OPENAI_API_KEY non trovata.\n"
            "Crea il file 04_scripts/.keys.env partendo da .keys.env.template."
        )

    client = OpenAI(api_key=OPENAI_API_KEY)

    df = pd.read_csv(SAMPLE_FILE)
    log.info(f"Dataset caricato: {len(df)} blocchi testuali da {SAMPLE_FILE.name}")
    log.info(f"Modello: {MODEL} | API: Responses (sincrono) | delay: {CALL_DELAY}s/chiamata")

    prompts_to_run = ["A", "B", "C"] if args.prompt == "all" else [args.prompt]

    for pid in prompts_to_run:
        out_path = OUT_DIR / f"gpt55_prompt{pid}_annotated.csv"
        if out_path.exists():
            log.info(f"File già esistente, skip: {out_path.name}")
            continue
        result_df = run_prompt(client, df, pid, out_path)
        result_df.to_csv(out_path, index=False)
        log.info(f"Salvato: {out_path}")

    log.info("Completato.")


if __name__ == "__main__":
    main()
