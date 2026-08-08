#!/usr/bin/env bash
#
# Script per testare GPT-5.2 con reasoning effort LOW sui 500 trigrammi.
#

set -euo pipefail

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     TEST GPT-5.2 - Reasoning Effort LOW                   ║"
echo "║     500 Trigrammi - Identificazione DIL                   ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# STEP 1: VERIFICA CHIAVE API
# ============================================================================

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo "❌ ERRORE: Chiave API OpenAI non trovata!"
    echo ""
    echo "Impostare la chiave con:"
    echo "  export OPENAI_API_KEY='sk-proj-XXXXXXXXXXXXXXXX'"
    echo ""
    echo "Oppure eseguire:"
    echo "  OPENAI_API_KEY='sk-proj-XXX' ./test_gpt52_low.sh"
    echo ""
    exit 1
fi

echo "✓ Chiave API trovata (${OPENAI_API_KEY:0:8}...)"
echo ""

# ============================================================================
# STEP 2: INSTALLA/AGGIORNA DIPENDENZE
# ============================================================================

echo "📦 Verifica dipendenze Python..."
echo ""

python3 - <<'PY' >/dev/null 2>&1 || NEED_INSTALL=1
from openai import OpenAI  # noqa: F401
import pandas  # noqa: F401
import tqdm  # noqa: F401
PY

if [[ "${NEED_INSTALL:-0}" -eq 1 ]]; then
    echo "Installazione/aggiornamento librerie (openai, pandas, tqdm)..."
    python3 -m pip install --upgrade "openai>=1.0.0" pandas tqdm
else
    VERSION=$(python3 -c "import openai; print(getattr(openai,'__version__','unknown'))")
    echo "✓ Dipendenze OK (openai version: $VERSION)"
fi

echo ""

# ============================================================================
# STEP 3: VERIFICA FILE
# ============================================================================

echo "📄 Verifica file di input..."

INPUT_FILE="corpus_labelled-trigrams_500_Sonnet_v2_annotated.csv"
if [[ ! -f "$INPUT_FILE" ]]; then
    echo "❌ ERRORE: File di input non trovato: $INPUT_FILE"
    exit 1
fi

echo "✓ File di input trovato ($(ls -lh "$INPUT_FILE" | awk '{print $5}'))"
echo ""

# ============================================================================
# STEP 4: STIMA COSTI (INDICATIVA)
# ============================================================================

echo "💰 Stima indicativa (dipende da pricing/tier e dal prompt):"
echo "   Modello:      GPT-5.2"
echo "   Reasoning:    LOW"
echo "   Trigrammi:    500"
echo ""

# ============================================================================
# STEP 5: CONFERMA
# ============================================================================

read -r -p "Procedere con il test? [y/N] " -n 1 REPLY
echo
if [[ ! "$REPLY" =~ ^[Yy]$ ]]; then
    echo "Test annullato."
    exit 0
fi

echo ""

# ============================================================================
# STEP 6: ESECUZIONE
# ============================================================================

echo "🚀 Avvio test GPT-5.2..."
echo ""

START_TIME=$(date +%s)

python3 annotate_dil_gpt_500_v2.py \
    --api-key "$OPENAI_API_KEY" \
    --model gpt-5.2 \
    --reasoning-effort low \
    --batch-size 5 \
    --eval 
    --compare

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo ""

# ============================================================================
# STEP 7: RIEPILOGO
# ============================================================================

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                    ✅ TEST COMPLETATO                      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "Tempo impiegato: ${MINUTES}m ${SECONDS}s"
echo ""
echo "File generati (default):"
echo "  📄 corpus_labelled-trigrams_500_DUAL_annotated.csv"
echo "  📊 corpus_labelled-trigrams_500_DUAL_annotated_metrics_gpt_5_2.json"
echo "  📈 corpus_labelled-trigrams_500_DUAL_annotated_comparison_gpt_5_2.json"
echo ""
echo "Colonne nel file CSV:"
echo "  • DIL          - Annotazioni umane (gold standard, se presente)"
echo "  • DIL_Sonnet   - Annotazioni Claude Sonnet (se presente)"
echo "  • DIL_gpt_5_2  - Annotazioni GPT-5.2 (reasoning LOW)"
echo ""
