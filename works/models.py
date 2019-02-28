from django.db import models
from django.urls import reverse
from django.contrib.auth.models import AbstractUser
from datetime import datetime as dt, timedelta


class CustomUser(AbstractUser):

    def __str__(self):
        return self.username + ":" + self.email


class Work(models.Model):
    """作品モデル"""
    class Meta:
        db_table = 'work'

    title = models.CharField(verbose_name='作品名', max_length=255)
    authorName = models.CharField(verbose_name='作者', max_length=255)
    material = models.CharField(verbose_name='画材', max_length=255)
    price = models.CharField(verbose_name='価格', max_length=255)
    memo = models.CharField(verbose_name='メモ', max_length=255, default='', blank=True)
    author = models.ForeignKey(
        'works.CustomUser',
        on_delete=models.CASCADE,
        verbose_name='制作者',
    )
    create_datetime = models.DateTimeField(verbose_name='作成年月日',
                                         default=(dt.now() + timedelta(days = -1)).strftime('%Y/%m/%d %H:%M:%S'))
    created_at = models.DateTimeField(verbose_name='登録日時', auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name='更新日時', auto_now=True)

    def __str__(self):
        return self.title + ',' + self.authorName + ',' + self.material + ',' + self.price + ',' + self.memo \
               + ',' + self.create_datetime

    @staticmethod
    def get_absolute_url(self):
        return reverse('works:index')


class Image(models.Model):
    """イメージモデル"""
    class Meta:
        db_table = 'image'

    work = models.ForeignKey(Work, verbose_name='作品', on_delete=models.PROTECT)
    image = models.ImageField(upload_to="image/", verbose_name='イメージ')
    created_at = models.DateTimeField(verbose_name='登録日時', auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name='更新日時', auto_now=True)

    def __str__(self):
        return self.work.title + ":" + str(self.data_datetime)