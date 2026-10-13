"""Прогон main() без сервера: python3 run_test.py [имя_файла_из_input_examples]

Читает input_examples/<файл>.json (по умолчанию input.json), вызывает main() напрямую
и сохраняет ответ в <каталог файлов>/response.json. Каталог для файлов ответа -
.test_response рядом со скриптом (или TROPASS_FILES_DIR), а не путь из JSON: на платформе
такого каталога локально нет.
"""
import asyncio
import json
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
from main import main  # noqa: E402

test_file = sys.argv[1] if len(sys.argv) > 1 else "input.json"
test_path = os.path.join(here, "input_examples", test_file)
if not os.path.exists(test_path):
    test_path += ".json"

with open(test_path, encoding="utf-8") as f:
    data = json.load(f)

model_input = data["model_input"]
common_resources = data["common_resources"]
files_dir = os.environ.get("TROPASS_FILES_DIR", os.path.join(here, ".test_response"))
common_resources["files_directory_path"] = files_dir
os.makedirs(files_dir, exist_ok=True)

result = asyncio.run(main(model_input, common_resources))

out_path = os.path.join(files_dir, "response.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2, default=str)
print(f"Panels: {[p['panel_output_name'] for p in result['panel_items']]}")
print(f"Response saved to: {out_path}")
