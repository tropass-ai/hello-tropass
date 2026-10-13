"""Проверки сервиса: python -m pytest tests -q (нужен pytest). Сеть не нужна"""
import asyncio
import copy
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import main as service  # noqa: E402

METADATA = json.loads((ROOT / "metadata.json").read_text(encoding="utf-8"))
SAMPLE = json.loads((ROOT / "input_examples" / "input.json").read_text(encoding="utf-8"))
REQUIRED = [i["indicator_name"] for i in METADATA["inputs"] if i.get("is_required", True)]


def run(tmp_path, **overrides):
    """Вызывает main() на тестовом входе; значение None в overrides удаляет поле"""
    model_input = copy.deepcopy(SAMPLE["model_input"])
    for key, value in overrides.items():
        if value is None:
            model_input.pop(key, None)
        else:
            model_input[key] = value
    return asyncio.run(service.main(model_input, {"files_directory_path": str(tmp_path)}))


def panels(result):
    return result["panel_items"]


def test_metadata_is_consistent():
    for group in ("inputs", "outputs"):
        names = [item["indicator_name"] for item in METADATA[group]]
        assert len(names) == len(set(names)), f"повторяются имена в {group}"
    assert METADATA["model_name"] == METADATA["model_name"].lower() and " " not in METADATA["model_name"]


def test_server_model_name_matches_metadata():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert f'model_name="{METADATA["model_name"]}"' in source


def test_sample_input_covers_every_metadata_input():
    assert {i["indicator_name"] for i in METADATA["inputs"]} <= set(SAMPLE["model_input"])


def test_response_panels_match_metadata_outputs_in_order(tmp_path):
    result = panels(run(tmp_path))
    assert [p["panel_output_name"] for p in result] == [o["indicator_name"] for o in METADATA["outputs"]]
    assert [p["panel_type"] for p in result] == [o["indicator_type"] for o in METADATA["outputs"]]
    assert [p["panel_show_order"] for p in result] == list(range(1, len(result) + 1))


def test_all_files_in_response_exist_inside_files_directory(tmp_path):
    result = panels(run(tmp_path))
    paths = []
    for p in result:
        paths += [m["local_abs_path"] for m in (p["primary_data"] or {}).get("media", [])]
        paths += [m["local_abs_path"] for m in p["attachments"]]
    assert len(paths) == 5  # 2 картинки, видео, отчёт в file и в series
    for path in paths:
        assert pathlib.Path(path).exists() and pathlib.Path(path).parent == tmp_path


def test_text_panel_has_no_primary_data_and_text_in_descriptions(tmp_path):
    text = panels(run(tmp_path))[0]
    assert text["primary_data"] is None and "Что пришло на вход" in text["descriptions"][0]["content"]


@pytest.mark.parametrize("field", REQUIRED)
def test_missing_required_input_returns_one_readable_error_panel(tmp_path, field):
    result = panels(run(tmp_path, **{field: None}))
    assert len(result) == 1 and "Не заполнено поле" in result[0]["descriptions"][0]["content"]


def test_optional_inputs_may_be_absent(tmp_path):
    optional = {i["indicator_name"]: None for i in METADATA["inputs"] if not i.get("is_required", True)}
    assert len(panels(run(tmp_path, **optional))) == len(METADATA["outputs"])


def test_invalid_number_and_json_are_user_errors(tmp_path):
    assert "ожидается число" in panels(run(tmp_path, number_input=["abc"]))[0]["descriptions"][0]["content"]
    assert "некорректный JSON" in panels(run(tmp_path, json_input=["{не json"]))[0]["descriptions"][0]["content"]


def test_checkbox_accepts_bool_and_strings():
    from utils import as_bool
    assert [as_bool(v) for v in (True, "True", "1", 1)] == [True] * 4
    assert [as_bool(v) for v in (False, "False", "0", 0, "")] == [False] * 5
