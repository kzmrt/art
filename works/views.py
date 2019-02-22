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
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic.edit import ModelFormMixin
from django.db.models import Q

logger = logging.getLogger('development')


class SearchView(LoginRequiredMixin, generic.ListView, ModelFormMixin):

    paginate_by = 3
    #ordering = ['-updated_at']
    template_name = 'works/index.html'
    form_class = WorkForm
    model = Work

    def get(self, request, *args, **kwargs): # これは必要
        self.object = None
        #self.form = self.get_form(self.form_class)
        # Explicitly states what get to call:
        return generic.ListView.get(self, request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # When the form is submitted, it will enter here
        self.object = None
        self.form = self.get_form(self.form_class)

        # if self.form.is_valid():
        #     self.object = self.form.save()
            # Here ou may consider creating a new instance of form_class(),
            # so that the form will come clean.

        form_value = [
            self.request.POST.getlist("title")[0],
            self.request.POST.getlist("authorName")[0],
            self.request.POST.getlist("material")[0],
            self.request.POST.getlist("start_date"),
            self.request.POST.getlist("end_date"),
        ]
        request.session['form_value'] = form_value

        # Whether the form validates or not, the view will be rendered by get()
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Form（カレンダー入力など）
        title = ''
        authorName = ''
        material = ''
        start = ''
        end = ''
        # sessionに値がある場合、その値をセットする。（ページングしてもform値が変わらないように）
        if 'form_value' in self.request.session:
            form_value = self.request.session['form_value']
            title = form_value[0]
            authorName = form_value[1]
            material = form_value[2]
            start = form_value[3]
            end = form_value[4]
        # else:
            # start = (dt.now() + timedelta(days=-2)).strftime('%Y/%m/%d')
            # end = (dt.now() + timedelta(days=1)).strftime('%Y/%m/%d')

        default_data = {'title': title,  # タイトル
                        'authorName': authorName,  # 作者名
                        'material': material,  # 画材
                        'start_date': start,  # 開始日時
                        'end_date': end}  # 終了日時
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
                'minDate': '2019/1/1',  # 最小日時（データ取得開始日）
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
        # sessionに値がある場合、その値でクエリ発行する。
        if 'form_value' in self.request.session:
            form_value = self.request.session['form_value']
            title = form_value[0]
            authorName = form_value[1]
            material = form_value[2]
            start = form_value[3]
            end = form_value[4]

            # 検索条件
            term_title = Q()
            term_authorName = Q()
            term_material = Q()
            term_create_datetime = Q()
            term_user = Q()

            current_user = self.request.user
            if not current_user.is_superuser:  # スーパーユーザの場合、リストにすべてを表示する。
                term_user = Q(author=current_user.id)
            if len(title) != 0 and title[0]:
                term_title = Q(title__icontains=title)
            if len(authorName) != 0 and authorName[0]:
                term_authorName = Q(authorName__contains=authorName)
            if len(material) != 0 and material[0]:
                term_material = Q(material__icontains=material)
            if (len(start) != 0 and len(end) != 0) and (start[0] and end[0]): # 日時が空ではない場合
                term_create_datetime = Q(create_datetime__range=(start[0].replace('/', '-'), end[0].replace('/', '-')))

            return Work.objects.select_related().filter(term_title & term_authorName & term_material & term_create_datetime & term_user)

        else:
            # 何も返さない
            return Work.objects.none()



"""


# 検索フォーム
class SearchView(LoginRequiredMixin, generic.FormView):
    model = Work
    template_name = 'works/index.html'
    form_class = WorkForm

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
                'minDate': '2019/1/1',  # 最小日時（データ取得開始日）
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
"""

class TestMixin1(UserPassesTestMixin):
    def test_func(self):
        # pkが現在ログイン中ユーザと同じ、またはsuperuserならOK。
        current_user = self.request.user
        author_id = Work.objects.values_list('author_id', flat=True).get(pk=self.kwargs['pk']) # 作品に紐づくID
        return current_user.pk == author_id or current_user.is_superuser


# 検索リスト
class ResultView(generic.ListView):

    #paginate_by = 3
    #ordering = ['-updated_at']
    template_name = 'works/result.html'
    model = Work
    #context_object_name = 'work_list'
    #queryset = Work.objects.all()

    def post(self, request, *args, **kwargs):
        work_list = self.get_queryset(request=request)
        page = request.GET.get('page', 1)
        paginator = Paginator(work_list, 3)
        try:
            work_list = paginator.page(page)
        except PageNotAnInteger:
            work_list = paginator.page(1)
        except EmptyPage:
            work_list = paginator.page(paginator.num_pages)
        return render(request, 'works/result.html', {'work_list': work_list, })

    def get_queryset(self, request):
        start = request.POST.getlist("start_date")  # 入力した値を取得
        end = request.POST.getlist("end_date")  # 入力した値を取得
        logger.debug("start = " + str(start[0]))
        logger.debug("end = " + str(end[0]))
        current_user = self.request.user
        if current_user.is_superuser:  # スーパーユーザの場合、リストにすべてを表示する。
            return Work.objects.all()
        else:  # 一般ユーザは自分のレコードのみ表示する。
            return Work.objects.filter(author=current_user.id)


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