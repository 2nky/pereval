from django.db.models import Model, DateTimeField, BinaryField, JSONField, CharField


class MountainCrossing(Model):
    date_added = DateTimeField(verbose_name="Дата создания")
    raw_data = JSONField(verbose_name="Сырые данные")
    images = JSONField(verbose_name="Список изображений")
    status = CharField(
        max_length=16,
        verbose_name="Статус заявки",
        default="new",
        choices=(
            ("new", "Новое"),
            ("pending", "В работе"),
            ("accepted", "Принято"),
            ("rejected", "Отказано"),
        ),
    )

    def __str__(self):
        prefix = self.raw_data["beautyTitle"].strip()
        title = self.raw_data["title"]
        other_names = self.raw_data["other_titles"]

        return f"{prefix} {title} ({other_names})"

    class Meta:
        db_table = "pereval_added"


class CrossingImages(Model):
    date_added = DateTimeField(verbose_name="Дата создания")
    img = BinaryField(null=True)

    class Meta:
        db_table = "pereval_images"
