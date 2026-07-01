from django.apps import AppConfig

class AppCoachConfig(AppConfig): # Anh có thể đổi tên Class cho đồng bộ
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.app_coach'
    
    # Sửa dòng này để đổi tên hiển thị trên trang chủ Admin
    verbose_name = '2. Hệ thống Huấn luyện (Coach)'