# Software sviluppati — Progetto annotazione DIL

## `create_chunks.py`
Preprocessing del corpus. Legge i 500 file CSV originali e genera i file derivati aggregando ogni tre frasi consecutive in un'unica unità di analisi (chunk). Output: 500 file CSV con campo `chunk`, per un totale di 536.676 unità.

## `annotate_dil.py`
Script principale di annotazione. Invia ciascun chunk all'API di Claude Sonnet 4.5 per la classificazione binaria DIL (YES/NO), gestisce la concorrenza asincrona, il checkpointing periodico e la scrittura dei file CSV annotati. È l'unico script eseguito in produzione sulla VM AWS.

## `test_local.py`
Test di connettività e correttezza dell'API su un campione minimale di 5 chunk. Utilizzato nella fase di sviluppo per verificare autenticazione e formato delle risposte prima di procedere con test più estesi.

## `test_annotate.py`
Test di throughput e stabilità del rate limiting su un campione intermedio (50–100 chunk). Utilizzato per validare il comportamento del sistema sotto carico prima del deployment.

## `test_complete.py`
Test end-to-end su un file completo. Verifica l'intera pipeline: lettura CSV, annotazione, aggiunta del campo `DIL`, scrittura dell'output. Costituisce il test di accettazione finale prima del deployment in produzione.

## `deploy_to_vm.sh`
Script bash di automazione del deployment. Trasferisce i file necessari sulla VM AWS e avvia la configurazione dell'ambiente remoto.

## `setup_vm.sh`
Script bash di configurazione della VM. Installa le dipendenze Python (`aiohttp`), configura GNU Screen e predispone la struttura delle directory di progetto.
