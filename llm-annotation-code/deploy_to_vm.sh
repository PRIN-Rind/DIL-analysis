#!/bin/bash
#
# Script per deployment file da computer locale a VM AWS
# Da eseguire dal TUO COMPUTER (non sulla VM)
#
# Uso: bash deploy_to_vm.sh <IP_VM> <path_chiave_ssh>
#
# Esempio:
#   bash deploy_to_vm.sh 54.123.45.67 ~/Downloads/dil-annotation-key.pem
#

set -e

# Colori
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Verifica argomenti
if [ $# -lt 2 ]; then
    echo "Uso: bash deploy_to_vm.sh <IP_VM> <path_chiave_ssh>"
    echo ""
    echo "Esempio:"
    echo "  bash deploy_to_vm.sh 54.123.45.67 ~/Downloads/dil-annotation-key.pem"
    echo ""
    exit 1
fi

VM_IP=$1
SSH_KEY=$2
VM_USER="ubuntu"

echo "=========================================="
echo "DEPLOYMENT VERSO VM AWS"
echo "=========================================="
echo ""
echo "VM IP: $VM_IP"
echo "SSH Key: $SSH_KEY"
echo "User: $VM_USER"
echo ""

# Verifica chiave SSH esista
if [ ! -f "$SSH_KEY" ]; then
    print_error "Chiave SSH non trovata: $SSH_KEY"
    exit 1
fi

# Verifica permessi chiave
print_step "Verifica permessi chiave SSH..."
chmod 400 "$SSH_KEY"
print_success "Permessi OK"

# Verifica connessione
print_step "Verifica connessione alla VM..."
if ! ssh -i "$SSH_KEY" -o ConnectTimeout=5 -o StrictHostKeyChecking=no \
    $VM_USER@$VM_IP "echo 'Connessione OK'" > /dev/null 2>&1; then
    print_error "Impossibile connettersi alla VM"
    echo "Verifica:"
    echo "  1. IP corretto: $VM_IP"
    echo "  2. Security group permette SSH dal tuo IP"
    echo "  3. VM è running"
    exit 1
fi
print_success "Connessione verificata"

# Directory corrente (dove sono gli script)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Verifica file necessari
print_step "Verifica file da caricare..."
MISSING_FILES=0

if [ ! -f "$SCRIPT_DIR/annotate_dil.py" ]; then
    print_warning "annotate_dil.py non trovato"
    MISSING_FILES=$((MISSING_FILES + 1))
fi

if [ ! -f "$SCRIPT_DIR/test_annotate.py" ]; then
    print_warning "test_annotate.py non trovato"
    MISSING_FILES=$((MISSING_FILES + 1))
fi

if [ ! -f "$SCRIPT_DIR/config.json" ]; then
    print_warning "config.json non trovato"
    MISSING_FILES=$((MISSING_FILES + 1))
fi

if [ ! -d "$SCRIPT_DIR/chunk" ]; then
    print_warning "Cartella chunk/ non trovata"
    MISSING_FILES=$((MISSING_FILES + 1))
fi

if [ $MISSING_FILES -gt 0 ]; then
    print_error "File mancanti. Assicurati di eseguire lo script dalla cartella corretta."
    exit 1
fi

print_success "Tutti i file trovati"

# Upload setup script
print_step "Caricamento setup script..."
scp -i "$SSH_KEY" -o StrictHostKeyChecking=no \
    "$SCRIPT_DIR/setup_vm.sh" \
    $VM_USER@$VM_IP:~/
print_success "Setup script caricato"

# Upload script Python
print_step "Caricamento script Python..."
scp -i "$SSH_KEY" -o StrictHostKeyChecking=no \
    "$SCRIPT_DIR/annotate_dil.py" \
    "$SCRIPT_DIR/test_annotate.py" \
    $VM_USER@$VM_IP:~/dil_project/
print_success "Script Python caricati"

# Upload config
print_step "Caricamento config.json..."
# Crea config temporaneo con percorsi VM corretti
TMP_CONFIG=$(mktemp)
cat "$SCRIPT_DIR/config.json" | \
    sed 's|"input_dir":.*|"input_dir": "/home/ubuntu/dil_project/chunk",|' | \
    sed 's|"output_dir":.*|"output_dir": "/home/ubuntu/dil_project/chunk_annotated",|' | \
    sed 's|"state_file":.*|"state_file": "/home/ubuntu/dil_project/annotation_state.json",|' | \
    sed 's|"log_file":.*|"log_file": "/home/ubuntu/dil_project/logs/annotation.log"|' \
    > "$TMP_CONFIG"

scp -i "$SSH_KEY" -o StrictHostKeyChecking=no \
    "$TMP_CONFIG" \
    $VM_USER@$VM_IP:~/dil_project/config.json
rm "$TMP_CONFIG"
print_success "Config caricato"

# Upload chunk data
print_step "Caricamento dati chunk/ (può richiedere tempo)..."
echo "Questo passaggio può richiedere diversi minuti..."

# Conta file per stima
NUM_FILES=$(find "$SCRIPT_DIR/chunk" -name "*.csv" | wc -l)
echo "File da caricare: $NUM_FILES"

scp -i "$SSH_KEY" -o StrictHostKeyChecking=no -r \
    "$SCRIPT_DIR/chunk/"*.csv \
    $VM_USER@$VM_IP:~/dil_project/chunk/

print_success "Dati chunk caricati"

# Esegui setup sulla VM
echo ""
print_step "Esecuzione setup automatico sulla VM..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no \
    $VM_USER@$VM_IP "bash ~/setup_vm.sh"

print_success "Setup VM completato"

# Riepilogo finale
echo ""
echo "=========================================="
echo "DEPLOYMENT COMPLETATO!"
echo "=========================================="
echo ""
echo "La VM è pronta per l'annotazione."
echo ""
echo "PROSSIMI PASSI:"
echo ""
echo "1. Connettiti alla VM:"
echo "   ssh -i $SSH_KEY $VM_USER@$VM_IP"
echo ""
echo "2. Testa con campione:"
echo "   cd ~/dil_project"
echo "   python3 test_annotate.py"
echo ""
echo "3. Avvia annotazione completa:"
echo "   screen -S dil_annotation"
echo "   python3 annotate_dil.py"
echo "   # Premi Ctrl+A poi D per detach"
echo ""
echo "4. Monitora da remoto:"
echo "   ssh -i $SSH_KEY $VM_USER@$VM_IP '~/dil_project/monitor.sh'"
echo ""
echo "COMANDI RAPIDI:"
echo "- Connetti: ssh -i $SSH_KEY $VM_USER@$VM_IP"
echo "- Monitor: ssh -i $SSH_KEY $VM_USER@$VM_IP '~/dil_project/monitor.sh'"
echo "- Log: ssh -i $SSH_KEY $VM_USER@$VM_IP 'tail -f ~/dil_project/logs/annotation.log'"
echo ""
