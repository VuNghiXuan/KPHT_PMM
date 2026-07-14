from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    path('upgrade/<int:plan_id>/', views.upgrade_plan_view, name='upgrade'),
]