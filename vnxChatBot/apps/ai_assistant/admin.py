from django.contrib import admin
from .models import GroupAIProvider

@admin.register(GroupAIProvider)
class GroupAIProviderAdmin(admin.ModelAdmin):
    list_display = ('group', 'provider', 'model_name')
    list_filter = ('provider',)