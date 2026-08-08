#!/usr/bin/env python3
"""
Script per annotazione automatica del Discorso Indiretto Libero (DIL)
usando Claude Sonnet 4.5 via API Anthropic.
"""

import asyncio
import aiohttp
import csv
import json
import logging
import os
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from datetime import datetime

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


@dataclass
class AnnotationState:
    """Stato dell'annotazione per checkpoint/resume."""
    total_chunks: int = 0
    processed_chunks: int = 0
    failed_chunks: int = 0
    current_file: str = ""
    completed_files: List[str] = None
    start_time: str = ""
    total_cost: float = 0.0

    def __post_init__(self):
        if self.completed_files is None:
            self.completed_files = []


class DILAnnotator:
    """Annotatore per identificazione DIL con API Anthropic."""

    def __init__(self, config_path: str = "config.json"):
        """Inizializza annotatore."""
        # Carica configurazione
        with open(config_path, 'r') as f:
            self.config = json.load(f)

        self.api_key = self.config['anthropic_api_key']
        self.model = self.config['model']
        self.max_concurrent = self.config['max_concurrent_requests']
        self.max_retries = self.config['max_retries']
        self.retry_delay = self.config['retry_delay']
        self.checkpoint_interval = self.config['checkpoint_interval']

        self.input_dir = Path(self.config['input_dir'])
        self.output_dir = Path(self.config['output_dir'])
        self.state_file = Path(self.config['state_file'])

        # Crea directory output
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config['log_file']),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        # Carica o inizializza stato
        self.state = self._load_state()

        # Statistiche sessione
        self.session_start = time.time()
        self.requests_made = 0
        self.input_tokens = 0
        self.output_tokens = 0

        # Pricing ($/MTok)
        self.input_price = 3.00
        self.output_price = 15.00

    def _load_state(self) -> AnnotationState:
        """Carica stato da file o crea nuovo."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                state = AnnotationState(**data)
                self.logger.info(f"Ripresa da checkpoint: {state.processed_chunks}/{state.total_chunks} chunk")
                return state
        else:
            state = AnnotationState(start_time=datetime.now().isoformat())
            self.logger.info("Nuova sessione di annotazione")
            return state

    def _save_state(self):
        """Salva stato corrente."""
        with open(self.state_file, 'w') as f:
            json.dump(asdict(self.state), f, indent=2)

    async def _call_api(self, session: aiohttp.ClientSession, chunk_text: str) -> Optional[str]:
        """Chiama API Anthropic per annotare un chunk."""
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        prompt = USER_PROMPT_TEMPLATE.format(testo_blocco=chunk_text)

        payload = {
            "model": self.model,
            "max_tokens": 10,  # Solo "YES" o "NO"
            "system": SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        for attempt in range(self.max_retries):
            try:
                async with session.post(url, headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()

                        # Estrai risposta
                        response_text = data['content'][0]['text'].strip().upper()

                        # Traccia token usage
                        usage = data.get('usage', {})
                        self.input_tokens += usage.get('input_tokens', 0)
                        self.output_tokens += usage.get('output_tokens', 0)

                        # Normalizza risposta
                        if 'YES' in response_text:
                            return 'YES'
                        elif 'NO' in response_text:
                            return 'NO'
                        else:
                            self.logger.warning(f"Risposta ambigua: {response_text}")
                            return 'UNCLEAR'

                    elif resp.status == 429:
                        # Rate limit
                        retry_after = int(resp.headers.get('retry-after', self.retry_delay * (attempt + 1)))
                        self.logger.warning(f"Rate limit hit, retry dopo {retry_after}s")
                        await asyncio.sleep(retry_after)

                    else:
                        error_text = await resp.text()
                        self.logger.error(f"API error {resp.status}: {error_text}")
                        await asyncio.sleep(self.retry_delay * (attempt + 1))

            except Exception as e:
                self.logger.error(f"Errore chiamata API (tentativo {attempt + 1}/{self.max_retries}): {e}")
                await asyncio.sleep(self.retry_delay * (attempt + 1))

        # Fallito dopo tutti i retry
        return None

    async def _process_file(self, csv_file: Path, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore):
        """Processa un singolo file CSV."""
        output_file = self.output_dir / csv_file.name

        # Skip se già completato
        if csv_file.name in self.state.completed_files:
            self.logger.info(f"Skip {csv_file.name} (già completato)")
            return

        self.state.current_file = csv_file.name
        self.logger.info(f"Processando {csv_file.name}...")

        # Leggi file input
        rows = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Processa chunk
        tasks = []
        for row in rows:
            chunk_text = row['chunk']
            tasks.append(self._annotate_chunk(session, semaphore, chunk_text))

        # Esegui in parallelo con rate limiting
        annotations = await asyncio.gather(*tasks)

        # Aggiungi annotazioni alle righe
        for row, annotation in zip(rows, annotations):
            row['DIL'] = annotation if annotation else 'ERROR'
            self.state.processed_chunks += 1
            if annotation is None:
                self.state.failed_chunks += 1

        # Scrivi file output
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            fieldnames = list(rows[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(rows)

        # Aggiorna stato
        self.state.completed_files.append(csv_file.name)

        # Checkpoint periodico
        if self.state.processed_chunks % self.checkpoint_interval == 0:
            self._update_cost()
            self._save_state()
            self._log_progress()

    async def _annotate_chunk(self, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore, chunk_text: str) -> Optional[str]:
        """Annota un singolo chunk con rate limiting."""
        async with semaphore:
            self.requests_made += 1
            return await self._call_api(session, chunk_text)

    def _update_cost(self):
        """Aggiorna costo totale."""
        input_cost = (self.input_tokens / 1_000_000) * self.input_price
        output_cost = (self.output_tokens / 1_000_000) * self.output_price
        self.state.total_cost = input_cost + output_cost

    def _log_progress(self):
        """Log progresso corrente."""
        elapsed = time.time() - self.session_start
        rate = self.state.processed_chunks / elapsed if elapsed > 0 else 0
        remaining = self.state.total_chunks - self.state.processed_chunks
        eta = remaining / rate if rate > 0 else 0

        self.logger.info(
            f"Progresso: {self.state.processed_chunks}/{self.state.total_chunks} "
            f"({self.state.processed_chunks/self.state.total_chunks*100:.1f}%) | "
            f"Rate: {rate:.1f} chunk/s | "
            f"ETA: {eta/3600:.1f}h | "
            f"Costo: ${self.state.total_cost:.2f}"
        )

    async def annotate_corpus(self):
        """Annota l'intero corpus."""
        # Trova tutti i file CSV
        csv_files = sorted(list(self.input_dir.glob("*_chunk.csv")))

        if not csv_files:
            self.logger.error(f"Nessun file trovato in {self.input_dir}")
            return

        # Conta chunk totali (se non già fatto)
        if self.state.total_chunks == 0:
            self.logger.info("Conteggio chunk totali...")
            for csv_file in csv_files:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    self.state.total_chunks += sum(1 for _ in f) - 1  # -1 per header
            self.logger.info(f"Chunk totali da processare: {self.state.total_chunks}")
            self._save_state()

        # Setup sessione HTTP e rate limiting
        connector = aiohttp.TCPConnector(limit=self.max_concurrent)
        timeout = aiohttp.ClientTimeout(total=60)
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Processa file
            for csv_file in csv_files:
                await self._process_file(csv_file, session, semaphore)

        # Statistiche finali
        self._update_cost()
        self._save_state()

        elapsed = time.time() - self.session_start
        self.logger.info("=" * 70)
        self.logger.info("ANNOTAZIONE COMPLETATA")
        self.logger.info("=" * 70)
        self.logger.info(f"Chunk processati: {self.state.processed_chunks}")
        self.logger.info(f"Chunk falliti: {self.state.failed_chunks}")
        self.logger.info(f"File completati: {len(self.state.completed_files)}")
        self.logger.info(f"Tempo totale: {elapsed/3600:.2f} ore")
        self.logger.info(f"Input tokens: {self.input_tokens:,}")
        self.logger.info(f"Output tokens: {self.output_tokens:,}")
        self.logger.info(f"Costo totale: ${self.state.total_cost:.2f}")
        self.logger.info("=" * 70)


async def main():
    """Entry point."""
    print("=" * 70)
    print("DIL CORPUS ANNOTATOR - Claude Sonnet 4.5")
    print("=" * 70)
    print()

    # Verifica config
    config_path = "config.json"
    if not Path(config_path).exists():
        print(f"ERRORE: File di configurazione non trovato: {config_path}")
        print(f"Directory corrente: {Path.cwd()}")
        print("Assicurati di eseguire lo script dalla directory ~/dil_project/")
        return

    # Verifica API key
    with open(config_path, 'r') as f:
        config = json.load(f)
        if config['anthropic_api_key'] == 'YOUR_API_KEY_HERE':
            print("ERRORE: API key non configurata in config.json")
            print("Sostituisci 'YOUR_API_KEY_HERE' con la tua chiave API Anthropic.")
            return

    # Conferma avvio
    print(f"Input directory: {config['input_dir']}")
    print(f"Output directory: {config['output_dir']}")
    print(f"Max concurrent requests: {config['max_concurrent_requests']}")
    print()

    response = input("Avviare l'annotazione? (yes/no): ")
    if response.lower() != 'yes':
        print("Annullato.")
        return

    print()
    print("Avvio annotazione...")
    print()

    # Esegui annotazione
    annotator = DILAnnotator(config_path)
    await annotator.annotate_corpus()


if __name__ == "__main__":
    asyncio.run(main())
