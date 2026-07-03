from django.contrib import admin

from videos.models import ContentImportLog, Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('id', 'description', 'username', 'category', 'source_type', 'license', 'created_at')
    list_filter = ('source_type', 'category')
    search_fields = ('description', 'tags', 'author_name', 'external_id')
    readonly_fields = ('external_id', 'source_type', 'source_url', 'license', 'author_name')
    date_hierarchy = 'created_at'

    def username(self, obj):
        return obj.user.username
    username.short_description = 'Usuario'


@admin.register(ContentImportLog)
class ContentImportLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action', 'source_type', 'category', 'external_id', 'author_name', 'license')
    list_filter = ('action', 'source_type', 'category')
    search_fields = ('external_id', 'author_name', 'notes')
    readonly_fields = (
        'video', 'action', 'source_type', 'category', 'external_id',
        'author_name', 'license', 'source_url', 'notes', 'created_at',
    )
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
