from django.db import models


class BaseModel(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if 'update_fields' in kwargs and 'updated_at' not in kwargs['update_fields']:
            kwargs['update_fields'] = frozenset(list(kwargs['update_fields']) + ['updated_at'])
        super(BaseModel, self).save(*args, **kwargs)