from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_dispatch_view, name='home_dispatch'),
    path('pos/', views.pos_view, name='pos_main'),
    path('pos/add-product/', views.add_product_view, name='add_product'),
    path('pos/checkout/', views.checkout_view, name='checkout'),
    path('pos/open-session/', views.open_session_view, name='open_session'),
    path('pos/close-session/', views.close_session_view, name='close_session'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),  # ← Esta es importante
    path('reports/sales/', views.sales_report_view, name='sales_report'),
    path('logout/', views.custom_logout_view, name='logout'),
]