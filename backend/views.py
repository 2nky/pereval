import base64
from datetime import datetime
import json

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from backend.models import MountainCrossing, CrossingImages


class JsonSchemaError(Exception):
    pass


def check_json_schema(data):
    if "images" not in data:
        raise JsonSchemaError("Отсутствуют ключ 'images'")

    for image in data["images"]:
        if "data" not in image:
            raise JsonSchemaError(
                "Отсутствует ключ 'data' в прикрепленном изображении!"
            )


class Crossing:
    raw_data = {}
    images = []

    def set_data(self, data):
        self.raw_data = data

    def add_image(self, title, encoded_data):
        raw_image = base64.b64decode(encoded_data)
        self.images.append((title, raw_image))

    def save_to_db(self):
        crossing = MountainCrossing()
        crossing.raw_data = self.raw_data
        crossing.date_added = datetime.now()
        saved_images = []

        for title, image_bytes in self.images:
            # Преобразуем закодированное фото в бинарные данные для БД
            img_record = CrossingImages(
                date_added=datetime.now(),
                img=image_bytes,
            )
            img_record.save()

            # Свяжем записи в таблицах перевалов и фотографий
            saved_images.append(
                {
                    "id": img_record.pk,
                    "title": title,
                }
            )
        crossing.images = {
            "images": saved_images,
        }
        crossing.save()
        return crossing.pk


@require_http_methods(["POST"])
def submit_data(request):
    try:
        incoming_data = json.loads(request.body)
        # Проверим корректность пришедших данных
        check_json_schema(incoming_data)

        new_crossing = Crossing()
        new_crossing.set_data(incoming_data)

        for image in incoming_data["images"]:
            new_crossing.add_image(image["title"], image["data"])

        object_id = new_crossing.save_to_db()

        return JsonResponse(
            {
                "status": 200,
                "message": None,
                "id": object_id,
            }
        )
    except JsonSchemaError as exc:
        return JsonResponse({"status": 400, "message": str(exc), "id": None})
    except Exception as exc:
        return JsonResponse({"status": 500, "message": str(exc), "id": None})
