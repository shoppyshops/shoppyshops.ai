from django.db import models
from django.utils import timezone
from shopify.models import ShopifyOrder


class EbayOrder(models.Model):
    """Represents an eBay order"""
    order_id = models.CharField(max_length=50, unique=True)
    order_status = models.CharField(max_length=50)
    order_total = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)
    shipping_address = models.JSONField(null=True, blank=True)
    payment_status = models.CharField(max_length=50)
    shopify_order = models.ForeignKey(
        ShopifyOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ebay_orders'
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['order_id']),
            models.Index(fields=['created_at']),
            models.Index(fields=['shopify_order']),
        ]
        
    def __str__(self):
        return f"eBay Order {self.order_id}"


class EbayOrderItem(models.Model):
    """Represents an item within an eBay order"""
    order = models.ForeignKey(EbayOrder, related_name='items', on_delete=models.CASCADE)
    item_id = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    seller_id = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=50)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['item_id']),
            models.Index(fields=['seller_id']),
        ]
        
    def __str__(self):
        return f"{self.title} ({self.item_id})"
