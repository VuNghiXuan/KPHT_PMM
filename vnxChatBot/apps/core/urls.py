# apps/core/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from .views_dev import architecture_dashboard
from . import views

app_name = 'core'

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # Đã xóa đường dẫn 'profile/setup/' vì không còn sử dụng Profile model cũ
    path('dev/architecture/', architecture_dashboard, name='arch_dashboard'),
]