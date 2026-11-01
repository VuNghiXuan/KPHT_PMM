from django.contrib import admin
from .models import Subscription

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    # Dùng tên field chính xác trong model Subscription
    list_display = ('group', 'plan_type', 'is_active') 
    list_filter = ('plan_type', 'is_active')