from django.urls import path

from krakenapp import views


namespace = 'krakenapp'
app_name = 'krakenapp'
urlpatterns = [
    path('', views.portal, name='portal'),
    path('map/claims/', views.map_claims, name='map_claims'),
    path('map/forces/', views.map_forces, name='map_forces'),
    path('map/stats/<str:type>/', views.map_stats, name='map_stats'),
    path('attack/<str:zone>/', views.action, name='attack'),
    path('claim/<str:zone>/', views.claim, name='claim'),
    path('move/<str:zone>/', views.action, name='move'),
    path('register/', views.register, name='register'),
    path('info/', views.info, name='info'),
]
