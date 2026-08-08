# Guida ai Test Prima del Deployment

Hai tre script di test disponibili, ognuno con uno scopo specifico.

---

## 📝 Script disponibili

### 1️⃣ `test_local.py` - Test Veloce API

**Scopo:** Verifica rapida che tutto funzioni (configurazione, API, connessione)

**Cosa fa:**
- ✓ Verifica config.json
- ✓ Verifica dipendenze (aiohttp)
- ✓ Testa 5 chunk con API
- ✓ Mostra risultati a schermo
- ✗ NON scrive file output

**Quando usarlo:** Prima volta, per verificare setup base

**Esecuzione:**
```bash
python3 test_local.py
```

**Costo:** ~$0.01 (5 chunk)

---

### 2️⃣ `test_annotate.py` - Test Statistiche Dettagliate

**Scopo:** Test approfondito con statistiche complete

**Cosa fa:**
- ✓ Annota N chunk personalizzabile (50-100 consigliato)
- ✓ Statistiche dettagliate (token, costi, distribuzione)
- ✓ Esempi di annotazioni
- ✓ Throughput e performance
- ✗ NON scrive file output

**Quando usarlo:** Per validare qualità annotazioni e stime costi

**Esecuzione:**
```bash
python3 test_annotate.py
# Ti chiederà quanti chunk testare
```

**Costo:** ~$0.02-0.10 (50-100 chunk)

---

### 3️⃣ `test_complete.py` - Test Completo con Output ⭐

**Scopo:** Test end-to-end completo con file CSV annotato

**Cosa fa:**
- ✓ Annota un file completo (o subset)
- ✓ **SCRIVE file CSV con campo DIL**
- ✓ Salva in `chunk_annotated_test/`
- ✓ Anteprima risultati
- ✓ Statistiche complete

**Quando usarlo:** Prima del deployment finale, per vedere output reale

**Esecuzione:**
```bash
python3 test_complete.py
```

**Interattivo:**
- Seleziona file più piccolo automaticamente
- Scegli: file completo o primi N chunk
- Conferma costo stimato

**Costo:** ~$0.02-0.50 (dipende da opzioni)

**Output:**
```
./chunk_annotated_test/
└── NomeFile_annotated_test.csv
```

---

## 🎯 Workflow Raccomandato

### Step 1: Setup iniziale
```bash
python3 test_local.py
```
✓ Verifica che API funzioni

### Step 2: Validazione qualità
```bash
python3 test_annotate.py
# Testa 50-100 chunk
```
✓ Verifica qualità annotazioni
✓ Controlla costi effettivi

### Step 3: Test completo ⭐
```bash
python3 test_complete.py
# Annota 50-200 chunk con output CSV
```
✓ Verifica scrittura file
✓ Ispeziona output finale
✓ Valida struttura CSV

### Step 4: Deployment
Se tutto OK → Procedi con AWS deployment!

---

## 📊 Confronto rapido

| Feature | test_local | test_annotate | test_complete ⭐ |
|---------|-----------|---------------|-----------------|
| Chunk | 5 (fisso) | Personalizzabile | Personalizzabile |
| Statistiche | Base | Dettagliate | Complete |
| Output CSV | ❌ | ❌ | ✅ |
| Anteprima | ❌ | Limitata | Completa |
| Costo | ~$0.01 | ~$0.02-0.10 | ~$0.02-0.50 |
| Tempo | <1 min | 1-3 min | 2-10 min |

---

## 🔍 Cosa Verificare nell'Output

Quando esegui `test_complete.py`, controlla:

### 1. Struttura CSV
```bash
head -n 3 chunk_annotated_test/*.csv
```

Dovresti vedere:
```csv
"filename","nome","titolo","anno","chunk","DIL"
"Autore-Titolo-Anno","Autore","Titolo","1890","Testo chunk...","YES"
...
```

### 2. Distribuzione annotazioni

Aspettati una distribuzione sensata:
- **YES**: 10-30% (dipende dal corpus)
- **NO**: 70-90%
- **UNCLEAR**: <5% (idealmente 0%)
- **ERROR**: 0% (se tutto funziona)

### 3. Qualità annotazioni

Apri il file e verifica manualmente alcuni chunk:
- I "YES" contengono effettivamente DIL?
- I "NO" sono corretti?
- Ci sono falsi positivi/negativi?

---

## ⚠️ Troubleshooting

### "Nessun file CSV trovato"
→ Verifica che `config.json` abbia `input_dir` corretto
→ Esegui da directory con cartella `chunk/`

### "API key error"
→ Verifica API key in `config.json`

### Molti "UNCLEAR"
→ Il prompt potrebbe necessitare tuning
→ Valuta se aggiustare definizione DIL

### "ERROR" nelle annotazioni
→ Problema API temporaneo
→ Rilancia il test

---

## 💡 Suggerimenti

1. **Inizia piccolo:** 5-10 chunk con `test_local.py`
2. **Valida bene:** 50-100 chunk con `test_annotate.py`
3. **Test finale:** File completo con `test_complete.py`
4. **Analizza manualmente:** Apri CSV e verifica 10-20 annotazioni random
5. **Se tutto OK:** Procedi con deployment AWS!

---

## 📍 File di output

Tutti i test salvano output in directory separate:

```
./
├── chunk/                    # Input originale
├── chunk_annotated_test/     # Output test_complete.py
├── chunk_annotated/          # Output annotazione completa (dopo AWS)
└── config.json
```

I file di test (`chunk_annotated_test/`) possono essere eliminati dopo verifica.

---

## ✅ Checklist Pre-Deployment

Prima di fare deployment AWS, assicurati:

- [ ] `test_local.py` completato con successo
- [ ] `test_annotate.py` mostra costi ragionevoli
- [ ] `test_complete.py` produce CSV valido
- [ ] Distribuzione annotazioni sensata (non tutto YES o NO)
- [ ] Validazione manuale su 10-20 chunk OK
- [ ] Campo DIL presente e formato corretto
- [ ] Nessun "ERROR" nelle annotazioni test

**Se tutti ✓ → Sei pronto per AWS!**
