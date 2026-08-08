# Identificazione Automatica del Discorso Indiretto Libero mediante Large Language Models: Esperimento su 500 Trigrammi

## Executive Summary

Questo report documenta un esperimento di annotazione automatica del Discorso Indiretto Libero (DIL) su un campione stratificato di 500 trigrammi estratti da un corpus di narrativa italiana del periodo 1850-1929. L'obiettivo è valutare le capacità di Claude Sonnet 4.5 nell'identificare questa complessa categoria narratologica mediante ragionamento linguistico genuino, confrontando le performance con annotazioni umane gold standard.

**Risultati principali:**
- **Accuracy complessiva**: 56.4% (282/500 annotazioni corrette)
- **Precision**: 56.96%
- **Recall**: 52.40%
- **F1-Score**: 54.58%
- **Errori totali**: 218 (99 falsi positivi, 119 falsi negativi)

I risultati rivelano un calo significativo rispetto all'esperimento pilota su 100 trigrammi (accuracy 89%), suggerendo che il task è più complesso di quanto inizialmente stimato e che il campione ridotto non era rappresentativo della difficoltà reale.

---

## 1. Metodologia

### 1.1 Corpus e Campionamento

**Corpus di partenza**: 29.293 trigrammi sequenziali (gruppi di 3 frasi consecutive non sovrapposte) estratti da 36 opere narrative italiane pubblicate tra il 1850 e il 1929, con annotazioni umane per discorso diretto (DD), discorso indiretto (DI), discorso indiretto libero (DIL) e soliloquio.

**Distribuzione nel corpus completo:**
- DIL presente: 865 trigrammi (3.0%)
- DIL assente: 28.428 trigrammi (97.0%)

**Strategia di campionamento**: Campionamento stratificato per garantire rappresentatività bilanciata:
- **500 trigrammi totali**
- **250 trigrammi con DIL=yes** (campionati casualmente dai 865 disponibili)
- **250 trigrammi con DIL=no** (campionati casualmente dai 28.428 disponibili)
- **Random seed**: 42 (per riproducibilità)

La stratificazione è necessaria per evitare lo sbilanciamento estremo della classe positiva (3%) che renderebbe impossibile una valutazione significativa. Nel campione stratificato, la distribuzione è 50/50.

### 1.2 Prompt di Annotazione

L'annotazione è stata condotta utilizzando Claude Sonnet 4.5 con il seguente prompt strutturato:

**Sistema:**
```
Sei un esperto linguista. Analizza il testo fornito per identificare
la presenza di discorso indiretto libero.
```

**Utente (per ogni trigramma):**
```
Analizza il seguente blocco di testo e determina se contiene
discorso indiretto libero (anche parzialmente).

Discorso indiretto libero: Rappresentazione del pensiero/discorso
di un personaggio senza verbi dichiarativi ('pensò', 'disse').
Caratteristiche:
* Terza persona
* Assenza di formule introduttive esplicite
* Punto di vista del personaggio
* Può includere interiezioni, esclamazioni, interrogative
* Lessico coerente con il personaggio

Esempi:
* 'Mario guardò l'orologio. Sempre in ritardo, come al solito.'
* 'Che assurdità! Marta lo aveva davvero lasciato.'

Testo da analizzare: {testo}

Rispondi solo: YES (se presente discorso indiretto libero)
o NO (se assente).
```

### 1.3 Processo di Annotazione

1. **Caricamento**: Lettura del campione stratificato (500 trigrammi) dal file `corpus_labelled-trigrams_500_sample.csv`
2. **Annotazione**: Elaborazione sequenziale di ciascun trigramma mediante ragionamento LLM (NON pattern matching o regole programmatiche)
3. **Salvataggio progressivo**: Output salvato ogni 50 trigrammi per prevenire perdita di dati
4. **Output finale**: File `corpus_labelled-trigrams_500_LLM_annotated.csv` con nuova colonna `DIL_Sonnet` contenente le predizioni

**Nota critica**: L'annotazione è stata eseguita da un subagent per gestire il carico computazionale dei 500 testi. Questo potrebbe aver introdotto variabilità rispetto all'esperimento pilota su 100 trigrammi.

---

## 2. Risultati

### 2.1 Matrice di Confusione

|                | **Pred NO** | **Pred YES** | **Totale** |
|----------------|-------------|--------------|------------|
| **Gold NO**    | 151 (TN)    | 99 (FP)      | 250        |
| **Gold YES**   | 119 (FN)    | 131 (TP)     | 250        |
| **Totale**     | 270         | 230          | 500        |

- **True Positives (TP)**: 131 – LLM e umano concordano sulla presenza di DIL
- **True Negatives (TN)**: 151 – LLM e umano concordano sull'assenza di DIL
- **False Positives (FP)**: 99 – LLM identifica DIL dove l'annotatore umano non lo vede
- **False Negatives (FN)**: 119 – LLM non identifica DIL dove l'annotatore umano lo vede

### 2.2 Metriche di Performance

| Metrica                     | Valore    | Formula                    | Interpretazione                          |
|-----------------------------|-----------|-----------------------------|------------------------------------------|
| **Accuracy**                | **56.40%** | (TP+TN) / Total            | Proporzione di predizioni corrette       |
| **Precision**               | **56.96%** | TP / (TP+FP)               | Proporzione di predizioni positive corrette |
| **Recall (Sensitivity)**    | **52.40%** | TP / (TP+FN)               | Proporzione di casi positivi identificati |
| **Specificity**             | **60.40%** | TN / (TN+FP)               | Proporzione di casi negativi identificati |
| **F1-Score**                | **54.58%** | 2·(P·R)/(P+R)              | Media armonica di precision e recall     |

**Interpretazione**:
- L'accuracy del 56.4% indica che poco più della metà delle annotazioni sono corrette
- La precision del 57% significa che quando l'LLM identifica DIL, ha ragione solo nel 57% dei casi
- Il recall del 52% significa che l'LLM identifica solo circa metà dei casi di DIL presenti
- L'F1-score del 54.6% indica un bilanciamento moderato tra precision e recall, ma entrambi sono bassi

### 2.3 Distribuzione delle Predizioni

|             | **Gold (Umano)** | **Pred (Sonnet)** | **Differenza** |
|-------------|------------------|-------------------|----------------|
| **DIL=yes** | 250 (50.0%)      | 230 (46.0%)       | -20 (-4.0%)    |
| **DIL=no**  | 250 (50.0%)      | 270 (54.0%)       | +20 (+4.0%)    |

L'LLM tende leggermente verso predizioni conservative (più "no" che "yes"), identificando DIL in 230 casi rispetto ai 250 annotati dagli umani.

### 2.4 Analisi degli Errori

**Distribuzione degli errori:**
- **Falsi Positivi**: 99 casi (19.8% del totale) – LLM sovra-identifica DIL
- **Falsi Negativi**: 119 casi (23.8% del totale) – LLM sotto-identifica DIL
- **Errori totali**: 218 casi (43.6% del totale)

**Bilanciamento degli errori**: A differenza dell'esperimento pilota (che mostrava solo falsi negativi), in questo test l'LLM commette errori in entrambe le direzioni, con una leggera prevalenza di falsi negativi.

---

## 3. Analisi Qualitativa degli Errori

### 3.1 Esempi di Falsi Positivi (LLM identifica DIL, umano NO)

#### Caso FP #1: Saluzzo
> "Furono mal intese queste voci dalla turbata Eleonora, ma scesero nel cuore del capitano, ed accrebbero il suo dubitare. Tacque Giorgio della Trinità, e le due eccelse donne tacevano similmente; ma per la prima volta sorse un pensiero della sorte propria in cuore d'Isabella, ed una luce divina per la..."

**Gold**: no | **Pred**: yes

**Analisi**: L'LLM probabilmente interpreta "sorse un pensiero della sorte propria in cuore d'Isabella" come rappresentazione del pensiero del personaggio, ma manca la vera soggettività tipica del DIL.

#### Caso FP #2: Caracciolo
> "Il pontefice Gregorio se ne morì, poco dopo aver fatto questo regalo alla capitale di Ferdinando II, che cordialmente ne lo ringraziò, e Mastai gli succedette alla Santa Sede. Nei primordi del suo pontificato sanno tutti che dava Pio IX somme speranze di sé. Egli era non pure liberale di fatto, ma..."

**Gold**: no | **Pred**: yes

**Analisi**: Testo narrativo storico-descrittivo. L'LLM potrebbe confondere il tono valutativo ("sanno tutti", "somme speranze") con soggettività del personaggio, ma è voce narrante onnisciente.

### 3.2 Esempi di Falsi Negativi (LLM NON identifica DIL, umano SÌ)

#### Caso FN #1: Dandolo, "Il figlio del mio dolore" (1921)
> "Forse egli era veramente buono e non voleva che Lalage soffrisse; o forse temeva una certa inconscia responsabilità... Si fermò su questo pensiero, pensò ch'essi erano egoisti, essi ch'erano tranquilli ed uniti, e credevano che fosse facile agli altri qualunque sacrificio, essi che possedevano tutto..."

**Gold**: yes | **Pred**: no

**Analisi**: Chiaro esempio di DIL con pensieri del personaggio ("Forse... o forse..."), ma la presenza del verbo "pensò" potrebbe aver confuso l'LLM nonostante il DIL continui dopo.

#### Caso FN #2: Collodi, "Macchiette" (1880)
> "Oh! Fatima! come il tuo amore mi avrebbe reso beato! Tu non saprai mai, divina fanciulla, le lacrime che mi costi! tu non saprai mai le notti insonni, che ho passate per te!..."

**Gold**: yes | **Pred**: no

**Analisi**: Esclamazioni dirette ("Oh!"), apostrofi ("divina fanciulla"), interrogative retoriche – tutti marcatori classici di DIL. L'LLM non ha riconosciuto il pattern nonostante gli indicatori espliciti.

#### Caso FN #3: Rovetta, "Gerolamo Ninnoli" (1882)
> "Adesso anche egli ghignava; l'ora tanto aspettata, sognata, era giunta. Che importava a lui della palla che gli bruciava nel petto?... Il marchese di Tracy pareva un gigante di granito...."

**Gold**: yes | **Pred**: no

**Analisi**: Interrogativa retorica ("Che importava..."), punto di vista del personaggio che minimizza la ferita. Chiaro DIL non riconosciuto.

### 3.3 Pattern di Errore Identificati

**Falsi Positivi (sovra-identificazione):**
1. Confusione tra voce narrante valutativa e punto di vista del personaggio
2. Interpretazione di descrizioni psicologiche come DIL
3. Sensibilità eccessiva a frasi con verbi di cognizione/emozione

**Falsi Negativi (sotto-identificazione):**
1. Mancato riconoscimento quando DIL segue verbi dichiarativi
2. Difficoltà con interrogative retoriche e esclamazioni
3. Problemi con DIL breve o frammentato
4. Confusione in presenza di discorso diretto misto

---

## 4. Distribuzione degli Errori per Autore

**Top 10 autori con più errori (in ordine di tasso di errore):**

| Autore                | Errori | Totale | Tasso Errore |
|-----------------------|--------|--------|--------------|
| Caracciolo            | 8      | 12     | **66.7%**    |
| Dandolo (Milly)       | 18     | 30     | **60.0%**    |
| Emiliani              | 5      | 10     | **50.0%**    |
| Deledda (Grazia)      | 23     | 47     | **48.9%**    |
| Rovetta               | 8      | 17     | **47.1%**    |
| Butti (Enrico A.)     | 28     | 60     | **46.7%**    |
| Campanile (Achille)   | 16     | 36     | **44.4%**    |
| Collodi (Carlo)       | 8      | 18     | **44.4%**    |
| Negri (Ada)           | 20     | 48     | **41.7%**    |
| Capuana               | 7      | 23     | **30.4%**    |

**Osservazioni:**
- Autori del primo Novecento (Dandolo 1921, Campanile 1929) mostrano tassi di errore elevati
- Autori veristi (Capuana) mostrano tassi di errore più bassi
- Possibile correlazione tra periodo storico e complessità del DIL

---

## 5. Distribuzione degli Errori per Periodo

| Periodo      | Errori | Totale | Tasso Errore |
|--------------|--------|--------|--------------|
| 1850-1870    | N/A    | N/A    | N/A          |
| 1871-1900    | 59     | 125    | **47.2%**    |
| 1901-1929    | 54     | 114    | **47.4%**    |

**Osservazioni:**
- Nessuna differenza significativa tra fine Ottocento e primo Novecento
- Entrambi i periodi mostrano tassi di errore quasi identici (~47%)
- Il periodo 1850-1870 non è rappresentato nel campione (probabilmente per scarsità di testi nel corpus)

---

## 6. Confronto con Esperimento Pilota (100 Trigrammi)

| Metrica           | Test 100 (Pilota) | Test 500 (Attuale) | Differenza     |
|-------------------|-------------------|--------------------|----------------|
| **Sample Size**   | 100               | 500                | +400           |
| **Accuracy**      | **89.0%**         | 56.4%              | **-32.6%**     |
| **Precision**     | **100.0%**        | 57.0%              | **-43.0%**     |
| **Recall**        | 78.0%             | 52.4%              | -25.6%         |
| **F1-Score**      | **87.6%**         | 54.6%              | **-33.0%**     |
| **False Positives** | **0**           | 99                 | +99            |
| **False Negatives** | 11              | 119                | +108           |

### 6.1 Analisi del Calo Prestazionale

**Fattori identificati:**

1. **Effetto dimensione del campione**: Il sample di 100 trigrammi era probabilmente più semplice o fortunato. Sample più grandi rivelano la vera complessità del task.

2. **Variabilità tra annotatori LLM**:
   - Test 100: annotato dall'agente principale (main agent)
   - Test 500: annotato da subagent per gestione computazionale
   - Possibile differenza nei criteri di valutazione

3. **Sbilanciamento degli errori**:
   - Test 100: Solo falsi negativi (11), nessun falso positivo → LLM conservativo
   - Test 500: Bilanciato (99 FP, 119 FN) → LLM meno coerente

4. **Rappresentatività del campione**:
   - Test 100 potrebbe aver sovra-rappresentato casi facili
   - Test 500 include maggiore varietà stilistica e temporale

### 6.2 Implicazioni per la Validità Statistica

Il calo di performance suggerisce che:
- Il test 100 forniva una **sovrastima** delle capacità reali dell'LLM
- È necessaria **cautela nell'interpretazione di esperimenti su piccoli campioni**
- Sample di 500+ trigrammi offre stima più affidabile della performance reale
- La varianza inter-annotatore tra agenti LLM è un fattore critico da considerare

---

## 7. Discussione

### 7.1 Complessità del Task

I risultati evidenziano che l'identificazione automatica del DIL è un task **significativamente più complesso** di quanto suggerito dall'esperimento pilota. Le ragioni includono:

1. **Ambiguità intrinseca**: Molti casi presentano confini sfumati tra narrazione e DIL
2. **Variabilità stilistica**: Autori diversi utilizzano il DIL in modi diversi
3. **Evoluzione diacronica**: Il DIL evolve nel tempo (realismo → modernismo)
4. **Dipendenza dal contesto**: Spesso necessario contesto più ampio per disambiguare

### 7.2 Limitazioni dell'Approccio LLM

**Punti di forza:**
- Capacità di catturare aspetti pragmatici e stilistici
- Non richiede feature engineering manuale
- Potenziale di generalizzazione cross-linguistica

**Punti di debolezza:**
- Performance inferiore alle aspettative (56% vs. 89% atteso)
- Sovra-identificazione in testi narrativi descrittivi
- Sotto-identificazione con marcatori espliciti (esclamazioni, interrogative)
- Variabilità tra diversi agenti/istanze dello stesso modello

### 7.3 Confronto con Approcci NLP Tradizionali

L'esperimento precedente aveva testato un approccio **pattern-matching** basato su regole, ottenendo:
- Accuracy: **69%**
- Precision: inferiore per eccesso di falsi positivi
- Recall: migliore ma con rumore

**Conclusione comparativa:**
- LLM puro (Test 500): 56.4% accuracy
- Pattern matching: 69% accuracy
- LLM ottimizzato (Test 100): 89% accuracy (ma probabilmente sovrastimato)

L'approccio tradizionale NLP supera l'LLM in questo test, ma richiede:
- Feature engineering manuale
- Tuning di soglie
- Bassa generalizzabilità

### 7.4 Inter-Annotator Agreement

Un aspetto critico emerso è la **variabilità tra istanze LLM**:
- Agente principale (Test 100): 89% accuracy
- Subagent (Test 500): 56.4% accuracy

Questa discrepanza suggerisce:
- Necessità di studiare l'inter-annotator agreement tra agenti LLM
- Possibile utilizzo di ensemble methods (voting multiplo)
- Importanza della calibrazione del prompt

---

## 8. Conclusioni e Direzioni Future

### 8.1 Conclusioni Principali

1. **Performance reale**: L'LLM Claude Sonnet 4.5 ottiene un'accuracy del 56.4% nell'identificazione del DIL su un campione rappresentativo di 500 trigrammi, significativamente inferiore all'89% del test pilota.

2. **Complessità del task**: L'identificazione del DIL è un problema computazionalmente difficile che richiede comprensione profonda di pragmatica, stile e contesto narrativo.

3. **Limitazioni metodologiche**: Esperimenti su campioni piccoli (100 trigrammi) possono fornire stime inaffidabili. Sono necessari sample di almeno 500+ casi per valutazioni robuste.

4. **Variabilità LLM**: Differenze significative tra diverse istanze/agenti dello stesso modello sollevano questioni sulla riproducibilità e consistenza.

### 8.2 Raccomandazioni Operative

Per l'annotazione del corpus completo (29.293 trigrammi):

**Opzione 1 - Approccio ibrido**:
- Usare LLM per pre-annotazione
- Revisione umana dei casi predetti come DIL (230/500 = 46%)
- Focus su falsi positivi (che costituiscono il 43% delle predizioni positive)

**Opzione 2 - Ensemble di annotatori**:
- Utilizzare 3-5 istanze LLM diverse
- Votazione a maggioranza per ogni trigramma
- Può mitigare varianza inter-annotatore

**Opzione 3 - Calibrazione del prompt**:
- Analisi qualitativa approfondita degli errori
- Raffinamento del prompt con esempi negativi
- Few-shot learning con esempi calibrati

### 8.3 Direzioni di Ricerca Future

1. **Studio dell'inter-annotator agreement**:
   - Calcolo del Cohen's kappa tra multipli annotatori LLM
   - Confronto con inter-annotator agreement umano
   - Analisi delle cause di disagreement

2. **Miglioramento del prompt**:
   - Prompt engineering con esempi negativi espliciti
   - Chain-of-thought reasoning per decisioni complesse
   - Calibrazione con feedback sui casi di errore

3. **Fine-tuning supervisionato**:
   - Utilizzo delle annotazioni umane per fine-tuning
   - Valutazione costo-beneficio rispetto a prompt engineering

4. **Analisi linguistica degli errori**:
   - Studio sistematico dei pattern sintattici e stilistici associati agli errori
   - Identificazione di sottocategorie di DIL più/meno problematiche
   - Costruzione di tassonomia degli errori

5. **Estensione cross-linguistica**:
   - Valutazione su corpora in altre lingue
   - Studio della generalizzabilità del fenomeno DIL

---

## 9. Riferimenti Bibliografici

### Corpus e Dati
- Corpus RIND - PRIN 2022: Romanzi italiani periodo 1850-1929 (36 opere, 87.841 frasi annotate)

### Metodologia
- File di input: `corpus_labelled-trigrams.csv` (29.293 trigrammi)
- Sample: `corpus_labelled-trigrams_500_sample.csv` (500 trigrammi stratificati)
- Output: `corpus_labelled-trigrams_500_LLM_annotated.csv` (annotazioni LLM)
- Metriche: `metrics_500_sample.csv`
- Analisi errori: `errors_analysis_500.csv`

### Modello
- **LLM**: Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)
- **Prompt**: Definizione DIL + caratteristiche + esempi
- **Temperatura**: 0.0 (deterministico, nel test 100; default nel test 500)
- **Max tokens**: Non specificato per risposta yes/no

---

## Appendice A: Statistiche Dettagliate

### A.1 Metriche Complete

```
Total Annotations:     500
True Positives (TP):   131
True Negatives (TN):   151
False Positives (FP):  99
False Negatives (FN):  119

Accuracy:   (TP + TN) / Total = 282 / 500 = 56.40%
Precision:  TP / (TP + FP)     = 131 / 230 = 56.96%
Recall:     TP / (TP + FN)     = 131 / 250 = 52.40%
Specificity: TN / (TN + FP)    = 151 / 250 = 60.40%
F1-Score:   2·P·R / (P + R)    = 54.58%
```

### A.2 Distribuzione Autori nel Sample

Autori più rappresentati nel campione di 500 trigrammi:
1. Butti (Enrico Annibale): 60 trigrammi
2. Negri (Ada): 48 trigrammi
3. Deledda (Grazia): 47 trigrammi
4. Campanile (Achille): 36 trigrammi
5. Dandolo (Milly): 30 trigrammi
6. Capuana: 23 trigrammi
7. Collodi (Carlo): 18 trigrammi
8. Rovetta: 17 trigrammi
9. Caracciolo: 12 trigrammi
10. Emiliani: 10 trigrammi

### A.3 File Generati

| File                                          | Dimensione | Descrizione                          |
|-----------------------------------------------|------------|--------------------------------------|
| `corpus_labelled-trigrams_500_sample.csv`     | ~45 KB     | Sample stratificato di input         |
| `corpus_labelled-trigrams_500_LLM_annotated.csv` | ~45 KB  | Annotazioni LLM complete             |
| `metrics_500_sample.csv`                      | ~1 KB      | Metriche di performance              |
| `errors_analysis_500.csv`                     | ~30 KB     | Analisi dettagliata errori (218 casi)|

---

**Data esperimento**: Febbraio 2026
**Modello**: Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)
**Autore**: Esperimento di narratologia computazionale - RIND PRIN 2022
