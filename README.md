# hello-tropass — полный пример и шаблон сервиса для платформы ТРОПАСС

Рабочий сервис, который показывает **все типы входных полей и все типы выходных панелей**, с тестами, прогоном без сервера и сборкой архива. Используйте его как шаблон: создайте из него свой репозиторий (на GitHub - **Use this template**), оставьте нужное и удалите лишнее.

Название сервиса на платформе (`model_name` в `metadata.json` и в `ModelServer`) - `hello_tropass`: оно пишется на латинице строчными буквами с нижним подчёркиванием, в отличие от названия папки.

## Быстрый старт

```bash
python3 -m venv .venv && source .venv/bin/activate     # Python 3.12 или новее
pip install -r requirements.txt pytest
python3 run_test.py          # вызвать main() на input_examples/input.json
python3 -m pytest tests -q   # проверки (16 тестов, сеть не нужна)
./build.sh                   # собрать deploy/archive.zip и deploy/metadata.json для загрузки на платформу
```

Через сервер: `uvicorn main:application --port 8000` и `POST http://localhost:8000/prediction` с телом из `input_examples/input.json` (каталог из `files_directory_path` должен существовать).

## Что сделать после создания из шаблона

| Шаг | Где |
|---|---|
| 1. Задать имя сервиса | `metadata.json`: `model_name` (латиница, строчные буквы, `_`), `model_service` (название для пользователей); `main.py`: `model_name` в `ModelServer` - то же значение (проверяет тест) |
| 2. Оставить нужные входы | удалите лишние поля из `inputs` в `metadata.json`, из `Inputs` и `read_inputs()` в `main.py`, из `input_examples/input.json` |
| 3. Оставить нужные панели | удалите лишние функции `panel_*` в `main.py`, их строки в списке `panels` в `main()` и записи в `outputs` в `metadata.json` |
| 4. Написать логику | в `main()` после разбора входов (место помечено «ваша логика»); данные для графиков и текстов считайте по `inputs` |
| 5. Зависимости | `requirements.txt`: `tropass-sdk[server]` остаётся, `pandas` уберите, если не нужен |
| 6. Файлы-примеры | если нет панелей image/video, удалите папку `output_examples/` и `shutil.copy` в `panel_images`/`panel_video` |
| 7. Проверить | `python3 -m pytest tests -q`: тесты упадут, если имена и типы панелей разойдутся с `metadata.json`, и подскажут, что поправить |

## Что показывает пример

**Входные поля** (`metadata.json`, чтение - `read_inputs()` в `main.py`): text, dropdown, number, number + slider, checkbox, multi-select, selector-slider, date, json, file, multi-file, voice. Ключи полей: `is_required`, `default_value`, `possible_values`, `min_value` / `max_value` / `ui_elem_type`, `allowed_file_extensions`.

**Выходные панели** (порядок = порядок в списке `panels`):

| # | panel_output_name | panel_type | Функция | Что показывает | Подпись |
|---|-------------------|------------|---------|----------------|---------|
| 1 | text_output | text | `panel_text` | сводка по всем полученным входам, `primary_data=None` | MD |
| 2 | series_output | series | `panel_series` | график с линиями, к панели прикреплён csv (`attachments`) | MD |
| 3 | diagram_output | diagram | `panel_diagram` | колончатая диаграмма из `pandas.DataFrame` | MD |
| 4 | dumbbell_output | dumbbell | `panel_dumbbell` | график «было-стало» | PLAIN |
| 5 | bd_output | bd | `panel_bd` | листалка | PLAIN |
| 6 | polarLine_output | polarLine | `panel_polar_line` | паутинка | HTML |
| 7 | polarColumn_output | polarColumn | `panel_polar_column` | полярная диаграмма | PLAIN |
| 8 | donut_output | donut | `panel_donut` | пончик | MD |
| 9 | images_output | image | `panel_images` | две картинки (`primary_data.media`) | MD |
| 10 | video_output | video | `panel_video` | видео (`primary_data.media`) | MD |
| 11 | file_output | file | `panel_file` | файл для скачивания (`attachments`), csv создаётся на лету | PLAIN |

**Контракт ответа:** `MLModelResponseSchema`, `ModelPanelOutputSchema`, `ModelPrimaryDataSchema`, `ModelPlotDataSchema`, `ModelSeriesDataSchema`, `ModelMediaItemSchema` (`media` и `attachments`), `ModelDescriptionSchema` с тремя типами `DescriptionTypeEnum` (MD, HTML, PLAIN).

**Поведение:** при ошибке во входных данных (не заполнено поле, не число, некорректный JSON) сервис возвращает одну текстовую панель с причиной (`utils.InputError`, `utils.get_err_panel`); необязательные поля могут отсутствовать.

## Структура

```
hello-tropass/
├── metadata.json               # входные и выходные поля (грузится на платформу отдельно от архива)
├── main.py                     # Inputs и read_inputs(), функции panel_*, main(), ModelServer
├── utils.py                    # разбор входов (first, required, as_float, as_bool), части ответа (plot, description...)
├── requirements.txt            # зависимости (обязательно tropass-sdk[server]==2.1)
├── modules/__init__.py         # место для ваших модулей
├── input_examples/input.json   # тестовый вход (его же использует платформа для автотеста)
├── output_examples/            # файлы для панелей image/video
├── tests/test_service.py       # проверки сервиса
├── run_test.py                 # прогон main() без сервера
├── build.sh                    # сборка deploy/archive.zip и копирование metadata.json в deploy/
└── .gitignore
```

Папки `tropass_sdk/` в проекте нет: SDK подключается как библиотека [tropass-sdk](https://pypi.org/project/tropass-sdk/) через `requirements.txt`.

В `archive.zip` попадают `main.py`, `utils.py`, `requirements.txt`, `modules/`, `input_examples/` и `output_examples/` (она нужна на платформе для панелей image и video). Тесты, `run_test.py`, README и `metadata.json` в архив не входят; `metadata.json` загружается отдельным файлом.

## Правила, которые легко нарушить

- Значения `model_input` всегда приходят **списками**; необязательные поля могут отсутствовать.
- Для графиков `plot_values` должны быть числами (`float`), без `NaN`.
- Текст панели передавайте в `descriptions`, а не в `primary_data`; у text-панели `primary_data` можно не передавать.
- Если `primary_data` передан, `plot_data` в нём обязателен (для панелей без графика есть заглушка `utils.empty_primary_data()`).
- Файлы результата кладите внутри `files_directory_path`.
- Имена и типы панелей в ответе должны совпадать с `outputs` в `metadata.json`.
- Не храните секреты в коде и в `input_examples/input.json`: ключи и настройки платформа передаёт в `common_resources`.
- Не переименовывайте сервис во время сборки, пока она не закончилась.

## Лицензия

Код распространяется по лицензии «TROPASS Platform Use License» (файл [LICENSE](LICENSE)): его можно использовать, копировать и изменять только для разработки, тестирования и эксплуатации сервисов на платформе ТРОПАСС. Название и логотип ТРОПАСС лицензией не предоставляются, файлы в `output_examples/` и зависимости имеют собственные условия.

Вопросы по лицензии и использованию: dev@tropass.me.
