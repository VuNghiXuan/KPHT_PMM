from django.urls import path
from . import views

# Khai báo app_name để sử dụng reverse('chatbot_guide:detail', ...) trong Admin và View
app_name = 'chatbot_guide'

urlpatterns = [
    path('', views.guide_view, name='index'), 
    path('<int:entry_id>/', views.guide_view, name='detail'),
]