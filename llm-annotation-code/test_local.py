#!/usr/bin/env python3
"""
Test locale rapido - Eseguibile sul TUO computer
Testa 5-10 chunk per verificare che tutto funzioni prima del deployment AWS.
"""

import json
import csv
import sys
from pathlib import Path

print("=" * 70)
print("TEST LOCALE PRELIMINARE")
print("=" * 70)
print()

# Step 1: Verifica config
print("[1/5] Verifica configurazione...")
config_file = Path("config.json")

if not config_file.exists():
    print("✗ ERRORE: config.json non trovato")
    print("  Assicurati di essere nella cartella corretta")
    sys.exit(1)

with open(config_file, 'r') as f:
    config = json.load(f)

api_key = config.get('anthropic_api_key', '')
if not api_key or api_key == 'YOUR_API_KEY_HERE':
    print("✗ ERRORE: API key non configurata in config.json")
    print("  Sostituisci 'YOUR_API_KEY_HERE' con la tua chiave Anthropic")
    sys.exit(1)

print(f"✓ Config OK (API key: {api_key[:20]}...)")

# Step 2: Verifica dipendenze
print()
print("[2/5] Verifica dipendenze...")
try:
    import aiohttp
    print(f"✓ aiohttp {aiohttp.__version__}")
except ImportError:
    print("✗ ERRORE: aiohttp non installato")
    print("  Installa con: pip install aiohttp")
    sys.exit(1)

# Step 3: Verifica file chunk
print()
print("[3/5] Verifica file chunk...")
chunk_dir = Path(config.get('input_dir', './chunk'))

if not chunk_dir.exists():
    print(f"✗ ERRORE: Cartella {chunk_dir} non trovata")
    print(f"  Path cercato: {chunk_dir.absolute()}")
    sys.exit(1)

csv_files = list(chunk_dir.glob("*_chunk.csv"))
if not csv_files:
    print(f"✗ ERRORE: Nessun file CSV trovato in {chunk_dir}")
    print(f"  Contenuto directory:")
    for item in chunk_dir.iterdir():
        print(f"    - {item.name}")
    sys.exit(1)

print(f"✓ Trovati {len(csv_files)} file CSV")

# Step 4: Leggi campione
print()
print("[4/5] Caricamento campione...")
test_file = csv_files[0]
print(f"  File test: {test_file.name}")

chunks = []
with open(test_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i >= 5:  # Solo 5 chunk per test rapido
            break
        chunks.append(row)

print(f"✓ Caricati {len(chunks)} chunk di test")

# Step 5: Test API (se confermi)
print()
print("[5/5] Test chiamata API...")
print()
print("⚠️  ATTENZIONE: Il test farà 5 chiamate API reali")
print(f"   Costo stimato: ~$0.01-0.02")
print()

response = input("Procedere con il test API? (yes/no): ")
if response.lower() != 'yes':
    print()
    print("Test annullato. Configurazione verificata con successo!")
    print()
    print("Quando sei pronto, puoi:")
    print("1. Eseguire questo test con 'yes'")
    print("2. Oppure procedere direttamente al deployment AWS")
    sys.exit(0)

# Esegui test API
print()
print("Esecuzione test API...")
print()

import asyncio

# Import dello script di test
from test_annotate import test_annotation

# Esegui test su 5 chunk
asyncio.run(test_annotation(api_key, config['model'], config['input_dir'], test_chunks=5))

print()
print("=" * 70)
print("Test completato!")
print("=" * 70)
print()
print("Se i risultati sono soddisfacenti, puoi procedere con:")
print("1. Deployment AWS (raccomandato per corpus completo)")
print("2. Esecuzione locale (solo se hai PC sempre acceso)")
print()
