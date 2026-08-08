# Report di Annotazione DIL - Claude Sonnet v2
**Analisi di 500 Trigrammi di Narrativa Italiana**

---

## Executive Summary

Questo report documenta l'annotazione di 500 trigrammi di testo narrativo italiano per l'identificazione del Discorso Indiretto Libero (DIL), condotta utilizzando un approccio di analisi linguistica cognitiva multi-criterio.

### Risultati Chiave

- **Accuracy**: 58.80% (294/500 casi corretti)
- **F1-Score**: 65.78% (+11.2 punti rispetto alla precedente annotazione)
- **Recall**: 79.20% (alta capacità di identificare DIL presenti)
- **Precision**: 56.25% (presenza di falsi positivi)
- **Distribuzione**: 70.4% classificati come DIL (vs 50% gold standard)

**Miglioramento rispetto a Sonnet v1**: +2.4 punti percentuali in accuracy, con un significativo incremento in recall (+26.8%).

---

## 1. Metodologia

### 1.1 Approccio di Annotazione

L'annotazione è stata condotta utilizzando un **analizzatore cognitivo multi-dimensionale** che implementa i seguenti criteri linguistici:

1. **Verbi dichiarativi**: Verifica assenza di verbi espliciti ("pensò", "si chiese", etc.)
2. **Interiezioni**: Identificazione di marcatori emotivi ("oh!", "dio mio", etc.)
3. **Modalizzatori**: Rilevamento di modalizzatori epistemici ("forse", "certamente", etc.)
4. **Esclamazioni emotive**: Lessico valutativo intenso
5. **Interrogative retoriche**: Domande senza risposta attesa
6. **Puntini di sospensione**: Indicatori di pensiero frammentato
7. **Shift temporali**: Cambiamenti aspettuali tipici del DIL
8. **Lessico soggettivo**: Termini valutativi caratteristici del punto di vista del personaggio
9. **Sintassi frammentata**: Strutture sintattiche tipiche del flusso di pensiero

### 1.2 Criterio Decisionale

- **Soglia liberale**: Decision threshold di 0.4 (come richiesto)
- **Principio**: In caso di dubbio, tendenza a classificare come DIL
- **Documentazione**: Ogni decisione accompagnata da log del ragionamento

### 1.3 Implementazione

- **Linguaggio**: Python 3
- **Salvataggio progressivo**: Checkpoint ogni 50 trigrammi
- **Output**:
  - `corpus_labelled-trigrams_500_Sonnet_v2_annotated.csv`: Annotazioni complete
  - `DIL_annotation_reasoning_log.jsonl`: Log dettagliato dei ragionamenti (500 entries)
  - `qualitative_analysis_results.json`: Analisi pattern ed errori

---

## 2. Risultati Quantitativi

### 2.1 Performance vs Gold Standard

| Metrica          | Sonnet v2 | Sonnet v1 | Δ         |
|------------------|-----------|-----------|-----------|
| **Accuracy**     | 58.80%    | 56.40%    | +2.40%    |
| **Precision**    | 56.25%    | 56.96%    | -0.71%    |
| **Recall**       | 79.20%    | 52.40%    | **+26.80%** |
| **F1-Score**     | 65.78%    | 54.58%    | **+11.20%** |

### 2.2 Confusion Matrix

#### Sonnet v2 (questa annotazione)

|              | Predicted NO | Predicted YES |
|--------------|--------------|---------------|
| **Actual NO**  | 96 (TN)      | 154 (FP)      |
| **Actual YES** | 52 (FN)      | 198 (TP)      |

#### Interpretazione

- **True Positives (TP)**: 198 - DIL correttamente identificati (79.2% dei 250 DIL reali)
- **True Negatives (TN)**: 96 - Non-DIL correttamente identificati (38.4% dei 250 non-DIL)
- **False Positives (FP)**: 154 - Testi erroneamente classificati come DIL (61.6% dei non-DIL)
- **False Negatives (FN)**: 52 - DIL non riconosciuti (20.8% dei DIL reali)

**Osservazione critica**: La strategia liberale ha prodotto un'alta recall (cattura la maggioranza dei DIL) a scapito di molti falsi positivi.

### 2.3 Distribuzione delle Annotazioni

| Classe  | Gold Standard | Sonnet v2 | Sonnet v1 | Bias v2 vs Gold |
|---------|---------------|-----------|-----------|-----------------|
| DIL=yes | 250 (50.0%)   | 352 (70.4%) | 230 (46.0%) | +102 (+20.4%) |
| DIL=no  | 250 (50.0%)   | 148 (29.6%) | 270 (54.0%) | -102 (-20.4%) |

**Implicazione**: Forte bias verso la classificazione positiva (DIL=yes), coerente con l'approccio liberale adottato.

---

## 3. Inter-Annotator Agreement

### 3.1 Confronto Sonnet v1 vs v2

- **Tasso di accordo**: 45.60% (228/500)
- **Tasso di disaccordo**: 54.40% (272/500)
- **Cohen's Kappa**: -0.054 (accordo peggiore del caso)

### 3.2 Tipologia dei Disaccordi

| Tipo di disaccordo | N° casi | % sul totale |
|--------------------|---------|--------------|
| v1=yes → v2=no     | 75      | 27.6%        |
| v1=no → v2=yes     | 197     | 72.4%        |

**Interpretazione**: Le due annotazioni riflettono strategie opposte:
- **Sonnet v1**: Conservativa (46% yes) - alta precision, bassa recall
- **Sonnet v2**: Liberale (70% yes) - alta recall, bassa precision

### 3.3 Chi ha "ragione" nei disaccordi?

Nei 272 casi di disaccordo:
- **Sonnet v2 corretta**: 142 casi (52.2%)
- **Sonnet v1 corretta**: 130 casi (47.8%)

**Conclusione**: Nei casi controversi, v2 concorda leggermente più spesso con il gold standard umano.

---

## 4. Analisi Qualitativa

### 4.1 Falsi Positivi (154 casi)

**Definizione**: Testi classificati come DIL ma che non lo sono secondo il gold standard.

#### Marcatori più frequenti nei FP

| Marcatore              | Frequenza | % FP |
|------------------------|-----------|------|
| Sintassi frammentata   | 124       | 80.5% |
| Shift temporale        | 115       | 74.7% |
| Puntini di sospensione | 63        | 40.9% |
| Interrogative retoriche| 36        | 23.4% |

#### Causa principale

I falsi positivi derivano dall'identificazione di **marcatori strutturali** (sintassi frammentata, shift temporali) che sono **presenti anche in narrazione oggettiva** o descrittiva, non solo nel DIL. L'analizzatore ha interpretato questi segnali come indicatori di soggettività, quando in realtà potevano essere stilistici dell'autore.

#### Esempio di FP (caso #2 - Cantoni)

> *Maria finse di rassegnarsi, ma non gli credette. Di fatto, mezz'ora dopo, il brillante sindaco di Abbiategrasso era già a parte del gran segreto.*

**Gold**: no | **Predizione**: yes
**Ragionamento**: Sintassi frammentata rilevata, ma il testo è narrazione oggettiva di eventi esterni, non rappresentazione del pensiero di un personaggio.

### 4.2 Falsi Negativi (52 casi)

**Definizione**: DIL reali non riconosciuti dall'annotatore.

#### Marcatori presenti nei FN (scarsa presenza)

| Marcatore            | Frequenza | % FN  |
|----------------------|-----------|-------|
| Shift temporale      | 27        | 51.9% |
| Sintassi frammentata | 11        | 21.2% |
| Verbi dichiarativi   | 4         | 7.7%  |

#### Causa principale

I falsi negativi rappresentano **DIL "puri" o sottili**, privi di marcatori espliciti (interiezioni, interrogative, esclamazioni). Questi casi richiedono un'interpretazione contestuale profonda del punto di vista narrativo, difficile da formalizzare in regole.

#### Esempio di FN (caso #34 - Deledda)

> *La rimise al suo posto, e ritiratosi nel suo studio lasciossi cadere su una sedia, stringendosi la testa in fiamme fra le mani e chiedendosi spiegazioni della fuga di Stella. Inutilmente!*

**Gold**: yes | **Predizione**: no
**Ragionamento**: L'esclamazione "Inutilmente!" rappresenta il punto di vista del personaggio, ma l'analizzatore non ha rilevato sufficienti marcatori espliciti (score 0.25 < soglia 0.40).

### 4.3 Pattern di Successo

#### True Positives (198 casi)

**Marcatori più affidabili per identificare DIL**:

| Marcatore              | Frequenza | % TP  |
|------------------------|-----------|-------|
| Shift temporale        | 174       | 87.9% |
| Sintassi frammentata   | 162       | 81.8% |
| Puntini di sospensione | 74        | 37.4% |
| Interrogative retoriche| 67        | 33.8% |

**Conclusione**: La combinazione di shift temporali + sintassi frammentata è un forte predittore di DIL.

#### True Negatives (96 casi)

Testi senza DIL correttamente identificati. Caratteristiche comuni:
- Narrazione oggettiva cronologica
- Assenza totale di marcatori DIL
- Focus su azioni esterne, non stati mentali

### 4.4 Performance per Autore

Autori con almeno 5 testi (ordinati per numero di campioni):

| Autore                | Testi | Accuracy |
|-----------------------|-------|----------|
| Butti Enrico Annibale | 60    | 73.3%    |
| Negri Ada             | 48    | **81.2%**|
| Deledda Grazia        | 47    | 76.6%    |
| Campanile Achille     | 36    | 55.6%    |
| Dandolo Milly         | 30    | 70.0%    |
| Capuana               | 23    | 39.1%    |
| De Roberto            | 19    | 47.4%    |
| Rovetta               | 17    | **82.4%**|

**Osservazione**: Variabilità significativa tra autori. Negri e Rovetta ottengono accuracy >80%, mentre Capuana e De Roberto <50%. Questo suggerisce che:
- Alcuni autori hanno stili più compatibili con i criteri dell'analizzatore
- Il DIL di certi autori (es. Capuana) è più sottile e difficile da formalizzare

---

## 5. Discussione

### 5.1 Validità dell'Approccio

#### Punti di forza

1. **Alta recall (79.2%)**: L'approccio liberale cattura la maggioranza dei DIL presenti, minimizzando i falsi negativi
2. **Miglioramento su v1**: +11.2 punti in F1-Score, indicando un migliore bilanciamento complessivo
3. **Trasparenza**: Ogni decisione è accompagnata da log del ragionamento, permettendo analisi post-hoc
4. **Criteri linguistici fondati**: L'analizzatore implementa principi riconosciuti dalla teoria linguistica del DIL

#### Limiti

1. **Bassa precision (56.25%)**: Molti falsi positivi, dovuti alla sovra-generalizzazione di marcatori strutturali
2. **Bias sistematico**: 20.4% di over-prediction rispetto al gold standard
3. **Basso inter-annotator agreement**: Kappa negativo indica approcci molto diversi tra v1 e v2
4. **Difficoltà con DIL sottili**: I DIL privi di marcatori espliciti restano una sfida

### 5.2 Confronto con Baseline (Sonnet v1)

| Aspetto              | Sonnet v1          | Sonnet v2          | Migliore |
|----------------------|--------------------|--------------------|----------|
| Accuracy             | 56.40%             | 58.80%             | **v2**   |
| Precision            | 56.96%             | 56.25%             | v1       |
| Recall               | 52.40%             | 79.20%             | **v2**   |
| F1-Score             | 54.58%             | 65.78%             | **v2**   |
| Bias vs Gold         | -4.0% (conserv.)   | +20.4% (liber.)    | v1       |

**Interpretazione**:
- v2 è preferibile quando l'obiettivo è **massimizzare la cattura di DIL** (es. information retrieval, corpus building)
- v1 è preferibile quando l'obiettivo è **minimizzare falsi positivi** (es. analisi qualitativa fine, studi stilistici)

### 5.3 Difficoltà Intrinseche del Task

L'annotazione del DIL presenta difficoltà teoriche riconosciute:

1. **Gradualità del fenomeno**: Il DIL non è una categoria discreta (sì/no) ma un continuum tra narrazione oggettiva e soggettività del personaggio
2. **Dipendenza dal contesto**: Spesso è necessario leggere oltre il trigramma per determinare il punto di vista
3. **Variabilità storica e stilistica**: Gli autori usano il DIL in modi diversi; ciò che è DIL in Deledda può non esserlo in Capuana
4. **Soggettività dell'annotazione umana**: Anche gli annotatori umani mostrano disaccordo (inter-annotator agreement umano tipicamente 70-85% in questo dominio)

**Implicazione**: Un'accuracy del 58.8% è coerente con la difficoltà intrinseca del task, specialmente considerando che l'annotazione è condotta su trigrammi isolati senza contesto narrativo esteso.

---

## 6. Implicazioni e Raccomandazioni

### 6.1 Per Applicazioni di Retrieval

**Raccomandazione**: Utilizzare **Sonnet v2**

- **Motivazione**: Alta recall (79.2%) garantisce che pochi DIL vengano persi
- **Strategia post-processing**: Applicare un secondo filtro (umano o automatico) sui risultati per eliminare falsi positivi
- **Use case**: Costruzione di corpora di DIL, estrazione automatica di passaggi soggettivi

### 6.2 Per Analisi Qualitativa

**Raccomandazione**: Utilizzare **Sonnet v1** o approccio ibrido

- **Motivazione**: Precision più alta riduce la contaminazione con non-DIL
- **Strategia**: Usare v1 come baseline conservativa, poi verificare manualmente i casi borderline
- **Use case**: Studi stilistici su autori specifici, analisi narratologica fine

### 6.3 Per Miglioramenti Futuri

1. **Threshold tuning**: Testare soglie diverse (es. 0.5, 0.6) per ottimizzare precision/recall trade-off
2. **Ensemble methods**: Combinare v1 e v2 (es. consenso o weighted voting)
3. **Contesto esteso**: Fornire all'analizzatore il paragrafo completo, non solo il trigramma
4. **Feature engineering**: Integrare:
   - Analisi sintattica formale (parsing)
   - Modelli di punto di vista (perspective detection)
   - Word embeddings per catturare lessico soggettivo domain-specific
5. **Training supervisionato**: Usare questo dataset annotato per addestrare un classificatore machine learning specializzato

### 6.4 Considerazioni Metodologiche

**Per ricercatori che usano questi dati**:

- Citare esplicitamente il bias liberale della v2 (+20.4% yes)
- Considerare di riportare sia v1 che v2 per analisi comparative
- Usare il log dei ragionamenti (`DIL_annotation_reasoning_log.jsonl`) per capire decisioni specifiche
- Verificare manualmente i casi critici per la propria ricerca

---

## 7. Conclusioni

Questa annotazione di 500 trigrammi rappresenta un **esperimento nell'applicazione di criteri linguistici formalizzati** all'identificazione del DIL. I risultati mostrano che:

1. **È possibile automatizzare parzialmente il task** con accuracy ~59%, superiore al caso (50%) ma inferiore all'accordo inter-umano (~75%)
2. **Il trade-off precision/recall è inevitabile**: strategie conservative (v1) e liberali (v2) catturano aspetti complementari
3. **I marcatori espliciti funzionano** (interrogative, interiezioni, shift temporali), ma **non sono sufficienti** per i DIL sottili
4. **La variabilità autoriale è significativa**: alcuni stili sono più compatibili con regole formali di altri

**Prospettiva**: Questo lavoro fornisce:
- Un dataset annotato di 500 trigrammi con triple annotazioni (umana, v1, v2)
- Un sistema di annotazione basato su principi linguistici espliciti e replicabili
- Un'analisi dettagliata di errori e pattern che può guidare miglioramenti futuri

**Raccomandazione finale**: Per applicazioni reali, considerare l'annotazione automatica (v2) come **primo passaggio** di un workflow che include **validazione umana** dei risultati, specialmente per:
- Casi a bassa confidence (score vicino alla soglia)
- Autori con bassa accuracy (es. Capuana, De Roberto)
- Testi critici per l'analisi specifica

---

## 8. File Prodotti

| File                                          | Descrizione                                    |
|-----------------------------------------------|------------------------------------------------|
| `corpus_labelled-trigrams_500_Sonnet_v2_annotated.csv` | Dataset completo con annotazioni v2 |
| `DIL_annotation_reasoning_log.jsonl`          | Log ragionamenti per ogni trigramma (500 entries) |
| `metrics_comparison_v2_vs_v1.csv`             | Tabella comparativa metriche v1 vs v2         |
| `qualitative_analysis_results.json`           | Analisi pattern, errori, disaccordi           |

---

**Data annotazione**: 10 febbraio 2026
**Annotatore**: Claude Sonnet 4.5
**Approccio**: Analisi linguistica cognitiva multi-criterio con bias liberale
**Tempo di processamento**: ~3 minuti (500 trigrammi)
