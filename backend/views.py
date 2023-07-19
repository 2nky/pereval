import base64
from datetime import datetime
import json

from django.http import JsonResponse

from backend.models import MountainCrossing, CrossingImages


ADD_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class JsonSchemaError(Exception):
    pass


def check_json_schema(data):
    if "images" not in data:
        raise JsonSchemaError("Отсутствует ключ 'images'")

    if "add_time" not in data:
        raise JsonSchemaError("Отсутствует ключ 'add_time'")

    for image in data["images"]:
        if "data" not in image:
            raise JsonSchemaError(
                "Отсутствует ключ 'data' в прикрепленном изображении!"
            )


def create_crossing_object(incoming_data):
    try:
        submitted_on = datetime.strptime(incoming_data["add_time"], ADD_TIME_FORMAT)
    except ValueError as exc:
        raise ValueError(f"Ошибка при обработке даты: {exc}")

    new_crossing = MountainCrossing()
    new_crossing.raw_data = incoming_data
    new_crossing.date_added = submitted_on
    saved_images = []

    for image in incoming_data["images"]:
        # Преобразуем закодированное фото в бинарные данные для БД
        img_record = CrossingImages(
            date_added=submitted_on,
            img=base64.b64decode(image["data"]),
        )
        img_record.save()

        # Свяжем записи в таблицах перевалов и фотографий
        saved_images.append(
            {
                "id": img_record.pk,
                "title": image["title"],
            }
        )
    new_crossing.images = {
        "images": saved_images,
    }
    new_crossing.save()
    return new_crossing


def submit_data(request):
    try:
        incoming_data = json.loads(request.body)
        # Проверим корректность пришедших данных
        check_json_schema(incoming_data)

        new_crossing = create_crossing_object(incoming_data)

        return JsonResponse(
            {
                "status": 200,
                "message": None,
                "id": new_crossing.pk,
            }
        )
    except JsonSchemaError as exc:
        return JsonResponse({"status": 400, "message": str(exc), "id": None})
    except Exception as exc:
        return JsonResponse({"status": 500, "message": str(exc), "id": None})
