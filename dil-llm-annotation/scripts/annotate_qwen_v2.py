#!/usr/bin/env python3
"""
Annotazione DIL - Qwen3-35B-A3B via LM Studio (reasoning attivo)
Esperimento V2: 3 prompt × 1000 blocchi testuali

Nota: LM Studio non disabilita il thinking di Qwen3 via /no_think.
Il reasoning viene esposto in reasoning_content (non in content).
MAX_TOKENS=8192 garantisce spazio per thinking (~600-800 tok) + risposta JSON.

Uso:
    python annotate_qwen_v2.py --prompt A
    python annotate_qwen_v2.py --prompt all
    python annotate_qwen_v2.py --model-id "qwen/qwen3.6-35b-a3b" --prompt A

    # Per vedere il model_id esatto del modello caricato in LM Studio:
    python annotate_qwen_v2.py --list-models

Output: 03_llm_annotated_csv/qwen3_35b_prompt[A|B|C]_annotated.csv

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

# Rimuove i tag <think>...</think> emessi da Qwen3 e altri modelli con reasoning
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

# ---------------------------------------------------------------------------
# LM Studio non richiede API key reale, ma carichiamo .keys.env per coerenza
# con gli altri script (potrebbe contenere il base_url personalizzato in futuro)
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).parent
load_dotenv(_SCRIPT_DIR / ".keys.env")

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

LMSTUDIO_BASE_URL   = "http://localhost:1234/v1"
MAX_TOKENS          = 8192    # LM Studio non disabilita il thinking via /no_think:
                              # il reasoning di Qwen3 occupa ~600-800 token, il resto
                              # va alla risposta finale. Con 1024 il budget esaurisce
                              # durante il reasoning e content rimane stringa vuota.
RETRY_WAIT          = 5       # secondi di attesa in caso di errore
MAX_RETRIES         = 3
INTER_REQUEST_DELAY = 0.5     # secondi tra una chiamata e l'altra (il server è locale)
CHECKPOINT_EVERY    = 50      # salva checkpoint ogni N blocchi testuali (resume in caso di interruzione)

# Parametri di sampling Qwen3 (doc ufficiale, modalità thinking):
# Temperature=0.6, TopP=0.95, TopK=20. NON usare 0.0: causa loop infiniti.
# Per Minerva-7B questi parametri sono comunque appropriati.
TEMPERATURE         = 0.6
TOP_P               = 0.95
TOP_K               = 20     # passato via extra_body (non standard OpenAI)

# /no_think: soft switch Qwen3 per disabilitare il thinking mode via system message.
# In modalità thinking con temperature=0.0, Qwen3 entra in loop e non produce output.
# Per Minerva-7B il tag è ignorato silenziosamente, senza effetti collaterali.
SYSTEM_MESSAGE = (
    "/no_think "
    "Sei un annotatore esperto di testi letterari italiani. "
    "Rispondi ESCLUSIVAMENTE con un oggetto JSON nel formato esatto: "
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
        logging.FileHandler(LOG_DIR / "lmstudio_v2.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_client() -> OpenAI:
    # LM Studio non richiede API key ma il client ne vuole una non vuota
    return OpenAI(base_url=LMSTUDIO_BASE_URL, api_key="lm-studio")


def auto_detect_model(client: OpenAI) -> str:
    models = client.models.list()
    if not models.data:
        raise SystemExit(
            "Nessun modello trovato in LM Studio. "
            "Carica Qwen3-35B e avvia il server prima di eseguire questo script."
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
    # Rimuovi eventuali blocchi <think>...</think> (Qwen3, DeepSeek-R1, ecc.)
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
            raise ValueError(f"Label non valido: {label}")
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
            msg = response.choices[0].message
            # content contiene la risposta finale; reasoning_content il thinking.
            # LM Studio li espone separatamente: content è vuoto se il budget
            # finisce durante il reasoning. In quel caso tentiamo reasoning_content.
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


MODEL_SLUG = "qwen3_35b"   # prefisso fisso per colonne e file di output


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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Annotazione DIL con Qwen3-35B via LM Studio"
    )
    parser.add_argument(
        "--model-id",
        default=None,
        help=(
            "Model ID esatto come restituito da LM Studio "
            "(es. 'qwen/qwen3.6-35b-a3b'). "
            "Se omesso, viene rilevato automaticamente dal server."
        ),
    )
    parser.add_argument("--prompt", choices=["A", "B", "C", "all"], default="all")
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Elenca i modelli disponibili in LM Studio e termina",
    )
    args = parser.parse_args()

    client = get_client()

    if args.list_models:
        list_models(client)
        return

    model_id = args.model_id if args.model_id else auto_detect_model(client)

    df = pd.read_csv(SAMPLE_FILE)
    log.info(f"Dataset caricato: {len(df)} blocchi testuali")
    log.info(f"Modello: {model_id} | slug output: qwen3_35b")

    prompts_to_run = ["A", "B", "C"] if args.prompt == "all" else [args.prompt]

    for pid in prompts_to_run:
        out_path = OUT_DIR / f"qwen3_35b_prompt{pid}_annotated.csv"
        if out_path.exists():
            log.info(f"File già esistente, skip: {out_path.name}")
            continue
        result_df = run_prompt(client, model_id, df, pid, out_path)
        result_df.to_csv(out_path, index=False)
        log.info(f"Salvato: {out_path}")

    log.info("Completato.")


if __name__ == "__main__":
    main()
