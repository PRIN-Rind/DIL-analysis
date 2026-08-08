# Guida AWS EC2 - Passo dopo Passo

Questa guida ti accompagna nella creazione di una VM AWS per eseguire l'annotazione DIL.

**Tempo stimato:** 10-15 minuti
**Costo:** ~$2 per settimana di processing (o gratis con Free Tier)

---

## FASE 1: Creazione Account AWS (se necessario)

### Step 1.1: Registrazione

1. Vai su [aws.amazon.com](https://aws.amazon.com)
2. Clicca **"Create an AWS Account"**
3. Inserisci:
   - Email
   - Password
   - Account name (es. "dil-research")
4. Clicca **"Continue"**

### Step 1.2: Informazioni contatto

1. Seleziona **"Personal"** come tipo account
2. Compila:
   - Nome completo
   - Numero di telefono
   - Indirizzo
3. Accetta i termini
4. Clicca **"Continue"**

### Step 1.3: Metodo di pagamento

1. Inserisci carta di credito/debito
2. Indirizzo di fatturazione
3. **NOTA:** AWS richiede carta ma molti servizi sono gratuiti con Free Tier

### Step 1.4: Verifica identità

1. Riceverai chiamata/SMS con codice di verifica
2. Inserisci il codice
3. Conferma

### Step 1.5: Seleziona piano

1. Seleziona **"Basic Support - Free"**
2. Clicca **"Complete sign up"**

✅ **Account creato!** Riceverai email di conferma in pochi minuti.

---

## FASE 2: Accesso a Console EC2

### Step 2.1: Login

1. Vai su [console.aws.amazon.com](https://console.aws.amazon.com)
2. Clicca **"Sign In"**
3. Inserisci email e password

### Step 2.2: Seleziona regione

1. In alto a destra, vedi nome regione (es. "N. Virginia", "Ireland")
2. Clicca sul nome
3. **Seleziona una regione vicina a te:**
   - Italia/Europa: **Europe (Ireland)** `eu-west-1`
   - USA East: **US East (N. Virginia)** `us-east-1`

⚠️ **IMPORTANTE:** Ricorda la regione selezionata!

### Step 2.3: Vai a servizio EC2

1. Nella barra di ricerca in alto, scrivi **"EC2"**
2. Clicca su **"EC2"** (dovrebbe essere prima opzione)
3. Sei ora nella console EC2

---

## FASE 3: Creazione Istanza (VM)

### Step 3.1: Launch Instance

1. Clicca il grande pulsante arancione **"Launch Instance"**
2. Si apre il form di configurazione

### Step 3.2: Nome e tag

**Name:** `dil-annotation-vm`

### Step 3.3: Application and OS Images (AMI)

1. Nella sezione **"Application and OS Images"**
2. Seleziona **"Ubuntu"** (logo arancione/rosso)
3. Dropdown sotto Ubuntu:
   - Seleziona **"Ubuntu Server 22.04 LTS"**
   - Architettura: **64-bit (x86)**

✅ Dovrebbe dire "Free tier eligible"

### Step 3.4: Instance type

1. Nella sezione **"Instance type"**
2. Cerca **"t3.micro"** (o **"t2.micro"** se in Free Tier)
3. Selezionalo dalla lista
   - 1 vCPU
   - 1 GiB Memory

✅ Se nuovo account, vedrai "Free tier eligible"

### Step 3.5: Key pair (cruciale!)

1. Nella sezione **"Key pair (login)"**
2. Clicca **"Create new key pair"**

**Nel popup:**
- **Key pair name:** `dil-annotation-key`
- **Key pair type:** `RSA`
- **Private key file format:**
  - **Mac/Linux:** `.pem`
  - **Windows (PuTTY):** `.ppk`
  - **Windows (altri):** `.pem`

3. Clicca **"Create key pair"**
4. **SCARICA e SALVA** il file `.pem` in luogo sicuro
   - ⚠️ **IMPORTANTE:** Non potrai scaricarlo di nuovo!
   - Suggerimento: rinomina in `dil-key.pem` e metti in `~/Documents/`

### Step 3.6: Network settings

Nella sezione **"Network settings"**, clicca **"Edit"**

**Firewall (security groups):**
1. Seleziona **"Create security group"**
2. **Security group name:** `dil-ssh-access`
3. **Description:** `Allow SSH for DIL annotation`

**Inbound security group rules:**
- Dovrebbe esserci già regola per SSH
- **Type:** `SSH`
- **Port:** `22`
- **Source type:** Seleziona **"My IP"** (più sicuro)

### Step 3.7: Configure storage

1. Nella sezione **"Configure storage"**
2. **Size (GiB):** `20` (dovrebbe essere default)
3. **Volume type:** `gp3` (default, performante)

✅ 20 GB sono sufficienti per script + dati + risultati

### Step 3.8: Advanced details

❌ **Non modificare** - lascia valori di default

### Step 3.9: Summary e Launch

1. A destra vedi **"Summary"** con stima costi
2. **Number of instances:** `1`
3. Verifica riepilogo:
   - Ubuntu 22.04 LTS
   - t3.micro (o t2.micro)
   - 20 GB storage
   - Security group con SSH

4. Clicca **"Launch instance"** (pulsante arancione)

✅ Vedrai: **"Successfully initiated launch of instance"**

5. Clicca **"View all instances"**

---

## FASE 4: Attendere avvio e ottenere IP

### Step 4.1: Monitorare avvio

1. Nella lista **"Instances"**, vedi la tua VM
2. **Instance state:** passa da "Pending" → "Running" (1-2 minuti)
3. **Status check:** aspetta che diventi "2/2 checks passed"

⏱️ Attendi che entrambi siano pronti (totale: 2-3 minuti)

### Step 4.2: Ottenere indirizzo IP pubblico

1. Seleziona (checkbox) la tua istanza
2. In basso, guarda **"Details"**
3. Trova **"Public IPv4 address"**
4. **COPIA questo IP** (es. `54.123.45.67`)

📋 Salva questo IP - ti servirà per connetterti!

---

## FASE 5: Prima connessione SSH

### Step 5.1: Prepara terminale

**Mac/Linux:**
1. Apri **Terminal**

**Windows:**
1. Apri **PowerShell** o **Windows Terminal**
   - (oppure installa [Git Bash](https://gitforwindows.org/))

### Step 5.2: Imposta permessi chiave

**Mac/Linux/Windows (PowerShell):**
```bash
chmod 400 ~/Documents/dil-key.pem
```

(Adatta il path se hai salvato la chiave altrove)

### Step 5.3: Connetti via SSH

**Sintassi:**
```bash
ssh -i /path/to/dil-key.pem ubuntu@YOUR_VM_IP
```

**Esempio concreto:**
```bash
ssh -i ~/Documents/dil-key.pem ubuntu@54.123.45.67
```

(Sostituisci con il TUO IP dalla Step 4.2)

### Step 5.4: Conferma connessione

Alla prima connessione vedrai:
```
The authenticity of host '54.123.45.67' can't be established.
...
Are you sure you want to continue connecting (yes/no)?
```

Scrivi: **`yes`** e premi Invio

✅ **SEI CONNESSO!** Vedrai prompt: `ubuntu@ip-xxx-xxx-xxx-xxx:~$`

---

## FASE 6: Deployment automatizzato

Ora che hai la VM pronta, disconnetti temporaneamente per eseguire il deployment automatico:

### Step 6.1: Disconnetti da VM

```bash
exit
```

Torna al tuo computer locale.

### Step 6.2: Prepara file

Assicurati di avere nella stessa cartella:
- `deploy_to_vm.sh` (script automatico)
- `annotate_dil.py`
- `test_annotate.py`
- `config.json` (con tua API key Anthropic configurata!)
- cartella `chunk/` con i CSV

### Step 6.3: Esegui deployment

```bash
bash deploy_to_vm.sh YOUR_VM_IP ~/Documents/dil-key.pem
```

Esempio:
```bash
bash deploy_to_vm.sh 54.123.45.67 ~/Documents/dil-key.pem
```

Lo script:
1. ✓ Verifica connessione
2. ✓ Carica file sulla VM
3. ✓ Esegue setup automatico (installa dipendenze)
4. ✓ Configura ambiente
5. ✓ Prepara tutto per l'esecuzione

⏱️ Tempo: 5-10 minuti (dipende da quantità dati)

### Step 6.4: Verifica completamento

Alla fine vedrai:
```
==========================================
DEPLOYMENT COMPLETATO!
==========================================

La VM è pronta per l'annotazione.
```

---

## FASE 7: Test e avvio annotazione

### Step 7.1: Riconnetti alla VM

```bash
ssh -i ~/Documents/dil-key.pem ubuntu@YOUR_VM_IP
```

### Step 7.2: Test preliminare

```bash
cd ~/dil_project
python3 test_annotate.py
```

Testa con 50-100 chunk per verificare:
- API funziona
- Qualità annotazioni
- Costi effettivi

### Step 7.3: Avvia annotazione completa

```bash
screen -S dil_annotation
cd ~/dil_project
python3 annotate_dil.py
```

Conferma con `yes` quando richiesto.

### Step 7.4: Detach da screen (lascia girare)

Premi: **`Ctrl+A`** poi **`D`**

Vedrai: `[detached from dil_annotation]`

### Step 7.5: Disconnetti tranquillamente

```bash
exit
```

🎉 **L'annotazione continua a girare sulla VM!**

---

## FASE 8: Monitoraggio remoto

### Metodo 1: Helper script (più facile)

Sul tuo computer locale:

```bash
# Carica helper
source vm_helpers.sh

# Modifica vm_helpers.sh con VM_IP e SSH_KEY
# Poi ricarica:
source vm_helpers.sh

# Usa comandi semplici:
vm_monitor    # Stato annotazione
vm_logs       # Log real-time
vm_stats      # Statistiche e costi
```

### Metodo 2: SSH manuale

```bash
# Stato
ssh -i ~/Documents/dil-key.pem ubuntu@YOUR_VM_IP '~/dil_project/monitor.sh'

# Log
ssh -i ~/Documents/dil-key.pem ubuntu@YOUR_VM_IP 'tail -f ~/dil_project/logs/annotation.log'

# Riattacca a screen
ssh -i ~/Documents/dil-key.pem ubuntu@YOUR_VM_IP
screen -r dil_annotation
```

---

## FASE 9: Download risultati

Quando l'annotazione è completata:

### Metodo 1: Helper script

```bash
source vm_helpers.sh
vm_download ./risultati_annotazione
```

### Metodo 2: SCP manuale

```bash
scp -i ~/Documents/dil-key.pem -r \
    ubuntu@YOUR_VM_IP:~/dil_project/chunk_annotated \
    ./risultati/
```

---

## FASE 10: Cleanup e costi

### Quando hai finito e scaricato i risultati:

1. Vai su **EC2 Console**
2. Seleziona la tua istanza
3. **Instance state** → **Terminate instance**
4. Conferma

⚠️ **Questo elimina definitivamente la VM e interrompe i costi**

### Conservare dati prima di terminare (opzionale):

1. Crea snapshot del volume EBS
2. O scarica tutti i file importanti con SCP

---

## Troubleshooting

### "Permission denied (publickey)"
→ Verifica path chiave SSH corretto e permessi 400

### "Connection refused"
→ Verifica security group permetta SSH dal tuo IP

### "No such file or directory"
→ Verifica di essere nella cartella corretta con i file necessari

### Script deployment fallisce
→ Verifica che config.json abbia API key Anthropic configurata

### VM non risponde dopo ore
→ Probabilmente tutto OK, usa vm_monitor per verificare stato

---

## Comandi utili rapidi

```bash
# Connetti
ssh -i ~/Documents/dil-key.pem ubuntu@YOUR_VM_IP

# Monitor
ssh -i ~/Documents/dil-key.pem ubuntu@YOUR_VM_IP '~/dil_project/monitor.sh'

# Riattacca screen
ssh -i ~/Documents/dil-key.pem ubuntu@YOUR_VM_IP
screen -r dil_annotation

# Download
scp -i ~/Documents/dil-key.pem -r ubuntu@YOUR_VM_IP:~/dil_project/chunk_annotated ./

# Stop VM (per risparmiare)
# EC2 Console → Instance → Instance state → Stop instance
```

---

## Stima costi finale

| Durata | Costo (t3.micro) | Note |
|--------|------------------|------|
| 2 giorni | $0.50 | Con tier 3 API |
| 7 giorni | $1.75 | Con tier 2 API |
| 30 giorni | $7.50 | Caso estremo |

**Free Tier:** Se account nuovo, primi 12 mesi sono gratuiti (750 ore/mese t2.micro)

---

## Hai bisogno di aiuto?

Se incontri problemi durante uno di questi step, fammi sapere esattamente:
1. Quale fase/step
2. Cosa hai fatto
3. Messaggio di errore esatto

Ti aiuterò a risolvere!
