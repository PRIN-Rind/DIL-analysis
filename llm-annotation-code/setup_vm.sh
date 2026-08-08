#!/bin/bash
#
# Script di setup automatico per VM AWS
# Da eseguire sulla VM dopo prima connessione SSH
#
# Uso: bash setup_vm.sh
#

set -e  # Exit on error

echo "=========================================="
echo "SETUP VM PER ANNOTAZIONE DIL"
echo "=========================================="
echo ""

# Colori per output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Step 1: Aggiorna sistema
print_step "Aggiornamento sistema..."
sudo apt update -qq
sudo apt upgrade -y -qq
print_success "Sistema aggiornato"

# Step 2: Installa Python e pip
print_step "Installazione Python3 e pip..."
sudo apt install -y python3 python3-pip
print_success "Python installato: $(python3 --version)"

# Step 3: Installa dipendenze Python
print_step "Installazione dipendenze Python (aiohttp)..."
pip3 install aiohttp --quiet
print_success "Dipendenze installate"

# Step 4: Installa screen per persistenza
print_step "Installazione screen..."
sudo apt install -y screen
print_success "Screen installato"

# Step 5: Crea struttura directory
print_step "Creazione directory progetto..."
cd ~
mkdir -p dil_project/chunk
mkdir -p dil_project/chunk_annotated
mkdir -p dil_project/logs
cd dil_project
print_success "Directory create in ~/dil_project"

# Step 6: Crea .screenrc per configurazione ottimale
print_step "Configurazione screen..."
cat > ~/.screenrc << 'EOF'
# Disabilita startup message
startup_message off

# Scrollback buffer grande
defscrollback 10000

# Status bar
hardstatus alwayslastline
hardstatus string '%{= kG}[%{G}%H%{g}][%= %{= kw}%?%-Lw%?%{r}(%{W}%n*%f%t%?(%u)%?%{r})%{w}%?%+Lw%?%?%= %{g}][%{B}%Y-%m-%d %{W}%c%{g}]'

# UTF-8
defutf8 on
EOF
print_success "Screen configurato"

# Step 7: Crea script helper per avvio rapido
print_step "Creazione script helper..."

# Script per avviare annotazione
cat > ~/dil_project/start_annotation.sh << 'EOF'
#!/bin/bash
cd ~/dil_project
screen -S dil_annotation python3 annotate_dil.py
EOF
chmod +x ~/dil_project/start_annotation.sh

# Script per monitoraggio
cat > ~/dil_project/monitor.sh << 'EOF'
#!/bin/bash
echo "=== STATO ANNOTAZIONE ==="
echo ""
if screen -list | grep -q dil_annotation; then
    echo "✓ Sessione screen attiva"
else
    echo "✗ Nessuna sessione screen attiva"
fi
echo ""
if [ -f ~/dil_project/annotation_state.json ]; then
    echo "--- State File ---"
    cat ~/dil_project/annotation_state.json | python3 -m json.tool
    echo ""
fi
if [ -f ~/dil_project/annotation.log ]; then
    echo "--- Ultimi log ---"
    tail -20 ~/dil_project/annotation.log
fi
EOF
chmod +x ~/dil_project/monitor.sh

print_success "Script helper creati"

# Step 8: Verifica installazione
print_step "Verifica installazione..."
echo ""
echo "Python: $(python3 --version)"
echo "pip: $(pip3 --version)"
echo "aiohttp: $(python3 -c 'import aiohttp; print(aiohttp.__version__)')"
echo "screen: $(screen --version | head -1)"
echo ""
print_success "Tutte le dipendenze verificate"

# Step 9: Info finale
echo ""
echo "=========================================="
echo "SETUP COMPLETATO!"
echo "=========================================="
echo ""
echo "Directory progetto: ~/dil_project"
echo ""
echo "PROSSIMI PASSI:"
echo "1. Carica i file necessari:"
echo "   - annotate_dil.py"
echo "   - test_annotate.py"
echo "   - config.json (con API key)"
echo "   - cartella chunk/ con i CSV"
echo ""
echo "2. Aggiorna config.json con i percorsi:"
echo "   nano ~/dil_project/config.json"
echo "   Imposta:"
echo "   - input_dir: /home/ubuntu/dil_project/chunk"
echo "   - output_dir: /home/ubuntu/dil_project/chunk_annotated"
echo "   - state_file: /home/ubuntu/dil_project/annotation_state.json"
echo "   - log_file: /home/ubuntu/dil_project/logs/annotation.log"
echo ""
echo "3. Test preliminare:"
echo "   cd ~/dil_project && python3 test_annotate.py"
echo ""
echo "4. Avvia annotazione:"
echo "   ~/dil_project/start_annotation.sh"
echo "   oppure manualmente:"
echo "   screen -S dil_annotation"
echo "   python3 annotate_dil.py"
echo ""
echo "COMANDI UTILI:"
echo "- Monitora stato: ~/dil_project/monitor.sh"
echo "- Riattacca a screen: screen -r dil_annotation"
echo "- Detach da screen: Ctrl+A, poi D"
echo "- Vedi log real-time: tail -f ~/dil_project/logs/annotation.log"
echo ""
