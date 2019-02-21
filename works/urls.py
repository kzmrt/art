from django.urls import path
from . import views

app_name = 'works'

urlpatterns = [
    # トップ画面（検索画面）
    path('', views.SearchView.as_view(), name='index'),

    # 検索結果
    path("works/result/", views.ResultView.as_view(), name='result'),

    # 詳細画面
    path('works/<int:pk>/', views.DetailView.as_view(), name='detail'),

    # パスワード変更画面
    path('password_change/', views.PasswordChange.as_view(), name='password_change'),
    path('password_change/done/', views.PasswordChangeDone.as_view(), name='password_change_done'),

    # パスワードリセット画面
    path('password_reset/', views.PasswordReset.as_view(), name='password_reset'),
    path('password_reset/done/', views.PasswordResetDone.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.PasswordResetConfirm.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.PasswordChangeComplete.as_view(), name='password_reset_complete'),
]
