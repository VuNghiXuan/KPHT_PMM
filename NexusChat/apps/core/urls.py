# apps/core/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

# apps/core/urls.py
app_name = 'core'

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'), # Thêm dòng này
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'), # Bỏ next_page ở đây để dùng cấu hình trong settings.py
    path('profile/setup/', views.profile_setup_view, name='profile-setup'),
]