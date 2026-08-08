#!/bin/bash
#
# Script per eseguire l'annotazione GPT sui 500 trigrammi
# con valutazione e confronto automatici
#

set -e  # Exit on error

# ============================================================================
# CONFIGURAZIONE
# ============================================================================

# IMPORTANTE: Inserire qui la propria chiave API OpenAI
API_KEY="${OPENAI_API_KEY:-YOUR_API_KEY_HERE}"

# Modello da usare (gpt-4o, gpt-4, gpt-4-turbo, o gpt-3.5-turbo)
# gpt-4o: Migliore rapporto qualità/prezzo (~$0.85 per 500 trigrammi)
MODEL="${MODEL:-gpt-4o}"

# File di input/output
INPUT_FILE="corpus_labelled-trigrams_500_LLM_annotated.csv"
OUTPUT_FILE="corpus_labelled-trigrams_500_DUAL_annotated.csv"

# Parametri di esecuzione
BATCH_SIZE=50

# ============================================================================
# VALIDAZIONE
# ============================================================================

if [ "$API_KEY" = "YOUR_API_KEY_HERE" ]; then
    echo "❌ ERRORE: Impostare la chiave API OpenAI"
    echo ""
    echo "Opzioni:"
    echo "  1. Esportare la variabile d'ambiente:"
    echo "     export OPENAI_API_KEY='sk-proj-...'"
    echo ""
    echo "  2. Modificare questo script alla riga 13:"
    echo "     API_KEY=\"sk-proj-...\""
    echo ""
    exit 1
fi

if [ ! -f "$INPUT_FILE" ]; then
    echo "❌ ERRORE: File di input non trovato: $INPUT_FILE"
    exit 1
fi

# ============================================================================
# VERIFICA DIPENDENZE
# ============================================================================

echo "Verifica dipendenze Python..."
python3 -c "import pandas, openai, tqdm" 2>/dev/null || {
    echo "❌ Dipendenze mancanti. Installare con:"
    echo "   pip install pandas openai tqdm"
    exit 1
}

# ============================================================================
# STIMA COSTI
# ============================================================================

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     ANNOTAZIONE DIL - 500 TRIGRAMMI con $MODEL"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "Configurazione:"
echo "  • Modello:        $MODEL"
echo "  • Input:          $INPUT_FILE"
echo "  • Output:         $OUTPUT_FILE"
echo "  • Batch size:     $BATCH_SIZE"
echo ""

case $MODEL in
    gpt-4o|gpt-4o-mini|chatgpt-4o-latest)
        ESTIMATED_COST="\$0.85"
        ;;
    gpt-4)
        ESTIMATED_COST="\$13.65 (legacy - costoso!)"
        ;;
    gpt-4-turbo)
        ESTIMATED_COST="\$4.60"
        ;;
    gpt-3.5-turbo)
        ESTIMATED_COST="\$0.23"
        ;;
    *)
        ESTIMATED_COST="~\$1-5 (dipende dal modello)"
        ;;
esac

echo "Costo stimato:     $ESTIMATED_COST"
echo "Tempo stimato:     45-60 minuti"
echo ""

# ============================================================================
# CONFERMA UTENTE
# ============================================================================

read -p "Procedere con l'annotazione? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Operazione annullata."
    exit 0
fi

# ============================================================================
# ESECUZIONE
# ============================================================================

echo ""
echo "Avvio annotazione..."
echo ""

START_TIME=$(date +%s)

python3 annotate_dil_gpt_500.py \
    --api-key "$API_KEY" \
    --model "$MODEL" \
    --batch-size "$BATCH_SIZE" \
    --input-file "$INPUT_FILE" \
    --output-file "$OUTPUT_FILE" \
    --eval \
    --compare

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

# ============================================================================
# RIEPILOGO
# ============================================================================

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                    ANNOTAZIONE COMPLETATA                  ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "File generati:"
echo "  ✓ $OUTPUT_FILE"
echo "  ✓ ${OUTPUT_FILE/.csv/_metrics_${MODEL/./-}.json}"
echo "  ✓ ${OUTPUT_FILE/.csv/_comparison_${MODEL/./-}.json}"
echo ""
echo "Tempo impiegato: ${MINUTES}m ${SECONDS}s"
echo ""
echo "Per visualizzare i risultati:"
echo "  • Aprire $OUTPUT_FILE in Excel/LibreOffice"
echo "  • Confrontare colonne DIL_Sonnet e DIL_${MODEL//-/_}"
echo ""
