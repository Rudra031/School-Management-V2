from django.contrib import admin
from core.models import SchoolSetting, AuditLog

@admin.register(SchoolSetting)
class SchoolSettingAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'phone', 'email', 'currency_code', 'attendance_threshold_percentage', 'updated_at')
    
    def has_add_permission(self, request):
        # Enforce singleton in Django admin
        if SchoolSetting.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'module', 'object_repr', 'ip_address')
    list_filter = ('action', 'module', 'timestamp')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'module', 'object_repr', 'ip_address')
    readonly_fields = ('timestamp', 'user', 'action', 'module', 'model_name', 'object_id', 'object_repr', 'changes', 'ip_address', 'user_agent')
    ordering = ('-timestamp',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        # Keep audit logs immutable
        return False

    def has_change_permission(self, request, obj=None):
        return False
