from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser, Work, Image
import bootstrap_datepicker_plus as datetimepicker
from datetime import datetime as dt, timedelta
from django import forms
import os
from django_superform import ModelFormField, SuperModelForm

VALID_EXTENSIONS = ['.jpg']


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm):
        model = CustomUser
        fields = ('username', 'email')


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email')


class WorkForm(forms.ModelForm):
    author = forms.ModelChoiceField(CustomUser.objects.all(), empty_label=None) # 空選択肢を除外

    class Meta:
        model = Work
        fields = ('title','authorName','size','material','price','memo','create_datetime','author',)

        title = forms.CharField(
            initial='',
            label='タイトル',
            required=True,  # 必須
            max_length=255,
        )
        authorName = forms.CharField(
            initial='',
            label='作者',
            required=True,  # 必須
            max_length=255,
        )
        size = forms.CharField(
            initial='',
            label='サイズ',
            required=True,  # 必須
            max_length=255,
        )
        material = forms.CharField(
            initial='',
            label='画材',
            required=True,  # 必須
            max_length=255,
        )
        price = forms.CharField(
            initial='',
            label='価格',
            required=True,  # 必須
            max_length=255,
        )
        memo = forms.CharField(
            initial='',
            label='メモ',
            required=False,  # 必須ではない
            max_length=255,
        )
        widgets = {
            'create_datetime': datetimepicker.DateTimePickerInput(
                format='%Y-%m-%d',
                attrs={'readonly': 'true'},
                options={
                    'locale': 'ja',
                    'dayViewHeaderFormat': 'YYYY年 MMMM',
                    'ignoreReadonly': True,
                    'allowInputToggle': True,
                    'maxDate': (dt.now() + timedelta(days = 1)).strftime('%Y/%m/%d'),  # 最大日時（翌日）
                    # 'defaultDate': (dt.now() + timedelta(days = -1)).strftime('%Y/%m/%d %H:%M:%S'), # 初期値はmodelで定義した値が採用される
                }
            ),
        }


class CalendarForm(forms.Form):

    title = forms.CharField(
        initial='',
        label='タイトル',
        required = False, # 必須ではない
    )
    authorName = forms.CharField(
        initial='',
        label='作者',
        required=False,  # 必須ではない
    )
    material = forms.CharField(
        initial='',
        label='画材',
        required=False,  # 必須ではない
    )
    start_date = forms.DateField(
        initial='',
        label='開始日時',
        required=False,  # 必須ではない
        widget=datetimepicker.DateTimePickerInput(
            format='%Y/%m/%d',
            # attrs={'readonly': 'true'}, # テキストボックス直接入力不可
            # attrs={'class': 'form-control'},
            options={
                'locale': 'ja',
                'dayViewHeaderFormat': 'YYYY年 MMMM',
                'ignoreReadonly': True,
                'allowInputToggle': True,
                # 'minDate': '', # 最小日時（データ取得開始日）
                # 'defaultDate': '2018/10/22', # 初期表示
            }
        ).start_of('term'),
    )
    end_date = forms.DateField(
        label='終了日時',
        initial='', # 初期値
        required=False,  # 必須ではない
        widget=datetimepicker.DateTimePickerInput(
            format='%Y/%m/%d',
            # attrs={'readonly': 'true'}, # テキストボックス直接入力不可
            options={
                'locale': 'ja',
                'dayViewHeaderFormat': 'YYYY年 MMMM',
                'ignoreReadonly': True,
                'allowInputToggle': True,
                'maxDate': (dt.now() + timedelta(days = 1)).strftime('%Y/%m/%d'),  # 最大日時（翌日）
            }
        ).end_of('term'),
    )


class UploadFileForm(forms.ModelForm):
    class Meta:
        model = Image
        fields = ('image',)

        image = forms.ImageField(
            label='画像',
            required=False,  # 必須 or 必須ではない
        )

    def clean_image(self):
        image = self.cleaned_data['image']
        if image:  # 画像ファイルが指定されている場合
            extension = os.path.splitext(image.name)[1]  # 拡張子を取得
            if not extension.lower() in VALID_EXTENSIONS:
                raise forms.ValidationError('jpgファイルを選択してください！')
        return image  # viewsでcleaned_dataを参照するためreturnする


class WorkSetForm(SuperModelForm):
    # 複数のフォームを使用する
    upload = ModelFormField(UploadFileForm)

    class Meta:
        model = Work
        fields = ('title', 'authorName', 'size', 'material', 'price', 'memo', 'create_datetime', 'author',)

        title = forms.CharField(
            initial='',
            label='タイトル',
            required=True,  # 必須
            max_length=255,
        )
        authorName = forms.CharField(
            initial='',
            label='作者',
            required=True,  # 必須
            max_length=255,
        )
        size = forms.CharField(
            initial='',
            label='サイズ',
            required=True,  # 必須
            max_length=255,
        )
        material = forms.CharField(
            initial='',
            label='画材',
            required=True,  # 必須
            max_length=255,
        )
        price = forms.CharField(
            initial='',
            label='価格',
            required=True,  # 必須
            max_length=255,
        )
        memo = forms.CharField(
            initial='',
            label='メモ',
            required=False,  # 必須ではない
            max_length=255,
        )
        widgets = {
            'create_datetime': datetimepicker.DateTimePickerInput(
                format='%Y-%m-%d',
                attrs={'readonly': 'true'},
                options={
                    'locale': 'ja',
                    'dayViewHeaderFormat': 'YYYY年 MMMM',
                    'ignoreReadonly': True,
                    'allowInputToggle': True,
                    'maxDate': (dt.now() + timedelta(days=1)).strftime('%Y/%m/%d'),  # 最大日時（翌日）
                    # 'defaultDate': (dt.now() + timedelta(days = -1)).strftime('%Y/%m/%d %H:%M:%S'), # 初期値はmodelで定義した値が採用される
                }
            ),
        }