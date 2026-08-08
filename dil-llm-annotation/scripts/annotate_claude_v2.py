#!/usr/bin/env python3
"""
Annotazione DIL - Claude Sonnet 4.6 via Anthropic Batches API
Esperimento V2: 3 prompt × 1000 blocchi testuali

Uso:
    python annotate_claude_v2.py --prompt A   # esegue solo prompt A
    python annotate_claude_v2.py --prompt all # esegue A, B, C in sequenza

Le API key vengono lette dal file .keys.env nella stessa cartella dello script.
Output: 03_llm_annotated_csv/claude_sonnet46_prompt[A|B|C]_annotated.csv
"""

import os
import json
import time
import argparse
import logging
import pandas as pd
import anthropic
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Caricamento API key da file esterno (.keys.env)
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).parent
load_dotenv(_SCRIPT_DIR / ".keys.env")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

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

# Model ID canonico (forma dateless, confermata dalla documentazione Anthropic)
MODEL         = "claude-sonnet-4-6"
MAX_TOKENS    = 64
POLL_INTERVAL = 30   # secondi tra un polling e il successivo

SYSTEM_PROMPT = (
    "Sei un annotatore di testi letterari italiani. "
    "Rispondi ESCLUSIVAMENTE con un oggetto JSON valido, senza nessun testo prima o dopo. "
    "Formato richiesto: {\"label\": \"yes\", \"confidence\": \"high\"} "
    "oppure {\"label\": \"no\", \"confidence\": \"low\"}. "
    "I valori ammessi per label sono solo 'yes' o 'no'. "
    "I valori ammessi per confidence sono solo 'high', 'medium' o 'low'."
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "claude_v2.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_prompt(prompt_id: str) -> str:
    path = PROMPT_FILES[prompt_id]
    return path.read_text(encoding="utf-8")


def build_requests(df: pd.DataFrame, prompt_template: str, prompt_id: str) -> list[dict]:
    """Costruisce la lista di richieste per Anthropic Batches API."""
    requests = []
    for idx, row in df.iterrows():
        text         = str(row["text"]).strip()
        user_content = prompt_template.replace("{TEXT}", text)
        requests.append({
            "custom_id": f"prompt{prompt_id}_row{idx}",
            "params": {
                "model":      MODEL,
                "max_tokens": MAX_TOKENS,
                "system":     SYSTEM_PROMPT,
                "messages": [
                    {"role": "user", "content": user_content},
                ],
            },
        })
    return requests


def submit_batch(client: anthropic.Anthropic, requests: list[dict]) -> str:
    log.info(f"Invio batch: {len(requests)} richieste — modello: {MODEL}")
    batch = client.messages.batches.create(requests=requests)
    log.info(f"Batch ID: {batch.id} | stato iniziale: {batch.processing_status}")
    return batch.id


def poll_batch(client: anthropic.Anthropic, batch_id: str) -> object:
    while True:
        batch  = client.messages.batches.retrieve(batch_id)
        status = batch.processing_status
        counts = batch.request_counts
        log.info(
            f"[{batch_id}] stato={status} | "
            f"ok={counts.succeeded} errori={counts.errored} "
            f"in corso={counts.processing}"
        )
        if status == "ended":
            return batch
        time.sleep(POLL_INTERVAL)


def parse_result(result_text: str) -> tuple[str, str]:
    """Estrae label e confidence dalla risposta JSON del modello."""
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


def collect_results(
    client: anthropic.Anthropic,
    batch_id: str,
    df: pd.DataFrame,
    prompt_id: str,
) -> pd.DataFrame:
    """Abbina i risultati del batch alle righe originali del DataFrame."""
    results_map: dict[str, tuple[str, str]] = {}

    for result in client.messages.batches.results(batch_id):
        cid = result.custom_id
        if result.result.type == "succeeded":
            content            = result.result.message.content[0].text
            label, confidence  = parse_result(content)
        else:
            # errored | canceled | expired
            log.error(f"Richiesta non riuscita: {cid} | tipo: {result.result.type}")
            label, confidence = "error", "unknown"
        results_map[cid] = (label, confidence)

    labels, confidences = [], []
    for idx in df.index:
        cid        = f"prompt{prompt_id}_row{idx}"
        lbl, conf  = results_map.get(cid, ("missing", "unknown"))
        if lbl == "missing":
            log.warning(f"Risultato assente per {cid}")
        labels.append(lbl)
        confidences.append(conf)

    out = df.copy()
    out[f"DIL_claude_sonnet46_prompt{prompt_id}"]        = labels
    out[f"confidence_claude_sonnet46_prompt{prompt_id}"] = confidences
    return out


def run_prompt(client: anthropic.Anthropic, df: pd.DataFrame, prompt_id: str) -> pd.DataFrame:
    log.info(f"=== Inizio prompt {prompt_id} ({len(df)} blocchi testuali) ===")
    template = load_prompt(prompt_id)
    requests = build_requests(df, template, prompt_id)
    batch_id = submit_batch(client, requests)

    # Salva il batch_id per eventuale ripresa manuale
    batch_log_path = LOG_DIR / "claude_batch_ids_v2.json"
    ids = json.loads(batch_log_path.read_text()) if batch_log_path.exists() else {}
    ids[f"prompt{prompt_id}_{datetime.now().isoformat()}"] = batch_id
    batch_log_path.write_text(json.dumps(ids, indent=2))

    poll_batch(client, batch_id)
    return collect_results(client, batch_id, df, prompt_id)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Annotazione DIL con Claude Sonnet 4.6 (Batches API)"
    )
    parser.add_argument(
        "--prompt",
        choices=["A", "B", "C", "all"],
        default="all",
        help="Quale prompt eseguire (default: all)",
    )
    args = parser.parse_args()

    if not ANTHROPIC_API_KEY:
        raise SystemExit(
            "ANTHROPIC_API_KEY non trovata.\n"
            "Crea il file 04_scripts/.keys.env partendo da .keys.env.template."
        )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    df = pd.read_csv(SAMPLE_FILE)
    log.info(f"Dataset caricato: {len(df)} blocchi testuali da {SAMPLE_FILE.name}")

    prompts_to_run = ["A", "B", "C"] if args.prompt == "all" else [args.prompt]

    for pid in prompts_to_run:
        out_path = OUT_DIR / f"claude_sonnet46_prompt{pid}_annotated.csv"
        if out_path.exists():
            log.info(f"File già esistente, skip: {out_path.name}")
            continue
        result_df = run_prompt(client, df, pid)
        result_df.to_csv(out_path, index=False)
        log.info(f"Salvato: {out_path}")

    log.info("Completato.")


if __name__ == "__main__":
    main()
