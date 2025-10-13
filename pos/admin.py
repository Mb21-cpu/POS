# pos/admin.py - VERSIÓN COMPLETA CON NAVEGACIÓN MEJORADA
from django.contrib import admin
from .models import Category, Supplier, Product, CashDrawerSession, Sale, SaleItem
from django.db.models import Sum
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'price', 'stock', 'category', 'get_stock_status']
    list_filter = ['category', 'supplier']
    search_fields = ['name', 'sku']

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
        'user',
        'start_time',
        'end_time',
        'starting_balance',
        'get_total_cash_sales',
        'get_expected_balance',
        'ending_balance',
        'get_difference',
        'get_status'
    ]

    list_filter = ['user', 'start_time', 'end_time']
    readonly_fields = ['start_time', 'end_time']
    search_fields = ['user__username', 'notes']
    date_hierarchy = 'start_time'

    def get_total_cash_sales(self, obj):
        """Calcula el total de ventas en efectivo para esta sesión"""
        cash_sales = obj.sales.filter(payment_method='cash').aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        return f"${cash_sales:.2f}"

    get_total_cash_sales.short_description = 'Ventas Efectivo'

    def get_expected_balance(self, obj):
        """Calcula el saldo esperado (fondo inicial + ventas efectivo)"""
        cash_sales = obj.sales.filter(payment_method='cash').aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        expected = obj.starting_balance + cash_sales
        return f"${expected:.2f}"

    get_expected_balance.short_description = 'Total Esperado'

    def get_difference(self, obj):
        """Calcula la diferencia entre lo esperado y lo contado"""
        if obj.ending_balance is not None:
            cash_sales = obj.sales.filter(payment_method='cash').aggregate(
                total=Sum('total_amount')
            )['total'] or 0
            expected = obj.starting_balance + cash_sales
            difference = obj.ending_balance - expected

            if difference == 0:
                return format_html('<span style="color: green; font-weight: bold;">✅ ${:.2f}</span>', difference)
            elif difference > 0:
                return format_html('<span style="color: #28a745; font-weight: bold;">↑ ${:.2f}</span>', difference)
            else:
                return format_html('<span style="color: #dc3545; font-weight: bold;">↓ ${:.2f}</span>', abs(difference))
        return format_html('<span style="color: gray;">-</span>')

    get_difference.short_description = 'Diferencia'

    def get_status(self, obj):
        """Muestra si la sesión está activa o cerrada"""
        if obj.end_time is None:
            return format_html('<span style="color: green; font-weight: bold;">🟢 ACTIVA</span>')
        else:
            return format_html('<span style="color: gray;">🔴 CERRADA</span>')

    get_status.short_description = 'Estado'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'get_user',
        'get_session',
        'total_amount',
        'payment_method_display',
        'created_at',
        'view_items'
    ]

    list_filter = ['payment_method', 'created_at', 'cash_drawer_session__user']
    readonly_fields = ['created_at']
    search_fields = ['id', 'cash_drawer_session__user__username']
    date_hierarchy = 'created_at'

    def get_user(self, obj):
        """Obtiene el usuario de la sesión de caja"""
        if obj.cash_drawer_session:
            return obj.cash_drawer_session.user.username
        return "-"

    get_user.short_description = 'Vendedor'

    def get_session(self, obj):
        """Muestra información de la sesión"""
        if obj.cash_drawer_session:
            return f"Sesión #{obj.cash_drawer_session.id}"
        return "-"

    get_session.short_description = 'Sesión'

    def payment_method_display(self, obj):
        """Muestra el método de pago con icono"""
        methods = {
            'cash': '💵 Efectivo',
            'card': '💳 Tarjeta'
        }
        return methods.get(obj.payment_method, obj.payment_method)

    payment_method_display.short_description = 'Método de Pago'

    def view_items(self, obj):
        """Enlace para ver los items de la venta"""
        url = reverse('admin:pos_saleitem_changelist') + f'?sale__id__exact={obj.id}'
        return format_html('<a href="{}" class="button">📋 Ver Items</a>', url)

    view_items.short_description = 'Items'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'cash_drawer_session',
            'cash_drawer_session__user'
        )


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = [
        'sale',
        'product_name',
        'quantity',
        'unit_price',
        'get_subtotal',
        'get_product_sku'
    ]

    list_filter = ['sale__created_at']
    search_fields = ['product_name', 'sale__id']

    def get_subtotal(self, obj):
        """Calcula el subtotal del item"""
        return f"${obj.quantity * obj.unit_price:.2f}"

    get_subtotal.short_description = 'Subtotal'

    def get_product_sku(self, obj):
        """Muestra el SKU del producto"""
        if obj.product:
            return obj.product.sku
        return "-"

    get_product_sku.short_description = 'SKU'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sale', 'product')


# Registros simples para Category y Supplier
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_product_count']
    search_fields = ['name']

    def get_product_count(self, obj):
        return obj.product_set.count()

    get_product_count.short_description = 'N° Productos'


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_product_count']
    search_fields = ['name']

    def get_product_count(self, obj):
        return obj.product_set.count()

    get_product_count.short_description = 'N° Productos'


# =============================================================================
# DASHBOARD MEJORADO CON MÁS MÉTRICAS
# =============================================================================

def pos_dashboard_view(request):
    """Dashboard mejorado para el admin"""
    today = timezone.now().date()

    # Métricas principales
    today_sales = Sale.objects.filter(created_at__date=today).aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    today_transactions = Sale.objects.filter(created_at__date=today).count()
    today_avg_ticket = today_sales / today_transactions if today_transactions > 0 else 0
    active_sessions = CashDrawerSession.objects.filter(end_time__isnull=True).count()

    # Ventas por método de pago
    cash_sales = Sale.objects.filter(created_at__date=today, payment_method='cash').aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    card_sales = Sale.objects.filter(created_at__date=today, payment_method='card').aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    # Productos más vendidos (de todos los tiempos)
    top_products = SaleItem.objects.values(
        'product_name'
    ).annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum('unit_price')
    ).order_by('-total_sold')[:5]

    # Sesiones de hoy
    today_sessions = CashDrawerSession.objects.filter(
        start_time__date=today
    ).select_related('user')[:10]

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

        # Métricas de pago
        'cash_sales': cash_sales,
        'card_sales': card_sales,

        # Datos detallados
        'top_products': top_products,
        'today_sessions': today_sessions,
        'recent_sales': recent_sales,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
        'today_date': today,

        'title': '📊 Dashboard POS - Sistema de Punto de Venta',
    }

    return TemplateResponse(request, 'admin/pos_dashboard.html', context)


def sales_report_admin_view(request):
    """Reporte de ventas integrado en el admin"""
    from django.db.models import Sum
    from datetime import datetime

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
                from django.contrib import messages
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
# PERSONALIZACIÓN COMPLETA DEL ADMIN SITE
# =============================================================================

class POSAdminSite(admin.AdminSite):
    """Admin site personalizado para el Sistema POS"""

    def get_app_list(self, request, app_label=None):
        """
        Personaliza la lista de apps para añadir enlaces de navegación
        """
        app_list = super().get_app_list(request, app_label)

        # Añadir sección de navegación rápida si el usuario es staff
        if request.user.is_staff:
            # Crear una "app" personalizada para navegación
            navigation_app = {
                'name': '🚀 Navegación Rápida',
                'app_label': 'pos_navigation',
                'app_url': '/dashboard/',
                'has_module_perms': True,
                'models': [
                    {
                        'name': '📊 Dashboard Principal',
                        'object_name': 'dashboard',
                        'admin_url': '/dashboard/',
                        'view_only': True,
                    },
                    {
                        'name': '🛒 Punto de Venta (POS)',
                        'object_name': 'pos',
                        'admin_url': '/pos/',
                        'view_only': True,
                    },
                    {
                        'name': '🏠 Dashboard Admin',
                        'object_name': 'admin_dashboard',
                        'admin_url': '/admin/pos-dashboard/',
                        'view_only': True,
                    },
                ],
            }
            # Insertar la navegación al principio
            app_list.insert(0, navigation_app)

        return app_list

    def index(self, request, extra_context=None):
        """
        Personaliza la página principal del admin
        """
        extra_context = extra_context or {}
        extra_context.update({
            'show_navigation': True,
            'dashboard_url': '/dashboard/',
            'pos_url': '/pos/',
            'admin_dashboard_url': '/admin/pos-dashboard/',
        })
        return super().index(request, extra_context)


# Reemplazar el admin site por defecto
admin_site = POSAdminSite(name='admin')

# Re-registrar todos los modelos con el nuevo admin site
admin_site.register(Category, CategoryAdmin)
admin_site.register(Supplier, SupplierAdmin)
admin_site.register(Product, ProductAdmin)
admin_site.register(CashDrawerSession, CashDrawerSessionAdmin)
admin_site.register(Sale, SaleAdmin)
admin_site.register(SaleItem, SaleItemAdmin)

# Reemplazar el admin site por defecto
admin.site = admin_site

# Guardar la función original get_urls
_original_get_urls = admin_site.get_urls


def custom_get_urls():
    """Añade las URLs personalizadas al admin"""
    custom_urls = [
        path('pos-dashboard/', admin_site.admin_view(pos_dashboard_view), name='pos-dashboard'),
        path('sales-report/', admin_site.admin_view(sales_report_admin_view), name='sales-report'),  # ← NUEVA
    ]
    return custom_urls + _original_get_urls()


admin_site.get_urls = custom_get_urls

# =============================================================================
# CONFIGURACIÓN FINAL DEL ADMIN SITE
# =============================================================================

admin_site.site_header = "🛒 Sistema POS - Administración"
admin_site.site_title = "POS Admin"
admin_site.index_title = "Dashboard del Sistema POS"

# Configuración adicional para mejor visualización
admin_site.enable_nav_sidebar = True

print("✅ Admin Site del Sistema POS configurado correctamente")
print("📍 Dashboard disponible en: /admin/pos-dashboard/")
print("📍 Dashboard principal en: /dashboard/")
print("📍 Punto de venta en: /pos/")