from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nombre")

    def __str__(self):
        return self.name

class Supplier(models.Model):
    name = models.CharField(max_length=150, verbose_name="Nombre del Proveedor")

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nombre")
    sku = models.CharField(max_length=100, unique=True, verbose_name="SKU / Código")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio de Venta")
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio de Costo", null=True, blank=True)
    stock = models.PositiveIntegerField(default=0, verbose_name="Cantidad en Stock")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name

class CashDrawerSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Cajero")
    start_time = models.DateTimeField(auto_now_add=True, verbose_name="Hora de Apertura")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="Hora de Cierre")
    starting_balance = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Fondo Inicial")
    ending_balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Saldo de Cierre")
    notes = models.TextField(blank=True, verbose_name="Notas")

    def __str__(self):
        # CORREGIDO: Usar formato seguro
        return "Sesión de {} - {}".format(
            self.user.username,
            self.start_time.strftime('%d/%m/%Y')
        )

    class Meta:
        verbose_name = "Sesión de Caja"
        verbose_name_plural = "Sesiones de Caja"


class Customer(models.Model):
    """Modelo para gestionar clientes del sistema"""
    name = models.CharField(max_length=200, verbose_name="Nombre o Razón Social")
    tax_id = models.CharField(max_length=20, blank=True, verbose_name="RUC / Cédula")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    email = models.EmailField(blank=True, verbose_name="Email")
    address = models.TextField(blank=True, verbose_name="Dirección")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de registro")

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.tax_id})" if self.tax_id else self.name



class Sale(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Efectivo'),
        ('card', 'Tarjeta'),
    ]

    # Campos existentes
    cash_drawer_session = models.ForeignKey(
        CashDrawerSession,
        on_delete=models.PROTECT,
        related_name='sales',
        null=True,
        blank=True
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total de Venta")
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='cash')
    created_at = models.DateTimeField(auto_now_add=True)

    # ✅ NUEVO CAMPO - Añade esta línea
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Cliente"
    )

    def __str__(self):
        return f"Venta #{self.id} - {self.total_amount}"
class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    product_name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"

# Create your models here.


class SaleReturn(models.Model):
    """Modelo para registrar una devolución completa"""
    original_sale = models.ForeignKey(Sale, on_delete=models.CASCADE, verbose_name="Venta Original")
    returned_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Devolución")
    reason = models.TextField(blank=True, verbose_name="Motivo de la Devolución")
    total_refund = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Total Reembolsado")
    processed_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Procesado por")

    class Meta:
        verbose_name = "Devolución"
        verbose_name_plural = "Devoluciones"
        ordering = ['-returned_at']

    def __str__(self):
        return f"Devolución #{self.id} - Venta #{self.original_sale.id}"


class SaleReturnItem(models.Model):
    """Modelo para los items devueltos"""
    return_request = models.ForeignKey(SaleReturn, on_delete=models.CASCADE, related_name='return_items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name="Producto")
    quantity = models.PositiveIntegerField(verbose_name="Cantidad Devuelta")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio Unitario")

    class Meta:
        verbose_name = "Item de Devolución"
        verbose_name_plural = "Items de Devolución"

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    def get_subtotal(self):
        return self.quantity * self.unit_price