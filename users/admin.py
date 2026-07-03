from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models.custom_user_models import CustomUser
from users.models.email_verification_token_model import EmailVerificationToken
from users.models.login_log_model import LoginLog


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_superuser', 'email_verified', 'date_joined', 'last_login_display')
    list_filter = ('is_staff', 'is_superuser', 'email_verified', 'senescyt_verified')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    date_hierarchy = 'date_joined'

    fieldsets = UserAdmin.fieldsets + (
        ('Perfil', {'fields': ('bio', 'profile_picture', 'birth_date')}),
        ('Profesional', {'fields': ('professional_title', 'professional_institution')}),
        ('Verificación', {'fields': ('email_verified', 'cedula', 'senescyt_number', 'senescyt_verified', 'senescyt_verified_name', 'senescyt_verified_at')}),
    )

    def last_login_display(self, obj):
        log = obj.login_logs.first()
        return log.created_at.strftime('%d/%m/%Y %H:%M') if log else '—'
    last_login_display.short_description = 'Último acceso'


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'token', 'created_at']
    readonly_fields = ['token', 'created_at']


@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'username_display', 'method', 'ip_address', 'user_agent_short')
    list_filter = ('method',)
    search_fields = ('user__username', 'user__email', 'ip_address')
    readonly_fields = ('user', 'ip_address', 'user_agent', 'method', 'created_at')
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def username_display(self, obj):
        return obj.user.username
    username_display.short_description = 'Usuario'

    def user_agent_short(self, obj):
        return obj.user_agent[:80] if obj.user_agent else '—'
    user_agent_short.short_description = 'Dispositivo'
