from django.db.models import DateTimeField, Model


class ReatsModel(Model):
    created: DateTimeField = DateTimeField(auto_now_add=True)
    modified: DateTimeField = DateTimeField(auto_now=True)

    class Meta:
        abstract = True
