#!/usr/bin/env python3
"""
Script per annotazione automatica del Discorso Indiretto Libero (DIL)
usando GPT-4 tramite API OpenAI.

Replica l'esperimento di valutazione LLM fatto con Claude Sonnet.
"""

import pandas as pd
import openai
import time
import json
from pathlib import Path
from typing import List, Dict
import argparse
from tqdm import tqdm

# ============================================================================
# CONFIGURAZIONE
# ============================================================================

# Prompt sistema e utente per identificazione DIL
SYSTEM_PROMPT = """Sei un esperto linguista. Analizza il testo fornito per identificare la presenza di discorso indiretto libero."""

USER_PROMPT_TEMPLATE = """Analizza il seguente blocco di testo e determina se contiene discorso indiretto libero (anche parzialmente).

Discorso indiretto libero: Rappresentazione del pensiero/discorso di un personaggio senza verbi dichiarativi ('pensò', 'disse'). Caratteristiche:
* Terza persona
* Assenza di formule introduttive esplicite
* Punto di vista del personaggio
* Può includere interiezioni, esclamazioni, interrogative
* Lessico coerente con il personaggio

Esempi:
* 'Mario guardò l'orologio. Sempre in ritardo, come al solito.'
* 'Che assurdità! Marta lo aveva davvero lasciato.'

Testo da analizzare: {testo_blocco}

Rispondi solo: YES (se presente discorso indiretto libero) o NO (se assente).

Risposta:"""


# ============================================================================
# CLASSE PRINCIPALE
# ============================================================================

class DILAnnotator:
    """Annotatore automatico per Discorso Indiretto Libero usando GPT."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        batch_size: int = 100,
        temperature: float = 0.0,
        max_retries: int = 3
    ):
        """
        Inizializza l'annotatore.

        Args:
            api_key: Chiave API OpenAI
            model: Modello GPT da usare (gpt-4, gpt-4-turbo, gpt-3.5-turbo)
            batch_size: Numero di righe da processare prima di salvare
            temperature: Temperatura per generazione (0 = deterministico)
            max_retries: Numero massimo di retry per errori API
        """
        openai.api_key = api_key
        self.model = model
        self.batch_size = batch_size
        self.temperature = temperature
        self.max_retries = max_retries

    def analyze_text(self, text: str) -> str:
        """
        Analizza un singolo testo per identificare DIL.

        Args:
            text: Testo da analizzare

        Returns:
            'yes' o 'no'
        """
        prompt = USER_PROMPT_TEMPLATE.format(testo_blocco=text)

        for attempt in range(self.max_retries):
            try:
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=10
                )

                answer = response.choices[0].message.content.strip().lower()

                # Normalizza risposta
                if 'yes' in answer or 'sì' in answer or 'si' in answer:
                    return 'yes'
                elif 'no' in answer:
                    return 'no'
                else:
                    print(f"Warning: risposta ambigua '{answer}', assumo 'no'")
                    return 'no'

            except openai.error.RateLimitError:
                wait_time = 2 ** attempt
                print(f"Rate limit raggiunto, attendo {wait_time}s...")
                time.sleep(wait_time)

            except openai.error.APIError as e:
                print(f"Errore API (tentativo {attempt+1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2)
                else:
                    raise

        return 'no'  # Default in caso di errori persistenti

    def annotate_corpus(
        self,
        input_file: str,
        output_file: str,
        text_column: str = 'text',
        resume: bool = True
    ) -> pd.DataFrame:
        """
        Annota l'intero corpus.

        Args:
            input_file: Path al file CSV di input
            output_file: Path al file CSV di output
            text_column: Nome colonna contenente il testo
            resume: Se True, riprende da dove si era fermato

        Returns:
            DataFrame annotato
        """
        # Carica input
        df = pd.read_csv(input_file, encoding='utf-8')
        print(f"Corpus caricato: {len(df):,} righe")

        # Crea colonna per annotazioni se non esiste
        annotation_col = f'DIL_{self.model.replace("-", "_")}'

        # Resume: carica progresso precedente
        if resume and Path(output_file).exists():
            df_existing = pd.read_csv(output_file, encoding='utf-8')
            if annotation_col in df_existing.columns:
                df[annotation_col] = df_existing[annotation_col]
                already_done = df[annotation_col].notna().sum()
                print(f"Ripresa da file esistente: {already_done:,} righe già annotate")
        else:
            df[annotation_col] = ''

        # Identifica righe da processare
        mask_todo = (df[annotation_col] == '') | df[annotation_col].isna()
        indices_todo = df[mask_todo].index.tolist()

        if not indices_todo:
            print("Tutte le righe sono già annotate!")
            return df

        print(f"Righe da processare: {len(indices_todo):,}")

        # Processa in batch con progress bar
        for i in tqdm(range(0, len(indices_todo), self.batch_size),
                      desc="Batch"):
            batch_indices = indices_todo[i:i + self.batch_size]

            for idx in tqdm(batch_indices, desc=f"Batch {i//self.batch_size + 1}",
                           leave=False):
                text = str(df.at[idx, text_column])
                annotation = self.analyze_text(text)
                df.at[idx, annotation_col] = annotation

                # Piccolo delay per evitare rate limiting
                time.sleep(0.1)

            # Salva dopo ogni batch
            df.to_csv(output_file, index=False, encoding='utf-8')
            print(f"✓ Salvato batch (completate {i + len(batch_indices):,}/{len(indices_todo):,} righe)")

        print(f"\n✓ Annotazione completata!")
        return df

    def compute_metrics(
        self,
        df: pd.DataFrame,
        gold_column: str = 'DIL',
        pred_column: str = None
    ) -> Dict:
        """
        Calcola metriche di performance rispetto ad annotazioni gold.

        Args:
            df: DataFrame con annotazioni
            gold_column: Nome colonna con annotazioni gold standard
            pred_column: Nome colonna con predizioni (default: DIL_{model})

        Returns:
            Dict con metriche
        """
        if pred_column is None:
            pred_column = f'DIL_{self.model.replace("-", "_")}'

        # Rimuovi righe senza predizione
        df_eval = df.dropna(subset=[pred_column, gold_column])

        # Calcola metriche
        tp = len(df_eval[(df_eval[gold_column] == 'yes') & (df_eval[pred_column] == 'yes')])
        tn = len(df_eval[(df_eval[gold_column] == 'no') & (df_eval[pred_column] == 'no')])
        fp = len(df_eval[(df_eval[gold_column] == 'no') & (df_eval[pred_column] == 'yes')])
        fn = len(df_eval[(df_eval[gold_column] == 'yes') & (df_eval[pred_column] == 'no')])

        accuracy = (tp + tn) / len(df_eval) if len(df_eval) > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        return {
            'total': len(df_eval),
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'true_positives': tp,
            'true_negatives': tn,
            'false_positives': fp,
            'false_negatives': fn
        }


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Annotazione automatica DIL con GPT'
    )
    parser.add_argument(
        'input_file',
        help='File CSV di input con i testi da annotare'
    )
    parser.add_argument(
        'output_file',
        help='File CSV di output con annotazioni'
    )
    parser.add_argument(
        '--api-key',
        required=True,
        help='Chiave API OpenAI'
    )
    parser.add_argument(
        '--model',
        default='gpt-4',
        choices=['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'],
        help='Modello GPT da usare'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Numero righe per batch (salvataggio intermedio)'
    )
    parser.add_argument(
        '--text-column',
        default='text',
        help='Nome colonna contenente il testo'
    )
    parser.add_argument(
        '--no-resume',
        action='store_true',
        help='Non riprendere da file esistente'
    )
    parser.add_argument(
        '--eval',
        action='store_true',
        help='Calcola metriche vs annotazioni gold (colonna DIL)'
    )

    args = parser.parse_args()

    # Inizializza annotatore
    annotator = DILAnnotator(
        api_key=args.api_key,
        model=args.model,
        batch_size=args.batch_size
    )

    print("="*70)
    print("ANNOTAZIONE AUTOMATICA DISCORSO INDIRETTO LIBERO")
    print("="*70)
    print(f"Modello: {args.model}")
    print(f"Input: {args.input_file}")
    print(f"Output: {args.output_file}")
    print(f"Batch size: {args.batch_size}")
    print("="*70)

    # Annota corpus
    df = annotator.annotate_corpus(
        input_file=args.input_file,
        output_file=args.output_file,
        text_column=args.text_column,
        resume=not args.no_resume
    )

    # Valutazione (opzionale)
    if args.eval:
        print("\n" + "="*70)
        print("VALUTAZIONE PERFORMANCE")
        print("="*70)

        metrics = annotator.compute_metrics(df)

        print(f"\nRighe valutate: {metrics['total']:,}")
        print(f"\nAccuracy:  {metrics['accuracy']:.2%}")
        print(f"Precision: {metrics['precision']:.2%}")
        print(f"Recall:    {metrics['recall']:.2%}")
        print(f"F1-Score:  {metrics['f1_score']:.2%}")

        print(f"\nMatrice di confusione:")
        print(f"{'':12s} | Pred NO | Pred YES")
        print(f"{'-'*35}")
        print(f"Gold NO      | {metrics['true_negatives']:7d} | {metrics['false_positives']:8d}")
        print(f"Gold YES     | {metrics['false_negatives']:7d} | {metrics['true_positives']:8d}")

        # Salva metriche
        metrics_file = args.output_file.replace('.csv', '_metrics.json')
        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2)
        print(f"\n✓ Metriche salvate in: {metrics_file}")


if __name__ == '__main__':
    main()
