from django.contrib import admin
from .models import ContentReport, CopyrightReport


@admin.register(ContentReport)
class ContentReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'video', 'reason', 'created_at', 'reviewed')
    list_filter = ('reason', 'reviewed')
    search_fields = ('reporter__username', 'video__id')
    actions = ['mark_reviewed']

    @admin.action(description='Marcar como revisado')
    def mark_reviewed(self, request, queryset):
        queryset.update(reviewed=True)


@admin.register(CopyrightReport)
class CopyrightReportAdmin(admin.ModelAdmin):
    list_display = ('reporter_email', 'reporter_name', 'video', 'created_at', 'reviewed')
    list_filter = ('reviewed',)
    search_fields = ('reporter_email', 'reporter_name')
    actions = ['mark_reviewed']

    @admin.action(description='Marcar como revisado')
    def mark_reviewed(self, request, queryset):
        queryset.update(reviewed=True)
