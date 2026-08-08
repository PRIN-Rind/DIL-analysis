# Prompt per Nuova Annotazione DIL con Claude Sonnet

Copia e incolla questo prompt in una nuova sessione di Claude (Cowork o Code):

---

## TASK: Annotazione Discorso Indiretto Libero (DIL) - 500 Trigrammi

### Contesto

Sto conducendo un esperimento di narratologia computazionale per confrontare la capacità di diversi Large Language Models nell'identificare il Discorso Indiretto Libero (DIL) in testi narrativi italiani del periodo 1850-1929.

Ho già completato un'annotazione con un subagent Claude Sonnet che ha ottenuto un'accuracy del 56.4%. Voglio ora ripetere l'esperimento in una nuova sessione per valutare:
1. La variabilità inter-annotatore tra diverse istanze di Claude Sonnet
2. L'effetto della modalità di annotazione (subagent vs sessione diretta)
3. La riproducibilità dei risultati

### File di Input

**File**: `corpus_labelled-trigrams_500_LLM_annotated.csv`

**Struttura**:
- `author`: Autore dell'opera
- `work`: Titolo dell'opera
- `year`: Anno di pubblicazione
- `doc_id`: Identificatore documento
- `text`: Testo del trigramma (3 frasi consecutive)
- `DIL`: Annotazione umana gold standard (yes/no)
- `DIL_Sonnet`: Annotazione precedente di Claude Sonnet (già presente)

### Il Tuo Compito

Devi annotare i 500 trigrammi aggiungendo una **nuova colonna** `DIL_Sonnet_v2` con le tue valutazioni.

**IMPORTANTE**:
- Usa il tuo **vero ragionamento linguistico** come LLM
- NON usare pattern matching o regole programmatiche
- Analizza ogni testo individualmente con attenzione
- Considera il contesto narrativo e le caratteristiche stilistiche

### Definizione di Discorso Indiretto Libero (DIL)

Il Discorso Indiretto Libero è una tecnica narrativa che rappresenta il pensiero o il discorso di un personaggio **senza verbi dichiarativi espliciti** (come "pensò", "disse", "si chiese").

**Caratteristiche distintive**:

1. **Terza persona**: Mantiene la terza persona grammaticale
2. **Assenza di verbi introduttivi**: Nessun "pensò", "disse", "mormorò", ecc.
3. **Punto di vista del personaggio**: Il testo riflette la prospettiva soggettiva del personaggio
4. **Soggettività lessicale**: Uso di lessico coerente con il personaggio, non con il narratore
5. **Marcatori sintattici**: Può includere:
   - Interiezioni: "Oh!", "Ah!", "Dio mio!"
   - Esclamazioni emotive
   - Interrogative retoriche: "Come poteva essere successo?"
   - Modalizzatori: "forse", "certamente", "senza dubbio"
   - Puntini di sospensione che indicano pensieri frammentati

### Esempi di DIL

**Esempio 1** (CON DIL):
> "Mario guardò l'orologio. Sempre in ritardo, come al solito! E lei si sarebbe arrabbiata di nuovo..."

**Spiegazione**: "Sempre in ritardo, come al solito!" è DIL - rappresenta il pensiero di Mario senza "pensò".

**Esempio 2** (CON DIL):
> "Che assurdità! Marta lo aveva davvero lasciato. Dopo dieci anni insieme, come poteva?"

**Spiegazione**: Esclamazione e interrogativa retorica riflettono il punto di vista emotivo del personaggio.

**Esempio 3** (SENZA DIL):
> "Il pontefice morì poco dopo. Gli succedette Pio IX, che nei primi anni del pontificato diede grandi speranze."

**Spiegazione**: Narrazione oggettiva, voce del narratore onnisciente, nessun punto di vista di personaggio.

**Esempio 4** (SENZA DIL):
> "Giovanni pensò che era troppo tardi. Si disse che non sarebbe più tornato."

**Spiegazione**: Presenza esplicita di verbi dichiarativi ("pensò", "si disse") = NON è DIL.

### Casi Difficili da Considerare

**1. DIL dopo verbo dichiarativo**:
> "Pensò che era finita. Tutto perduto, inutile continuare..."
→ La seconda frase È DIL (continua il pensiero senza verbo)

**2. Descrizione psicologica vs DIL**:
> "Un pensiero gli attraversò la mente: non sarebbe mai tornato."
→ NON è DIL (formula introduttiva presente)

**3. Narrazione con tono valutativo**:
> "Era un uomo strano, difficile da capire. I suoi modi erano bruschi."
→ NON è DIL se è voce narrante oggettiva

### Procedura di Annotazione

Per ogni trigramma:

1. **Leggi attentamente** tutto il testo
2. **Identifica** se ci sono pensieri/discorsi di personaggi
3. **Verifica** l'assenza di verbi dichiarativi
4. **Controlla** marcatori sintattici (esclamazioni, interrogative, etc.)
5. **Valuta** se il punto di vista è del personaggio o del narratore
6. **Rispondi**:
   - `yes` se c'è DIL (anche parziale nel trigramma)
   - `no` se non c'è DIL

### Formato Output

Crea un nuovo file CSV chiamato `corpus_labelled-trigrams_500_Sonnet_v2_annotated.csv` con:
- Tutte le colonne originali
- Nuova colonna `DIL_Sonnet_v2` con i tuoi giudizi (yes/no)

### Processo di Esecuzione

1. **Carica il file** di input
2. **Processa i 500 trigrammi** uno per uno
3. **Salva progressivamente** ogni 50 righe per prevenire perdita dati
4. **Al termine**, calcola le seguenti metriche:
   - Accuracy vs annotazioni umane (colonna `DIL`)
   - Matrice di confusione (TP, TN, FP, FN)
   - Precision, Recall, F1-Score
   - Confronto con annotazione precedente (`DIL_Sonnet`):
     * Tasso di accordo inter-annotatore
     * Cohen's Kappa (se possibile)
     * Distribuzione dei disaccordi

### Codice Python Suggerito (Struttura)

```python
import pandas as pd

# Carica dati
df = pd.read_csv('corpus_labelled-trigrams_500_LLM_annotated.csv')

# Aggiungi colonna per nuove annotazioni
df['DIL_Sonnet_v2'] = ''

# Per ogni trigramma
for idx, row in df.iterrows():
    text = row['text']

    # ANALIZZA IL TESTO usando il tuo ragionamento LLM
    # (qui valuti se c'è DIL)

    dil_present = analyze_for_dil(text)  # Funzione che usa il tuo ragionamento

    df.at[idx, 'DIL_Sonnet_v2'] = 'yes' if dil_present else 'no'

    # Salva ogni 50 righe
    if (idx + 1) % 50 == 0:
        df.to_csv('corpus_labelled-trigrams_500_Sonnet_v2_annotated.csv',
                  index=False, encoding='utf-8')
        print(f"Salvate {idx + 1} annotazioni")

# Salvataggio finale
df.to_csv('corpus_labelled-trigrams_500_Sonnet_v2_annotated.csv',
          index=False, encoding='utf-8')

# Calcola metriche
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

y_true = df['DIL']
y_pred = df['DIL_Sonnet_v2']

accuracy = accuracy_score(y_true, y_pred)
precision, recall, f1, _ = precision_recall_fscore_support(
    y_true, y_pred, pos_label='yes', average='binary'
)
cm = confusion_matrix(y_true, y_pred, labels=['no', 'yes'])

print(f"Accuracy: {accuracy:.2%}")
print(f"Precision: {precision:.2%}")
print(f"Recall: {recall:.2%}")
print(f"F1-Score: {f1:.2%}")
print(f"\nConfusion Matrix:")
print(cm)

# Confronto con annotazione precedente
agreement = (df['DIL_Sonnet'] == df['DIL_Sonnet_v2']).sum()
agreement_rate = agreement / len(df)
print(f"\nAccordo con annotazione precedente: {agreement_rate:.2%}")
```

### Output Attesi

Alla fine dovrai fornirmi:

1. **File CSV** con le nuove annotazioni
2. **Report delle metriche**:
   - Performance vs gold standard (umano)
   - Confronto con annotazione precedente
   - Analisi dei casi di disaccordo
3. **Analisi qualitativa**: Breve discussione sui pattern osservati

### Domande?

Se hai dubbi su casi specifici durante l'annotazione, segna l'indice della riga e documentalo per discussione successiva. L'importante è essere consistente nei criteri.

### Aspettative

**Tempo**: ~2-3 ore per processare 500 trigrammi con attenzione
**Accuracy attesa**: 50-65% (il task è difficile anche per gli umani)
**Inter-annotator agreement**: 60-75% tra te e la versione precedente

Grazie e buon lavoro!
