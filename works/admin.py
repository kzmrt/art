from django.contrib import admin
from .models import Work, Image
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ['username', 'email',]


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Work)
admin.site.register(Image)
