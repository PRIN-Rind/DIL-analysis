# Annotazione automatica del Discorso Indiretto Libero mediante Large Language Model: metodi e design sperimentale

## 1. Corpus

Il corpus impiegato comprende 500 opere della narrativa italiana pubblicate tra il 1830 e il 1930, per un totale di 1.609.559 frasi tokenizzate a livello di *sentence boundary*. I testi sono stati estratti da edizioni digitalizzate e distribuiti in formato tabulare (CSV, codifica UTF-8), con un file per ciascuna opera, corredato dei relativi metadati bibliografici (autore, titolo, anno di pubblicazione).

L'arco cronologico coperto — dall'affermazione del romanzo storico risorgimentale fino alle avanguardie novecentesche — consente di osservare l'evoluzione diacronica del DIL attraverso fasi decisive della storia letteraria italiana: il romanticismo, il verismo, il decadentismo e le sperimentazioni primonovecentesche.

## 2. Unità di analisi: segmentazione in chunk

L'identificazione del DIL richiede un contesto testuale che ecceda la singola frase, poiché il fenomeno si manifesta attraverso indicatori distribuiti su più unità sintattiche — trasposizioni deittiche, adeguamenti dei tempi verbali, modulazioni del registro lessicale — la cui interpretazione dipende dal co-testo immediatamente adiacente. D'altra parte, unità di analisi eccessivamente ampie introducono rumore informativo e incrementano in modo significativo i costi computazionali, tanto in termini di token di input quanto di latenza inferenziale.

Si è dunque adottata una strategia di segmentazione in *chunk* non sovrapposti, ciascuno composto da tre frasi consecutive. Tale granularità rappresenta un compromesso operativo fra due esigenze contrapposte: fornire al modello un contesto sufficiente a riconoscere i marcatori del DIL, e mantenere l'unità di classificazione entro dimensioni gestibili per un task di annotazione su larga scala. I chunk terminali — contenenti meno di tre frasi — sono stati conservati per garantire copertura completa del corpus.

La segmentazione ha prodotto 536.676 chunk, con un rapporto di riduzione di circa 3:1 rispetto alle frasi originali. Ciascun chunk eredita i metadati bibliografici dell'opera di appartenenza.

## 3. Sistema di annotazione

### 3.1 Modello e configurazione

L'annotazione è stata eseguita mediante il modello Claude Sonnet 4.5 (identificatore: `claude-sonnet-4-5-20250929`), accessibile tramite l'API di Anthropic. La scelta del modello è motivata dalla combinazione di capacità di comprensione linguistica su testi letterari in lingua italiana, efficienza inferenziale adeguata a un task di classificazione binaria su larga scala, e rapporto favorevole tra prestazioni e costi per milione di token.

### 3.2 Design del prompt

Il prompt è stato progettato secondo un'architettura a due componenti.

Il *system prompt* fornisce al modello una definizione operativa del DIL fondata sulla tradizione linguistica e narratologica, articolata nei seguenti elementi: (i) caratterizzazione del fenomeno come forma di rappresentazione del discorso in cui la voce del personaggio si inscrive nel tessuto della narrazione in terza persona senza marche introduttive esplicite; (ii) elenco dei tratti diagnostici — trasposizione dei deittici temporali e spaziali, shift dei tempi verbali, modulazione del registro lessicale verso l'idioletto del personaggio, presenza di elementi espressivi o esclamativi non riconducibili al narratore; (iii) istruzioni per la classificazione binaria, con vincolo di output a un singolo token (YES o NO).

Lo *user prompt* contiene il testo del chunk da annotare e la richiesta esplicita di classificazione.

La scelta di un output strettamente binario — anziché una risposta argomentata — è stata adottata per due ragioni complementari: da un lato, la riduzione della lunghezza delle risposte del modello produce una contrazione significativa dei costi di elaborazione (stimata nell'ordine del 62%); dall'altro, un formato di output deterministico e normalizzato semplifica il parsing automatico e minimizza gli errori di estrazione.

### 3.3 Task di classificazione

Per ciascun chunk, il modello produce una classificazione binaria:

- **YES**: il chunk contiene almeno un'occorrenza identificabile di DIL
- **NO**: il chunk non contiene occorrenze identificabili di DIL

Il task è formulato come classificazione a livello di chunk, non di frase. Questa scelta implica che la granularità dell'annotazione è vincolata alla dimensione dell'unità di analisi: un chunk classificato come YES segnala la presenza del fenomeno senza localizzarlo a livello sub-chunk.

## 4. Elaborazione e infrastruttura

### 4.1 Strategia di elaborazione

L'annotazione è stata eseguita in modalità batch asincrona, con un sistema di concorrenza controllata che limita a cinque il numero di richieste API simultanee. Tale vincolo è stato calibrato in funzione dei rate limit imposti dal provider e della necessità di evitare errori di throttling che avrebbero degradato il throughput effettivo.

Il tempo di elaborazione stimato per l'intero corpus è compreso tra 90 e 180 ore, in funzione del tier di accesso API e delle condizioni di carico del servizio.

### 4.2 Persistenza e ripresa

Data la durata dell'elaborazione, è stato implementato un meccanismo di *checkpointing* periodico (intervallo: 1.000 chunk). Lo stato di avanzamento — comprensivo dell'ultimo file completato e dell'ultimo chunk processato — viene serializzato su disco, consentendo la ripresa automatica del processo in caso di interruzione, senza perdita di lavoro né duplicazione di annotazioni.

### 4.3 Gestione degli errori

Le risposte del modello non conformi al formato atteso (ovvero diverse da YES o NO) sono state marcate con il valore ERROR nel dataset di output. Questa strategia consente di preservare la continuità dell'elaborazione senza perdere traccia dei chunk problematici, che possono essere rielaborati in una fase successiva. Il tasso di errore atteso, sulla base dei test preliminari, è inferiore all'1%.

### 4.4 Infrastruttura computazionale

L'elaborazione è stata eseguita su un'istanza cloud AWS EC2 (tipo t3.micro, regione eu-central-1, sistema operativo Ubuntu 22.04 LTS). La scelta di un'istanza a risorse minime è giustificata dalla natura I/O-bound del workload: il collo di bottiglia risiede nella latenza delle chiamate API, non nella capacità computazionale locale. Il costo infrastrutturale risulta trascurabile (~$2 per l'intero ciclo di elaborazione).

## 5. Stima dei costi e vincoli di budget

Il costo dell'annotazione è dominato dal consumo di token API. Assumendo una lunghezza media di circa 300 token di input per chunk e 5 token di output (risposta binaria), il costo totale stimato per il corpus completo è di circa $225 (al netto dei costi infrastrutturali).

Il vincolo del tier di accesso API (limite mensile: $100) ha imposto una suddivisione dell'elaborazione in due fasi: una prima tranche di circa 236.000 chunk (~44% del corpus), seguita dal completamento dopo innalzamento del limite di spesa o reset del ciclo di fatturazione mensile. Il meccanismo di checkpoint garantisce la continuità tra le due fasi senza discontinuità nell'output.

## 6. Validazione preliminare

Prima dell'avvio dell'elaborazione su scala corpus, il sistema è stato sottoposto a una validazione incrementale articolata in tre fasi: (i) test di connettività e correttezza delle chiamate API su un campione ridotto (5 chunk); (ii) test di throughput e stabilità del rate limiting su un campione intermedio (50–100 chunk); (iii) test end-to-end con verifica della correttezza dell'output CSV — preservazione dei metadati, aggiunta del campo di annotazione, integrità delle codifiche — su un file completo.

Va sottolineato che la presente fase del progetto non include una validazione sistematica dell'accuratezza del modello rispetto a un gold standard annotato manualmente. La costruzione di un campione di riferimento per la valutazione inter-annotator — confrontando le classificazioni del modello con annotazioni esperte — costituisce uno sviluppo necessario e previsto.

## 7. Formato dei dati di output

L'output consiste in 500 file CSV (uno per opera), ciascuno contenente tutte le colonne del file di input (metadati bibliografici e campo `chunk`) con l'aggiunta di un campo `DIL` che registra il risultato della classificazione (YES, NO o ERROR). Il formato tabulare è stato scelto per garantire interoperabilità con gli strumenti di analisi quantitativa più diffusi e per facilitare l'aggregazione dei risultati a diversi livelli (opera, autore, decennio, genere letterario).

## 8. Limiti metodologici

È opportuno esplicitare i principali limiti dell'approccio adottato.

In primo luogo, l'assenza di un dataset di riferimento annotato manualmente impedisce, allo stato attuale, una quantificazione rigorosa della precisione e del richiamo del classificatore. Tale lacuna potrà essere colmata in una fase successiva del progetto.

In secondo luogo, la definizione operativa del DIL incorporata nel prompt riflette una sintesi della tradizione critica, ma il fenomeno presenta notoriamente zone di indeterminazione — in particolare nelle forme ibride o attenuate — su cui non esiste consenso unanime nella letteratura specialistica. Il modello potrebbe dunque manifestare bias sistematici legati alla formulazione del prompt.

In terzo luogo, la segmentazione in chunk di tre frasi introduce una granularità fissa che potrebbe risultare inadeguata per fenomeni di DIL estesi su periodi più ampi, oppure per occorrenze brevi confinate a una singola proposizione all'interno di un chunk altrimenti non marcato. La scelta della dimensione del chunk è dunque un parametro metodologicamente rilevante, la cui ottimizzazione richiede indagine empirica.

Infine, la perdita del contesto narrativo più ampio — il modello opera su frammenti isolati senza accesso al resto dell'opera — può ridurre la capacità di riconoscimento nei casi in cui l'identificazione del DIL dipende dalla conoscenza della situazione enunciativa globale.
