#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
SCRIPT DI ANNOTAZIONE DIL TRAMITE API CLAUDE (ANTHROPIC)
=============================================================================
Autore    : Fabio Ciotti
Versione  : 1.0
Data      : Febbraio 2026

Descrizione
-----------
Questo script automatizza l'annotazione del Discorso Indiretto Libero (DIL)
su un corpus di 500 trigrammi di narrativa italiana, utilizzando le API
ufficiali di Anthropic (Claude).

A differenza di approcci basati su regole o pattern matching, questo script
sfrutta le capacità di ragionamento linguistico del modello LLM per valutare
ogni testo secondo criteri teoricamente fondati.

Strategia tecnica adottata
--------------------------
Si utilizza il **Batches API** di Anthropic, che offre:
  - Riduzione del 50% sui costi rispetto alle chiamate singole
  - Elaborazione asincrona di fino a 100.000 richieste in un unico batch
  - Risultati disponibili per 29 giorni dopo la creazione
  - Supporto completo a tutte le funzionalità della Messages API

Gli output vengono vincolati tramite **Structured Outputs** (JSON schema),
garantendo risposte parsable e consistenti con decisione + ragionamento.

Requisiti
---------
  pip install anthropic pandas scikit-learn

Configurazione
--------------
  - Inserire la propria chiave API in 'api_config.json'
  - NON inserire la chiave direttamente nel codice
  - NON committare 'api_config.json' su repository pubblici (aggiungere a .gitignore)

Utilizzo
--------
  python annotate_dil_claude_api.py

  Modalità opzionali (argomenti da riga di comando):
    --config PERCORSO    Percorso al file JSON di configurazione (default: api_config.json)
    --mode batch         Usa Batches API [default, consigliato]
    --mode sequential    Usa chiamate sequenziali (più lento ma con controllo in tempo reale)
    --resume BATCH_ID    Riprende il polling di un batch già inviato in precedenza

Flusso di esecuzione
---------------------
  1. Caricamento configurazione da api_config.json
  2. Caricamento e validazione del dataset CSV
  3. Costruzione delle richieste batch (una per trigramma)
  4. Invio del batch all'API Anthropic
  5. Polling ciclico finché il batch non è completato
  6. Raccolta e parsing dei risultati
  7. Salvataggio del CSV annotato con nuova colonna
  8. Calcolo e stampa delle metriche (accuracy, F1, ecc.)
  9. Confronto con annotazione precedente (inter-annotator agreement)
=============================================================================
"""

# ---------------------------------------------------------------------------
# IMPORTAZIONI STANDARD
# ---------------------------------------------------------------------------
import os          # Operazioni sul filesystem (verifica esistenza file)
import sys         # Accesso ad argv e uscita con codice di errore
import json        # Lettura/scrittura file JSON (configurazione, log)
import time        # Pausa tra polling successivi
import logging     # Logging strutturato su file e console
import argparse    # Parsing degli argomenti da riga di comando
from datetime import datetime          # Timestamp nei log
from pathlib import Path               # Gestione percorsi cross-platform
from typing import Optional            # Type hints

# ---------------------------------------------------------------------------
# IMPORTAZIONI TERZE PARTI
# ---------------------------------------------------------------------------
import pandas as pd   # Gestione del dataset CSV

try:
    import anthropic
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request
except ImportError:
    print("ERRORE: la libreria 'anthropic' non è installata.")
    print("Eseguire: pip install anthropic")
    sys.exit(1)

try:
    from sklearn.metrics import (
        accuracy_score,
        precision_recall_fscore_support,
        confusion_matrix,
        cohen_kappa_score,
    )
except ImportError:
    print("ERRORE: la libreria 'scikit-learn' non è installata.")
    print("Eseguire: pip install scikit-learn")
    sys.exit(1)

# ---------------------------------------------------------------------------
# CONFIGURAZIONE DEL LOGGER
# ---------------------------------------------------------------------------
# Configura il logger per scrivere sia su console che su file di log.
# Il livello INFO registra messaggi informativi e di avanzamento.
# Il livello WARNING registra anomalie non bloccanti.
# Il livello ERROR registra errori che richiedono attenzione.

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),          # Output su console
        logging.FileHandler("annotazione_dil.log"), # Output su file
    ],
)
logger = logging.getLogger(__name__)


# ===========================================================================
# SEZIONE 1: PROMPT DI SISTEMA
# ===========================================================================

# Il system prompt viene inviato a Claude come istruzione permanente e
# definisce: (a) il compito, (b) la teoria linguistica di riferimento,
# (c) i criteri di giudizio, (d) il formato dell'output richiesto.
# Un system prompt ben costruito è cruciale per la qualità dell'annotazione.

SYSTEM_PROMPT = """Sei un esperto di stilistica e narratologia italiana, con specializzazione nell'analisi del Discorso Indiretto Libero (DIL) nella narrativa di fine Ottocento e primo Novecento.

## Il tuo compito

Devi analizzare trigrammi (gruppi di tre frasi consecutive) estratti da opere narrative italiane e determinare se contengono DIL.

## Definizione teorica

Il Discorso Indiretto Libero è una tecnica narrativa che rappresenta il pensiero o il discorso di un personaggio SENZA verbi dichiarativi espliciti (come "pensò", "disse", "si chiese").

Caratteristiche diagnostiche del DIL:
1. **Assenza di verbi introduttivi**: Nessun "pensò", "disse", "mormorò", "si chiese", "si disse", "rifletté" che espliciti la voce del personaggio
2. **Terza persona grammaticale**: Mantiene la terza persona, ma con prospettiva soggettiva del personaggio
3. **Punto di vista interno**: Il testo riflette la prospettiva soggettiva del personaggio, non del narratore
4. **Marcatori sintattici tipici** (uno o più):
   - Interiezioni: "Oh!", "Ah!", "Dio mio!", "Ahimè!"
   - Esclamazioni emotive dirette
   - Interrogative retoriche (domande senza risposta attesa)
   - Modalizzatori epistemici: "forse", "certamente", "senza dubbio", "probabilmente"
   - Puntini di sospensione (pensiero frammentato)
   - Lessico valutativo coerente con il personaggio, non con il narratore

## Distinzioni critiche

- DIL ≠ Discorso Diretto: il DI usa virgolette/trattino e prima persona
- DIL ≠ Discorso Indiretto classico: il DIR usa verbi dichiarativi + "che"
- DIL ≠ Descrizione psicologica: "un pensiero lo attraversò" = NO DIL
- DIL può seguire un verbo dichiarativo: "Pensò che era finita. Tutto perduto..." (la seconda frase PUÒ essere DIL)
- Narrazione con tono valutativo ma senza soggettività del personaggio = NO DIL

## Istruzione per casi dubbi

In caso di incertezza, considera presente il DIL se ci sono almeno indicatori deboli ma coerenti di soggettività del personaggio.

## Formato dell'output (OBBLIGATORIO)

Rispondi ESCLUSIVAMENTE con un oggetto JSON valido nel seguente formato:
{
  "dil": "yes" oppure "no",
  "confidenza": "alta", "media" oppure "bassa",
  "ragionamento": "Spiegazione sintetica (max 3 frasi) della tua decisione con riferimento ai criteri teorici",
  "marcatori": ["lista", "dei", "marcatori", "trovati"]
}

Non aggiungere nulla prima o dopo il JSON.
"""


# ===========================================================================
# SEZIONE 2: FUNZIONI DI SUPPORTO
# ===========================================================================

def carica_configurazione(percorso_config: str) -> dict:
    """
    Carica e valida il file di configurazione JSON.

    Il file di configurazione contiene la chiave API e i parametri operativi.
    Viene tenuto separato dal codice per ragioni di sicurezza: la chiave API
    non deve mai essere committata in un repository.

    Parameters
    ----------
    percorso_config : str
        Percorso al file api_config.json

    Returns
    -------
    dict
        Dizionario con la configurazione caricata

    Raises
    ------
    FileNotFoundError
        Se il file di configurazione non esiste
    ValueError
        Se la chiave API non è stata impostata
    json.JSONDecodeError
        Se il file JSON è malformato
    """
    percorso = Path(percorso_config)

    if not percorso.exists():
        raise FileNotFoundError(
            f"File di configurazione non trovato: {percorso_config}\n"
            "Creare il file api_config.json con la propria chiave API Anthropic."
        )

    with open(percorso, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Verifica che la chiave API sia stata impostata (non il placeholder)
    api_key = config.get("api_key", "")
    if not api_key or api_key == "INSERISCI_QUI_LA_TUA_CHIAVE_ANTHROPIC":
        raise ValueError(
            "La chiave API non è stata impostata in api_config.json.\n"
            "Sostituire 'INSERISCI_QUI_LA_TUA_CHIAVE_ANTHROPIC' con la propria chiave."
        )

    logger.info(f"Configurazione caricata da '{percorso_config}'")
    logger.info(f"Modello selezionato: {config.get('modello', 'claude-opus-4-6')}")
    return config


def carica_dataset(percorso_csv: str) -> pd.DataFrame:
    """
    Carica e valida il dataset CSV con i trigrammi.

    Verifica la presenza delle colonne richieste e segnala eventuali
    valori mancanti nelle colonne critiche.

    Parameters
    ----------
    percorso_csv : str
        Percorso al file CSV di input

    Returns
    -------
    pd.DataFrame
        DataFrame con i dati caricati

    Raises
    ------
    FileNotFoundError
        Se il file CSV non esiste
    ValueError
        Se mancano colonne obbligatorie
    """
    percorso = Path(percorso_csv)

    if not percorso.exists():
        raise FileNotFoundError(f"File di input non trovato: {percorso_csv}")

    df = pd.read_csv(percorso, encoding="utf-8")

    # Verifica presenza delle colonne obbligatorie
    colonne_richieste = {"text", "DIL", "DIL_Sonnet"}
    colonne_mancanti = colonne_richieste - set(df.columns)
    if colonne_mancanti:
        raise ValueError(
            f"Colonne mancanti nel dataset: {colonne_mancanti}\n"
            f"Colonne presenti: {list(df.columns)}"
        )

    # Segnala testi mancanti o molto brevi
    testi_vuoti = df["text"].isna().sum()
    if testi_vuoti > 0:
        logger.warning(f"Trovati {testi_vuoti} testi mancanti (NaN) nel dataset.")

    logger.info(f"Dataset caricato: {len(df)} trigrammi")
    logger.info(f"Distribuzione gold standard — yes: {(df['DIL']=='yes').sum()}, no: {(df['DIL']=='no').sum()}")
    return df


def costruisci_prompt_utente(riga: pd.Series) -> str:
    """
    Costruisce il prompt utente per un singolo trigramma.

    Il prompt include il contesto bibliografico del testo (autore, opera, anno)
    per aiutare il modello a calibrare il registro storico-linguistico,
    e il testo da analizzare.

    Parameters
    ----------
    riga : pd.Series
        Riga del DataFrame con author, work, year, text

    Returns
    -------
    str
        Prompt utente formattato
    """
    # Recupera il contesto bibliografico, gestendo valori mancanti
    autore = str(riga.get("author", "Autore sconosciuto")) if pd.notna(riga.get("author")) else "Autore sconosciuto"
    opera = str(riga.get("work", "Opera sconosciuta")) if pd.notna(riga.get("work")) else "Opera sconosciuta"
    anno = str(int(riga["year"])) if pd.notna(riga.get("year")) else "anno ignoto"
    testo = str(riga["text"]) if pd.notna(riga.get("text")) else ""

    prompt = f"""Analizza il seguente trigramma estratto da un'opera narrativa italiana.

CONTESTO BIBLIOGRAFICO:
- Autore: {autore}
- Opera: {opera}
- Anno: {anno}

TESTO DA ANALIZZARE:
---
{testo}
---

Determina se questo trigramma contiene Discorso Indiretto Libero (DIL) secondo i criteri teorici forniti. Rispondi con il JSON richiesto."""

    return prompt


def costruisci_schema_output() -> dict:
    """
    Restituisce lo schema JSON che vincola il formato della risposta del modello.

    Structured Outputs garantisce che la risposta sia sempre un JSON valido
    conforme allo schema, eliminando la necessità di gestire output malformati.
    Questo è preferibile al semplice parsing del testo libero perché:
      - Garantisce consistenza tra tutte le 500 annotazioni
      - Evita errori di parsing per output non conformi
      - Permette di estrarre automaticamente decisione, confidenza e marcatori

    Returns
    -------
    dict
        Schema JSON per output strutturato
    """
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "annotazione_dil",
            "description": "Annotazione del Discorso Indiretto Libero in un trigramma narrativo",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "dil": {
                        "type": "string",
                        "enum": ["yes", "no"],
                        "description": "Presenza (yes) o assenza (no) di DIL nel trigramma"
                    },
                    "confidenza": {
                        "type": "string",
                        "enum": ["alta", "media", "bassa"],
                        "description": "Livello di certezza della decisione"
                    },
                    "ragionamento": {
                        "type": "string",
                        "description": "Spiegazione della decisione con riferimento ai criteri teorici (max 3 frasi)"
                    },
                    "marcatori": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista dei marcatori linguistici DIL trovati nel testo, o lista vuota se assenti"
                    }
                },
                "required": ["dil", "confidenza", "ragionamento", "marcatori"],
                "additionalProperties": False
            }
        }
    }


def prepara_richieste_batch(df: pd.DataFrame, config: dict) -> list:
    """
    Prepara la lista di richieste da inviare al Batches API.

    Ogni richiesta corrisponde a un trigramma e viene identificata da un
    custom_id univoco (indice della riga nel DataFrame) per poter ricongiunger
    i risultati con i dati originali dopo il completamento del batch.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame con i trigrammi
    config : dict
        Configurazione con modello, max_tokens, ecc.

    Returns
    -------
    list
        Lista di oggetti Request pronti per il Batches API
    """
    modello = config.get("modello", "claude-opus-4-6")
    max_tokens = config.get("max_tokens", 512)
    usa_thinking = config.get("usa_thinking_adattivo", False)

    richieste = []

    for idx, riga in df.iterrows():
        # Costruisce il prompt specifico per questo trigramma
        prompt_utente = costruisci_prompt_utente(riga)

        # Parametri base della chiamata API
        params = {
            "model": modello,
            "max_tokens": max_tokens,
            "system": SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": prompt_utente}
            ],
            # Structured outputs per risposta JSON garantita
            "output_config": {
                "format": costruisci_schema_output()
            }
        }

        # Aggiunge thinking adattivo se richiesto nella configurazione.
        # Nota: thinking adattivo è disponibile solo su claude-opus-4-6 e
        # aumenta significativamente costi e latenza. Per classificazione
        # binaria si sconsiglia, ma può migliorare casi ambigui.
        if usa_thinking and "opus-4-6" in modello:
            params["thinking"] = {"type": "adaptive"}
            # Con thinking attivo i max_tokens devono essere più alti
            params["max_tokens"] = max(max_tokens, 4096)

        # Il custom_id permette di associare il risultato alla riga originale.
        # Usiamo str(idx) per garantire unicità anche se l'indice non è sequenziale.
        richiesta = Request(
            custom_id=str(idx),
            params=MessageCreateParamsNonStreaming(**params)
        )
        richieste.append(richiesta)

    logger.info(f"Preparate {len(richieste)} richieste per il batch")
    return richieste


def invia_batch(client: anthropic.Anthropic, richieste: list, config: dict) -> str:
    """
    Invia il batch all'API Anthropic e registra l'ID del batch.

    L'ID del batch viene salvato su file per permettere il ripristino
    in caso di interruzione dello script: con --resume BATCH_ID si può
    riprendere il polling senza re-inviare il batch.

    Parameters
    ----------
    client : anthropic.Anthropic
        Client Anthropic autenticato
    richieste : list
        Lista di oggetti Request pronti per il Batches API
    config : dict
        Configurazione con percorso_log_batch

    Returns
    -------
    str
        ID del batch creato

    Raises
    ------
    anthropic.APIError
        In caso di errore nella comunicazione con le API
    """
    logger.info(f"Invio del batch con {len(richieste)} richieste...")

    batch = client.messages.batches.create(requests=richieste)

    batch_id = batch.id
    logger.info(f"Batch creato con successo. ID: {batch_id}")
    logger.info(f"Stato iniziale: {batch.processing_status}")

    # Salva l'ID del batch su file per permettere ripristino
    percorso_log = config.get("percorso_log_batch", "batch_ids_log.json")
    entry_log = {
        "batch_id": batch_id,
        "timestamp_creazione": datetime.now().isoformat(),
        "n_richieste": len(richieste),
        "modello": config.get("modello"),
        "stato": batch.processing_status
    }

    # Carica il log esistente (se presente) e aggiunge la nuova entry
    log_esistente = []
    if Path(percorso_log).exists():
        with open(percorso_log, "r", encoding="utf-8") as f:
            try:
                log_esistente = json.load(f)
            except json.JSONDecodeError:
                log_esistente = []

    log_esistente.append(entry_log)

    with open(percorso_log, "w", encoding="utf-8") as f:
        json.dump(log_esistente, f, ensure_ascii=False, indent=2)

    logger.info(f"ID batch salvato in '{percorso_log}' per eventuale ripristino.")
    return batch_id


def polling_batch(client: anthropic.Anthropic, batch_id: str, config: dict) -> object:
    """
    Esegue il polling del batch finché non è completato.

    Il Batches API elabora le richieste in modo asincrono: lo stato passa da
    'in_progress' a 'ended' quando tutte le richieste sono state processate.
    Lo script esegue un controllo periodico (ogni N secondi configurabili)
    fino al completamento o al timeout.

    Parameters
    ----------
    client : anthropic.Anthropic
        Client Anthropic autenticato
    batch_id : str
        ID del batch da monitorare
    config : dict
        Configurazione con pausa_polling_secondi e max_tentativi_polling

    Returns
    -------
    object
        Oggetto batch finale restituito dall'API

    Raises
    ------
    TimeoutError
        Se il batch non si completa entro il numero massimo di tentativi
    """
    pausa = config.get("pausa_polling_secondi", 60)
    max_tentativi = config.get("max_tentativi_polling", 60)

    logger.info(f"Inizio polling del batch '{batch_id}'...")
    logger.info(f"Controllo ogni {pausa}s per max {max_tentativi} tentativi ({max_tentativi * pausa / 60:.0f} minuti)")

    for tentativo in range(1, max_tentativi + 1):
        # Recupera lo stato aggiornato del batch
        batch = client.messages.batches.retrieve(batch_id)

        # Estrae i conteggi di richieste nei diversi stati
        conteggi = batch.request_counts
        logger.info(
            f"[{tentativo}/{max_tentativi}] Stato: {batch.processing_status} | "
            f"In elaborazione: {conteggi.processing} | "
            f"Completate: {conteggi.succeeded} | "
            f"Errori: {conteggi.errored}"
        )

        # Il batch è terminato quando lo stato è 'ended'
        if batch.processing_status == "ended":
            logger.info(f"Batch completato. Richieste riuscite: {conteggi.succeeded}/{conteggi.processing + conteggi.succeeded + conteggi.errored + conteggi.canceled + conteggi.expired}")
            return batch

        # Attende prima del prossimo controllo
        time.sleep(pausa)

    # Se si supera il numero massimo di tentativi, solleva un errore
    raise TimeoutError(
        f"Il batch '{batch_id}' non si è completato entro {max_tentativi * pausa} secondi.\n"
        f"Riprendere con: python annotate_dil_claude_api.py --resume {batch_id}"
    )


def raccogli_risultati(
    client: anthropic.Anthropic,
    batch_id: str,
    df: pd.DataFrame,
    config: dict
) -> tuple[pd.DataFrame, list]:
    """
    Raccoglie e parser i risultati del batch completato.

    Per ogni richiesta riuscita, estrae la risposta JSON del modello,
    la valida, e assegna la decisione DIL alla riga corrispondente del DataFrame.
    Le risposte fallite vengono segnalate e marchiate come 'error'.

    Parameters
    ----------
    client : anthropic.Anthropic
        Client Anthropic autenticato
    batch_id : str
        ID del batch completato
    df : pd.DataFrame
        DataFrame originale (verrà modificato in-place)
    config : dict
        Configurazione con colonna_annotazione_nuova, ecc.

    Returns
    -------
    tuple[pd.DataFrame, list]
        - DataFrame aggiornato con la nuova colonna di annotazioni
        - Lista di entry di log con i ragionamenti
    """
    colonna_nuova = config.get("colonna_annotazione_nuova", "DIL_Claude_API")

    # Inizializza la nuova colonna con un valore placeholder
    df[colonna_nuova] = "non_annotato"

    log_ragionamenti = []    # Lista delle entry di log per tutti i trigrammi
    n_riuscite = 0           # Contatore richieste riuscite
    n_errori = 0             # Contatore richieste fallite
    n_parse_error = 0        # Contatore errori di parsing del JSON

    logger.info(f"Raccolta risultati dal batch '{batch_id}'...")

    # Itera sui risultati del batch. Ogni 'result' corrisponde a una richiesta.
    for result in client.messages.batches.results(batch_id):

        # Il custom_id è l'indice della riga nel DataFrame originale
        idx = int(result.custom_id)

        if result.result.type == "succeeded":
            # La richiesta è stata elaborata correttamente
            n_riuscite += 1
            messaggio = result.result.message

            # Estrae il testo della risposta dal primo blocco di contenuto
            testo_risposta = ""
            for blocco in messaggio.content:
                if blocco.type == "text":
                    testo_risposta = blocco.text
                    break

            # Parsa la risposta JSON del modello
            try:
                risposta_json = json.loads(testo_risposta)

                # Estrae i campi dalla risposta strutturata
                decisione = risposta_json.get("dil", "error")
                confidenza = risposta_json.get("confidenza", "sconosciuta")
                ragionamento = risposta_json.get("ragionamento", "")
                marcatori = risposta_json.get("marcatori", [])

                # Assegna la decisione al DataFrame
                df.at[idx, colonna_nuova] = decisione

                # Prepara l'entry di log per questo trigramma
                entry_log = {
                    "index": idx,
                    "timestamp": datetime.now().isoformat(),
                    "testo_anteprima": str(df.at[idx, "text"])[:150] + "..." if len(str(df.at[idx, "text"])) > 150 else str(df.at[idx, "text"]),
                    "decisione": decisione,
                    "confidenza": confidenza,
                    "gold_standard": df.at[idx, "DIL"],
                    "annotazione_precedente": df.at[idx, "DIL_Sonnet"],
                    "ragionamento": ragionamento,
                    "marcatori": marcatori,
                    "tokens_input": messaggio.usage.input_tokens,
                    "tokens_output": messaggio.usage.output_tokens
                }

            except (json.JSONDecodeError, KeyError, AttributeError) as e:
                # Il modello ha restituito una risposta non parsable.
                # Questo non dovrebbe accadere con structured outputs,
                # ma viene gestito per robustezza.
                logger.warning(
                    f"Errore parsing risposta per riga {idx}: {e}\n"
                    f"Risposta grezza: {testo_risposta[:200]}"
                )
                n_parse_error += 1
                df.at[idx, colonna_nuova] = "parse_error"
                entry_log = {
                    "index": idx,
                    "timestamp": datetime.now().isoformat(),
                    "decisione": "parse_error",
                    "errore": str(e),
                    "risposta_grezza": testo_risposta[:500]
                }

            log_ragionamenti.append(entry_log)

        elif result.result.type == "errored":
            # La richiesta è fallita per un errore API
            n_errori += 1
            tipo_errore = result.result.error.type
            logger.warning(f"Richiesta fallita per riga {idx}: tipo errore = {tipo_errore}")

            # Gli errori di tipo 'invalid_request' non devono essere riprovati,
            # quelli di tipo 'server_error' sì.
            df.at[idx, colonna_nuova] = "api_error"
            log_ragionamenti.append({
                "index": idx,
                "timestamp": datetime.now().isoformat(),
                "decisione": "api_error",
                "tipo_errore": tipo_errore
            })

        elif result.result.type == "expired":
            # La richiesta è scaduta (il batch ha superato le 24 ore)
            logger.warning(f"Richiesta scaduta per riga {idx}")
            df.at[idx, colonna_nuova] = "expired"

    logger.info(
        f"Raccolta completata: {n_riuscite} riuscite, "
        f"{n_errori} errori API, {n_parse_error} errori di parsing"
    )

    return df, log_ragionamenti


def salva_log_ragionamenti(log_ragionamenti: list, percorso_log: str):
    """
    Salva il log dei ragionamenti in formato JSONL (JSON Lines).

    Il formato JSONL (una entry JSON per riga) è preferito per file di log
    grandi perché permette lettura incrementale senza caricare tutto in memoria.

    Parameters
    ----------
    log_ragionamenti : list
        Lista di dizionari con i ragionamenti
    percorso_log : str
        Percorso del file di output .jsonl
    """
    with open(percorso_log, "w", encoding="utf-8") as f:
        for entry in log_ragionamenti:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    logger.info(f"Log ragionamenti salvato in '{percorso_log}' ({len(log_ragionamenti)} entries)")


# ===========================================================================
# SEZIONE 3: CALCOLO METRICHE
# ===========================================================================

def calcola_metriche(df: pd.DataFrame, colonna_nuova: str):
    """
    Calcola e stampa le metriche di valutazione dell'annotazione.

    Confronta la nuova annotazione Claude API con:
      (a) Il gold standard (annotazioni umane, colonna 'DIL')
      (b) L'annotazione precedente (colonna 'DIL_Sonnet')

    Metriche calcolate:
      - Accuracy, Precision, Recall, F1-Score vs gold standard
      - Confusion matrix (TP, TN, FP, FN)
      - Tasso di accordo inter-annotatore
      - Cohen's Kappa vs annotazione precedente

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame con gold standard e nuove annotazioni
    colonna_nuova : str
        Nome della colonna con le nuove annotazioni
    """
    # Filtra le righe annotate correttamente (esclude errori API)
    df_valido = df[df[colonna_nuova].isin(["yes", "no"])].copy()

    if len(df_valido) == 0:
        logger.error("Nessuna annotazione valida trovata. Impossibile calcolare metriche.")
        return

    n_valide = len(df_valido)
    n_totale = len(df)

    # Vettori di labels per le metriche
    y_gold = df_valido["DIL"].values
    y_nuova = df_valido[colonna_nuova].values
    y_v1 = df_valido["DIL_Sonnet"].values

    print("\n" + "=" * 70)
    print(f"METRICHE DI VALUTAZIONE — {colonna_nuova}")
    print(f"Richieste valide: {n_valide}/{n_totale}")
    print("=" * 70)

    # -----------------------------------------------------------------------
    # 1. PERFORMANCE VS GOLD STANDARD
    # -----------------------------------------------------------------------
    print("\n[1] PERFORMANCE VS GOLD STANDARD (Annotatori Umani)")
    print("─" * 70)

    acc = accuracy_score(y_gold, y_nuova)
    prec, rec, f1, _ = precision_recall_fscore_support(
        y_gold, y_nuova, pos_label="yes", average="binary", zero_division=0
    )
    cm = confusion_matrix(y_gold, y_nuova, labels=["no", "yes"])

    print(f"\n  Accuracy:  {acc:.2%}")
    print(f"  Precision: {prec:.2%}")
    print(f"  Recall:    {rec:.2%}")
    print(f"  F1-Score:  {f1:.2%}")

    print(f"\n  Confusion Matrix:")
    print(f"              Pred NO   Pred YES")
    print(f"  Gold NO   {cm[0,0]:>8}  {cm[0,1]:>8}   (TN={cm[0,0]}, FP={cm[0,1]})")
    print(f"  Gold YES  {cm[1,0]:>8}  {cm[1,1]:>8}   (FN={cm[1,0]}, TP={cm[1,1]})")

    # Confronto con Sonnet v1
    acc_v1 = accuracy_score(y_gold, y_v1)
    prec_v1, rec_v1, f1_v1, _ = precision_recall_fscore_support(
        y_gold, y_v1, pos_label="yes", average="binary", zero_division=0
    )

    print(f"\n  Confronto con Sonnet v1:")
    print(f"  {'Metrica':<12} {'API (nuova)':<15} {'v1 (prec.)':<15} {'Δ':<10}")
    print(f"  {'─'*52}")
    print(f"  {'Accuracy':<12} {acc:<15.2%} {acc_v1:<15.2%} {(acc - acc_v1)*100:+.2f}%")
    print(f"  {'Precision':<12} {prec:<15.2%} {prec_v1:<15.2%} {(prec - prec_v1)*100:+.2f}%")
    print(f"  {'Recall':<12} {rec:<15.2%} {rec_v1:<15.2%} {(rec - rec_v1)*100:+.2f}%")
    print(f"  {'F1-Score':<12} {f1:<15.2%} {f1_v1:<15.2%} {(f1 - f1_v1)*100:+.2f}%")

    # -----------------------------------------------------------------------
    # 2. INTER-ANNOTATOR AGREEMENT
    # -----------------------------------------------------------------------
    print(f"\n[2] INTER-ANNOTATOR AGREEMENT ({colonna_nuova} vs DIL_Sonnet)")
    print("─" * 70)

    accordo = (df_valido[colonna_nuova] == df_valido["DIL_Sonnet"]).sum()
    tasso_accordo = accordo / n_valide
    kappa = cohen_kappa_score(y_v1, y_nuova)

    print(f"\n  Tasso di accordo: {accordo}/{n_valide} ({tasso_accordo:.2%})")
    print(f"  Cohen's Kappa:    {kappa:.3f}")
    print(f"  Interpretazione:  ", end="")
    if kappa < 0:      print("Accordo inferiore al caso")
    elif kappa < 0.20: print("Accordo minimo")
    elif kappa < 0.40: print("Accordo debole")
    elif kappa < 0.60: print("Accordo moderato")
    elif kappa < 0.80: print("Accordo sostanziale")
    else:              print("Accordo quasi perfetto")

    # -----------------------------------------------------------------------
    # 3. DISTRIBUZIONE ANNOTAZIONI
    # -----------------------------------------------------------------------
    print(f"\n[3] DISTRIBUZIONE DELLE ANNOTAZIONI")
    print("─" * 70)

    gold_yes = (y_gold == "yes").sum()
    nuova_yes = (y_nuova == "yes").sum()
    v1_yes = (y_v1 == "yes").sum()

    print(f"\n  {'Annotatore':<25} {'DIL=yes':<15} {'DIL=no':<15} {'Bias vs Gold'}")
    print(f"  {'─'*65}")
    print(f"  {'Gold Standard (umani)':<25} {gold_yes:<15} {n_valide-gold_yes:<15} —")
    print(f"  {colonna_nuova:<25} {nuova_yes:<15} {n_valide-nuova_yes:<15} {(nuova_yes-gold_yes)/n_valide*100:+.1f}%")
    print(f"  {'DIL_Sonnet (prec.)':<25} {v1_yes:<15} {n_valide-v1_yes:<15} {(v1_yes-gold_yes)/n_valide*100:+.1f}%")

    print("\n" + "=" * 70 + "\n")


# ===========================================================================
# SEZIONE 4: MODALITÀ SEQUENZIALE (ALTERNATIVA AL BATCH)
# ===========================================================================

def annota_sequenziale(
    client: anthropic.Anthropic,
    df: pd.DataFrame,
    config: dict
) -> tuple[pd.DataFrame, list]:
    """
    Annota i trigrammi con chiamate API sequenziali (alternativa al Batches API).

    Questa modalità è più lenta ma permette di:
      - Vedere i risultati in tempo reale
      - Interrompere e riprendere a partire da un indice specifico
      - Gestire il rate limiting in modo più granulare
      - Debuggare problemi su singole richieste

    Il salvataggio avviene ogni 50 trigrammi per prevenire perdita di dati
    in caso di interruzione.

    Parameters
    ----------
    client : anthropic.Anthropic
        Client Anthropic autenticato
    df : pd.DataFrame
        DataFrame con i trigrammi
    config : dict
        Configurazione operativa

    Returns
    -------
    tuple[pd.DataFrame, list]
        - DataFrame aggiornato
        - Lista dei log dei ragionamenti
    """
    colonna_nuova = config.get("colonna_annotazione_nuova", "DIL_Claude_API")
    modello = config.get("modello", "claude-opus-4-6")
    max_tokens = config.get("max_tokens", 512)
    percorso_output = config.get("percorso_output", "output_annotato.csv")
    usa_thinking = config.get("usa_thinking_adattivo", False)

    if colonna_nuova not in df.columns:
        df[colonna_nuova] = "non_annotato"

    log_ragionamenti = []

    logger.info(f"Avvio annotazione sequenziale di {len(df)} trigrammi...")

    for idx, riga in df.iterrows():
        # Salta le righe già annotate (utile per riprendere da un'interruzione)
        if df.at[idx, colonna_nuova] not in ["non_annotato", "", None]:
            continue

        prompt_utente = costruisci_prompt_utente(riga)

        # Costruisce i parametri della richiesta
        params = {
            "model": modello,
            "max_tokens": max_tokens,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt_utente}],
            "output_config": {
                "format": costruisci_schema_output()
            }
        }

        if usa_thinking and "opus-4-6" in modello:
            params["thinking"] = {"type": "adaptive"}
            params["max_tokens"] = max(max_tokens, 4096)

        try:
            # Usa lo streaming per prevenire timeout su risposte lunghe
            # e ottiene il messaggio completo con get_final_message()
            with client.messages.stream(**params) as stream:
                messaggio = stream.get_final_message()

            # Estrae e parsa il testo della risposta
            testo_risposta = messaggio.content[0].text
            risposta_json = json.loads(testo_risposta)

            decisione = risposta_json.get("dil", "error")
            confidenza = risposta_json.get("confidenza", "sconosciuta")
            ragionamento = risposta_json.get("ragionamento", "")
            marcatori = risposta_json.get("marcatori", [])

            df.at[idx, colonna_nuova] = decisione

            log_ragionamenti.append({
                "index": idx,
                "timestamp": datetime.now().isoformat(),
                "testo_anteprima": str(riga["text"])[:150],
                "decisione": decisione,
                "confidenza": confidenza,
                "gold_standard": riga["DIL"],
                "annotazione_precedente": riga["DIL_Sonnet"],
                "ragionamento": ragionamento,
                "marcatori": marcatori,
                "tokens_input": messaggio.usage.input_tokens,
                "tokens_output": messaggio.usage.output_tokens
            })

            # Feedback progressivo su console
            simbolo = "✓" if decisione == riga["DIL"] else "✗"
            logger.info(f"[{idx+1}/{len(df)}] {simbolo} DIL={decisione} (gold={riga['DIL']}) — {str(riga['author'])[:25]}")

        except anthropic.RateLimitError:
            # Rate limit raggiunto: attende 60 secondi prima di riprovare
            logger.warning(f"Rate limit raggiunto alla riga {idx}. Attesa 60 secondi...")
            time.sleep(60)
            # Ridecrementa per riprovare questa riga al prossimo ciclo
            # (pandas itera una volta sola, quindi gestiamo con una seconda iterazione)
            df.at[idx, colonna_nuova] = "non_annotato"

        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                # Errore server: riprova dopo una breve pausa
                logger.warning(f"Errore server alla riga {idx} (HTTP {e.status_code}). Pausa 30s...")
                time.sleep(30)
            else:
                # Errore client (4xx): non riprovare
                logger.error(f"Errore client alla riga {idx}: {e.message}")
                df.at[idx, colonna_nuova] = "api_error"

        except json.JSONDecodeError as e:
            logger.warning(f"Errore parsing JSON alla riga {idx}: {e}")
            df.at[idx, colonna_nuova] = "parse_error"

        # Salva il CSV ogni 50 trigrammi per prevenire perdita di dati
        if (idx + 1) % 50 == 0:
            df.to_csv(percorso_output, index=False, encoding="utf-8")
            logger.info(f"Checkpoint: salvate {idx+1} annotazioni in '{percorso_output}'")

    # Salvataggio finale
    df.to_csv(percorso_output, index=False, encoding="utf-8")
    logger.info(f"Annotazione sequenziale completata. File salvato: '{percorso_output}'")

    return df, log_ragionamenti


# ===========================================================================
# SEZIONE 5: MAIN
# ===========================================================================

def parse_argomenti() -> argparse.Namespace:
    """
    Configura e parsa gli argomenti da riga di comando.

    Returns
    -------
    argparse.Namespace
        Namespace con gli argomenti parsati
    """
    parser = argparse.ArgumentParser(
        description="Annotazione DIL tramite API Claude (Anthropic)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi di utilizzo:
  python annotate_dil_claude_api.py
  python annotate_dil_claude_api.py --config mia_config.json --mode sequential
  python annotate_dil_claude_api.py --resume msgbatch_01abc123xyz
        """
    )

    parser.add_argument(
        "--config",
        type=str,
        default="api_config.json",
        help="Percorso al file di configurazione JSON (default: api_config.json)"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["batch", "sequential"],
        default="batch",
        help="Modalità di annotazione: 'batch' (consigliato) o 'sequential' (default: batch)"
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="ID di un batch già inviato da riprendere (es: msgbatch_01abc123)"
    )

    return parser.parse_args()


def main():
    """
    Funzione principale che orchestra l'intero pipeline di annotazione.

    Flusso di esecuzione:
    1. Parsing argomenti da riga di comando
    2. Caricamento configurazione da JSON
    3. Inizializzazione client Anthropic (con chiave API dal config)
    4. Caricamento dataset CSV
    5. Annotazione (batch o sequenziale)
    6. Salvataggio risultati
    7. Calcolo e stampa metriche
    """
    args = parse_argomenti()

    logger.info("=" * 70)
    logger.info("AVVIO SCRIPT ANNOTAZIONE DIL — API CLAUDE ANTHROPIC")
    logger.info(f"Data/ora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    # --- Passo 1: Caricamento configurazione ---
    try:
        config = carica_configurazione(args.config)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        logger.error(f"Errore nella configurazione: {e}")
        sys.exit(1)

    # --- Passo 2: Inizializzazione client Anthropic ---
    # La chiave API proviene dal file JSON, NON dal codice.
    # In alternativa, si può usare la variabile d'ambiente ANTHROPIC_API_KEY
    # e lasciare che l'SDK la rilevi automaticamente con anthropic.Anthropic().
    api_key = config["api_key"]
    client = anthropic.Anthropic(api_key=api_key)
    logger.info("Client Anthropic inizializzato.")

    # --- Passo 3: Caricamento dataset ---
    percorso_input = config.get("percorso_input", "corpus_labelled-trigrams_500_LLM_annotated.csv")
    try:
        df = carica_dataset(percorso_input)
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Errore nel caricamento del dataset: {e}")
        sys.exit(1)

    # --- Passo 4: Annotazione ---
    colonna_nuova = config.get("colonna_annotazione_nuova", "DIL_Claude_API")

    if args.mode == "sequential":
        # Modalità sequenziale: una richiesta API alla volta
        logger.info("Modalità: chiamate sequenziali")
        df, log_ragionamenti = annota_sequenziale(client, df, config)

    else:
        # Modalità batch: tutte le richieste in un unico batch (consigliata)
        logger.info("Modalità: Batches API")

        if args.resume:
            # Riprende un batch già inviato in precedenza
            batch_id = args.resume
            logger.info(f"Riprendendo il polling del batch esistente: {batch_id}")
        else:
            # Nuovo batch: prepara e invia le richieste
            richieste = prepara_richieste_batch(df, config)

            try:
                batch_id = invia_batch(client, richieste, config)
            except anthropic.APIError as e:
                logger.error(f"Errore nell'invio del batch: {e}")
                sys.exit(1)

        # Attende il completamento del batch
        try:
            polling_batch(client, batch_id, config)
        except TimeoutError as e:
            logger.error(str(e))
            sys.exit(1)

        # Raccoglie i risultati
        df, log_ragionamenti = raccogli_risultati(client, batch_id, df, config)

    # --- Passo 5: Salvataggio CSV annotato ---
    percorso_output = config.get("percorso_output", "corpus_labelled-trigrams_500_Claude_API_annotated.csv")
    df.to_csv(percorso_output, index=False, encoding="utf-8")
    logger.info(f"CSV annotato salvato in '{percorso_output}'")

    # --- Passo 6: Salvataggio log ragionamenti ---
    if config.get("salva_ragionamento", True):
        percorso_log = config.get("percorso_log_ragionamenti", "DIL_API_reasoning_log.jsonl")
        salva_log_ragionamenti(log_ragionamenti, percorso_log)

    # --- Passo 7: Calcolo metriche ---
    calcola_metriche(df, colonna_nuova)

    # --- Passo 8: Salvataggio metriche in CSV ---
    percorso_metriche = config.get("percorso_metriche", "metrics_API_vs_gold.csv")
    try:
        from sklearn.metrics import accuracy_score, precision_recall_fscore_support

        df_valido = df[df[colonna_nuova].isin(["yes", "no"])]
        if len(df_valido) > 0:
            acc = accuracy_score(df_valido["DIL"], df_valido[colonna_nuova])
            prec, rec, f1, _ = precision_recall_fscore_support(
                df_valido["DIL"], df_valido[colonna_nuova],
                pos_label="yes", average="binary", zero_division=0
            )
            metriche_df = pd.DataFrame([{
                "annotatore": colonna_nuova,
                "n_valide": len(df_valido),
                "accuracy": round(acc, 4),
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1_score": round(f1, 4),
            }])
            metriche_df.to_csv(percorso_metriche, index=False)
            logger.info(f"Metriche salvate in '{percorso_metriche}'")
    except Exception as e:
        logger.warning(f"Impossibile salvare le metriche: {e}")

    logger.info("=" * 70)
    logger.info("SCRIPT COMPLETATO CON SUCCESSO")
    logger.info("=" * 70)


# ---------------------------------------------------------------------------
# PUNTO DI INGRESSO
# ---------------------------------------------------------------------------
# Lo script viene eseguito solo quando chiamato direttamente,
# non quando importato come modulo da altri script.

if __name__ == "__main__":
    main()
