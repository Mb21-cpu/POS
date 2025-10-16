# pos/admin.py - VERSIÓN COMPLETA CON BOTÓN FUNCIONAL
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from .models import Category, Supplier, Product, CashDrawerSession, Sale, SaleItem, Customer,SaleReturn, SaleReturnItem
from django.db.models import Sum, Count
from django.utils.html import format_html
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib import messages
from django.http import HttpResponse
import re


# =============================================================================
# MODELADMIN REGISTRATIONS
# =============================================================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_product_count']
    search_fields = ['name']

    def get_product_count(self, obj):
        count = obj.product_set.count()
        return format_html(
            '<span style="background: #417690; color: white; padding: 4px 8px; border-radius: 12px;">{}</span>', count)

    get_product_count.short_description = 'N° Productos'


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_product_count']
    search_fields = ['name']

    def get_product_count(self, obj):
        count = obj.product_set.count()
        return format_html(
            '<span style="background: #28a745; color: white; padding: 4px 8px; border-radius: 12px;">{}</span>', count)

    get_product_count.short_description = 'Productos'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'price', 'stock', 'category', 'supplier', 'get_stock_status']
    list_filter = ['category', 'supplier']
    search_fields = ['name', 'sku']
    list_editable = ['price', 'stock']
    list_per_page = 25

    def get_stock_status(self, obj):
        if obj.stock == 0:
            return format_html('<span style="color: red; font-weight: bold;">❌ SIN STOCK</span>')
        elif obj.stock < 10:
            return format_html('<span style="color: orange; font-weight: bold;">⚠️ BAJO ({})</span>', obj.stock)
        else:
            return format_html('<span style="color: green;">✅ {} unidades</span>', obj.stock)

    get_stock_status.short_description = 'Estado Stock'


@admin.register(CashDrawerSession)
class CashDrawerSessionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'start_time', 'end_time', 'starting_balance',
        'get_total_cash_sales', 'ending_balance', 'get_status'
    ]
    list_filter = ['user', 'start_time']
    readonly_fields = ['start_time', 'end_time']
    search_fields = ['user__username']

    def get_total_cash_sales(self, obj):
        cash_sales = obj.sales.filter(payment_method='cash').aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        return f"${cash_sales:.2f}"

    get_total_cash_sales.short_description = 'Ventas Efectivo'

    def get_status(self, obj):
        if obj.end_time is None:
            return format_html('<span style="color: green; font-weight: bold;">🟢 ACTIVA</span>')
        else:
            return format_html('<span style="color: gray;">🔴 CERRADA</span>')

    get_status.short_description = 'Estado'


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'get_user', 'total_amount', 'payment_method_display',
        'customer', 'created_at'
    ]
    list_filter = ['payment_method', 'created_at']
    search_fields = ['id', 'cash_drawer_session__user__username']
    readonly_fields = ['created_at']

    def get_user(self, obj):
        if obj.cash_drawer_session:
            return obj.cash_drawer_session.user.username
        return "-"

    get_user.short_description = 'Vendedor'

    def payment_method_display(self, obj):
        methods = {'cash': '💵 Efectivo', 'card': '💳 Tarjeta'}
        return methods.get(obj.payment_method, obj.payment_method)

    payment_method_display.short_description = 'Método de Pago'


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ['sale', 'product_name', 'quantity', 'unit_price', 'get_subtotal']
    list_filter = ['sale__created_at']
    search_fields = ['product_name', 'sale__id']

    def get_subtotal(self, obj):
        return f"${obj.quantity * obj.unit_price:.2f}"

    get_subtotal.short_description = 'Subtotal'


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'tax_id', 'phone', 'email', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'tax_id', 'email']
    ordering = ['name']

    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'tax_id')
        }),
        ('Información de Contacto', {
            'fields': ('phone', 'email', 'address')
        }),
    )


# =============================================================================
# DASHBOARD COMPLETO
# =============================================================================

@staff_member_required
def pos_dashboard_view(request):
    """Dashboard completo para el admin"""
    today = timezone.now().date()

    # Métricas principales
    today_sales = Sale.objects.filter(created_at__date=today).aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    today_transactions = Sale.objects.filter(created_at__date=today).count()
    today_avg_ticket = today_sales / today_transactions if today_transactions > 0 else 0
    active_sessions = CashDrawerSession.objects.filter(end_time__isnull=True).count()

    # Métricas de la semana
    week_ago = today - timezone.timedelta(days=7)
    week_sales = Sale.objects.filter(created_at__date__gte=week_ago).aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    # Ventas por método de pago hoy
    cash_sales_today = Sale.objects.filter(
        created_at__date=today,
        payment_method='cash'
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    card_sales_today = Sale.objects.filter(
        created_at__date=today,
        payment_method='card'
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # Productos más vendidos
    top_products = SaleItem.objects.values(
        'product_name'
    ).annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum('unit_price')
    ).order_by('-total_sold')[:5]

    # Sesiones de hoy
    today_sessions = CashDrawerSession.objects.filter(
        start_time__date=today
    ).select_related('user')

    # Ventas recientes
    recent_sales = Sale.objects.select_related(
        'cash_drawer_session',
        'cash_drawer_session__user'
    ).order_by('-created_at')[:10]

    # Productos con stock bajo
    low_stock_products = Product.objects.filter(stock__lt=10, stock__gt=0).order_by('stock')[:5]
    out_of_stock_products = Product.objects.filter(stock=0)[:5]

    context = {
        # Métricas principales
        'today_sales': today_sales,
        'today_transactions': today_transactions,
        'today_avg_ticket': today_avg_ticket,
        'active_sessions': active_sessions,

        # Nuevas métricas
        'week_sales': week_sales,
        'cash_sales_today': cash_sales_today,
        'card_sales_today': card_sales_today,

        # Datos detallados
        'top_products': top_products,
        'today_sessions': today_sessions,
        'recent_sales': recent_sales,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
        'today_date': today,
        'week_ago': week_ago,

        'title': '📊 Dashboard POS - Sistema de Punto de Venta',
    }

    return TemplateResponse(request, 'admin/pos_dashboard.html', context)


# =============================================================================
# REPORTE DE VENTAS EN EL ADMIN
# =============================================================================

@staff_member_required
def sales_report_admin_view(request):
    """Reporte de ventas integrado en el admin"""
    sales = Sale.objects.none()
    total_sales = 0
    total_transactions = 0
    start_date = None
    end_date = None

    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')

        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

                # Filtrar ventas por rango de fechas
                sales = Sale.objects.filter(
                    created_at__date__range=[start_date, end_date]
                ).select_related(
                    'cash_drawer_session',
                    'cash_drawer_session__user'
                ).order_by('-created_at')

                # Calcular totales
                if sales.exists():
                    total_sales_result = sales.aggregate(total=Sum('total_amount'))
                    total_sales = total_sales_result['total'] or 0
                    total_transactions = sales.count()

            except ValueError:
                messages.error(request, "Formato de fecha inválido")

    context = {
        'sales': sales,
        'total_sales': total_sales,
        'total_transactions': total_transactions,
        'start_date': start_date,
        'end_date': end_date,
        'today': timezone.now().date(),
        'title': '📈 Reporte de Ventas - Admin',
    }

    return TemplateResponse(request, 'admin/sales_report.html', context)


# =============================================================================
# BOTÓN DEFINITIVO - INYECCIÓN DIRECTA EN HTML
# =============================================================================

class AdminConBoton(admin.ModelAdmin):
    """Mixin que añade botón a todas las vistas del admin"""

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)
        if hasattr(response, 'render'):
            try:
                response.render()
                content = response.content.decode('utf-8')

                # Botón HTML
                boton_html = '''
                <div style="background: #28a745; padding: 15px; margin: 20px 0; border-radius: 8px; text-align: center; border: 2px solid #218838; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <a href="/dashboard/" style="color: white; text-decoration: none; font-size: 16px; font-weight: bold; display: block;">
                        📊 VOLVER AL DASHBOARD PRINCIPAL
                    </a>
                </div>
                '''

                # Insertar después del breadcrumb o antes del content-main
                if 'id="content-main"' in content:
                    content = content.replace(
                        '<div id="content-main">',
                        boton_html + '<div id="content-main">'
                    )
                    response.content = content.encode('utf-8')

            except Exception as e:
                print(f"Error inyectando botón: {e}")

        return response


# Aplicar a todos los modelos
for model, model_admin in admin.site._registry.items():
    if not hasattr(model_admin, 'changelist_view_original'):
        model_admin.changelist_view_original = model_admin.changelist_view


        def new_changelist_view(self, request, extra_context=None):
            response = self.changelist_view_original(request, extra_context)
            if hasattr(response, 'render'):
                try:
                    response.render()
                    content = response.content.decode('utf-8')

                    boton_html = '''
                    <div style="background: #28a745; padding: 15px; margin: 20px 0; border-radius: 8px; text-align: center; border: 2px solid #218838;">
                        <a href="/dashboard/" style="color: white; text-decoration: none; font-size: 16px; font-weight: bold; display: block;">
                            📊 VOLVER AL DASHBOARD PRINCIPAL
                        </a>
                    </div>
                    '''

                    if 'id="content-main"' in content:
                        content = content.replace(
                            '<div id="content-main">',
                            boton_html + '<div id="content-main">'
                        )
                        response.content = content.encode('utf-8')

                except Exception:
                    pass

            return response


        model_admin.changelist_view = new_changelist_view.__get__(model_admin, type(model_admin))

# =============================================================================
# BOTÓN ESPECÍFICO PARA EL ÍNDICE /admin/
# =============================================================================

original_index = admin.site.index


def index_con_boton(request, extra_context=None):
    """Índice del admin con botón"""
    response = original_index(request, extra_context)

    if hasattr(response, 'render'):
        try:
            response.render()
            content = response.content.decode('utf-8')

            boton_html = '''
            <div style="background: #28a745; padding: 20px; margin: 0 0 30px 0; border-radius: 10px; text-align: center; border: 3px solid #218838; box-shadow: 0 4px 8px rgba(0,0,0,0.15);">
                <a href="/dashboard/" style="color: white; text-decoration: none; font-size: 18px; font-weight: bold; display: block;">
                    📊 VOLVER AL DASHBOARD PRINCIPAL
                </a>
                <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 14px;">
                    Regresar al panel principal del sistema POS
                </p>
            </div>
            '''

            # Insertar al inicio del contenido principal
            if 'id="content-main"' in content:
                content = content.replace(
                    '<div id="content-main">',
                    boton_html + '<div id="content-main">'
                )
                response.content = content.encode('utf-8')

        except Exception as e:
            print(f"Error en índice: {e}")

    return response


admin.site.index = index_con_boton

# =============================================================================
# CONFIGURACIÓN FINAL DEL ADMIN
# =============================================================================

# Personalizar headers del admin
admin.site.site_header = "🛒 Sistema POS - Administración"
admin.site.site_title = "POS Admin"
admin.site.index_title = "Dashboard del Sistema POS"

# Añadir URLs personalizadas
original_get_urls = admin.site.get_urls


def custom_get_urls():
    custom_urls = [
        path('pos-dashboard/', admin.site.admin_view(pos_dashboard_view), name='pos-dashboard'),
        path('sales-report/', admin.site.admin_view(sales_report_admin_view), name='sales-report'),
    ]
    return custom_urls + original_get_urls()


admin.site.get_urls = custom_get_urls


# =============================================================================
# BOTÓN EN BASE_SITE.HTML (FALLBACK)
# =============================================================================

def get_admin_site_header():
    """Header personalizado con botón"""
    original_header = "🛒 Sistema POS - Administración"
    boton_header = '''
    <div style="float: right; margin-right: 20px;">
        <a href="/dashboard/" style="color: white; text-decoration: none; background: #28a745; padding: 8px 15px; border-radius: 4px; font-size: 14px; font-weight: bold;">
            📊 Dashboard Principal
        </a>
    </div>
    '''
    return format_html(original_header)


@admin.register(SaleReturn)
class SaleReturnAdmin(admin.ModelAdmin):
    list_display = ['id', 'original_sale', 'returned_at', 'total_refund', 'processed_by']
    list_filter = ['returned_at', 'processed_by']
    readonly_fields = ['returned_at']
    search_fields = ['original_sale__id']


@admin.register(SaleReturnItem)
class SaleReturnItemAdmin(admin.ModelAdmin):
    list_display = ['return_request', 'product', 'quantity', 'unit_price', 'get_subtotal']
    list_filter = ['return_request__returned_at']

    def get_subtotal(self, obj):
        return f"${obj.get_subtotal():.2f}"

    get_subtotal.short_description = 'Subtotal'


# Forzar el header personalizado
admin.site.site_header = get_admin_site_header()

