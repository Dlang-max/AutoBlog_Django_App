from .models import User
from .models import Member, Blog, BlogSkeleton, AutomatedBlogging, BlogHistory
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm

class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User

class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    
    fieldsets = UserAdmin.fieldsets + (
            ("Custom User Information:", {'fields': ('is_verified', 'is_member', 'key',)}),
    )

# Register your models here.
admin.site.register(User, CustomUserAdmin)
admin.site.register(Member)
admin.site.register(Blog)
admin.site.register(BlogSkeleton)
admin.site.register(BlogHistory)
admin.site.register(AutomatedBlogging)
