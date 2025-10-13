# skeleton/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views  # ← AÑADE ESTA LÍNEA

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    # COMENTA o ELIMINA la línea de logout de Django:
    # path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', include('pos.urls')),
]