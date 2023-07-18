import base64
from datetime import datetime
import json

from django.http import JsonResponse

from backend.models import MountainCrossing, CrossingImages


def submit_data(request):
    incoming_data = json.loads(request.body)

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

    return JsonResponse(
        {
            "status": 200,
            "message": None,
            "id": new_crossing.pk,
        }
    )
