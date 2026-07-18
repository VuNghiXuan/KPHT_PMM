# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView # Nhớ import
from apps.core.views import dashboard_view
from apps.core.views_dev import architecture_dashboard, download_manifest

urlpatterns = [
    # CHIẾN THUẬT: Bẻ lái triệt để
    path('accounts/login/', RedirectView.as_view(url='/core/login/', permanent=True)),
    
    path('admin/', admin.site.urls),
    # path('accounting/', include('apps.accounting.urls')),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('subscriptions/', include('apps.subscriptions.urls', namespace='subscriptions')),
    path('core/', include('apps.core.urls', namespace='core')),
    path('dev/architecture/', architecture_dashboard, name='dev_architecture'),
    path('dev/architecture/download/', download_manifest, name='download_manifest'),

    path('', RedirectView.as_view(url='/dashboard/'), name='index'),
    # path('chat/', include('apps.group_chat.urls')),
    path('chat/', include('apps.group_chat.urls', namespace='group_chat')),
]