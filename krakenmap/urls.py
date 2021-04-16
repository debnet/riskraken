from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView
from rest_framework.authtoken import views as drf_views

admin.site.site_header = 'Kraken Map'

urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.ico', permanent=True)),
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='logout.html'), name='logout'),
    path('api/', include('rest_framework.urls', namespace='rest_framework')),
    path('api/auth/', drf_views.obtain_auth_token, name='token'),
    path('api/common/', include('common.api.urls', namespace='common-api')),
    path('common/', include('common.urls', namespace='common')),
    path('api/', include('krakenapp.api', namespace='front-api')),
    path('', include('krakenapp.urls', namespace='front')),
]

if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    import debug_toolbar
    urlpatterns += [path('debug/', include(debug_toolbar.urls))]
