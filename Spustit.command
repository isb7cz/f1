#!/bin/sh
cd -- "$(dirname -- "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo "Pro spuštění nainstalujte Python 3.9 nebo novější z https://www.python.org/downloads/"
  read -r answer
  exit 1
fi
exec python3 app.py --open
