# /var/www/gea/core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('analise-servicos/', views.analise_servicos_view, name='analise_servicos'),
    path('performance/', views.performance_view, name='performance'),
]