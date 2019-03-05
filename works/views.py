from django.shortcuts import render, redirect, reverse
from django.views import generic
from .models import Work, CustomUser, Image
from django.contrib.auth.mixins import LoginRequiredMixin
import logging
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView, PasswordResetView, \
    PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.urls import reverse_lazy
from .forms import CalendarForm, WorkForm, WorkSetForm
from datetime import datetime as dt, timedelta
import bootstrap_datepicker_plus as datetimepicker
from django.views.generic.edit import ModelFormMixin
from django.db.models import Q
from django.contrib import messages
from django.http import HttpResponseRedirect
import os, shutil
from art import settings
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import A4
from reportlab.lib.pagesizes import portrait
from reportlab.lib.units import mm
from reportlab.platypus import Table
from reportlab.platypus import TableStyle
from reportlab.lib import colors

logger = logging.getLogger('development')

NO_IMAGE = '/image/noimage.jpg'  # NO IMAGEパス


class SearchView(LoginRequiredMixin, generic.ListView, ModelFormMixin):

    paginate_by = 5
    template_name = 'works/index.html'
    form_class = WorkForm
    model = Work

    def get(self, request, *args, **kwargs):  # これは必要
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
            format='%Y/%m/%d',
            # attrs={'readonly': 'true', 'class': 'form-control'}, # テキストボックス直接入力不可
            # attrs={'class': 'form-control'},
            options={
                'locale': 'ja',
                'dayViewHeaderFormat': 'YYYY年 MMMM',
                'ignoreReadonly': True,
                'allowInputToggle': True,
                'minDate': '2019/1/1',  # 最小日時（データ取得開始日）
                'defaultDate': start,  # 初期表示
            }
        ).start_of('term')

        calendar_form.fields["end_date"].widget = datetimepicker.DateTimePickerInput(
            format='%Y/%m/%d',
            # attrs={'readonly': 'true'}, # テキストボックス直接入力不可
            options={
                'locale': 'ja',
                'dayViewHeaderFormat': 'YYYY年 MMMM',
                'ignoreReadonly': True,
                'allowInputToggle': True,
                'maxDate': (dt.now() + timedelta(days=1)).strftime('%Y/%m/%d %H:%M:%S'),  # 最大日時（翌日）
                'defaultDate': end,  # 初期表示
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
            condition_title = Q()
            condition_authorName = Q()
            condition_material = Q()
            condition_create_datetime = Q()
            condition_start_datetime = Q()
            condition_end_datetime = Q()
            condition_user = Q()

            current_user = self.request.user
            if not current_user.is_superuser:  # スーパーユーザの場合、リストにすべてを表示する。
                condition_user = Q(author=current_user.id)
            if len(title) != 0 and title[0]:
                condition_title = Q(title__icontains=title)
            if len(authorName) != 0 and authorName[0]:
                condition_authorName = Q(authorName__contains=authorName)
            if len(material) != 0 and material[0]:
                condition_material = Q(material__icontains=material)
            if (len(start) != 0 and len(end) != 0) and (start and end): # 日時が空ではない場合
                condition_create_datetime = Q(create_datetime__range=(start.replace('/', '-'), end.replace('/', '-')))
            elif len(start) != 0 and start: # 開始日時が空ではない場合
                condition_start_datetime = Q(create_datetime__gte=start.replace('/', '-'))
            elif len(end) != 0 and end: # 終了日時が空ではない場合
                condition_end_datetime = Q(create_datetime__lte=end.replace('/', '-'))

            return Work.objects.select_related().filter(condition_title & condition_authorName & condition_material
                                                        & condition_create_datetime
                                                        & condition_start_datetime
                                                        & condition_end_datetime
                                                        & condition_user)

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
    # 詳細画面
    model = Work
    template_name = 'works/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if Image.objects.filter(work_id=self.object.pk).exists():  # 画像が紐づく場合
            # 作品に紐づく画像パスを取得
            image = Image.objects.values_list('image', flat=True).get(work_id=self.object.pk)
        else:
            # No Imageパス
            image = settings.MEDIA_URL + NO_IMAGE
        context['image'] = image

        return context


class CreateView(LoginRequiredMixin, generic.CreateView):
    # 登録画面
    model = Work
    # form_class = WorkForm
    form_class = WorkSetForm

    # def get_success_url(self):  # 詳細画面にリダイレクトする。
    #     return reverse('works:detail', kwargs={'pk': self.object.pk})

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super().get_form_kwargs(*args, **kwargs)
        form_kwargs['initial'] = {'author': self.request.user} # フォームに初期値を設定する。
        return form_kwargs

    def form_valid(self, form):
        # if not form.instance.author_id: # 制作者が未選択の場合
        #     form.instance.author_id = self.request.user.id
        # result = super().form_valid(form)

        # DBへの保存
        work = Work()
        work.title = form.instance.title
        work.authorName = form.instance.authorName
        work.material = form.instance.material
        work.price = form.instance.price
        work.memo = form.instance.memo
        work.author = form.instance.author
        work.create_datetime = form.instance.create_datetime
        work.save()

        if len(self.request.FILES) != 0 and\
                self.request.FILES['form-upload-image'].name:  # 画像ファイルが添付されている場合
            logger.debug("With Image.")

            # サーバーのアップロード先ディレクトリを作成、画像を保存
            save_dir = "/image/" + '{0}/{1}/'.format(self.request.user.id, work.pk)  # auhter_id / work_id
            upload_dir = settings.MEDIA_ROOT + save_dir
            os.makedirs(upload_dir, exist_ok=True)  # ディレクトリが存在しない場合作成する
            path = os.path.join(upload_dir, self.request.FILES['form-upload-image'].name)
            with open(path, 'wb+') as destination:
                for chunk in self.request.FILES['form-upload-image'].chunks():
                    destination.write(chunk)

            # DBへの保存
            image = Image()
            image.work_id = work.pk  # 作品ID
            image.image = settings.MEDIA_URL + save_dir + self.request.FILES['form-upload-image'].name  # アップロードしたイメージパス（サーバー側）
            image.save()
        else:
            logger.debug("No Image.")

        messages.success(self.request, '作品情報を登録しました。')
        return HttpResponseRedirect(reverse('works:detail', kwargs={'pk': work.pk}))  # 詳細画面にリダイレクト

    def form_invalid(self, form):
        result = super().form_invalid(form)
        return result


class UpdateView(TestMixin1, generic.UpdateView):
    # 更新画面
    model = Work
    template_name = 'works/update_form.html'

    # form_class = WorkForm
    form_class = WorkSetForm

    # def get_success_url(self):  # 詳細画面にリダイレクトする。
    #     return reverse('works:detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        # result = super().form_valid(form)

        # 作品情報(Work)を更新する。
        self.object.__dict__.update(form.cleaned_data)
        self.object.save()

        if len(self.request.FILES) != 0 and\
                self.request.FILES['form-upload-image'].name:  # 画像ファイルが添付されている場合
            logger.debug("With Image.")

            save_dir = "/image/" + '{0}/{1}/'.format(self.request.user.id, self.object.pk)  # auhter_id / work_id

            # 古いイメージが存在する場合削除する
            if Image.objects.filter(work_id=self.object.pk).exists():  # 画像が紐づく場合
                # DBレコード削除
                Image.objects.filter(work_id=self.object.pk).delete()

                #  画像ファイルをディレクトリごと削除する。
                upload_dir = settings.MEDIA_ROOT + save_dir
                shutil.rmtree(upload_dir)

            # サーバーのアップロード先ディレクトリを作成、画像を保存
            upload_dir = settings.MEDIA_ROOT + save_dir
            os.makedirs(upload_dir, exist_ok=True)  # ディレクトリが存在しない場合作成する
            path = os.path.join(upload_dir, self.request.FILES['form-upload-image'].name)
            with open(path, 'wb+') as destination:
                for chunk in self.request.FILES['form-upload-image'].chunks():
                    destination.write(chunk)

            # DBへの保存
            image = Image()
            image.work_id = self.object.pk  # 作品ID
            image.image = settings.MEDIA_URL + save_dir + self.request.FILES['form-upload-image'].name  # アップロードしたイメージパス（サーバー側）
            image.save()
        else:
            logger.debug("No Image.")

        messages.success(self.request, '作品情報を更新しました。')
        return HttpResponseRedirect(reverse('works:detail', kwargs={'pk': self.object.pk}))  # 詳細画面にリダイレクト

    def form_invalid(self, form):
        result = super().form_invalid(form)
        return result


class DeleteView(TestMixin1, generic.DeleteView):
    # 削除画面
    model = Work
    template_name = 'works/delete.html'
    success_url = reverse_lazy('works:index')  # 検索画面にリダイレクトする。

    def delete(self, request, *args, **kwargs):

        if Image.objects.filter(work_id=self.kwargs['pk']).exists():  # 画像が紐づく場合
            #  画像ファイルをディレクトリごと削除する。
            save_dir = "/image/" + '{0}/{1}/'.format(self.request.user.id, self.kwargs['pk'])  # auhter_id / work_id
            upload_dir = settings.MEDIA_ROOT + save_dir
            shutil.rmtree(upload_dir)

        result = super().delete(request, *args, **kwargs)

        messages.success(
            self.request, '「{}」を削除しました。'.format(self.object))
        return result


class BasicPdf(LoginRequiredMixin, generic.View):
    filename = 'art_work_list.pdf'  # 出力ファイル名
    title = 'title: Art Works'
    font_name = 'HeiseiKakuGo-W5'  # フォント
    is_bottomup = True

    def get(self, request, *args, **kwargs):

        # PDF出力
        response = HttpResponse(status=200, content_type='application/pdf')
        # response['Content-Disposition'] = 'attachment; filename="{}"'.format(self.filename)  # ダウンロードする場合
        response['Content-Disposition'] = 'filename="{}"'.format(self.filename)  # 画面に表示する場合

        # A4縦書きのpdfを作る
        size = portrait(A4)

        # pdfを描く場所を作成：位置を決める原点は左上にする(bottomup)
        # デフォルトの原点は左下
        p = canvas.Canvas(response, pagesize=size, bottomup=self.is_bottomup)

        pdfmetrics.registerFont(UnicodeCIDFont(self.font_name))
        p.setFont(self.font_name, 16)  # フォントを設定

        # pdfのタイトルを設定
        p.setTitle(self.title)

        # Draw things on the PDF. Here's where the PDF generation happens.
        # See the ReportLab documentation for the full list of functionality.
        # X座標(左端から)、Y座標(下から)
        # p.drawString(100, 500, "こんにちは")

        if Image.objects.filter(work_id=1).exists():  # 画像が紐づく場合
            # 作品に紐づく画像パスを取得
            image = Image.objects.values_list('image', flat=True).get(work_id=1)
        else:
            # No Imageパス
            image = settings.MEDIA_URL + NO_IMAGE

        # 画像の描画
        p.drawImage(ImageReader(image[1:]), 10, 550, width=580, height=280, mask='auto', preserveAspectRatio=True)

        # キャプション情報
        # 複数行の表を用意したい場合、二次元配列でデータを用意する
        data = [
            ['作品タイトル', '最後の晩餐', '価格','￥9,000,000,000,000.-'],
            ['作者', 'レオナルド・ダ・ヴィンチ', '画材','油絵'],
        ]

        table = Table(data)
        # TableStyleを使って、Tableの装飾をします
        table.setStyle(TableStyle([
            # 表で使うフォントとそのサイズを設定
            ('FONT', (0, 0), (-1, -1), self.font_name, 9),
            # 四角に罫線を引いて、0.5の太さで、色は黒
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            # 四角の内側に格子状の罫線を引いて、0.25の太さで、色は黒
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
            # セルの縦文字位置を、TOPにする
            # 他にMIDDLEやBOTTOMを指定できるのでお好みで
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        # tableを描き出す位置を指定
        table.wrapOn(p, 50 * mm, 10 * mm)
        table.drawOn(p, 50 * mm, 170 * mm)

        # Close the PDF object cleanly, and we're done.
        p.showPage()  # Canvasに書き込み
        p.save()  # ファイル保存

        self._draw(p)

        return response

    def _draw(self, p):
        pass


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