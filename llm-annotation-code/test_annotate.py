#!/usr/bin/env python3
"""
Script di test per validare l'annotazione su un campione ridotto.
Usa solo i primi N chunk del primo file per verificare:
- Connessione API
- Qualità delle risposte
- Costi effettivi
- Performance
"""

import asyncio
import aiohttp
import csv
import json
import time
from pathlib import Path

# Usa gli stessi prompt dello script principale
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


async def test_annotation(api_key: str, model: str, input_dir: str, test_chunks: int = 50):
    """Testa annotazione su un campione."""

    print("=" * 70)
    print(f"TEST ANNOTAZIONE DIL - {test_chunks} chunk")
    print("=" * 70)
    print()

    # Trova primo file
    input_path = Path(input_dir)
    csv_files = sorted(list(input_path.glob("*_chunk.csv")))

    if not csv_files:
        print(f"ERRORE: Nessun file CSV trovato in {input_path}")
        print(f"Path assoluto cercato: {input_path.absolute()}")
        print(f"Path esiste: {input_path.exists()}")
        if input_path.exists():
            print(f"Contenuto directory:")
            for item in input_path.iterdir():
                print(f"  - {item.name}")
        return

    test_file = csv_files[0]
    print(f"File di test: {test_file.name}")

    # Leggi primi N chunk
    chunks = []
    with open(test_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= test_chunks:
                break
            chunks.append(row)

    print(f"Chunk da testare: {len(chunks)}")
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
    results = []

    # Processa chunk sequenzialmente per test
    async with aiohttp.ClientSession() as session:
        for i, chunk_data in enumerate(chunks, 1):
            chunk_text = chunk_data['chunk']

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

                        # Normalizza
                        if 'YES' in response:
                            annotation = 'YES'
                        elif 'NO' in response:
                            annotation = 'NO'
                        else:
                            annotation = 'UNCLEAR'

                        results.append({
                            'chunk_preview': chunk_text[:100] + '...',
                            'annotation': annotation,
                            'raw_response': response
                        })

                        print(f"[{i}/{len(chunks)}] {annotation}", end='\r')

                    else:
                        error = await resp.text()
                        print(f"\nERRORE API [{resp.status}]: {error}")
                        return

            except Exception as e:
                print(f"\nERRORE: {e}")
                return

    elapsed = time.time() - start_time

    # Calcola costi
    input_cost = (input_tokens / 1_000_000) * 3.00
    output_cost = (output_tokens / 1_000_000) * 15.00
    total_cost = input_cost + output_cost

    # Report
    print()
    print()
    print("=" * 70)
    print("RISULTATI TEST")
    print("=" * 70)
    print(f"Chunk processati: {len(results)}")
    print(f"Tempo totale: {elapsed:.1f}s")
    print(f"Tempo medio per chunk: {elapsed/len(results):.2f}s")
    print(f"Throughput: {len(results)/elapsed*60:.1f} chunk/min")
    print()
    print(f"Input tokens: {input_tokens:,}")
    print(f"Output tokens: {output_tokens:,}")
    print(f"Token medi per chunk: {input_tokens/len(results):.0f} input + {output_tokens/len(results):.0f} output")
    print()
    print(f"Costo test: ${total_cost:.4f}")
    print(f"Costo stimato per corpus completo: ${total_cost * (536676/len(results)):.2f}")
    print()

    # Distribuzione annotazioni
    yes_count = sum(1 for r in results if r['annotation'] == 'YES')
    no_count = sum(1 for r in results if r['annotation'] == 'NO')
    unclear_count = sum(1 for r in results if r['annotation'] == 'UNCLEAR')

    print(f"Distribuzione annotazioni:")
    print(f"  YES: {yes_count} ({yes_count/len(results)*100:.1f}%)")
    print(f"  NO: {no_count} ({no_count/len(results)*100:.1f}%)")
    print(f"  UNCLEAR: {unclear_count} ({unclear_count/len(results)*100:.1f}%)")
    print()

    # Mostra alcuni esempi
    print("Esempi di annotazioni:")
    print("-" * 70)
    for i, result in enumerate(results[:5], 1):
        print(f"\n{i}. {result['annotation']}")
        print(f"   Chunk: {result['chunk_preview']}")
        print(f"   Risposta: {result['raw_response']}")

    print()
    print("=" * 70)
    print(f"Credito rimanente stimato: ${5.00 - total_cost:.4f}")
    print("=" * 70)


async def main():
    """Entry point."""
    # Cerca config.json nella directory corrente
    config_path = Path("config.json")

    if not config_path.exists():
        print("ERRORE: config.json non trovato nella directory corrente")
        print(f"Directory corrente: {Path.cwd()}")
        print("\nAssicurati di eseguire lo script dalla cartella che contiene:")
        print("  - config.json")
        print("  - chunk/ (cartella con i file CSV)")
        return

    with open(config_path, 'r') as f:
        config = json.load(f)

    api_key = config['anthropic_api_key']
    model = config['model']
    input_dir = config['input_dir']

    if api_key == 'YOUR_API_KEY_HERE':
        print("ERRORE: Configura API key in config.json")
        return

    # Info directory
    print(f"Directory input: {input_dir}")
    print()

    # Chiedi numero chunk da testare
    print("Quanti chunk vuoi testare? (consigliato: 50-100)")
    print(f"Stima costo per 50 chunk: ~$0.02-0.05")
    print(f"Stima costo per 100 chunk: ~$0.05-0.10")
    print()

    try:
        test_chunks = int(input("Numero chunk da testare (default 50): ") or "50")
    except ValueError:
        test_chunks = 50

    print()
    await test_annotation(api_key, model, input_dir, test_chunks)


if __name__ == "__main__":
    asyncio.run(main())
