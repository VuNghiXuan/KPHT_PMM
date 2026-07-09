
# File: config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView # Import thêm dòng này
from apps.core.views import dashboard_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounting/', include('apps.accounting.urls')),
    path('dashboard/', dashboard_view, name='dashboard'),
    
    # Thêm dòng này để khi gõ http://127.0.0.1:8000/ nó tự chuyển sang /dashboard/
    path('', RedirectView.as_view(url='/dashboard/'), name='index'),
]