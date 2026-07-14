# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView # Nhớ import
from apps.core.views import dashboard_view

urlpatterns = [
    # CHIẾN THUẬT: Bẻ lái triệt để
    path('accounts/login/', RedirectView.as_view(url='/core/login/', permanent=True)),
    
    path('admin/', admin.site.urls),
    # path('accounting/', include('apps.accounting.urls')),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('subscriptions/', include('apps.subscriptions.urls', namespace='subscriptions')),
    path('core/', include('apps.core.urls', namespace='core')),
    path('', RedirectView.as_view(url='/dashboard/'), name='index'),
    path('chat/', include('apps.group_chat.urls')),
]