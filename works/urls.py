from django.urls import path
from . import views

app_name = 'works'

urlpatterns = [
    # トップ画面（検索画面）
    path('', views.SearchView.as_view(), name='index'),

    # 詳細画面
    path('works/<int:pk>/', views.DetailView.as_view(), name='detail'),

    # 登録画面
    path('create/', views.CreateView.as_view(), name='create'),

    # 更新画面
    path('update/<int:pk>/', views.UpdateView.as_view(), name='update'),

    # 削除画面
    path('delete/<int:pk>/', views.DeleteView.as_view(), name='delete'),

    # CSV出力
    path('csv/', views.BasicCsv.as_view(), name='csv'),

    # PDF出力
    path('pdf/', views.BasicPdf.as_view(), name='pdf'),

    # パスワード変更画面
    path('password_change/', views.PasswordChange.as_view(), name='password_change'),
    path('password_change/done/', views.PasswordChangeDone.as_view(), name='password_change_done'),

    # パスワードリセット画面
    path('password_reset/', views.PasswordReset.as_view(), name='password_reset'),
    path('password_reset/done/', views.PasswordResetDone.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.PasswordResetConfirm.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.PasswordChangeComplete.as_view(), name='password_reset_complete'),
]
