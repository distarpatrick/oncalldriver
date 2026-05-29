"""
WhatsApp Admin Configuration
Register WhatsApp models in Django admin for monitoring and management
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import WhatsAppMessage


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'message_type', 'status_badge', 'created_at', 'message_preview')
    list_filter = ('message_type', 'status', 'created_at')
    search_fields = ('phone_number', 'content', 'message_id')
    readonly_fields = ('id', 'message_id', 'created_at', 'delivered_at', 'read_at', 'content_formatted', 'metadata_formatted')
    
    fieldsets = (
        ('Message Information', {
            'fields': ('id', 'phone_number', 'message_type', 'status_badge', 'message_id')
        }),
        ('Content', {
            'fields': ('content_formatted',)
        }),
        ('Metadata', {
            'fields': ('metadata_formatted',)
        }),
        ('Relations', {
            'fields': ('booking', 'visit', 'payment'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'delivered_at', 'read_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        """Display status as a colored badge"""
        colors = {
            'sent': '#FFC107',
            'delivered': '#2196F3',
            'failed': '#F44336',
            'read': '#4CAF50',
        }
        color = colors.get(obj.status, '#9E9E9E')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def message_preview(self, obj):
        """Show preview of message content"""
        preview = obj.content[:50]
        if len(obj.content) > 50:
            preview += '...'
        return preview
    message_preview.short_description = 'Message'
    
    def content_formatted(self, obj):
        """Display full message content in readable format"""
        return format_html(
            '<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px; white-space: pre-wrap; word-wrap: break-word;">{}</pre>',
            obj.content
        )
    content_formatted.short_description = 'Full Content'
    
    def metadata_formatted(self, obj):
        """Display metadata as formatted JSON"""
        import json
        metadata_str = json.dumps(obj.metadata, indent=2, ensure_ascii=False)
        return format_html(
            '<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px; white-space: pre-wrap; word-wrap: break-word;">{}</pre>',
            metadata_str
        )
    metadata_formatted.short_description = 'Metadata'
    
    def has_add_permission(self, request):
        """Don't allow manual creation - messages are created programmatically"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion for audit purposes"""
        return request.user.is_superuser
