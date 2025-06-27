#!/bin/bash

# Script to generate the Python code for the Qt Designer UI file.
# It first tries to use the ``pyuic6`` command (PyQt6). If that is not
# available, it falls back to ``python -m PyQt6.uic.pyuic``.
# The script exits with a non‑zero status if generation fails.
# The script exits with a non‑zero status if the generation fails.

UI_FILE="ui/main_window.ui"
OUT_FILE="ui/main_window.py"

if command -v pyuic6 >/dev/null 2>&1; then
    GENERATOR=(pyuic6)
elif python -m PyQt6.uic.pyuic --version >/dev/null 2>&1; then
    echo "pyuic6 not found; using 'python -m PyQt6.uic.pyuic'"
    GENERATOR=(python -m PyQt6.uic.pyuic)
else
    echo "Error: no suitable pyuic command found (PyQt6 required)." >&2
    exit 1
fi

"${GENERATOR[@]}" "$UI_FILE" -o "$OUT_FILE"
status=$?

if [ $status -ne 0 ]; then
    echo "UI generation failed" >&2
    exit $status
fi
