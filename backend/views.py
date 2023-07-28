import base64
from datetime import datetime
import json

from django.http import (
    JsonResponse,
    HttpResponse,
    HttpResponseNotFound,
    HttpResponseNotAllowed,
    HttpResponseGone,
    HttpResponseBadRequest,
)
from django.views.decorators.http import require_http_methods

from backend.models import MountainCrossing, CrossingImages


class JsonSchemaError(Exception):
    pass


class ForbiddenFieldError(Exception):
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
    def __init__(self):
        self.raw_data = {}
        self.images = []
        self._image_title_to_pk = {}
        self.object_pk = None
        self.status = "new"

    def set_data(self, data):
        self.raw_data = data

    def add_image(self, title, encoded_data):
        raw_image = base64.b64decode(encoded_data)

        # Ищем уже существующее изображение с таким заголовком...
        existing_image_index = None
        for index, data in enumerate(self.images):
            if data[0] == title:
                existing_image_index = index
                break

        # ...и если оно есть - удаляем.
        if existing_image_index is not None:
            self.images.pop(existing_image_index)

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
            # Мы перезаписываем уже существующее изображение, надо удалить старую запись
            if title in self._image_title_to_pk:
                old_image_pk = self._image_title_to_pk[title]
                try:
                    CrossingImages.objects.get(pk=old_image_pk).delete()
                except CrossingImages.DoesNotExist:
                    # Кто знает, может объект уже удалили из БД :(
                    pass

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
            for img_record in crossing_from_db.images["images"]:
                linked_photo_obj = CrossingImages.objects.get(pk=img_record["id"])
                new_object.images.append((img_record["title"], linked_photo_obj.img))
                # Сохраняем связь между заголовком и записью для возможного обновления
                new_object._image_title_to_pk[img_record["title"]] = img_record["id"]
            return new_object

        except MountainCrossing.DoesNotExist:
            return None

    @staticmethod
    def crossings_by_user(email):
        return MountainCrossing.objects.filter(raw_data__user__email=email).values_list(
            "pk", flat=True
        )


@require_http_methods(["GET", "POST"])
def submit_data(request):
    if request.method == "POST":
        return create_crossing_data(request)
    elif request.method == "GET":
        user_email = request.GET.get("user__email")

        # Проверим что передам необходимый параметр
        if user_email is None:
            return HttpResponseBadRequest()

        crossing_dicts = users_crossing(user_email)
        if len(crossing_dicts) == 0:
            # Если у пользователя нет зарегистрированных перевалов, то покажем ошибку "No Content"
            return HttpResponse(status=204)

        return JsonResponse({"crossings": crossing_dicts})

    return HttpResponseNotAllowed(["GET", "POST"])


def users_crossing(email):
    result = []
    record_pks = Crossing.crossings_by_user(email)
    for crossing_pk in record_pks:
        crossing = Crossing.get_by_id(crossing_pk)
        result.append(crossing_to_dict(crossing))

    return result


def create_crossing_data(request):
    try:
        incoming_data = json.loads(request.body)
        # Проверим корректность пришедших данных
        check_json_schema(incoming_data)

        new_crossing = Crossing()
        new_crossing.set_data(incoming_data)
        # Нет смысла сохранять изображения в данных запроса, мы их отдельно храним
        images = incoming_data.pop("images")

        for image in images:
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
        check_json_schema(incoming_data)

        if "user" in incoming_data:
            raise ForbiddenFieldError("Horizon: Forbidden West")

        crossing = Crossing.get_by_id(record_id)
        # Изображения должны сохраняться в отдельную таблицу
        incoming_images = incoming_data.pop("images", [])
        for image in incoming_images:
            crossing.add_image(image["title"], image["data"])

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

    return JsonResponse(crossing_to_dict(crossing))


def crossing_to_dict(crossing):
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
    return response
