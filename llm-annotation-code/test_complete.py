#!/usr/bin/env python3
"""
Test completo con scrittura output CSV.
Annota un file completo e salva il risultato in chunk_annotated_test/.
"""

import asyncio
import aiohttp
import csv
import json
import time
from pathlib import Path

# Prompt templates
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


async def annotate_file(api_key: str, model: str, input_file: Path, output_file: Path, max_chunks: int = None):
    """Annota un file CSV e salva l'output."""

    print("=" * 70)
    print("TEST COMPLETO CON OUTPUT CSV")
    print("=" * 70)
    print()
    print(f"File input:  {input_file.name}")
    print(f"File output: {output_file}")
    print()

    # Leggi file input
    rows = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if max_chunks and i >= max_chunks:
                break
            rows.append(row)

    print(f"Chunk da annotare: {len(rows)}")
    print()

    # Setup API
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    # Statistiche
    start_time = time.time()
    input_tokens = 0
    output_tokens = 0
    annotations = []

    # Annota chunk
    print("Annotazione in corso...")
    async with aiohttp.ClientSession() as session:
        for i, row in enumerate(rows, 1):
            chunk_text = row['chunk']

            prompt = USER_PROMPT_TEMPLATE.format(testo_blocco=chunk_text)
            payload = {
                "model": model,
                "max_tokens": 10,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": prompt}]
            }

            try:
                async with session.post(url, headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        response = data['content'][0]['text'].strip().upper()

                        usage = data.get('usage', {})
                        input_tokens += usage.get('input_tokens', 0)
                        output_tokens += usage.get('output_tokens', 0)

                        # Normalizza risposta
                        if 'YES' in response:
                            annotation = 'YES'
                        elif 'NO' in response:
                            annotation = 'NO'
                        else:
                            annotation = 'UNCLEAR'

                        annotations.append(annotation)
                        print(f"[{i}/{len(rows)}] {annotation}", end='\r')

                    else:
                        error = await resp.text()
                        print(f"\nERRORE API [{resp.status}]: {error}")
                        # In caso di errore, marca come ERROR
                        annotations.append('ERROR')

            except Exception as e:
                print(f"\nERRORE chunk {i}: {e}")
                annotations.append('ERROR')

    elapsed = time.time() - start_time
    print()
    print()

    # Aggiungi campo DIL alle righe
    for row, annotation in zip(rows, annotations):
        row['DIL'] = annotation

    # Scrivi file output
    print(f"Scrittura file output: {output_file}")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        # Le colonne sono quelle originali + DIL
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✓ File salvato: {output_file}")
    print()

    # Statistiche
    input_cost = (input_tokens / 1_000_000) * 3.00
    output_cost = (output_tokens / 1_000_000) * 15.00
    total_cost = input_cost + output_cost

    yes_count = annotations.count('YES')
    no_count = annotations.count('NO')
    unclear_count = annotations.count('UNCLEAR')
    error_count = annotations.count('ERROR')

    print("=" * 70)
    print("RISULTATI")
    print("=" * 70)
    print(f"Chunk annotati: {len(rows)}")
    print(f"Tempo totale: {elapsed:.1f}s")
    print(f"Tempo medio: {elapsed/len(rows):.2f}s per chunk")
    print()
    print(f"Distribuzione annotazioni:")
    print(f"  YES:     {yes_count:4d} ({yes_count/len(rows)*100:5.1f}%)")
    print(f"  NO:      {no_count:4d} ({no_count/len(rows)*100:5.1f}%)")
    print(f"  UNCLEAR: {unclear_count:4d} ({unclear_count/len(rows)*100:5.1f}%)")
    print(f"  ERROR:   {error_count:4d} ({error_count/len(rows)*100:5.1f}%)")
    print()
    print(f"Costo test: ${total_cost:.4f}")
    print()
    print("=" * 70)

    # Mostra prime righe output
    print()
    print("ANTEPRIMA OUTPUT (prime 5 righe):")
    print("-" * 70)
    with open(output_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            if i > 5:
                break
            print(f"\nRiga {i}:")
            print(f"  Titolo: {row['titolo']}")
            print(f"  Chunk: {row['chunk'][:80]}...")
            print(f"  DIL: {row['DIL']}")

    print()
    print("=" * 70)
    print(f"File completo disponibile in: {output_file}")
    print("=" * 70)


async def main():
    """Entry point."""
    # Carica config
    config_path = Path("config.json")

    if not config_path.exists():
        print("ERRORE: config.json non trovato")
        print(f"Directory corrente: {Path.cwd()}")
        return

    with open(config_path, 'r') as f:
        config = json.load(f)

    api_key = config['anthropic_api_key']
    model = config['model']
    input_dir = Path(config['input_dir'])

    if api_key == 'YOUR_API_KEY_HERE':
        print("ERRORE: Configura API key in config.json")
        return

    # Trova file CSV
    csv_files = sorted(list(input_dir.glob("*_chunk.csv")))

    if not csv_files:
        print(f"ERRORE: Nessun file CSV in {input_dir}")
        return

    # Usa il file più piccolo per il test (meno chunk = più veloce)
    file_sizes = []
    for csv_file in csv_files[:10]:  # Controlla primi 10 file
        with open(csv_file, 'r') as f:
            num_rows = sum(1 for _ in f) - 1  # -1 per header
            file_sizes.append((csv_file, num_rows))

    # Ordina per dimensione
    file_sizes.sort(key=lambda x: x[1])
    smallest_file, num_chunks = file_sizes[0]

    print()
    print(f"File più piccolo trovato: {smallest_file.name}")
    print(f"Numero di chunk nel file: {num_chunks}")
    print()

    # Chiedi conferma e numero chunk
    print("Opzioni:")
    print(f"  1. Annota TUTTO il file ({num_chunks} chunk, ~${num_chunks * 0.004:.2f})")
    print(f"  2. Annota solo primi N chunk (personalizzabile)")
    print()

    choice = input("Scelta (1/2, default 2): ").strip() or "2"

    if choice == "1":
        max_chunks = None
        estimated_cost = num_chunks * 0.004
    else:
        try:
            max_chunks = int(input(f"Quanti chunk annotare? (max {num_chunks}, consigliato 50-100): ") or "50")
            max_chunks = min(max_chunks, num_chunks)
            estimated_cost = max_chunks * 0.004
        except ValueError:
            max_chunks = 50
            estimated_cost = max_chunks * 0.004

    print()
    print(f"Annotazione: {max_chunks if max_chunks else num_chunks} chunk")
    print(f"Costo stimato: ~${estimated_cost:.2f}")
    print()

    confirm = input("Procedere? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Annullato.")
        return

    # Prepara file output
    output_dir = Path("./chunk_annotated_test")
    output_file = output_dir / smallest_file.name.replace('_chunk.csv', '_annotated_test.csv')

    print()
    await annotate_file(api_key, model, smallest_file, output_file, max_chunks)


if __name__ == "__main__":
    asyncio.run(main())
