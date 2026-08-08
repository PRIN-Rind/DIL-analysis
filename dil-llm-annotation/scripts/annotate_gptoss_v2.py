#!/usr/bin/env python3
"""
Annotazione DIL - openai/gpt-oss-120b via LM Studio
Esperimento V2: 3 prompt × 1000 blocchi testuali

Il modello potrebbe avere reasoning interno: lo script gestisce sia il caso
in cui la risposta sia in content sia il caso in cui sia in reasoning_content,
e rimuove eventuali blocchi <think>...</think> prima del parsing JSON.

Uso:
    python annotate_gptoss_v2.py --prompt A
    python annotate_gptoss_v2.py --prompt all
    python annotate_gptoss_v2.py --model-id "openai/gpt-oss-120b" --prompt A

    # Per vedere il model_id esatto del modello caricato in LM Studio:
    python annotate_gptoss_v2.py --list-models

Output: 03_llm_annotated_csv/gpt_oss_120b_prompt[A|B|C]_annotated.csv

Dipendenze: pip install openai pandas python-dotenv
"""

import os
import re
import json
import time
import argparse
import logging
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Rimuove blocchi <think>...</think> emessi da modelli con reasoning interno
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

_SCRIPT_DIR = Path(__file__).parent
load_dotenv(_SCRIPT_DIR / ".keys.env")

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

LMSTUDIO_BASE_URL   = "http://127.0.0.1:1234/v1"
MAX_TOKENS          = 8192   # budget ampio: accomoda reasoning interno + risposta finale
RETRY_WAIT          = 5
MAX_RETRIES         = 3
INTER_REQUEST_DELAY = 0.5
CHECKPOINT_EVERY    = 50     # salva checkpoint ogni N blocchi testuali

# Parametri di sampling conservativi, compatibili con modelli reasoning.
TEMPERATURE = 0.6
TOP_P       = 0.95
TOP_K       = 20     # passato via extra_body (non standard OpenAI)

MODEL_SLUG  = "gpt_oss_120b"   # prefisso fisso per colonne e file di output

SYSTEM_MESSAGE = (
    "Sei un annotatore esperto di testi letterari italiani. "
    "Rispondi ESCLUSIVAMENTE con questo formato, senza nessun altro testo: "
    '{"label": "yes", "confidence": "high"} '
    'oppure {"label": "no", "confidence": "low"}. '
    "I valori ammessi per label sono solo 'yes' o 'no'. "
    "I valori ammessi per confidence sono solo 'high', 'medium' o 'low'. "
    "Non aggiungere spiegazioni, testo libero o formattazione aggiuntiva."
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "gptoss_v2.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


def get_client() -> OpenAI:
    return OpenAI(base_url=LMSTUDIO_BASE_URL, api_key="lm-studio")


def auto_detect_model(client: OpenAI) -> str:
    models = client.models.list()
    if not models.data:
        raise SystemExit(
            "Nessun modello trovato in LM Studio. "
            "Carica gpt-oss-120b e avvia il server prima di eseguire questo script."
        )
    model_id = models.data[0].id
    log.info(f"Modello rilevato automaticamente: {model_id}")
    return model_id


def list_models(client: OpenAI):
    models = client.models.list()
    print("Modelli disponibili in LM Studio:")
    for m in models.data:
        print(f"  id={m.id}")


def load_prompt(prompt_id: str) -> str:
    return PROMPT_FILES[prompt_id].read_text(encoding="utf-8")


def parse_result(result_text: str) -> tuple[str, str]:
    if result_text is None:
        log.warning("Risposta None dal modello")
        return "error", "unknown"
    cleaned = _THINK_RE.sub("", result_text).strip()
    try:
        start = cleaned.find("{")
        end   = cleaned.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("Nessun JSON trovato nella risposta")
        obj        = json.loads(cleaned[start:end])
        label      = str(obj.get("label", "")).lower().strip()
        confidence = str(obj.get("confidence", "")).lower().strip()
        if label not in ("yes", "no"):
            raise ValueError(f"Label non valido: '{label}'")
        if confidence not in ("high", "medium", "low"):
            confidence = "unknown"
        return label, confidence
    except Exception as e:
        log.warning(f"Parsing fallito: {e} | testo (pulito): {cleaned[:200]}")
        return "error", "unknown"


def call_model(client: OpenAI, model_id: str, prompt: str) -> tuple[str, str]:
    messages = [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user",   "content": prompt},
    ]
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                extra_body={"top_k": TOP_K},
            )
            msg  = response.choices[0].message
            text = msg.content or ""
            if not text.strip():
                try:
                    text = (msg.model_extra or {}).get("reasoning_content", "") or ""
                    if text:
                        log.debug("Fallback a reasoning_content (content vuoto)")
                except Exception:
                    pass
            return parse_result(text)
        except Exception as e:
            log.warning(f"Tentativo {attempt}/{MAX_RETRIES} fallito: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_WAIT * attempt)
    return "error", "unknown"


def run_prompt(
    client: OpenAI,
    model_id: str,
    df: pd.DataFrame,
    prompt_id: str,
    out_path: Path,
) -> pd.DataFrame:
    lbl_col  = f"DIL_{MODEL_SLUG}_prompt{prompt_id}"
    conf_col = f"confidence_{MODEL_SLUG}_prompt{prompt_id}"
    partial  = out_path.with_suffix(".partial.csv")
    total    = len(df)

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
    log.info(f"=== {MODEL_SLUG} | Prompt {prompt_id} — {total - n_done} blocchi testuali rimanenti ===")

    for i, (_, row) in enumerate(remaining.iterrows(), start=n_done + 1):
        text = str(row["text"]).strip()
        label, confidence = call_model(client, model_id, template.replace("{TEXT}", text))
        labels.append(label)
        confs.append(confidence)

        if len(labels) % CHECKPOINT_EVERY == 0 or i == total:
            ckpt = df.iloc[:n_done + len(labels)].copy()
            ckpt[lbl_col]  = labels
            ckpt[conf_col] = confs
            ckpt.to_csv(partial, index=False)
            log.info(f"  [{i}/{total}] completati | errori: {labels.count('error')} | checkpoint salvato")

        time.sleep(INTER_REQUEST_DELAY)

    out = df.copy()
    out[lbl_col]  = labels
    out[conf_col] = confs
    partial.unlink(missing_ok=True)

    err_count = labels.count("error")
    log.info(f"=== Prompt {prompt_id} completato: {total - err_count}/{total} ok, {err_count} errori ===")
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Annotazione DIL con gpt-oss-120b via LM Studio"
    )
    parser.add_argument(
        "--model-id", default=None,
        help="Model ID esatto come restituito da LM Studio. Se omesso, rilevato automaticamente."
    )
    parser.add_argument("--prompt", choices=["A", "B", "C", "all"], default="all")
    parser.add_argument(
        "--list-models", action="store_true",
        help="Elenca i modelli disponibili in LM Studio e termina"
    )
    args = parser.parse_args()

    client = get_client()

    if args.list_models:
        list_models(client)
        return

    model_id = args.model_id if args.model_id else auto_detect_model(client)

    df = pd.read_csv(SAMPLE_FILE)
    log.info(f"Dataset caricato: {len(df)} blocchi testuali")
    log.info(f"Modello: {model_id} | slug output: {MODEL_SLUG}")

    prompts_to_run = ["A", "B", "C"] if args.prompt == "all" else [args.prompt]

    for pid in prompts_to_run:
        out_path = OUT_DIR / f"{MODEL_SLUG}_prompt{pid}_annotated.csv"
        if out_path.exists():
            log.info(f"File già esistente, skip: {out_path.name}")
            continue
        result_df = run_prompt(client, model_id, df, pid, out_path)
        result_df.to_csv(out_path, index=False)
        log.info(f"Salvato: {out_path}")

    log.info("Completato.")


if __name__ == "__main__":
    main()
