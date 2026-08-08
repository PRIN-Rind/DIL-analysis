#!/bin/bash
#
# Script helper per operazioni comuni con VM
# Da eseguire dal TUO COMPUTER (non sulla VM)
#
# Uso: source vm_helpers.sh
#       poi puoi usare i comandi: vm_connect, vm_monitor, vm_download, etc.
#

# Configurazione (da modificare dopo creazione VM)
export VM_IP="YOUR_VM_IP_HERE"           # es. 54.123.45.67
export SSH_KEY="YOUR_SSH_KEY_PATH_HERE"  # es. ~/Downloads/dil-annotation-key.pem
export VM_USER="ubuntu"

# Colori
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Verifica configurazione
check_config() {
    if [ "$VM_IP" == "YOUR_VM_IP_HERE" ] || [ "$SSH_KEY" == "YOUR_SSH_KEY_PATH_HERE" ]; then
        echo -e "${RED}ERRORE:${NC} Configura VM_IP e SSH_KEY in questo file prima dell'uso"
        return 1
    fi
    if [ ! -f "$SSH_KEY" ]; then
        echo -e "${RED}ERRORE:${NC} Chiave SSH non trovata: $SSH_KEY"
        return 1
    fi
    chmod 400 "$SSH_KEY" 2>/dev/null
    return 0
}

# Connetti alla VM
vm_connect() {
    check_config || return 1
    echo -e "${BLUE}Connessione a VM...${NC}"
    ssh -i "$SSH_KEY" $VM_USER@$VM_IP
}

# Esegui comando sulla VM
vm_exec() {
    check_config || return 1
    if [ $# -eq 0 ]; then
        echo "Uso: vm_exec '<comando>'"
        return 1
    fi
    ssh -i "$SSH_KEY" $VM_USER@$VM_IP "$@"
}

# Monitora stato annotazione
vm_monitor() {
    check_config || return 1
    echo -e "${BLUE}Stato annotazione su VM:${NC}"
    echo ""
    vm_exec "~/dil_project/monitor.sh"
}

# Mostra log real-time
vm_logs() {
    check_config || return 1
    echo -e "${BLUE}Log real-time (Ctrl+C per uscire):${NC}"
    echo ""
    ssh -i "$SSH_KEY" $VM_USER@$VM_IP "tail -f ~/dil_project/logs/annotation.log"
}

# Mostra ultimi N log
vm_tail() {
    local lines=${1:-50}
    check_config || return 1
    echo -e "${BLUE}Ultimi $lines log:${NC}"
    echo ""
    vm_exec "tail -n $lines ~/dil_project/logs/annotation.log"
}

# Riattacca a sessione screen
vm_attach() {
    check_config || return 1
    echo -e "${BLUE}Riattacco a sessione screen...${NC}"
    ssh -i "$SSH_KEY" -t $VM_USER@$VM_IP "screen -r dil_annotation"
}

# Mostra sessioni screen attive
vm_screens() {
    check_config || return 1
    echo -e "${BLUE}Sessioni screen:${NC}"
    vm_exec "screen -ls"
}

# Download risultati
vm_download() {
    check_config || return 1
    local dest=${1:-.}

    echo -e "${BLUE}Download risultati...${NC}"
    echo "Destinazione: $dest"
    echo ""

    # Crea directory locale se non esiste
    mkdir -p "$dest"

    # Scarica chunk_annotated
    echo "Download chunk_annotated/..."
    scp -i "$SSH_KEY" -r \
        $VM_USER@$VM_IP:~/dil_project/chunk_annotated \
        "$dest/"

    # Scarica log e stato
    echo "Download log e stato..."
    scp -i "$SSH_KEY" \
        $VM_USER@$VM_IP:~/dil_project/logs/annotation.log \
        $VM_USER@$VM_IP:~/dil_project/annotation_state.json \
        "$dest/"

    echo ""
    echo -e "${GREEN}Download completato!${NC}"
    echo "File in: $dest"
}

# Upload file singolo alla VM
vm_upload() {
    check_config || return 1
    if [ $# -lt 1 ]; then
        echo "Uso: vm_upload <file_locale> [path_remoto]"
        return 1
    fi

    local local_file=$1
    local remote_path=${2:-~/dil_project/}

    if [ ! -f "$local_file" ]; then
        echo -e "${RED}ERRORE:${NC} File non trovato: $local_file"
        return 1
    fi

    echo -e "${BLUE}Upload $local_file...${NC}"
    scp -i "$SSH_KEY" "$local_file" $VM_USER@$VM_IP:$remote_path
    echo -e "${GREEN}Upload completato${NC}"
}

# Verifica spazio disco sulla VM
vm_disk() {
    check_config || return 1
    echo -e "${BLUE}Spazio disco VM:${NC}"
    echo ""
    vm_exec "df -h | grep -E 'Filesystem|/dev/'"
}

# Stima progresso e costo
vm_stats() {
    check_config || return 1
    echo -e "${BLUE}Statistiche annotazione:${NC}"
    echo ""

    # Leggi stato
    local state=$(vm_exec "cat ~/dil_project/annotation_state.json 2>/dev/null")

    if [ -z "$state" ]; then
        echo "Nessuno stato disponibile (annotazione non ancora avviata)"
        return 0
    fi

    echo "$state" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    total = data.get('total_chunks', 0)
    processed = data.get('processed_chunks', 0)
    failed = data.get('failed_chunks', 0)
    cost = data.get('total_cost', 0)

    if total > 0:
        pct = (processed / total) * 100
        remaining = total - processed
        print(f'Chunk processati: {processed:,}/{total:,} ({pct:.1f}%)')
        print(f'Chunk rimanenti: {remaining:,}')
        print(f'Chunk falliti: {failed:,}')
        print(f'Costo corrente: \${cost:.2f}')
        if processed > 0:
            cost_per_chunk = cost / processed
            estimated_total = cost_per_chunk * total
            print(f'Costo stimato totale: \${estimated_total:.2f}')
    else:
        print('Nessun chunk ancora processato')
except:
    print('Errore parsing stato')
"
}

# Stop annotazione
vm_stop() {
    check_config || return 1
    echo -e "${RED}Fermando annotazione...${NC}"
    read -p "Sei sicuro? (yes/no): " confirm
    if [ "$confirm" == "yes" ]; then
        vm_exec "screen -X -S dil_annotation quit"
        echo -e "${GREEN}Annotazione fermata${NC}"
    else
        echo "Annullato"
    fi
}

# Riavvia annotazione (usa checkpoint)
vm_restart() {
    check_config || return 1
    echo -e "${BLUE}Riavvio annotazione da checkpoint...${NC}"
    vm_exec "screen -S dil_annotation -d -m python3 ~/dil_project/annotate_dil.py"
    echo -e "${GREEN}Annotazione riavviata${NC}"
    echo "Usa 'vm_attach' per vedere output"
}

# Help
vm_help() {
    echo "=========================================="
    echo "VM HELPERS - Comandi disponibili"
    echo "=========================================="
    echo ""
    echo "CONNESSIONE:"
    echo "  vm_connect        - Connetti via SSH alla VM"
    echo "  vm_exec <cmd>     - Esegui comando sulla VM"
    echo ""
    echo "MONITORING:"
    echo "  vm_monitor        - Mostra stato annotazione"
    echo "  vm_logs           - Log real-time (Ctrl+C per uscire)"
    echo "  vm_tail [N]       - Mostra ultimi N log (default 50)"
    echo "  vm_stats          - Statistiche progresso e costi"
    echo "  vm_disk           - Verifica spazio disco"
    echo ""
    echo "SCREEN:"
    echo "  vm_attach         - Riattacca a sessione screen"
    echo "  vm_screens        - Lista sessioni screen attive"
    echo ""
    echo "FILE TRANSFER:"
    echo "  vm_upload <file>  - Upload file alla VM"
    echo "  vm_download [dir] - Download risultati (default: .)"
    echo ""
    echo "CONTROLLO:"
    echo "  vm_stop           - Ferma annotazione"
    echo "  vm_restart        - Riavvia da checkpoint"
    echo ""
    echo "CONFIGURAZIONE CORRENTE:"
    echo "  VM IP: $VM_IP"
    echo "  SSH Key: $SSH_KEY"
    echo ""
}

# Mostra messaggio iniziale
if [ "$VM_IP" == "YOUR_VM_IP_HERE" ]; then
    echo "=========================================="
    echo "VM HELPERS CARICATI"
    echo "=========================================="
    echo ""
    echo "PRIMA VOLTA:"
    echo "Modifica questo file (vm_helpers.sh) e imposta:"
    echo "  - VM_IP: indirizzo IP della tua VM AWS"
    echo "  - SSH_KEY: path alla tua chiave SSH"
    echo ""
    echo "Poi esegui nuovamente: source vm_helpers.sh"
    echo ""
else
    echo -e "${GREEN}VM Helpers caricati!${NC}"
    echo "Usa 'vm_help' per vedere i comandi disponibili"
fi
