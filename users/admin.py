from django.contrib import admin
from users.models.email_verification_token_model import EmailVerificationToken


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'token', 'created_at']
    readonly_fields = ['token', 'created_at']
