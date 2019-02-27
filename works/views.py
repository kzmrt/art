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
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic.edit import ModelFormMixin
from django.db.models import Q

logger = logging.getLogger('development')


class SearchView(LoginRequiredMixin, generic.ListView, ModelFormMixin):

    paginate_by = 5
    #ordering = ['-updated_at']
    template_name = 'works/index.html'
    form_class = WorkForm
    model = Work

    def get(self, request, *args, **kwargs): # これは必要
        self.object = None
        return generic.ListView.get(self, request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = None
        self.form = self.get_form(self.form_class)

        form_value = [
            self.request.POST.get('title', None),
            self.request.POST.get('authorName', None),
            self.request.POST.get('material', None),
            self.request.POST.get('start_date', None),
            self.request.POST.get('end_date', None),
        ]
        request.session['form_value'] = form_value

        # 検索時にページネーションに関連したエラーを防ぐ
        self.request.GET = self.request.GET.copy()
        self.request.GET.clear()

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


class TestMixin1(UserPassesTestMixin):
    def test_func(self):
        # pkが現在ログイン中ユーザと同じ、またはsuperuserならOK。
        current_user = self.request.user
        author_id = Work.objects.values_list('author_id', flat=True).get(pk=self.kwargs['pk']) # 作品に紐づくID
        return current_user.pk == author_id or current_user.is_superuser


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