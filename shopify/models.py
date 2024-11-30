from django.db import models
from django.utils import timezone

class ShopifyOrder(models.Model):
    order_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)  # e.g., "#1102"
    email = models.EmailField(null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    created_at = models.DateTimeField()
    tags = models.JSONField(default=list)
    note = models.TextField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.total_price} {self.currency}"
