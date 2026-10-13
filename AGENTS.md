# Правила для ИИ-агента: сервис для платформы ТРОПАСС

Этот репозиторий — рабочий пример и шаблон сервиса для платформы ТРОПАСС. Сервис загружается на платформу как модель: `archive.zip` + `metadata.json`. Этот файл самодостаточен: здесь всё, что нужно, чтобы написать, проверить и подготовить к загрузке любой сервис. Образец кода — `main.py`, `utils.py`, `metadata.json`, `tests/`; описание примера — [README.md](README.md).

## Структура проекта

```text
main.py            # точка входа: функция main и переменная application
utils.py           # вспомогательные функции (можно добавлять свои модули/пакеты в modules/)
metadata.json      # описание входов и выходов (грузится отдельным файлом, в архив не входит)
requirements.txt   # зависимости с точными версиями
input_examples/    # тестовые входы {"model_input": {...}, "common_resources": {...}}; input.json платформа использует как автотест после сборки
output_examples/   # примеры файлов результата (опционально)
tests/             # pytest
run_test.py        # прогон main() без сервера
build.sh           # сборка deploy/archive.zip + копия metadata.json в deploy/
deploy/            # archive.zip, metadata.json, DEPLOY.md для загрузки на платформу (создаётся build.sh, в .gitignore)
```

В архиве `main.py` и `requirements.txt` лежат в корне; в него идут `main.py utils.py requirements.txt modules input_examples output_examples`. Python >= 3.12.

## metadata.json

```json
{
  "model_name": "my_service",
  "model_service": "Мой сервис",
  "python_version": "3.12",
  "inputs":  [{"indicator_name": "text_input", "display_field_name": "Введите текст", "indicator_type": "text", "is_required": true, "default_value": "..."}],
  "outputs": [{"indicator_name": "text_output", "display_result_name": "Результат", "indicator_type": "text"}],
  "system_dependencies": {"extra_apt_packages": ["ffmpeg"]}
}
```

- `model_name` - совпадает с названием модели на платформе и с `model_name` в `ModelServer`. `model_service` — название для пользователей.
- `python_version` необязателен: `3.10`–`3.14`. `system_dependencies.extra_apt_packages` — apt-пакеты (ffmpeg, pandoc, poppler-utils, libgomp1 и т.п.).
- Вход: `indicator_name` (ключ в `model_input`), `display_field_name`, `indicator_type`, `is_required`, `default_value`, `possible_values` (для селекторов), `allowed_file_extensions` (для файлов), `min_value`/`max_value`/`ui_elem_type: "slider"` (слайдер — это `number`).
- Типы входов: `text`, `date`, `dropdown` (+`possible_values`), `number`, `checkbox`, `file`, `multi-file`, `multi-select` (+`possible_values`), `voice`, `selector-slider`, `json`.
- `default_value` — всегда строка: number — `"0.42"` (точка), checkbox — `"True"`/`"False"`, multi-select — JSON-массив строк `"[\"a\",\"b\"]"` (только двойные кавычки), selector-slider — `"[\"a\",1]"`. Для `voice`, `file`, `multi-file` значения по умолчанию нет.
- Выход: `indicator_name` (латиница), `display_result_name`, `indicator_type` — один из: `text`, `series`, `diagram`, `donut`, `dumbbell`, `bd`, `polarLine`, `polarColumn`, `circles`, `image`, `video`, `file`. Панелей может быть сколько угодно.

## main.py и входные данные

`main(model_input, common_resources, *args, **kwargs)` — синхронная или асинхронная функция. Завершается `schemas.MLModelResponseSchema(panel_items=panels).model_dump()`. В конце файла:

```python
from tropass_sdk import schemas
from tropass_sdk.server import ModelServer

server = ModelServer(model_func=main, model_name="my_service", model_description="...", model_version="1.0.0", debug=False)
application = server.build_application()   # имя application менять нельзя
```

Чтение входов (`model_input[indicator_name]`):

- **Значения всегда приходят списками**, даже одиночные; необязательные поля могут отсутствовать. Берите первый элемент (`utils.first`, `utils.required`).
- text/dropdown — строка; number — число или строка (`utils.as_float`); checkbox приходит как `true/false`, `"1"/"0"`, `"True"/"False"` (`utils.as_bool`); date — строка; json — строка с JSON (парсить и ловить `JSONDecodeError`).
- file — **абсолютный путь** к файлу внутри контейнера (имя файла может не совпадать с исходным); multi-file — список путей; multi-select — список строк; selector-slider — `[строка, число]`; voice — путь к аудио.
- Обязательные по `metadata.json` поля проверяйте в коде. Ошибки пользователя (пусто, не число, битый JSON) бросайте как `utils.InputError` и возвращайте `utils.get_err_panel(текст)` — одну текстовую панель с причиной, а не исключение.
- Дополнительно в `model_input["request_metadata"]` приходят `user_id`, `locale`, `user_api_token` (из заголовков `X-User-ID`, `X-User-Locale`, `X-User-Api-Token`).

## Выходные панели и контракт

```python
schemas.ModelPanelOutputSchema(
    panel_output_name="series_output",   # = indicator_name из outputs, иначе панель не отобразится
    panel_type="series",                 # = indicator_type
    panel_show_order=1,                  # порядок; в примере расставляется enumerate по списку панелей
    primary_data=schemas.ModelPrimaryDataSchema(
        plot_data=schemas.ModelPlotDataSchema(
            x_axis_values=["Пн", "Вт"],
            series_data=[schemas.ModelSeriesDataSchema(legend_name="Продажи", plot_values=[1.0, 2.0])]),
        media=[schemas.ModelMediaItemSchema(file_name="Картинка", local_abs_path=str(path))]),
    descriptions=[schemas.ModelDescriptionSchema(content="# Текст", description_type=schemas.DescriptionTypeEnum.MD)],
    attachments=[schemas.ModelMediaItemSchema(file_name="Отчёт.csv", local_abs_path=str(report))],
)
```

Какие данные нужны какой панели (рабочие примеры каждой — функции `panel_*` в `main.py`):

| Панель | Что заполнять |
|---|---|
| `text` | `descriptions` (текст), `primary_data=None` |
| `series`, `diagram`, `dumbbell`, `polarLine`, `polarColumn` | `plot_data`: `x_axis_values` + ряды `series_data` (`legend_name`, `plot_values`) |
| `donut` | `plot_data`: каждый сектор — отдельный ряд с одним значением |
| `bd` («листалка») | `plot_data`; одна плашка — один ряд с одним значением |
| `image`, `video` | `media` с файлами + заглушка `plot_data` (`utils.empty_primary_data()`) |
| `file` | `attachments` с файлами для скачивания |

Правила SDK 2.1 (нарушение даёт «молчаливые» ошибки):

- В `ModelPrimaryDataSchema` только два поля: `plot_data` и `media`. Поля `text_content` нет — оно молча игнорируется. Текст панели — только в `descriptions[].content`; `description_type`: `MD`, `HTML`, `PLAIN` (в ответе строчные `md`/`html`/`plain`; вручную собранные словари с `"MD"` отклоняются).
- Если `primary_data` передан, `plot_data` в нём обязателен: для не-графических панелей ставьте заглушку (`x_axis_values=["1"]`, один ряд `plot_values=[0.0]`).
- `plot_values` — `float`, без `NaN` (замените нулями/уберите до сборки ответа).
- Файлы результата (картинки, видео, вложения) должны лежать **внутри** `common_resources["files_directory_path"]`; платформа подхватит их по `local_abs_path`. `attachments` можно прикрепить к любой панели.
- Если считаете таблицы в pandas и используете `DataFrame.to_markdown()`, добавьте `tabulate` в `requirements.txt`.

## Ресурсы платформы: common_resources

Второй аргумент `main()` платформа заполняет сама из конфигурации сервиса. Читайте ключи через `.get(...)`, не рассчитывайте, что они есть всегда:

| Ключ | Назначение |
|---|---|
| `files_directory_path` | каталог для файлов ответа (есть всегда) |
| `model_api_gateway_params` | `url` и `api_token` шлюза для вызова других сервисов |
| `big_llm_api_params`, `medium_llm_api_params`, `small_llm_api_params` | параметры LLM трёх размеров |
| `web_search_params` | веб-поиск (опционально) |
| `coredev_database_params`, `hot_database_params` | подключения к БД (опционально) |

Секреты (пароли БД, токены, пароли LLM) никогда не кладите в код, `input_examples` и репозиторий — их выдаёт платформа. В тестовых входах — плейсхолдеры. Если модулей много, не передавайте `common_resources` по всем функциям: положите в `ContextVar` (модуль `context.py` с `set`/`get`); `asyncio.to_thread` копирует контекст, `ThreadPoolExecutor` — нет.

## Вызов других сервисов (model gateway)

`POST` на адрес `model_api_gateway_params.url` (multipart/form-data), заголовки `Authorization: Bearer <token>` и `Idempotency-Key: <uuid4>` (уникален на каждый вызов). Токен: `request_metadata.user_api_token` (приоритет, списание с пользователя), иначе сервисный `api_token`.

- Поле `model_payload` — JSON-строка `{"model_id": "<UUID сервиса>", "model_request_data": {...}}`; `model_id` — UUID, не `model_name`.
- **Все значения входов — массивы**: `"prompt": ["текст"]`, `"width_px": ["1600"]`.
- Файловые входы: значение — имя файла, а сам файл прикладывается в поле `files` под тем же именем: `"data_file": ["data.json"]` + `files=(("data.json", fh),)`. Расширение имени определяет парсер на той стороне.
- `common_resources` вызываемого сервиса передавать не нужно.
- Режим по умолчанию синхронный (ответ в теле, HTTP 200). С заголовком `Tropass-Model-Call-Version: 2` — асинхронный: `202 {"task_id": ...}`, результат — поллингом `GET` на `…/api/rest/model-tasks/{task_id}` до статуса, отличного от `distributed`/`processing` (ошибка: `processing_error`, текст в `error_message`).
- Ответ: `panel_items[]` (искать по `panel_output_name`), файлы в `primary_data.media[]` (`local_abs_path` или `s3_url` — presigned, живёт около часа, скачивайте сразу), текст в `descriptions[].content`.
- Ошибки: 422 — не приложены `files` или неверное имя; 503 — один ретрай через ~30 с. Клиентский таймаут для тяжёлых сервисов 300–600 с. Ретраить только transient-ошибки (сеть, 5xx, битый JSON) с экспоненциальной задержкой; ошибка исполнения приходит как HTTP 200 и текстовая панель — ретраем не лечится.

Известные сервисы:

| Сервис | model_id |
|---|---|
| Image-gen (генерация изображений по промпту) | `019e2248-902a-77c1-8a48-335d175f866b` |
| Upscaler (повышение разрешения) | `019e224a-33b1-7b42-a654-2b5b3ab6c3c6` |
| Web-search | `019fd153-2b4e-77fc-bae0-855bd71161bd` |
| Инфографер (PNG-инфографика по таблице и промпту) | `01a06309-f4b5-7a16-a827-aca0e70fccde` |
| Инфографер (R-исполнитель) | `01a06bb2-6c2f-753f-be5e-4942d1875f45` |

MD-конвертер (docx/pdf/xlsx в Markdown): `model_id` смотрите в карточке сервиса на платформе.

## LLM

Параметры — `big_llm_api_params`, `medium_llm_api_params`, `small_llm_api_params`: словарь с `api` (базовый адрес), `model`, авторизацией и `verify`. Это OpenAI-совместимый эндпоинт `POST` на `{api}/v1/chat/completions` (`model`, `messages`, `temperature`, `max_tokens`). Авторизация по приоритету: `api_key` → `Authorization: Bearer`; иначе `user` + `password` → basic; иначе без авторизации. `verify` передавайте в `requests` (`params.get("verify", True)`).

Практика:

- Цепочка запасных моделей: big → medium → small; не падайте, если большая недоступна после ретраев.
- Ретраи 3–5 раз с экспоненциальной задержкой, только на transient-ошибки.
- Thinking-модели: ответ может быть в `message.reasoning_content`/`reasoning`, а в `content` — блоки `<think>…</think>`: вырезайте регулярным выражением; можно передавать `"chat_template_kwargs": {"enable_thinking": False}`.
- JSON-ответы: просите «строгий JSON без markdown» и парсите по шагам: `json.loads` → починка типовых ошибок → fenced-блок ```json → первый `{…}`/`[…]`.
- Картинки (VL): `{"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}`, ширину перед отправкой уменьшайте до ~1600 px.

## requirements.txt

Обязательно `tropass-sdk[server]==2.1` (без `[server]` при деплое поставятся не те зависимости). Остальное — с точными версиями, совместимыми с Python 3.12+; вместо `psycopg2` — `psycopg2-binary`. Все импортируемые пакеты должны быть в файле, иначе автосборка их не поставит.

## Тестирование

- `python3 -m pytest tests -q` — тесты (в примере 16).
- `python3 run_test.py [файл.json]` — вызывает `main()` напрямую на файле из `input_examples/`, подставляет локальный каталог результатов, сохраняет `response.json`.
- Через сервер: `uvicorn main:application --port 8000`, затем `curl -X POST http://localhost:8000/prediction -H 'Content-Type: application/json' -H 'X-User-Locale: ru' -d '{"model_input": {...}, "common_resources": {"files_directory_path": "/tmp/test_response"}}'` (каталог должен существовать).
- Если сервис вызывает другие сервисы или LLM, реальные параметры подставляйте только из своих секретов, не из репозитория.
- Любое изменение сопровождайте тестами и запускайте их.

## Сборка и загрузка

1. Тесты проходят, `metadata.json` корректен, `requirements.txt` содержит `tropass-sdk[server]==2.1`, секретов в коде и входах нет.
2. `./build.sh` собирает `deploy/archive.zip` и копирует `metadata.json` в `deploy/`.
3. Загрузка — страница «Создание модели» в разделе «Модели аналитика» админки: заполнить форму, загрузить `archive.zip` и `metadata.json`, нажать «Сохранить». После сборки платформа прогонит `input_examples/input.json` как автотест.
4. Сборка Python-сервиса с pandas занимает около 10–12 минут, после неё сервис запускается за секунды. Это нормально.

Чек-лист:

- [ ] в `metadata.json` есть `model_name`, `model_service`, `inputs`, `outputs`; `model_name` латиницей
- [ ] все `panel_output_name` совпадают с `indicator_name` из `outputs`
- [ ] `main()` возвращает `MLModelResponseSchema(...).model_dump()`
- [ ] `plot_data` заполнен для графиков, для text — `primary_data=None` или заглушка; текст в `descriptions[].content`
- [ ] файлы результата лежат в `files_directory_path` и указаны в `media`/`attachments`
- [ ] при вызовах шлюза: `model_id` — UUID, значения массивами, `Idempotency-Key` уникален, токен пользователя приоритетнее
- [ ] в коде и `input_examples` нет секретов
- [ ] `archive.zip` собран, `main.py` и `requirements.txt` в корне архива

## Известные проблемы

- **Health check:** параметр «Включить health check» при загрузке пока **не включать**.
- **Переименование:** модель **не переименовывать во время сборки**, пока статус не станет `VALID` или ошибкой.

Нашли ещё проблему или нужна функция платформы — почта dev@tropass.me.

## Папка deploy/

Когда сервис готов к загрузке, обновите папку `deploy/` в корне: `./build.sh` создаёт её и кладёт туда архив и `metadata.json`, а `DEPLOY.md` пишет агент. Папка в `.gitignore`, в git не попадает. Состав:

1. `deploy/archive.zip` — результат `./build.sh`. Перед этим тесты должны проходить.
2. `deploy/metadata.json` — копия актуального `metadata.json` (её тоже делает `./build.sh`).
3. `deploy/DEPLOY.md` — инструкция по заполнению страницы «Создание модели».

### Как писать DEPLOY.md

Структура:

1. Заголовок «Деплой сервиса «<model_service>» (<model_name>)», список файлов для загрузки (`archive.zip` с размером, `metadata.json`), что проверено до загрузки (формат `metadata.json`, число проходящих тестов).
2. «Где грузить»: страница «Создание модели», «Сохранить» нажать один раз. Три блока таблицами «Поле на странице / Что ввести / Почему»:
   - **Основная информация**: Название модели (= `model_name`), Техническое описание (готовый текст), Доступна всем, Есть заряженный режим, Возможен запуск по расписанию, Доступна в чате.
   - **Модель**: Язык модели (Python), Версия Python (= `python_version`), Менеджер пакетов (pip/uv), Ссылка на архив модели (ZIP) — пусто, если грузится файл (заполняется либо ссылка, либо файл), Архив модели (ZIP), Metadata (JSON), Base image for buildkit executor for Python agent / for R agent / Base image for agent (обычно пусто).
   - **Ресурсы и настройки**: Queue Length, Workers Count, Min Replica Count, Max Replica Count, k8s limit CPU cores, k8s request CPU cores, k8s limit memory (GB), k8s request memory (GB), k8s limit gpu memory (MB), k8s request ephemeral storage for build (GB), Требует GPU, Включить health check, Extra env variables (JSON).
3. «Сколько ждать»: сборка занимает около 10–12 минут; если статус не меняется дольше 20 минут — посмотреть статус и сообщение об ошибке модели и написать на dev@tropass.me.
4. «После загрузки»: статусы `UPLOADING -> UPLOADED -> PENDING -> IN_PROGRESS -> VALID` (при `UPLOADED_ERROR` и `VALIDATION_ERROR` смотреть текст ошибки), сценарии проверки запуском из интерфейса (ожидаемое число панелей, ошибочные входы), включение «Доступна всем» и «Доступна в чате» после успешной проверки.

Значения по умолчанию для небольшого сервиса (меняйте, если сервису нужно больше):

| Поле | Значение |
|---|---|
| Queue Length | `5` |
| Workers Count | `1` |
| Min / Max Replica Count | `1` / `2` |
| k8s limit CPU cores / request | `2` / `0.1` |
| k8s limit memory (GB) / request | `2` / `0.5` |
| k8s request ephemeral storage for build (GB) | `2` |
| Требует GPU | выключено |
| Включить health check | **выключено** |
| Extra env variables (JSON) | `{}` |

- Запросы (request) держите минимальными — они резервируют ресурсы платформы; лимиты (limit) ничего не резервируют. При перезапусках из-за нехватки памяти поднимайте limit memory, а не request.
- Значения, которые нельзя определить по коду (название, ресурсы под нагрузку), помечайте в ответе пользователю как предположения, а не проверенные факты.

## Общие правила

- Никаких секретов, токенов, адресов стендов и внутренних названий сервисов платформы в коде, примерах входов и документации.
- Файл `LICENSE` не изменять без запроса пользователя.
