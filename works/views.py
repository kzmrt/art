from django.shortcuts import render, redirect
from django.views import generic
from .models import Work
from django.contrib.auth.mixins import LoginRequiredMixin
import logging
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView, PasswordResetView, \
    PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.urls import reverse_lazy
from .forms import CalendarForm, WorkForm
from datetime import datetime as dt, timedelta
import bootstrap_datepicker_plus as datetimepicker

logger = logging.getLogger('development')


class IndexView(LoginRequiredMixin, generic.ListView):

    paginate_by = 5
    ordering = ['-updated_at']
    template_name = 'works/index.html'
    form_class = WorkForm
    model = Work

    def get_form(self):
        form = super().get_form()
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Form（カレンダー入力）
        default_data = {'start_date': (dt.now() + timedelta(days=-2)).strftime('%Y/%m/%d'),  # 開始日時は2日前
                        'end_date': (dt.now() + timedelta(days=1)).strftime('%Y/%m/%d')}  # カレンダー初期値の設定
        calendar_form = CalendarForm(initial=default_data)
        calendar_form.fields["start_date"].widget = datetimepicker.DateTimePickerInput(
            format='%Y/%m/%d %H:%M:%S',
            # attrs={'readonly': 'true', 'class': 'form-control'}, # テキストボックス直接入力不可
            # attrs={'class': 'form-control'},
            options={
                'locale': 'ja',
                'dayViewHeaderFormat': 'YYYY年 MMMM',
                'ignoreReadonly': True,
                'allowInputToggle': True,
                'minDate': '2019/2/20',  # 最小日時（データ取得開始日）
                # 'defaultDate': '2018/10/22', # 初期表示
            }
        ).start_of('term')

        calendar_form.fields["end_date"].widget = datetimepicker.DateTimePickerInput(
            format='%Y/%m/%d %H:%M:%S',
            # attrs={'readonly': 'true'}, # テキストボックス直接入力不可
            options={
                'locale': 'ja',
                'dayViewHeaderFormat': 'YYYY年 MMMM',
                'ignoreReadonly': True,
                'allowInputToggle': True,
                'maxDate': (dt.now() + timedelta(days=1)).strftime('%Y/%m/%d %H:%M:%S'),  # 最大日時（翌日）
            }
        ).end_of('term')

        context['calendar_form'] = calendar_form

        return context

    def get_queryset(self):
        current_user = self.request.user
        if current_user.is_superuser:  # スーパーユーザの場合、リストにすべてを表示する。
            return Work.objects.all()
        else:  # 一般ユーザは自分のレコードのみ表示する。
            return Work.objects.filter(author=current_user.id)


class TestMixin1(UserPassesTestMixin):
    def test_func(self):
        # pkが現在ログイン中ユーザと同じ、またはsuperuserならOK。
        current_user = self.request.user
        author_id = Work.objects.values_list('author_id', flat=True).get(pk=self.kwargs['pk']) # 作品に紐づくID
        return current_user.pk == author_id or current_user.is_superuser


def update_query_result(request, pk):
    start = request.POST.getlist("start_date")  # 入力した値を取得
    end = request.POST.getlist("end_date")  # 入力した値を取得

    # 指定日時のデータを取得
    """
    for data in db.GetDbRecord.get_greenhouse_record(pk, start_datetime=start[0],
                                                     end_datetime=end[0]):  # DBレコード取得
        x_greenhouse_data.append(data[2].strftime('%Y/%m/%d %H:%M:%S'))
        data_temp_out.append(data[3])
        data_temp_in.append(data[4])
        data_temp_set.append(data[5])
        data_rh_out.append(data[6])
        data_rh_in.append(data[7])
        data_irradiance.append(data[8])
        data_co2_conc.append(data[9])
        data_net_photos.append(data[10])
    """

    return render(request, 'works/result.html')
#    return render(request, 'works/result.html', {'x_greenhouse_data': x_greenhouse_data,})


class DetailView(TestMixin1, generic.DetailView):
    model = Work
    template_name = 'works/detail.html'


class PasswordChange(LoginRequiredMixin, PasswordChangeView):
    # パスワード変更
    success_url = reverse_lazy('works:password_change_done')
    template_name = 'works/password_change_form.html'

    def get_context_data(self, **kwargs):
        self.request.session.modified = True  # セッション更新
        context = super().get_context_data(**kwargs) # 継承元のメソッドCALL
        context["form_name"] = "password_change"
        return context


class PasswordChangeDone(LoginRequiredMixin, PasswordChangeDoneView):
    # パスワード変更完了
    template_name = 'works/password_change_done.html'


class PasswordReset(PasswordResetView):
    """パスワード変更用URLの送付ページ"""
    subject_template_name = 'works/mail_template/reset/subject.txt'
    email_template_name = 'works/mail_template/reset/message.txt'
    template_name = 'works/password_reset_form.html'
    success_url = reverse_lazy('works:password_reset_done')


class PasswordResetDone(PasswordResetDoneView):
    """パスワード変更用URLを送りましたページ"""
    template_name = 'works/password_reset_done.html'


class PasswordResetConfirm(PasswordResetConfirmView):
    # パスワードリセット確認
    success_url = reverse_lazy('works:password_reset_complete')
    template_name = 'works/password_reset_confirm.html'


class PasswordChangeComplete(PasswordResetCompleteView):
    # パスワードリセット完了
    template_name = 'works/password_reset_complete.html'