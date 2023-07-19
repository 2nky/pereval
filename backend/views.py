import base64
from datetime import datetime
import json

from django.http import JsonResponse

from backend.models import MountainCrossing, CrossingImages


def check_json_schema(data):
    if "images" not in data:
        raise ValueError("Отсутствуют ключ 'images'")

    for image in data["images"]:
        if "data" not in image:
            raise ValueError("Отсутствует ключ 'data' в прикрепленном изображении!")


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
    except Exception as exc:
        return JsonResponse({"status": 500, "message": str(exc), "id": None})


def create_crossing_object(incoming_data):
    new_crossing = MountainCrossing()
    new_crossing.raw_data = incoming_data
    new_crossing.date_added = datetime.now()
    saved_images = []

    for image in incoming_data["images"]:
        # Преобразуем закодированное фото в бинарные данные для БД
        img_record = CrossingImages(
            date_added=datetime.now(),
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
