"""Вспомогательные функции: разбор входов и сборка частей ответа"""
import typing

import pandas as pd
from tropass_sdk import schemas

DescType = schemas.DescriptionTypeEnum


class InputError(ValueError):
    """Ошибка во входных данных пользователя: показываем её текстовой панелью, а не падаем"""


# ---- разбор входов: значения приходят списками, необязательные поля могут отсутствовать ----

def first(model_input: dict[str, typing.Any], key: str, default: typing.Any = None) -> typing.Any:
    """Первое непустое значение поля или default"""
    values = model_input.get(key)
    if not values:
        return default
    value = values[0] if isinstance(values, list) else values
    return default if value in (None, "") else value


def required(model_input: dict[str, typing.Any], key: str, label: str) -> typing.Any:
    """Значение обязательного поля; если его нет - InputError с названием поля для пользователя"""
    value = first(model_input, key)
    if value is None:
        raise InputError(f"Не заполнено поле «{label}»")
    return value


def as_float(value: typing.Any, label: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as e:
        raise InputError(f"В поле «{label}» ожидается число, получено: {value!r}") from e


def as_bool(value: typing.Any) -> bool:
    """Чекбокс приходит как true/false, 1/0 или True/False строкой"""
    return str(value).strip().lower() in ("1", "true", "да")


# ---- части ответа ----

def description(content: str, kind: DescType = DescType.MD) -> list[schemas.ModelDescriptionSchema]:
    """Подпись панели. kind: MD (markdown), HTML или PLAIN (простой текст)"""
    return [schemas.ModelDescriptionSchema(content=content, description_type=kind)]


def plot(series: dict[str, list[float]], x_axis: list) -> schemas.ModelPrimaryDataSchema:
    """primary_data для графиков: series = {имя ряда: числа}"""
    return schemas.ModelPrimaryDataSchema(
        plot_data=schemas.ModelPlotDataSchema(
            x_axis_values=x_axis,
            series_data=[schemas.ModelSeriesDataSchema(legend_name=n, plot_values=v) for n, v in series.items()],
        )
    )


def convert_to_plot_data(data: pd.DataFrame, legends: list[str], x_axis_values: list) -> schemas.ModelPlotDataSchema:
    """DataFrame (одна строка = один ряд графика) -> plot_data для панели"""
    series_data = [
        schemas.ModelSeriesDataSchema(legend_name=name, plot_values=values)
        for name, values in zip(legends, data.values.tolist())
    ]
    return schemas.ModelPlotDataSchema(x_axis_values=x_axis_values, series_data=series_data)


def empty_primary_data() -> schemas.ModelPrimaryDataSchema:
    """Заглушка primary_data для панелей без графика (text, file): plot_data обязателен"""
    return schemas.ModelPrimaryDataSchema(
        plot_data=schemas.ModelPlotDataSchema(
            x_axis_values=[1],
            series_data=[schemas.ModelSeriesDataSchema(legend_name="-", plot_values=[0])],
        ),
    )


def get_err_panel(text: str) -> dict:
    """Ответ с единственной текстовой панелью - удобно возвращать при ошибке входных данных"""
    return schemas.MLModelResponseSchema(panel_items=[
        schemas.ModelPanelOutputSchema(
            panel_output_name="text_output",
            panel_type="text",
            panel_show_order=1,
            primary_data=empty_primary_data(),
            descriptions=description(text, DescType.PLAIN),
        )
    ]).model_dump()
