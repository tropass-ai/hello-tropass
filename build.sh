#!/usr/bin/env bash
# Собирает archive.zip для загрузки на платформу и кладёт его вместе с metadata.json в deploy/.
# Запуск: ./build.sh
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p deploy
rm -f deploy/archive.zip
zip -qr deploy/archive.zip main.py utils.py requirements.txt modules input_examples output_examples \
  -x '*/__pycache__/*' '*.pyc' '.DS_Store'
cp metadata.json deploy/metadata.json
echo "Готово: deploy/archive.zip ($(wc -c < deploy/archive.zip) байт) и deploy/metadata.json. Загрузите их на платформу."
