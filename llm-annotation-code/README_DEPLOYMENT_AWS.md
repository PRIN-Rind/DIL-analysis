# Sistema di Annotazione DIL - Deployment AWS

Sistema completo per annotazione automatica di corpus letterario italiano con discorso indiretto libero (DIL) usando Claude Sonnet 4.5 su VM AWS.

---

## 📁 File disponibili

### Script di annotazione
- **`annotate_dil.py`** - Script principale per annotazione corpus completo
- **`test_annotate.py`** - Script di test su campione ridotto
- **`config.json`** - Configurazione (da completare con API key)

### Script di deployment AWS
- **`setup_vm.sh`** - Setup automatico da eseguire sulla VM
- **`deploy_to_vm.sh`** - Deployment automatico da computer locale a VM
- **`vm_helpers.sh`** - Comandi helper per operazioni comuni

### Documentazione
- **`GUIDA_AWS_PASSO_PASSO.md`** - Guida dettagliata creazione VM AWS
- **`README_ANNOTAZIONE.md`** - Documentazione sistema annotazione
- **Questo file** - Overview generale

---

## 🚀 Quick Start (3 passaggi)

### 1. Configura API key Anthropic

Apri `config.json` e inserisci la tua chiave API:
```json
{
  "anthropic_api_key": "sk-ant-api03-YOUR_KEY_HERE",
  ...
}
```

### 2. Crea VM AWS e ottieni IP

Segui **`GUIDA_AWS_PASSO_PASSO.md`** (10 minuti):
- Crea istanza EC2 t3.micro
- Scarica chiave SSH
- Annota IP pubblico

### 3. Deploy automatico

```bash
bash deploy_to_vm.sh YOUR_VM_IP /path/to/ssh-key.pem
```

Questo script:
- ✅ Carica tutti i file sulla VM
- ✅ Installa dipendenze automaticamente
- ✅ Configura ambiente completo
- ✅ Prepara tutto per l'esecuzione

**Fatto!** La VM è pronta per annotare.

---

## 📊 Specifiche tecniche

### Corpus
- **File:** 500 CSV chunk
- **Chunk totali:** 536.676
- **Sentence totali:** 1.609.559
- **Periodo:** Letteratura italiana 1830-1930

### Costi stimati
- **API Anthropic (Sonnet 4.5):** ~$225
- **VM AWS (t3.micro):** ~$2 per settimana
- **Totale:** ~$230

### Tempi stimati
- **Tier 2 API (50 req/min):** ~7 giorni
- **Tier 3 API (100 req/min):** ~3 giorni
- **Tier 4 API (200 req/min):** ~2 giorni

### Output
- **Formato:** CSV con campo `DIL` aggiunto
- **Valori:** `YES`, `NO`, `UNCLEAR`, `ERROR`
- **Location VM:** `~/dil_project/chunk_annotated/`

---

## 🔧 Workflow completo

### Fase 1: Preparazione locale

```bash
# Verifica file necessari
ls annotate_dil.py config.json chunk/

# Assicurati che config.json abbia API key
cat config.json | grep anthropic_api_key
```

### Fase 2: Setup AWS

Segui **GUIDA_AWS_PASSO_PASSO.md** per:
1. Creare account AWS (se necessario)
2. Lanciare istanza EC2 t3.micro Ubuntu 22.04
3. Configurare security group per SSH
4. Scaricare chiave SSH
5. Ottenere IP pubblico

### Fase 3: Deployment automatico

```bash
# Esegui script deployment
bash deploy_to_vm.sh <VM_IP> <SSH_KEY>

# Esempio:
bash deploy_to_vm.sh 54.123.45.67 ~/Documents/dil-key.pem
```

Lo script fa tutto automaticamente:
- Upload file (script, config, dati)
- Installazione dipendenze (Python, aiohttp, screen)
- Configurazione ambiente
- Creazione struttura directory

### Fase 4: Test preliminare

```bash
# Connetti alla VM
ssh -i ~/Documents/dil-key.pem ubuntu@<VM_IP>

# Test con campione
cd ~/dil_project
python3 test_annotate.py

# Inserisci 50-100 per test
```

Verifica:
- ✓ API funziona
- ✓ Qualità annotazioni è accettabile
- ✓ Costi corrispondono a stime

### Fase 5: Annotazione completa

```bash
# Sulla VM
screen -S dil_annotation
python3 annotate_dil.py

# Conferma con 'yes'
# Premi Ctrl+A poi D per detach

# Disconnetti
exit
```

### Fase 6: Monitoraggio remoto

**Opzione A: Helper script (raccomandato)**

```bash
# Sul tuo computer
source vm_helpers.sh

# Modifica VM_IP e SSH_KEY nel file
# Poi ricarica e usa comandi:

vm_monitor      # Stato corrente
vm_logs         # Log real-time
vm_stats        # Progresso e costi
vm_attach       # Riconnetti a screen
```

**Opzione B: Comandi manuali**

```bash
# Stato
ssh -i <KEY> ubuntu@<IP> '~/dil_project/monitor.sh'

# Log
ssh -i <KEY> ubuntu@<IP> 'tail -f ~/dil_project/logs/annotation.log'
```

### Fase 7: Download risultati

Quando completato:

```bash
# Con helper
vm_download ./risultati

# Manuale
scp -i <KEY> -r ubuntu@<IP>:~/dil_project/chunk_annotated ./risultati/
```

### Fase 8: Cleanup

**EC2 Console → Seleziona istanza → Instance state → Terminate**

⚠️ Scarica TUTTI i risultati prima di terminare!

---

## 🔍 Monitoring e debugging

### Verifica stato annotazione

```bash
vm_monitor
```

Output mostra:
- Sessione screen attiva/inattiva
- Chunk processati / totali
- Percentuale completamento
- Ultimi log

### Statistiche dettagliate

```bash
vm_stats
```

Output:
- Progresso (chunk, %)
- Chunk rimanenti
- Costo corrente
- Stima costo totale

### Log real-time

```bash
vm_logs
# Ctrl+C per uscire
```

### Riattacca a sessione

```bash
ssh -i <KEY> ubuntu@<IP>
screen -r dil_annotation
```

Vedi output in tempo reale. Detach: `Ctrl+A`, `D`

---

## 💡 Features avanzate

### Checkpoint e resume

Il sistema salva stato ogni 1000 chunk in `annotation_state.json`.

Se lo script si interrompe:
1. Riconnetti alla VM
2. Rilancia: `python3 annotate_dil.py`
3. Riprende automaticamente dall'ultimo checkpoint

### Retry automatico

- Ogni richiesta API fallita: 3 retry con exponential backoff
- Rate limit (429): attesa automatica e retry
- Errori temporanei: gestione intelligente

### Gestione errori

Chunk che falliscono dopo tutti i retry:
- Marcati come `ERROR` nel campo DIL
- Conteggiati in `failed_chunks` nello stato
- Log dettagliato per debugging

---

## 📋 Checklist pre-lancio

Verifica questi punti prima di avviare annotazione completa:

- [ ] API key Anthropic configurata in `config.json`
- [ ] Test preliminare completato con successo
- [ ] Qualità annotazioni validata manualmente su campione
- [ ] VM AWS creata e accessibile via SSH
- [ ] Tutti i file caricati sulla VM
- [ ] Spazio disco sufficiente (verifica con `vm_disk`)
- [ ] Budget API approvato (~$225)
- [ ] Screen session avviata correttamente
- [ ] Primo checkpoint salvato (dopo ~10-15 minuti)

---

## ⚠️ Troubleshooting comune

### "Permission denied (publickey)"
```bash
chmod 400 /path/to/key.pem
```

### "Connection refused"
→ Verifica security group AWS permetta SSH dal tuo IP

### Molti chunk con "UNCLEAR"
→ Rivedi definizione DIL nel prompt o aumenta max_tokens in config

### Script si blocca
→ Controlla `annotation.log` per errori API o rate limiting

### "No space left on device"
→ Aumenta volume EBS su AWS Console

### Rate limit costante
→ Riduci `max_concurrent_requests` in config.json

---

## 📈 Ottimizzazioni possibili

### Per velocizzare

1. **Aumenta concurrency** (se hai tier API alto):
   ```json
   "max_concurrent_requests": 15  // da 5 a 15
   ```

2. **Richiedi tier upgrade** ad Anthropic:
   - Email: sales@anthropic.com
   - Spiega progetto di ricerca
   - Possibile upgrade immediato

### Per ridurre costi

1. **Stop VM quando non necessario**:
   - EC2 Console → Stop instance (non terminate!)
   - Riavvia quando serve
   - Costo storage minimo, nessun costo compute

2. **Usa spot instances** (avanzato):
   - 70% sconto su compute
   - Può essere interrotto da AWS
   - Adatto se hai checkpoint robusti

---

## 🆘 Supporto

### Se incontri problemi

1. **Consulta log dettagliato**:
   ```bash
   vm_logs
   ```

2. **Verifica stato**:
   ```bash
   vm_monitor
   cat ~/dil_project/annotation_state.json
   ```

3. **Documenta l'errore**:
   - Quale fase/comando
   - Messaggio errore completo
   - Cosa hai fatto prima

### Risorse utili

- [Documentazione API Anthropic](https://docs.anthropic.com)
- [AWS EC2 User Guide](https://docs.aws.amazon.com/ec2/)
- [Screen Manual](https://www.gnu.org/software/screen/manual/)

---

## 📄 Licenza e crediti

Sistema sviluppato per ricerca accademica su discorso indiretto libero nella letteratura italiana ottocentesca.

**Componenti:**
- Claude Sonnet 4.5 (Anthropic) - Annotazione linguistica
- AWS EC2 - Infrastructure
- Python 3 + aiohttp - Processing asincrono

**Sviluppato:** Febbraio 2026
**Versione:** 1.0

---

## 🎯 Prossimi passi

Dopo aver letto questa overview:

1. **Primo utilizzo:** Segui `GUIDA_AWS_PASSO_PASSO.md`
2. **Dettagli annotazione:** Leggi `README_ANNOTAZIONE.md`
3. **Deploy rapido:** Usa `deploy_to_vm.sh`
4. **Operazioni quotidiane:** Carica `vm_helpers.sh`

**Buona annotazione! 🚀**
