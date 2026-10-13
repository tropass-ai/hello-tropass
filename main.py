import csv
import dataclasses
import json
import pathlib
import shutil
import typing

import pandas as pd

# Загрузка классов ТРОПАСС
from tropass_sdk import schemas
from tropass_sdk.server import ModelServer

# Загрузка пользовательских модулей (utils.py лежит рядом с main.py; свои пакеты можно складывать в modules/)
import utils

# Путь к файлам для панелей image/video считаем от самого файла, а не хардкодим:
# так сервис работает и на платформе, и локально
OUTPUT_EXAMPLES = pathlib.Path(__file__).parent / "output_examples"

# Тестовый вход: input_examples/input.json, прогон - python3 run_test.py.
# Значения всегда приходят списками, даже для одиночных полей.

X_AXIS = ["Сегодня", "Вчера", "На прошлой неделе", "На позапрошлой неделе"]
DescType = schemas.DescriptionTypeEnum


# ===========================================================================
# 1. Входы: как читать поля каждого типа из model_input
# ===========================================================================
@dataclasses.dataclass
class Inputs:
    text: str                                    # text
    selector: str                                # dropdown
    number: float                                # number
    slider: float                                # number + slider
    checkbox: bool                               # checkbox
    multi_select: list[str]                      # multi-select: список выбранных строк
    selector_slider: tuple[str, float]           # selector-slider: [строка, число]
    date: str | None                             # date: строка
    json_value: typing.Any                       # json: строка с JSON или уже разобранный объект
    input_file: str | None                       # file: абсолютный путь к файлу
    multi_file: list[str]                        # multi-file: список путей
    voice: str | None                            # voice: путь к аудиозаписи


def read_inputs(model_input: dict[str, typing.Any]) -> Inputs:
    """Разбирает model_input. Ошибки пользователя - utils.InputError (их показываем текстовой панелью).
    Необязательные поля (is_required: false в metadata.json) могут отсутствовать"""
    multi_select = list(model_input.get("multi-select_input") or [])
    if not multi_select:
        raise utils.InputError("Не заполнено поле «Мультиселект»")
    parts = list(model_input.get("selector-slider_input") or [])
    if len(parts) < 2:
        raise utils.InputError("Не заполнено поле «Селектор + слайдер»")
    selector_slider = (str(parts[0]), utils.as_float(parts[1], "Селектор + слайдер"))

    raw_json = utils.first(model_input, "json_input")
    try:
        json_value = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
    except json.JSONDecodeError as e:
        raise utils.InputError(f"Поле «JSON» содержит некорректный JSON: {e.msg}") from e

    return Inputs(
        text=str(utils.required(model_input, "text_input", "Текст")),
        selector=str(utils.required(model_input, "selector_input", "Селектор")),
        number=utils.as_float(utils.required(model_input, "number_input", "Число"), "Число"),
        slider=utils.as_float(utils.required(model_input, "slyder_input", "Слайдер"), "Слайдер"),
        checkbox=utils.as_bool(utils.required(model_input, "checkbox_input", "Чекбокс")),
        multi_select=multi_select,
        selector_slider=selector_slider,
        date=utils.first(model_input, "date_input"),
        json_value=json_value,
        input_file=utils.first(model_input, "input_file"),
        multi_file=list(model_input.get("multi-file_input") or []),
        voice=utils.first(model_input, "voice_input"),
    )


# ===========================================================================
# 2. Панели: по одной функции на тип. Ненужные удалите вместе со строкой в main()
#    и записью в outputs из metadata.json. Порядок вывода задаётся в main()
# ===========================================================================
def panel_text(inputs: Inputs) -> schemas.ModelPanelOutputSchema:
    """text: текстовая панель. Текст - в descriptions (markdown), primary_data не нужен"""
    summary = "\n".join([
        "# Что пришло на вход",
        f"- Текст: `{inputs.text}`",
        f"- Селектор: `{inputs.selector}`",
        f"- Число: `{inputs.number}`, слайдер: `{inputs.slider}`, чекбокс: `{inputs.checkbox}`",
        f"- Мультиселект: `{inputs.multi_select}`, селектор + слайдер: `{inputs.selector_slider}`",
        f"- Дата: `{inputs.date}`, JSON: `{inputs.json_value}`",
        f"- Файл: `{inputs.input_file}`, файлы: `{inputs.multi_file}`, голос: `{inputs.voice}`",
    ])
    return schemas.ModelPanelOutputSchema(
        panel_output_name="text_output",   # = indicator_name из outputs в metadata.json
        panel_type="text",                 # = indicator_type из outputs
        primary_data=None,
        descriptions=utils.description(summary, DescType.MD),
    )


def panel_series() -> schemas.ModelPanelOutputSchema:
    """series: график с линиями. Подпись в markdown. К панели прикреплён файл (attachments)"""
    return schemas.ModelPanelOutputSchema(
        panel_output_name="series_output",
        panel_type="series",
        primary_data=utils.plot({"Продажи": [100.5, 200.3, 150.0, 300.2], "Другие продажи": [10.5, 20.3, 15.0, 30.2]}, X_AXIS),
        descriptions=utils.description("# Тестовое описание\n*Пример series_output*", DescType.MD),
    )


def panel_diagram() -> schemas.ModelPanelOutputSchema:
    """diagram: колончатая диаграмма. Данные строим из pandas через utils.convert_to_plot_data"""
    df = pd.DataFrame([[100.5, 200.3, 150.0, 300.2], [10.5, 20.3, 15.0, 30.2]])
    return schemas.ModelPanelOutputSchema(
        panel_output_name="diagram_output",
        panel_type="diagram",
        primary_data=schemas.ModelPrimaryDataSchema(
            plot_data=utils.convert_to_plot_data(df, ["Продажи", "Другие продажи"], X_AXIS)
        ),
        descriptions=utils.description("Данные собраны из `pandas.DataFrame`", DescType.MD),
    )


def panel_dumbbell() -> schemas.ModelPanelOutputSchema:
    """dumbbell: график «было-стало». Подпись простым текстом"""
    return schemas.ModelPanelOutputSchema(
        panel_output_name="dumbbell_output",
        panel_type="dumbbell",
        primary_data=utils.plot({"Было": [100.5, 200.3, 150.0, 300.2], "Стало": [10.5, 20.3, 15.0, 30.2]}, X_AXIS),
        descriptions=utils.description("Пример dumbbell_output", DescType.PLAIN),
    )


def panel_bd() -> schemas.ModelPanelOutputSchema:
    """bd: листалка"""
    return schemas.ModelPanelOutputSchema(
        panel_output_name="bd_output",
        panel_type="bd",
        primary_data=utils.plot({"Легенда первой плашки": [100.5], "Легенда второй плашки": [10.5]}, X_AXIS),
        descriptions=utils.description("Пример bd_output", DescType.PLAIN),
    )


def panel_polar_line() -> schemas.ModelPanelOutputSchema:
    """polarLine: паутинка. Подпись в HTML"""
    return schemas.ModelPanelOutputSchema(
        panel_output_name="polarLine_output",
        panel_type="polarLine",
        primary_data=utils.plot({"Что-то было": [1, 2, 3, 4], "Что-то стало": [6, 7, 8, 9]}, X_AXIS),
        descriptions=utils.description(
            "<p>Солнце - <strong>центр</strong> нашей системы, <em>гигантский</em> шар из плазмы.</p>",
            DescType.HTML,
        ),
    )


def panel_polar_column() -> schemas.ModelPanelOutputSchema:
    """polarColumn: полярная диаграмма (ромашка)"""
    return schemas.ModelPanelOutputSchema(
        panel_output_name="polarColumn_output",
        panel_type="polarColumn",
        primary_data=utils.plot({"Что-то было": [1, 2, 3, 4], "Что-то стало": [6, 7, 8, 9]}, X_AXIS),
        descriptions=utils.description("Это простая подпись простым текстом", DescType.PLAIN),
    )


def panel_donut() -> schemas.ModelPanelOutputSchema:
    """donut: пончик. Каждый сектор - отдельный ряд с одним значением"""
    return schemas.ModelPanelOutputSchema(
        panel_output_name="donut_output",
        panel_type="donut",
        primary_data=utils.plot({"Раздел 1": [1], "Раздел 2": [2], "Раздел 3": [3], "Раздел 4": [2.5]}, X_AXIS),
        descriptions=utils.description("Структура по разделам", DescType.MD),
    )


def panel_images(files_dir: pathlib.Path) -> schemas.ModelPanelOutputSchema:
    """image: картинки передаются в primary_data.media. Файл должен лежать внутри files_directory_path"""
    for name in ("cat1.png", "cat2.png"):
        shutil.copy(OUTPUT_EXAMPLES / name, files_dir / name)
    return schemas.ModelPanelOutputSchema(
        panel_output_name="images_output",
        panel_type="image",
        primary_data=schemas.ModelPrimaryDataSchema(
            plot_data=utils.empty_primary_data().plot_data,  # plot_data обязателен, даже если график не нужен
            media=[
                schemas.ModelMediaItemSchema(file_name="Первая фотка кота", local_abs_path=str(files_dir / "cat1.png")),
                schemas.ModelMediaItemSchema(file_name="Вторая фотка кота", local_abs_path=str(files_dir / "cat2.png")),
            ],
        ),
        descriptions=utils.description("# Тестовое описание фоток с котами", DescType.MD),
    )


def panel_video(files_dir: pathlib.Path) -> schemas.ModelPanelOutputSchema:
    """video: видео тоже идёт в media"""
    shutil.copy(OUTPUT_EXAMPLES / "example.mp4", files_dir / "example.mp4")
    return schemas.ModelPanelOutputSchema(
        panel_output_name="video_output",
        panel_type="video",
        primary_data=schemas.ModelPrimaryDataSchema(
            plot_data=utils.empty_primary_data().plot_data,
            media=[schemas.ModelMediaItemSchema(file_name="Демо-видео", local_abs_path=str(files_dir / "example.mp4"))],
        ),
        descriptions=utils.description("# Тестовое описание видео", DescType.MD),
    )


def make_report(files_dir: pathlib.Path) -> pathlib.Path:
    """Файл для скачивания создаём на лету прямо в files_directory_path"""
    path = files_dir / "report.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["period", "sales"])
        writer.writerows(zip(X_AXIS, [100.5, 200.3, 150.0, 300.2]))
    return path


def panel_file(report: pathlib.Path) -> schemas.ModelPanelOutputSchema:
    """file: файлы для скачивания идут в attachments"""
    return schemas.ModelPanelOutputSchema(
        panel_output_name="file_output",
        panel_type="file",
        primary_data=utils.empty_primary_data(),
        attachments=[schemas.ModelMediaItemSchema(file_name="Отчёт.csv", local_abs_path=str(report))],
        descriptions=utils.description("Файл для скачивания", DescType.PLAIN),
    )


# -----------------------------
# Главная функция сервиса
# -----------------------------
async def main(model_input: dict[str, typing.Any], common_resources: dict[str, typing.Any], *args, **kwargs) -> dict[str, typing.Any]:
    # model_input - значения полей из metadata.json по indicator_name
    # common_resources["files_directory_path"] - каталог для файлов, которые уйдут пользователю
    files_dir = pathlib.Path(common_resources["files_directory_path"])
    files_dir.mkdir(parents=True, exist_ok=True)

    try:
        inputs = read_inputs(model_input)
    except utils.InputError as e:
        # Ошибку во входных данных показываем пользователю текстовой панелью
        return utils.get_err_panel(f"Некорректные входные данные: {e}")

    # ---- ваша логика: здесь считаете результат по inputs ----

    report = make_report(files_dir)
    panels = [
        panel_text(inputs),
        panel_series(),
        panel_diagram(),
        panel_dumbbell(),
        panel_bd(),
        panel_polar_line(),
        panel_polar_column(),
        panel_donut(),
        panel_images(files_dir),
        panel_video(files_dir),
        panel_file(report),
    ]
    # attachments можно прикрепить к любой панели, не только к file: добавим отчёт к графику series
    panels[1].attachments.append(schemas.ModelMediaItemSchema(file_name="Данные графика.csv", local_abs_path=str(report)))

    # Порядок вывода панелей = порядок в списке
    for order, panel in enumerate(panels, start=1):
        panel.panel_show_order = order

    return schemas.MLModelResponseSchema(panel_items=panels).model_dump()


# -----------------------------
# Сервер для модели
# -----------------------------
server = ModelServer(
    model_func=main,
    model_name="hello_tropass",  # = model_name из metadata.json (латиница, строчные буквы, _)
    model_description="Демо-сервис: все типы входов и выходных панелей",
    model_version="1.0.0",
    debug=False,
)
application = server.build_application()
