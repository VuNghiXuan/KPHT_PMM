from django.urls import path
from . import views

urlpatterns = [
    path('reports/', views.financial_report_view, name='financial_reports'),
]