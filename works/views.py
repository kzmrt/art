import openpyxl
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
from openpyxl.writer.excel import save_virtual_workbook

logger = logging.getLogger('development')

NO_IMAGE = '/image/noimage.jpg'  # NO IMAGEパス
TEMPLATE_EXCEL = '/excel/template.xlsx'  # Template.xlsxパス


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

        if self.request.POST.get('search', None):  # 検索ボタンが押された場合
            logger.debug("検索")

        elif self.request.POST.get('csv', None):  # キャプション情報出力ボタンが押された場合
            logger.debug("キャプション情報出力")
            return HttpResponseRedirect(reverse('works:csv'))  # CSV出力へリダイレクト

        else:  # PDF出力ボタンが押された場合
            logger.debug("PDF出力")
            check_value =[
                self.request.POST.getlist('checkbox')
            ]
            request.session['check_value'] = check_value  # チェックボックスの値をセッションに渡す
            return HttpResponseRedirect(reverse('works:pdf'))  # PDF出力へリダイレクト

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

        # No Imageパス
        no_image = settings.MEDIA_URL + NO_IMAGE
        context['no_image'] = no_image

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
        work.size = form.instance.size
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


class BasicCsv(LoginRequiredMixin, generic.View):
    """
    キャプション情報のダウンロード
    """
    filename = 'art_work_list.xlsx'  # 出力ファイル名

    def get(self, request, *args, **kwargs):
        # Template.xlsxパス
        template_xlsx = settings.MEDIA_ROOT + TEMPLATE_EXCEL
        wb = openpyxl.load_workbook(template_xlsx)  # テンプレートの読み込み
        sheet = wb['data']  # sheetの選択

        # 全ての作品情報を出力する。（検索結果は無関係）
        id_array = list(Work.objects.all().values_list('pk', flat=True))

        for work_count, work_id in enumerate(id_array):

            # キャプション情報
            captionInfo = Work.objects.filter(pk=work_id).first()

            # 複数行の表を用意したい場合、二次元配列でデータを用意する
            if captionInfo.price > 0:
                price = "￥{:,d}.-".format(captionInfo.price)
            elif captionInfo.price <= -100:
                price = "SOLD OUT"
            else:
                price = "非売品"

            sheet["A{:,d}".format(work_count + 2)] = captionInfo.title       # タイトル
            sheet["B{:,d}".format(work_count + 2)] = captionInfo.authorName  # 作者
            sheet["C{:,d}".format(work_count + 2)] = captionInfo.size        # サイズ
            sheet["D{:,d}".format(work_count + 2)] = captionInfo.material    # 画材
            sheet["E{:,d}".format(work_count + 2)] = price                   # 価格
            sheet["F{:,d}".format(work_count + 2)] = captionInfo.memo        # メモ

        # CSV出力
        response = HttpResponse(status=200, content=save_virtual_workbook(wb), content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(self.filename)  # ダウンロードする場合

        return response

    def _draw(self, p):
        pass


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

        # sessionに値がある場合
        if 'check_value' in self.request.session:
            check_value = self.request.session['check_value']
            checkList = check_value[0]
            logger.debug(checkList)

        if len(checkList) > 0:
            logger.debug("チェックあり")

            # チェックされた作品情報のみ出力する。
            id_array = checkList[-1].split(",")  # 最後の要素（最新の情報）を取得する。
        else:
            logger.debug("チェックなし")

            current_user = self.request.user
            if current_user.is_superuser:
                # 管理者の場合、すべて出力する。
                logger.debug('管理者です。')
                # 全ての作品情報を出力する。（検索結果は無関係）
                id_array = list(Work.objects.all().values_list('pk', flat=True))
            else:
                # 一般ユーザーの場合、自分の作品のみ出力する。
                logger.debug('一般ユーザーです。')
                id_array = list(Work.objects.filter(author=current_user.id).values_list('pk', flat=True))

        for work_count, work_id in enumerate(id_array):

            logger.debug(work_count)

            if Image.objects.filter(work_id=work_id).exists():  # 画像が紐づく場合
                # 作品に紐づく画像パスを取得
                image = Image.objects.values_list('image', flat=True).get(work_id=work_id)
            else:
                # No Imageパス
                image = settings.MEDIA_URL + NO_IMAGE

            # キャプション情報
            workInfo = Work.objects.filter(pk=work_id).first()

            # 複数行の表を用意したい場合、二次元配列でデータを用意する
            if workInfo.price > 0 :
                price = "￥{:,d}.-".format(workInfo.price)
            elif workInfo.price <= -100:
                price = "SOLD OUT"
            else:
                price = "非売品"

            data = [
                ['タイトル', workInfo.title, 'サイズ', workInfo.size],
                ['作者', workInfo.authorName, '画材', workInfo.material],
                ['価格', price, 'メモ', workInfo.memo],
            ]

            # table = Table(data)
            table = Table(data, (15 * mm, 50 * mm, 12 * mm, 50 * mm), None, hAlign='CENTER')
            # TableStyleを使って、Tableの装飾をします
            table.setStyle(TableStyle([
                # 表で使うフォントとそのサイズを設定
                ('FONT', (0, 0), (-1, -1), self.font_name, 9),
                # 四角に罫線を引いて、0.5の太さで、色は黒
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                # 四角の内側に格子状の罫線を引いて、0.25の太さで、色は黒
                ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                # セルの結合
                #('SPAN', (2, 2), (3, 2)),
                # セルの縦文字位置
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ('TEXTCOLOR', (0, 0), (0, 2), colors.darkblue),
                ('TEXTCOLOR', (2, 0), (2, 2), colors.darkblue),
            ]))

            if work_count % 2 == 0:  # 偶数の場合

                # 画像の描画
                p.drawImage(ImageReader(image[1:]), 10, 530, width=580, height=280, mask='auto',
                            preserveAspectRatio=True)

                # tableを描き出す位置を指定
                table.wrapOn(p, 50 * mm, 50 * mm)
                table.drawOn(p, 43 * mm, 160 * mm)

            else:  # 奇数の場合

                # 画像の描画
                p.drawImage(ImageReader(image[1:]), 10, 130, width=580, height=280, mask='auto',
                            preserveAspectRatio=True)

                # tableを描き出す位置を指定
                table.wrapOn(p, 50 * mm, 50 * mm)
                table.drawOn(p, 43 * mm, 19 * mm)

                p.showPage()  # Canvasに書き込み（改ページ）

        if len(id_array) % 2 != 0:  # 出力作品数が奇数の場合
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