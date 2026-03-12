#!/bin/bash
# Computational Theseus Toolkit — Folder structure setup script
# Usage: Run this script inside the flat folder containing all files.
#   cd /folder/containing/files
#   bash setup_structure.sh

set -e  # Stop on error

echo "🔧 Creating folder structure..."

# ── Create folders ────────────────────────────────────────────────────────────
mkdir -p ct_toolkit/core
mkdir -p ct_toolkit/divergence
mkdir -p ct_toolkit/endorsement/probes/domain_probes
mkdir -p ct_toolkit/identity/templates
mkdir -p ct_toolkit/kernels
mkdir -p ct_toolkit/provenance/vault
mkdir -p ct_toolkit/utils
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p tests/fixtures
mkdir -p examples
mkdir -p docs

echo "✅ Folders created"

# ── Move files ───────────────────────────────────────────────────────────────

# core/
mv __init__.py       ct_toolkit/__init__.py
mv wrapper.py        ct_toolkit/core/wrapper.py
mv kernel.py         ct_toolkit/core/kernel.py
mv compatibility.py  ct_toolkit/core/compatibility.py
mv exceptions.py     ct_toolkit/core/exceptions.py

# identity/
mv embedding.py      ct_toolkit/identity/embedding.py
mv general.yaml      ct_toolkit/identity/templates/general.yaml
mv medical.yaml      ct_toolkit/identity/templates/medical.yaml
mv finance.yaml      ct_toolkit/identity/templates/finance.yaml
mv defense.yaml      ct_toolkit/identity/templates/defense.yaml

# kernels/  (default and defense kernels — different from templates!)
# NOTE: There are two defense.yaml files with the same name:
#   - defense.yaml (identity template)  → ct_toolkit/identity/templates/defense.yaml
#   - defense.yaml (kernel)             → ct_toolkit/kernels/defense.yaml
# You should manually download and place the kernel versions here:
#   ct_toolkit/kernels/default.yaml
#   ct_toolkit/kernels/defense.yaml
mv default.yaml      ct_toolkit/kernels/default.yaml  2>/dev/null || \
  echo "⚠️  default.yaml not found — create ct_toolkit/kernels/default.yaml manually"

# provenance/
mv log.py            ct_toolkit/provenance/log.py

# utils/
# logger.py needs to be downloaded separately — create if not present here
if [ -f logger.py ]; then
  mv logger.py ct_toolkit/utils/logger.py
else
  cat > ct_toolkit/utils/logger.py << 'PYEOF'
"""ct_toolkit.utils.logger — Centralized logging."""
import logging


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "[%(levelname)s] %(name)s: %(message)s"
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
PYEOF
  echo "✅ logger.py created"
fi

# examples/
mv quickstart_openai.py          examples/quickstart_openai.py
mv enterprise_military_medical.py examples/enterprise_military_medical.py

# tests/
mv test_all.py tests/unit/test_all.py

# pyproject.toml remains in the root directory
echo "✅ Files moved"

# ── Create __init__.py files ──────────────────────────────────────────────────
touch ct_toolkit/core/__init__.py
touch ct_toolkit/divergence/__init__.py
touch ct_toolkit/endorsement/__init__.py
touch ct_toolkit/endorsement/probes/__init__.py
touch ct_toolkit/identity/__init__.py
touch ct_toolkit/provenance/__init__.py
touch ct_toolkit/provenance/vault/__init__.py
touch ct_toolkit/utils/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py

echo "✅ __init__.py files created"

# ── Result ────────────────────────────────────────────────────────────────────
echo ""
echo "📁 Structure created:"
find . -not -path '*/__pycache__/*' -not -name '*.pyc' -not -name '.gitkeep' \
  | grep -v __pycache__ | sort

echo ""
echo "⚠️  MANUAL STEPS REQUIRED:"
echo "   ct_toolkit/kernels/defense.yaml is still missing."
echo "   Download this file and place it under ct_toolkit/kernels/."
echo "   (Note: identity/templates/defense.yaml is a different file!)"
echo ""
echo "🎉 Setup complete!"