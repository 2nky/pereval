import base64
from datetime import datetime
import json

from django.http import (
    JsonResponse,
    HttpResponse,
    HttpResponseNotFound,
    HttpResponseNotAllowed,
    HttpResponseGone,
)
from django.views.decorators.http import require_http_methods

from backend.models import MountainCrossing, CrossingImages


class JsonSchemaError(Exception):
    pass


def check_json_schema(data):
    if "images" not in data:
        raise JsonSchemaError("Отсутствуют ключ 'images'")

    for image in data["images"]:
        if "title" not in image:
            raise JsonSchemaError(
                "Отсутствует ключ 'title' в прикрепленном изображении!"
            )

        if "data" not in image:
            raise JsonSchemaError(
                "Отсутствует ключ 'data' в прикрепленном изображении!"
            )


class Crossing:
    raw_data = {}
    images = []
    status = "new"
    object_pk = None

    def set_data(self, data):
        self.raw_data = data

    def add_image(self, title, encoded_data):
        raw_image = base64.b64decode(encoded_data)
        self.images.append((title, raw_image))

    def save_to_db(self):
        # Если объект уже есть в БД, то используем его
        try:
            print(f"Updating object with {self.object_pk}")
            crossing = MountainCrossing.objects.get(pk=self.object_pk)
        except MountainCrossing.DoesNotExist:
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

        crossing.object_pk = crossing.pk
        return crossing.pk

    @staticmethod
    def get_by_id(record_id):
        try:
            # Получаем объект из БД
            crossing_from_db = MountainCrossing.objects.get(pk=record_id)

            # Заполняем объект данными из БД
            new_object = Crossing()
            new_object.raw_data = crossing_from_db.raw_data
            new_object.status = crossing_from_db.status
            new_object.object_pk = record_id

            # Достать из БД связанные с перевалом изображения
            for image_record in crossing_from_db.images["images"]:
                linked_photo_obj = CrossingImages.objects.get(pk=image_record["id"])
                new_object.images.append((image_record["title"], linked_photo_obj.img))

            return new_object

        except MountainCrossing.DoesNotExist:
            return None


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


def update_by_id(record_id, request):
    try:
        incoming_data = json.loads(request.body)

        crossing = Crossing.get_by_id(record_id)
        crossing.set_data(incoming_data)
        crossing.save_to_db()

        return JsonResponse(
            {
                "state": 1,
                "message": "",
            }
        )
    except Exception as exc:
        return JsonResponse(
            {
                "state": 0,
                "message": str(exc),
            }
        )


@require_http_methods(["GET", "PATCH"])
def single_crossing_operations(request, record_id):
    if request.method == "GET":
        return get_by_id(record_id)
    elif request.method == "PATCH":
        return update_by_id(record_id, request)

    return HttpResponseNotAllowed(["GET", "PATCH"])


def get_by_id(record_id):
    crossing = Crossing.get_by_id(record_id)
    if crossing is None:
        return HttpResponseNotFound(f"Crossing with ID={record_id} not found.")
    response = {}
    response.update(crossing.raw_data)
    response["status"] = crossing.status
    response["images"] = []
    for title, image_bytes in crossing.images:
        response["images"].append(
            {
                "title": title,
                "data": base64.b64encode(image_bytes).decode("ascii"),
            }
        )
    return JsonResponse(response)
