# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from apps.core.views import dashboard_view
from apps.core.views_dev import architecture_dashboard, download_manifest
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.storage import staticfiles_storage

urlpatterns = [
    # Sửa từ as_url thành as_view và trỏ đúng định dạng static nếu dùng favicon
    path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('favicon.ico'), permanent=True)),
    
    # Chuyển hướng đăng nhập
    path('accounts/login/', RedirectView.as_view(url='/core/login/', permanent=True)),
    
    path('admin/', admin.site.urls),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('subscriptions/', include('apps.subscriptions.urls', namespace='subscriptions')),
    path('core/', include('apps.core.urls', namespace='core')),
    path('dev/architecture/', architecture_dashboard, name='dev_architecture'),
    path('dev/architecture/download/', download_manifest, name='download_manifest'),

    path('', RedirectView.as_view(url='/dashboard/'), name='index'),
    path('groups/', include('apps.group_chat.urls', namespace='group_chat')),
    path('architecture/', include('apps.arch_manager.urls', namespace='arch_manager')),
    
]

# Phục vụ file media trong môi trường phát triển (Development)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)