#!/usr/bin/env python3
"""annotate_dil_gpt_500_v2.py

Annotazione automatica del Discorso Indiretto Libero (DIL) su un CSV.

Caratteristiche principali
  - Legge un CSV con trigrammi/brani (colonna `text` di default)
  - Aggiunge una colonna di output con le predizioni del modello OpenAI
  - Supporta ripresa (resume) da un output CSV già parzialmente annotato
  - Opzionalmente calcola metriche vs gold standard (colonna `DIL`) e
    confronto di accordo vs annotatore LLM (colonna `DIL_Sonnet`)

Nota tecnica (importante):
  - Per i modelli GPT-5.* si usa la Responses API e si legge l'output tramite
    `response.output_text` (scorciatoia dell'SDK).
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from openai import OpenAI
from tqdm import tqdm


# ============================================================================
# CONFIGURAZIONE
# ============================================================================

DEFAULT_INPUT_FILE = "corpus_labelled-trigrams_500_Sonnet_v2_annotated.csv"
DEFAULT_OUTPUT_FILE = "corpus_labelled-trigrams_500_DUAL_annotated.csv"

SYSTEM_PROMPT = (
    "Sei un linguista esperto di narratologia e stilistica italiana. "
    "Il tuo compito è identificare la presenza di Discorso Indiretto Libero (DIL) "
    "in brevi brani narrativi. "
    "Valuta ogni brano caso per caso, considerando contesto e segnali stilistici; "
    "non limitarti a regole superficiali."
)

USER_PROMPT_TEMPLATE = """Valuta se il seguente testo contiene Discorso Indiretto Libero (DIL), anche solo in parte.

DEFINIZIONE (DIL)
Tecnica narrativa che rappresenta pensiero/discorso di un personaggio SENZA verbi dichiarativi o introduttivi espliciti
(es. "pensò", "disse", "si chiese", "mormorò", "si disse"). Di norma mantiene la terza persona e la cornice del narratore,
ma fa emergere la soggettività del personaggio.

INDIZI TIPICI (non necessari tutti)
- Prospettiva del personaggio (valutazioni, emozioni, giudizi "interna" al personaggio).
- Lessico/intonazione coerenti con il personaggio più che con un narratore neutro.
- Marcatori: interiezioni ("Oh!", "Ah!", "Dio mio!"), esclamazioni, interrogative retoriche,
  modalizzatori ("forse", "certamente", "senza dubbio"), ellissi/puntini di sospensione.

CASI DI CONTROLLO
1) Presenza di verbo dichiarativo = NON è DIL per quel segmento:
   "Giovanni pensò che era troppo tardi. Si disse che non sarebbe più tornato." -> NO (solo indiretto con verbi)
2) DIL può seguire un verbo dichiarativo e continuare senza di esso:
   "Pensò che era finita. Tutto perduto, inutile continuare..." -> YES (la seconda frase è DIL)
3) Psicologizzazione/descrizione con formula introduttiva NON è DIL:
   "Un pensiero gli attraversò la mente: non sarebbe mai tornato." -> NO
4) Narrazione valutativa del narratore non è automaticamente DIL:
   "Era un uomo strano, difficile da capire." -> NO se non è chiaramente prospettiva di un personaggio.

CRITERIO DECISIONALE
Rispondi YES se nel testo è presente almeno un tratto riconoscibile di DIL (anche parziale).
Rispondi NO se il testo resta in voce narrante neutra/onnisciente o usa solo forme introdotte esplicitamente da verbi dicendi/pensiero.

TESTO DA ANALIZZARE:
{testo_blocco}

IMPORTANTE: Rispondi SOLO con: YES oppure NO."""


# Modelli che supportano `reasoning.effort`.
# (Puoi aggiungere alias/varianti se ti servono.)
REASONING_MODELS = {
    "gpt-5.2",
}


VALID_LABELS = {"yes", "no"}


# ============================================================================
# HELPERS
# ============================================================================


def sanitize_model_name(model: str) -> str:
    """Rende il nome modello sicuro per nomi colonna/file."""
    return model.replace("-", "_").replace(".", "_")


def normalize_binary_answer(answer_text: str) -> str:
    """Normalizza una risposta del modello in 'yes'/'no'.

    Regola: match sul primo token significativo, con fallback prudente su 'no'.
    """
    ans = str(answer_text).strip().upper()
    if ans.startswith("YES"):
        return "yes"
    if ans.startswith("NO"):
        return "no"
    # Fallback prudente
    print(f"Warning: risposta ambigua '{ans}', assumo 'no'")
    return "no"


def extract_output_text(response) -> str:
    """Estrae testo da una risposta Responses API.
    
    Gestisce correttamente la struttura output della Responses API
    per modelli GPT-5.* che può contenere blocchi di tipo 'text' o 'reasoning'.
    Per i modelli con reasoning, cerca prima i blocchi 'text' e poi estrae
    il summary dai blocchi 'reasoning' se necessario.
    """
    # Tentativo 1: usa output_text se disponibile (alcuni SDK lo forniscono)
    if hasattr(response, 'output_text') and response.output_text:
        return str(response.output_text).strip()
    
    # Tentativo 2: parsing manuale di response.output
    if not hasattr(response, 'output'):
        print("WARNING: response non ha attributo 'output'")
        return ""
    
    output_items = response.output
    if not output_items:
        print("WARNING: response.output è vuoto o None")
        return ""
    
    # Raccogli tutti i blocchi di testo e reasoning
    text_blocks = []
    reasoning_summaries = []
    
    for item in output_items:
        # Gestisci sia dict che oggetti
        if isinstance(item, dict):
            item_type = item.get("type")
            
            # Blocchi di testo diretto
            if item_type == "text":
                text_content = item.get("text", "")
                if text_content:
                    text_blocks.append(text_content)
            
            # Blocchi di reasoning (contengono summary)
            elif item_type == "reasoning":
                summary = item.get("summary", [])
                if summary:
                    # summary è tipicamente una lista di stringhe
                    if isinstance(summary, list):
                        reasoning_summaries.extend(summary)
                    else:
                        reasoning_summaries.append(str(summary))
        else:
            # Oggetto con attributi
            item_type = getattr(item, "type", None)
            
            # Blocchi di testo diretto
            if item_type == "text":
                text_content = getattr(item, "text", "")
                if text_content:
                    text_blocks.append(text_content)
            
            # Blocchi di reasoning (contengono summary)
            elif item_type == "reasoning":
                summary = getattr(item, "summary", [])
                if summary:
                    # summary è tipicamente una lista di stringhe
                    if isinstance(summary, list):
                        reasoning_summaries.extend(summary)
                    else:
                        reasoning_summaries.append(str(summary))
    
    # Priorità: prima i blocchi text, poi i reasoning summaries
    if text_blocks:
        result = "".join(text_blocks).strip()
    elif reasoning_summaries:
        result = " ".join(reasoning_summaries).strip()
    else:
        result = ""
    
    # Debug: se ancora vuoto, stampa la struttura per diagnostica
    if not result:
        print(f"WARNING: Risposta vuota. Struttura response: {type(response)}")
        print(f"  hasattr output: {hasattr(response, 'output')}")
        if hasattr(response, 'output'):
            print(f"  output type: {type(response.output)}")
            print(f"  output length: {len(response.output) if response.output else 0}")
            if response.output and len(response.output) > 0:
                print(f"  first item type: {type(response.output[0])}")
                print(f"  first item: {response.output[0]}")
                # Stampa tutti gli attributi del primo item per debug
                if hasattr(response.output[0], '__dict__'):
                    print(f"  first item attributes: {response.output[0].__dict__}")
    
    return result


# ============================================================================
# CLASSE PRINCIPALE
# ============================================================================


class DILAnnotator:
    """Annotatore automatico per Discorso Indiretto Libero (DIL)."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5.2",
        batch_size: int = 5,
        max_retries: int = 3,
        reasoning_effort: str = "medium",
        request_timeout_s: float = 120.0,
        debug: bool = False,
    ):
        self.client = OpenAI(api_key=api_key, timeout=request_timeout_s)
        self.model = model
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.reasoning_effort = reasoning_effort
        self.is_reasoning_model = model in REASONING_MODELS
        self.debug = debug

    def analyze_text(self, text: str) -> str:
        """Analizza un singolo testo; ritorna 'yes'/'no'."""
        prompt = USER_PROMPT_TEMPLATE.format(testo_blocco=text)

        for attempt in range(self.max_retries):
            try:
                answer_text = self._call_responses_api(prompt)
                
                # Validazione risposta
                if not answer_text or answer_text.strip() == "":
                    print(f"WARNING: risposta vuota al tentativo {attempt+1}/{self.max_retries}")
                    if attempt < self.max_retries - 1:
                        time.sleep(2)
                        continue
                    # Se anche l'ultimo tentativo fallisce, ritorna default
                    print("ERROR: Tutti i tentativi hanno prodotto risposte vuote, assumo 'no'")
                    return "no"
                
                return normalize_binary_answer(answer_text)

            except Exception as e:
                # L'SDK OpenAI fa già retry su 429/5xx; qui gestiamo un backoff
                # aggiuntivo (utile se stai facendo molte chiamate ravvicinate).
                error_name = type(e).__name__
                if "RateLimit" in error_name or "429" in str(e):
                    wait_time = 2 ** attempt
                    print(f"Rate limit, attendo {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                print(f"Errore API (tentativo {attempt+1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2)
                    continue
                raise

        # Fallback finale se tutti i retry falliscono
        print("ERROR: Esauriti tutti i tentativi, assumo 'no'")
        return "no"

    def _call_responses_api(self, user_prompt: str) -> str:
        """Chiama la Responses API e ritorna testo."""
        params = {
            "model": self.model,
            "instructions": SYSTEM_PROMPT,
            "input": user_prompt,
            "max_output_tokens": 100,
        }

        # Per GPT-5.* puoi guidare lo sforzo di reasoning.
        # (Per gpt-5.2 sono supportati: none (default), low, medium, high, xhigh.)
        #if self.is_reasoning_model and self.reasoning_effort:
        #    params["reasoning"] = {"effort": self.reasoning_effort}

        if self.debug:
            print(f"DEBUG: chiamata API con model={self.model}, effort={self.reasoning_effort}")
        
        try:
            response = self.client.responses.create(**params)
            
            if self.debug:
                print(f"DEBUG: response type={type(response)}")
                print(f"DEBUG: response attributes={dir(response)[:10]}...")  # primi 10 per brevità
            
            text = extract_output_text(response)
            
            if self.debug:
                print(f"DEBUG: extracted text='{text}'")
            
            return text
            
        except Exception as e:
            print(f"ERROR nella chiamata API: {type(e).__name__}: {e}")
            raise

    def annotate_corpus(
        self,
        input_file: str,
        output_file: str,
        text_column: str = "text",
        resume: bool = True,
        save_every_batch: bool = True,
        inter_request_sleep_s: float = 0.1,
    ) -> pd.DataFrame:
        """Annota un CSV e salva incrementalmente in output_file."""

        df = pd.read_csv(input_file, encoding="utf-8")
        print(f"Corpus caricato: {len(df):,} righe")
        print(f"Colonne presenti: {', '.join(df.columns)}")

        if text_column not in df.columns:
            raise ValueError(
                f"Colonna testo '{text_column}' non trovata. Colonne disponibili: {list(df.columns)}"
            )

        if "DIL_Sonnet" not in df.columns:
            print("WARNING: Colonna DIL_Sonnet non trovata!")

        safe_model = sanitize_model_name(self.model)
        gpt_column = f"DIL_{safe_model}"

        # Resume: carica progresso precedente
        if resume and Path(output_file).exists():
            df_existing = pd.read_csv(output_file, encoding="utf-8")
            if gpt_column in df_existing.columns:
                # FIX: assicura dtype object per evitare errori con stringhe vuote
                df[gpt_column] = df_existing[gpt_column].astype(object)
                already_done = (
                    df[gpt_column].notna() & (df[gpt_column].astype(str).str.strip() != "")
                ).sum()
                print(f"Ripresa da file esistente: {already_done:,} righe già annotate")
            else:
                # FIX: inizializza con dtype object
                df[gpt_column] = pd.Series(dtype=object)
        else:
            # FIX: inizializza con dtype object
            df[gpt_column] = pd.Series(dtype=object)

        # Righe da processare
        mask_todo = df[gpt_column].isna() | (df[gpt_column].astype(str).str.strip() == "")
        indices_todo = df[mask_todo].index.tolist()

        if not indices_todo:
            print("Tutte le righe sono già annotate!")
            return df

        print(f"Righe da processare: {len(indices_todo):,}")
        print(f"Colonna output: {gpt_column}")
        print(f"Modello: {self.model} {'(reasoning)' if self.is_reasoning_model else ''}")

        for i in tqdm(range(0, len(indices_todo), self.batch_size), desc="Batch"):
            batch_indices = indices_todo[i : i + self.batch_size]

            for idx in tqdm(batch_indices, desc=f"Batch {i // self.batch_size + 1}", leave=False):
                text = str(df.at[idx, text_column])
                result = self.analyze_text(text)
                df.at[idx, gpt_column] = result
                
                if self.debug:
                    print(f"DEBUG: idx={idx}, result='{result}'")
                
                time.sleep(inter_request_sleep_s)

            if save_every_batch:
                df.to_csv(output_file, index=False, encoding="utf-8")
                done = min(i + len(batch_indices), len(indices_todo))
                print(f"✓ Salvato batch (completate {done:,}/{len(indices_todo):,} righe)")

        if not save_every_batch:
            df.to_csv(output_file, index=False, encoding="utf-8")

        print("\n✓ Annotazione completata!")
        return df

    def compute_metrics(
        self,
        df: pd.DataFrame,
        gold_column: str = "DIL",
        pred_column: Optional[str] = None,
    ) -> Dict:
        """Metriche vs gold standard (binario yes/no)."""
        safe_model = sanitize_model_name(self.model)
        if pred_column is None:
            pred_column = f"DIL_{safe_model}"

        if gold_column not in df.columns:
            raise ValueError(f"Colonna gold '{gold_column}' non trovata")
        if pred_column not in df.columns:
            raise ValueError(f"Colonna pred '{pred_column}' non trovata")

        df_eval = df[df[pred_column].isin(VALID_LABELS) & df[gold_column].isin(VALID_LABELS)]

        tp = len(df_eval[(df_eval[gold_column] == "yes") & (df_eval[pred_column] == "yes")])
        tn = len(df_eval[(df_eval[gold_column] == "no") & (df_eval[pred_column] == "no")])
        fp = len(df_eval[(df_eval[gold_column] == "no") & (df_eval[pred_column] == "yes")])
        fn = len(df_eval[(df_eval[gold_column] == "yes") & (df_eval[pred_column] == "no")])

        total = len(df_eval)
        accuracy = (tp + tn) / total if total else 0.0
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) else 0.0
        specificity = tn / (tn + fp) if (tn + fp) else 0.0

        return {
            "total": total,
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "specificity": specificity,
            "f1_score": f1,
            "true_positives": tp,
            "true_negatives": tn,
            "false_positives": fp,
            "false_negatives": fn,
        }

    def compare_annotators(
        self,
        df: pd.DataFrame,
        annotator1_col: str = "DIL_Sonnet",
        annotator2_col: Optional[str] = None,
    ) -> Dict:
        """Confronto di accordo (Sonnet vs GPT), su etichette yes/no."""
        safe_model = sanitize_model_name(self.model)
        if annotator2_col is None:
            annotator2_col = f"DIL_{safe_model}"

        if annotator1_col not in df.columns:
            raise ValueError(f"Colonna annotatore1 '{annotator1_col}' non trovata")
        if annotator2_col not in df.columns:
            raise ValueError(f"Colonna annotatore2 '{annotator2_col}' non trovata")

        df_compare = df[df[annotator1_col].isin(VALID_LABELS) & df[annotator2_col].isin(VALID_LABELS)]

        agreement = len(df_compare[df_compare[annotator1_col] == df_compare[annotator2_col]])
        total = len(df_compare)
        agreement_rate = agreement / total if total else 0.0

        both_yes = len(df_compare[(df_compare[annotator1_col] == "yes") & (df_compare[annotator2_col] == "yes")])
        both_no = len(df_compare[(df_compare[annotator1_col] == "no") & (df_compare[annotator2_col] == "no")])
        sonnet_yes_gpt_no = len(
            df_compare[(df_compare[annotator1_col] == "yes") & (df_compare[annotator2_col] == "no")]
        )
        sonnet_no_gpt_yes = len(
            df_compare[(df_compare[annotator1_col] == "no") & (df_compare[annotator2_col] == "yes")]
        )

        return {
            "total_compared": total,
            "agreement": agreement,
            "agreement_rate": agreement_rate,
            "both_yes": both_yes,
            "both_no": both_no,
            "sonnet_yes_gpt_no": sonnet_yes_gpt_no,
            "sonnet_no_gpt_yes": sonnet_no_gpt_yes,
        }


# ============================================================================
# MAIN
# ============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Annotazione automatica DIL con modelli OpenAI su 500 trigrammi"
    )
    parser.add_argument("--input-file", default=DEFAULT_INPUT_FILE)
    parser.add_argument("--output-file", default=DEFAULT_OUTPUT_FILE)
    parser.add_argument("--api-key", default=None, help="Chiave API OpenAI (default: env OPENAI_API_KEY)")
    parser.add_argument("--model", default="gpt-5.2", help="Nome modello (es. gpt-5.2)")
    parser.add_argument(
        "--reasoning-effort",
        default="low",
        choices=["none", "low", "medium", "high", "xhigh"],
        help="Sforzo reasoning (per modelli che lo supportano).",
    )
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--text-column", default="text")
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--eval", action="store_true", help="Calcola metriche vs gold (colonna DIL)")
    parser.add_argument("--compare", action="store_true", help="Confronta Sonnet vs GPT")
    parser.add_argument("--debug", action="store_true", help="Attiva modalità debug con output verbose")

    args = parser.parse_args()

    api_key = args.api_key
    if not api_key:
        # fallback su env var (stesso nome usato dall'SDK)
        import os

        api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Chiave API mancante: usa --api-key oppure imposta OPENAI_API_KEY")

    # Per coerenza: se l'utente passa 'none', non inviamo la chiave reasoning.
    reasoning_effort = "" if args.reasoning_effort == "none" else args.reasoning_effort

    annotator = DILAnnotator(
        api_key=api_key,
        model=args.model,
        batch_size=args.batch_size,
        reasoning_effort=reasoning_effort,
        debug=args.debug,
    )

    print("=" * 70)
    print("ANNOTAZIONE AUTOMATICA DISCORSO INDIRETTO LIBERO")
    print("Esperimento 500 Trigrammi: Claude Sonnet vs GPT")
    print("=" * 70)
    print(f"Modello: {args.model}")
    if annotator.is_reasoning_model:
        print(f"Reasoning effort: {args.reasoning_effort}")
    print(f"Input:  {args.input_file}")
    print(f"Output: {args.output_file}")
    print(f"Batch size: {args.batch_size}")
    if args.debug:
        print("Modalità DEBUG: attiva")
    print("=" * 70)

    df = annotator.annotate_corpus(
        input_file=args.input_file,
        output_file=args.output_file,
        text_column=args.text_column,
        resume=not args.no_resume,
    )

    safe_model = sanitize_model_name(args.model)

    if args.eval:
        print("\n" + "=" * 70)
        print("VALUTAZIONE PERFORMANCE vs GOLD STANDARD")
        print("=" * 70)

        metrics = annotator.compute_metrics(df)

        print(f"\nRighe valutate: {metrics['total']:,}")
        print(f"\nAccuracy:    {metrics['accuracy']:.2%}")
        print(f"Precision:   {metrics['precision']:.2%}")
        print(f"Recall:      {metrics['recall']:.2%}")
        print(f"Specificity: {metrics['specificity']:.2%}")
        print(f"F1-Score:    {metrics['f1_score']:.2%}")

        print("\nMatrice di confusione:")
        print(f"{'':12s} | Pred NO | Pred YES")
        print("-" * 35)
        print(f"Gold NO      | {metrics['true_negatives']:7d} | {metrics['false_positives']:8d}")
        print(f"Gold YES     | {metrics['false_negatives']:7d} | {metrics['true_positives']:8d}")

        metrics_file = args.output_file.replace(".csv", f"_metrics_{safe_model}.json")
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
        print(f"\n✓ Metriche salvate in: {metrics_file}")

    if args.compare:
        print("\n" + "=" * 70)
        print("CONFRONTO ANNOTATORI: Claude Sonnet vs GPT")
        print("=" * 70)

        comparison = annotator.compare_annotators(df)
        print(f"\nRighe confrontate: {comparison['total_compared']:,}")
        print(f"Accordo totale: {comparison['agreement']:,} ({comparison['agreement_rate']:.2%})")
        print("\nDettaglio accordo:")
        print(f"  Entrambi YES:       {comparison['both_yes']:7d}")
        print(f"  Entrambi NO:        {comparison['both_no']:7d}")
        print(f"  Sonnet YES, GPT NO: {comparison['sonnet_yes_gpt_no']:7d}")
        print(f"  Sonnet NO, GPT YES: {comparison['sonnet_no_gpt_yes']:7d}")

        comparison_file = args.output_file.replace(".csv", f"_comparison_{safe_model}.json")
        with open(comparison_file, "w", encoding="utf-8") as f:
            json.dump(comparison, f, indent=2)
        print(f"\n✓ Confronto salvato in: {comparison_file}")


if __name__ == "__main__":
    main()