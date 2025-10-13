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
        return f"Sesión de {self.user.username} - {self.start_time.strftime('%d/%m/%Y')}"


class Sale(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Efectivo'),
        ('card', 'Tarjeta'),
    ]

    # CAMPO MODIFICADO - Añade null=True y blank=True
    cash_drawer_session = models.ForeignKey(
        CashDrawerSession,
        on_delete=models.PROTECT,
        related_name='sales',
        null=True,  # ← AÑADE ESTO
        blank=True  # ← AÑADE ESTO
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total de Venta")
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='cash')
    created_at = models.DateTimeField(auto_now_add=True)

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
