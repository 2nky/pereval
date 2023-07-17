from django.db.models import Model, DateTimeField, BinaryField, JSONField


class MountainCrossing(Model):
    date_added = DateTimeField(verbose_name="Дата создания")
    raw_data = JSONField(verbose_name="Сырые данные")
    images = JSONField(verbose_name="Список изображений")

    class Meta:
        db_table = "pereval_added"


class CrossingImages(Model):
    date_added = DateTimeField(verbose_name="Дата создания")
    img = BinaryField(null=True)

    class Meta:
        db_table = "pereval_images"
