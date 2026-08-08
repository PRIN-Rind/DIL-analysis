#!/usr/bin/env python3
"""
Calcolo metriche e comparazione - Esperimento V2
Elabora tutti i CSV annotati in 03_llm_annotated_csv/ e produce:
  - metrics_v2_summary.csv        (una riga per condizione modello×prompt)
  - metrics_v2_summary.json       (stesso contenuto in JSON)
  - confusion_matrices_v2.png     (griglia di confusion matrices)
  - metrics_v2_heatmap.png        (heatmap accuracy/F1/kappa per condizione)
  - inter_session_agreement.csv   (Cohen's κ tra run diversi dello stesso modello)

Uso:
    python compute_metrics_v2.py

Dipendenze: pip install pandas scikit-learn matplotlib seaborn
"""

import json
import re
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    cohen_kappa_score,
)

# ---------------------------------------------------------------------------
# Percorsi
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.parent
CSV_DIR  = BASE_DIR / "annotations"
OUT_DIR  = BASE_DIR / "results"
OUT_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

# Mappa: prefisso colonna → etichetta leggibile per le tabelle
LABEL_MAP = {
    "claude_sonnet46": "Claude Sonnet 4.6",
    "gpt55":           "GPT-5.5",
    "gemini35flash":   "Gemini 3.5 Flash",
    "qwen3_35b":       "Qwen3-35B-A3B",
    "gpt_oss_120b":    "GPT-OSS-120B",
}

# Modelli da escludere dall'analisi comparativa (bias sistematico, risultati non utilizzabili)
EXCLUDE_MODELS = {"minerva7b"}

BASELINE_LABEL = "DIL"  # colonna baseline umana nel CSV
GOLD_LABEL = BASELINE_LABEL  # alias mantenuto per compatibilità interna


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def binarize(series: pd.Series) -> pd.Series:
    """Converte yes/no in 1/0; tutto il resto → NaN."""
    return series.map({"yes": 1, "no": 0})


def compute_metrics(y_true: pd.Series, y_pred: pd.Series) -> dict:
    # Rimuove righe con valori mancanti o errori
    mask  = y_true.notna() & y_pred.notna()
    yt    = y_true[mask].astype(int)
    yp    = y_pred[mask].astype(int)
    n_valid = int(mask.sum())
    n_error = int((~mask).sum())

    if len(yt) == 0:
        return {"error": "Nessun dato valido"}

    tn, fp, fn, tp = confusion_matrix(yt, yp, labels=[0, 1]).ravel()
    specificity = tn / (tn + fp) if (tn + fp) > 0 else float("nan")

    return {
        "n_total":    n_valid + n_error,
        "n_valid":    n_valid,
        "n_error":    n_error,
        "accuracy":   round(accuracy_score(yt, yp), 4),
        "precision":  round(precision_score(yt, yp, zero_division=0), 4),
        "recall":     round(recall_score(yt, yp, zero_division=0), 4),
        "f1":         round(f1_score(yt, yp, zero_division=0), 4),
        "specificity": round(specificity, 4),
        "kappa":      round(cohen_kappa_score(yt, yp), 4),
        "TP": int(tp), "FP": int(fp), "FN": int(fn), "TN": int(tn),
    }


def detect_annotation_columns(df: pd.DataFrame) -> list[tuple[str, str, str]]:
    """
    Rileva le colonne DIL_<model>_prompt<X> e restituisce una lista di tuple
    (col_name, model_key, prompt_id). I modelli in EXCLUDE_MODELS vengono omessi.
    """
    results = []
    pattern = re.compile(r"^DIL_(.+)_prompt([ABC])$")
    for col in df.columns:
        m = pattern.match(col)
        if m:
            model_key = m.group(1)
            if model_key in EXCLUDE_MODELS:
                log.info(f"Modello escluso dall'analisi: {model_key}")
                continue
            results.append((col, model_key, m.group(2)))
    return results


def load_all_annotations() -> pd.DataFrame:
    """
    Carica tutti i CSV annotati, effettua il merge sul testo e restituisce
    un unico DataFrame con una colonna per ogni condizione.
    """
    csv_files = sorted(CSV_DIR.glob("*_annotated.csv"))
    if not csv_files:
        raise FileNotFoundError(f"Nessun file annotato in {CSV_DIR}")

    log.info(f"Trovati {len(csv_files)} file annotati:")
    for f in csv_files:
        log.info(f"  {f.name}")

    # Carica il primo come base
    base = pd.read_csv(csv_files[0])
    # Mantieni solo le colonne strutturali + gold standard
    base_cols = [c for c in base.columns
                 if not c.startswith("DIL_") and not c.startswith("confidence_")]
    merged = base[base_cols].copy()

    for f in csv_files:
        df = pd.read_csv(f)
        ann_cols = [c for c in df.columns
                    if c.startswith("DIL_") or c.startswith("confidence_")]
        if ann_cols:
            merged = merged.merge(
                df[["text"] + ann_cols],
                on="text",
                how="left",
                suffixes=("", f"_dup_{f.stem}"),
            )

    return merged


# ---------------------------------------------------------------------------
# Analisi principale
# ---------------------------------------------------------------------------

def run_analysis(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    gold = binarize(df[BASELINE_LABEL])
    ann_cols = detect_annotation_columns(df)

    if not ann_cols:
        raise ValueError("Nessuna colonna di annotazione rilevata nel dataset.")

    rows = []
    raw  = {}

    for col, model_key, prompt_id in ann_cols:
        pred    = binarize(df[col])
        metrics = compute_metrics(gold, pred)
        model_label = LABEL_MAP.get(model_key, model_key)
        row = {
            "model":       model_label,
            "model_key":   model_key,
            "prompt":      f"Prompt {prompt_id}",
            **metrics,
        }
        rows.append(row)
        raw[f"{model_key}_prompt{prompt_id}"] = metrics
        log.info(f"{model_label} / Prompt {prompt_id}: acc={metrics.get('accuracy')} κ={metrics.get('kappa')}")

    summary = pd.DataFrame(rows)
    return summary, raw


# ---------------------------------------------------------------------------
# Inter-session agreement (stesso modello, prompt diversi o stesse condizioni)
# ---------------------------------------------------------------------------

def inter_session_agreement(df: pd.DataFrame) -> pd.DataFrame:
    """Cohen's κ tra ogni coppia di sistemi (indipendentemente dalla baseline)."""
    ann_cols = detect_annotation_columns(df)
    rows     = []

    for i, (col_i, model_i, prompt_i) in enumerate(ann_cols):
        for col_j, model_j, prompt_j in ann_cols[i+1:]:
            pred_i = binarize(df[col_i])
            pred_j = binarize(df[col_j])
            mask   = pred_i.notna() & pred_j.notna()
            if mask.sum() < 10:
                continue
            try:
                kappa = cohen_kappa_score(
                    pred_i[mask].astype(int),
                    pred_j[mask].astype(int),
                )
            except Exception:
                kappa = float("nan")

            model_i_label = LABEL_MAP.get(model_i, model_i)
            model_j_label = LABEL_MAP.get(model_j, model_j)
            rows.append({
                "system_A": f"{model_i_label} / Prompt {prompt_i}",
                "system_B": f"{model_j_label} / Prompt {prompt_j}",
                "kappa":    round(kappa, 4),
                "n":        int(mask.sum()),
            })

    return pd.DataFrame(rows)


def rank_alignment(summary: pd.DataFrame) -> dict:
    """
    Produce ranking di allineamento con la baseline umana.

    Restituisce un dizionario con:
      - 'best_model':       modello con κ medio più alto (media sui 3 prompt)
      - 'best_prompt':      prompt con κ medio più alto (media su tutti i modelli)
      - 'best_per_model':   per ogni modello, il prompt con κ più alto
      - 'model_ranking':    DataFrame ordinato per κ medio decrescente
      - 'prompt_ranking':   DataFrame ordinato per κ medio decrescente
    """
    # κ medio per modello (media sui 3 prompt)
    model_rank = (
        summary.groupby("model_key")
        .agg(kappa_mean=("kappa", "mean"), kappa_std=("kappa", "std"),
             f1_mean=("f1", "mean"), accuracy_mean=("accuracy", "mean"))
        .reset_index()
    )
    model_rank["model_label"] = model_rank["model_key"].map(
        lambda k: LABEL_MAP.get(k, k)
    )
    model_rank = model_rank.sort_values("kappa_mean", ascending=False)

    # κ medio per prompt (media su tutti i modelli)
    prompt_rank = (
        summary.groupby("prompt")
        .agg(kappa_mean=("kappa", "mean"), kappa_std=("kappa", "std"),
             f1_mean=("f1", "mean"))
        .reset_index()
        .sort_values("kappa_mean", ascending=False)
    )

    # miglior prompt per ogni modello
    best_per_model = {}
    for model_key in summary["model_key"].unique():
        sub = summary[summary["model_key"] == model_key]
        best_row = sub.loc[sub["kappa"].idxmax()]
        best_per_model[LABEL_MAP.get(model_key, model_key)] = {
            "prompt":   best_row["prompt"],
            "kappa":    round(best_row["kappa"], 4),
            "f1":       round(best_row["f1"], 4),
            "accuracy": round(best_row["accuracy"], 4),
        }

    best_model  = LABEL_MAP.get(model_rank.iloc[0]["model_key"], model_rank.iloc[0]["model_key"])
    best_prompt = prompt_rank.iloc[0]["prompt"]

    return {
        "best_model":      best_model,
        "best_model_kappa": round(model_rank.iloc[0]["kappa_mean"], 4),
        "best_prompt":     best_prompt,
        "best_prompt_kappa": round(prompt_rank.iloc[0]["kappa_mean"], 4),
        "best_per_model":  best_per_model,
        "model_ranking":   model_rank,
        "prompt_ranking":  prompt_rank,
    }


# ---------------------------------------------------------------------------
# Visualizzazioni
# ---------------------------------------------------------------------------

def plot_confusion_matrices(df: pd.DataFrame, summary: pd.DataFrame, out_path: Path):
    gold     = binarize(df[GOLD_LABEL])
    ann_cols = detect_annotation_columns(df)
    n        = len(ann_cols)
    ncols    = 3
    nrows    = (n + ncols - 1) // ncols

    fig, axes = plt.subplots(nrows, ncols, figsize=(ncols * 4, nrows * 3.5))
    axes = axes.flatten() if n > 1 else [axes]

    for i, (col, model_key, prompt_id) in enumerate(ann_cols):
        pred = binarize(df[col])
        mask = gold.notna() & pred.notna()
        yt   = gold[mask].astype(int)
        yp   = pred[mask].astype(int)

        cm = confusion_matrix(yt, yp, labels=[0, 1])
        model_label = LABEL_MAP.get(model_key, model_key)

        row_summary = summary[
            (summary["model_key"] == model_key) & (summary["prompt"] == f"Prompt {prompt_id}")
        ]
        acc   = row_summary["accuracy"].values[0]  if len(row_summary) else "?"
        kappa = row_summary["kappa"].values[0]     if len(row_summary) else "?"

        sns.heatmap(
            cm, annot=True, fmt="d", cmap="Blues",
            xticklabels=["pred: no", "pred: yes"],
            yticklabels=["gold: no", "gold: yes"],
            ax=axes[i], cbar=False,
        )
        axes[i].set_title(
            f"{model_label}\nPrompt {prompt_id} | acc={acc} κ={kappa}",
            fontsize=9,
        )

    # Nascondi assi vuoti
    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)

    plt.suptitle("Confusion Matrices — Esperimento V2", fontsize=12, y=1.01)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"Confusion matrices salvate: {out_path}")


def plot_heatmap(summary: pd.DataFrame, out_path: Path):
    pivot = summary.pivot_table(
        index="model", columns="prompt", values="accuracy"
    )
    plt.figure(figsize=(7, max(3, len(pivot) * 0.8)))
    sns.heatmap(
        pivot, annot=True, fmt=".3f", cmap="YlGn",
        linewidths=0.5, linecolor="white", vmin=0.5, vmax=1.0,
    )
    plt.title("Accuracy per modello e prompt — Esperimento V2")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"Heatmap salvata: {out_path}")


def plot_kappa_heatmap(summary: pd.DataFrame, out_path: Path):
    pivot = summary.pivot_table(
        index="model", columns="prompt", values="kappa"
    )
    plt.figure(figsize=(7, max(3, len(pivot) * 0.8)))
    sns.heatmap(
        pivot, annot=True, fmt=".3f", cmap="RdYlGn",
        linewidths=0.5, linecolor="white", vmin=-0.2, vmax=0.8,
    )
    plt.title("Cohen's κ per modello e prompt — Esperimento V2")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"Heatmap κ salvata: {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("Caricamento annotazioni…")
    df = load_all_annotations()
    log.info(f"Dataset unificato: {len(df)} righe, {len(df.columns)} colonne")

    log.info("Calcolo metriche di allineamento con la baseline umana…")
    summary, raw = run_analysis(df)

    summary_path = OUT_DIR / "metrics_v2_summary.csv"
    summary.to_csv(summary_path, index=False)
    log.info(f"Metriche salvate: {summary_path}")

    json_path = OUT_DIR / "metrics_v2_summary.json"
    json_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False))
    log.info(f"Metriche JSON: {json_path}")

    log.info("Calcolo inter-system agreement…")
    isa = inter_session_agreement(df)
    isa_path = OUT_DIR / "inter_session_agreement_v2.csv"
    isa.to_csv(isa_path, index=False)
    log.info(f"Inter-system agreement: {isa_path}")

    log.info("Calcolo ranking di allineamento…")
    ranking = rank_alignment(summary)
    ranking_path = OUT_DIR / "alignment_ranking_v2.json"
    ranking_export = {
        "best_model":         ranking["best_model"],
        "best_model_kappa":   ranking["best_model_kappa"],
        "best_prompt":        ranking["best_prompt"],
        "best_prompt_kappa":  ranking["best_prompt_kappa"],
        "best_per_model":     ranking["best_per_model"],
    }
    ranking_path.write_text(json.dumps(ranking_export, indent=2, ensure_ascii=False))
    log.info(f"Ranking salvato: {ranking_path}")

    log.info("Generazione grafici…")
    plot_confusion_matrices(df, summary, OUT_DIR / "confusion_matrices_v2.png")
    plot_heatmap(summary, OUT_DIR / "accuracy_heatmap_v2.png")
    plot_kappa_heatmap(summary, OUT_DIR / "kappa_heatmap_v2.png")

    # ── Output a terminale ──────────────────────────────────────────────────
    SEP = "=" * 72

    print(f"\n{SEP}")
    print("RIEPILOGO METRICHE DI ALLINEAMENTO — Esperimento V2")
    print("(misura la convergenza di ogni sistema con la baseline umana)")
    print(SEP)
    cols_display = ["model", "prompt", "accuracy", "precision", "recall",
                    "f1", "specificity", "kappa", "n_error"]
    print(summary[cols_display].to_string(index=False))

    print(f"\n{SEP}")
    print("RANKING MODELLI — allineamento medio con la baseline (κ medio su 3 prompt)")
    print(SEP)
    mr = ranking["model_ranking"][["model_label", "kappa_mean", "kappa_std",
                                    "f1_mean", "accuracy_mean"]]
    mr.columns = ["modello", "κ_medio", "κ_std", "F1_medio", "acc_media"]
    print(mr.to_string(index=False))

    print(f"\n{SEP}")
    print("RANKING PROMPT — allineamento medio con la baseline (κ medio su tutti i modelli)")
    print(SEP)
    pr = ranking["prompt_ranking"][["prompt", "kappa_mean", "kappa_std", "f1_mean"]]
    pr.columns = ["prompt", "κ_medio", "κ_std", "F1_medio"]
    print(pr.to_string(index=False))

    print(f"\n{SEP}")
    print("MIGLIOR PROMPT PER OGNI MODELLO")
    print(SEP)
    for model_label, info in ranking["best_per_model"].items():
        print(f"  {model_label:<22}  {info['prompt']}  "
              f"κ={info['kappa']:.4f}  F1={info['f1']:.4f}  acc={info['accuracy']:.4f}")

    print(f"\n{SEP}")
    print("RACCOMANDAZIONE OPERATIVA")
    print(SEP)
    print(f"  Modello con maggiore allineamento alla baseline:  "
          f"{ranking['best_model']}  (κ medio = {ranking['best_model_kappa']:.4f})")
    print(f"  Prompt con maggiore allineamento alla baseline:   "
          f"{ranking['best_prompt']}  (κ medio = {ranking['best_prompt_kappa']:.4f})")
    print()

    print(f"\n{SEP}")
    print("INTER-SYSTEM AGREEMENT (κ tra coppie di sistemi)")
    print(SEP)
    if not isa.empty:
        print(isa.sort_values("kappa", ascending=False).to_string(index=False))
    else:
        print("(nessun dato disponibile)")

    log.info("Analisi completata.")


if __name__ == "__main__":
    main()
