from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser, Work
import bootstrap_datepicker_plus as datetimepicker
from datetime import datetime as dt, timedelta
from django import forms


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm):
        model = CustomUser
        fields = ('username', 'email')


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email')


class WorkForm(forms.ModelForm):
    class Meta:
        model = Work
        fields = ('create_datetime',) # DateTimePickerInputを使用するために必要
        widgets = {
            'create_datetime': datetimepicker.DateTimePickerInput(
                format='%Y-%m-%d %H:%M:%S',
                attrs={'readonly': 'true'},
                options={
                    'locale': 'ja',
                    'dayViewHeaderFormat': 'YYYY年 MMMM',
                    'ignoreReadonly': True,
                    'allowInputToggle': True,
                }
            ),
        }

        # fields = ('title','authorName','material','price','memo',)


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
            format='%Y/%m/%d %H:%M:%S',
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
            format='%Y/%m/%d %H:%M:%S',
            # attrs={'readonly': 'true'}, # テキストボックス直接入力不可
            options={
                'locale': 'ja',
                'dayViewHeaderFormat': 'YYYY年 MMMM',
                'ignoreReadonly': True,
                'allowInputToggle': True,
                'maxDate': (dt.now() + timedelta(days = 1)).strftime('%Y/%m/%d %H:%M:%S'),  # 最大日時（翌日）
            }
        ).end_of('term'),
    )
