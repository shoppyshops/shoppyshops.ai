import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_root)

import django
from decimal import Decimal
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shoppyshops.settings')
django.setup()

import asyncio
from io import StringIO
from django.db.models import Sum, Avg, Count
from django.utils import timezone
from datetime import datetime, timedelta

from shopify.models import ShopifyOrder
from ebay.models import EbayOrder

async def generate_profit_report(days_back=180):
    """Generate a profit report for orders in the specified time period"""
    
    # Calculate the date range
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days_back)
    
    print(f"\nGenerating profit report from {start_date.date()} to {end_date.date()}")
    print("="*50)
    
    # Get all Shopify orders in date range
    shopify_orders = ShopifyOrder.objects.filter(
        created_at__range=(start_date, end_date)
    ).prefetch_related('ebay_orders')
    
    total_orders = await shopify_orders.acount()
    
    orders_with_ebay = 0
    total_revenue = Decimal('0.00')
    total_cost = Decimal('0.00')
    total_profit = Decimal('0.00')
    
    print("\nDetailed Order Analysis:")
    print("="*50)
    
    async for shopify_order in shopify_orders.aiterator():
        print(f"\nShopify Order: {shopify_order.name}")
        print(f"Created: {shopify_order.created_at}")
        print(f"Revenue: ${shopify_order.total_price:.2f} {shopify_order.currency}")
        
        # Get linked eBay orders
        ebay_orders = []
        async for ebay_order in shopify_order.ebay_orders.all().aiterator():
            ebay_orders.append(ebay_order)
        
        if ebay_orders:
            orders_with_ebay += 1
            order_cost = sum(order.order_total for order in ebay_orders)
            order_profit = shopify_order.total_price - order_cost
            
            print(f"eBay Cost: ${order_cost:.2f}")
            print(f"Profit: ${order_profit:.2f}")
            print(f"Margin: {(order_profit / shopify_order.total_price * 100):.1f}%")
            
            total_revenue += shopify_order.total_price
            total_cost += order_cost
            total_profit += order_profit
        else:
            print("No linked eBay orders found")
    
    # Calculate averages
    if orders_with_ebay > 0:
        avg_revenue = total_revenue / orders_with_ebay
        avg_cost = total_cost / orders_with_ebay
        avg_profit = total_profit / orders_with_ebay
        avg_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    else:
        avg_revenue = avg_cost = avg_profit = avg_margin = 0
    
    # Print summary
    print("\nSummary Report")
    print("="*50)
    print(f"Time Period: {days_back} days")
    print(f"Total Shopify Orders: {total_orders}")
    print(f"Orders with eBay Links: {orders_with_ebay}")
    print(f"Orders Missing eBay Links: {total_orders - orders_with_ebay}")
    print("\nFinancials:")
    print(f"Total Revenue: ${total_revenue:.2f}")
    print(f"Total Cost: ${total_cost:.2f}")
    print(f"Total Profit: ${total_profit:.2f}")
    print(f"Overall Margin: {(total_profit / total_revenue * 100):.1f}% (profit/revenue)")
    print("\nAverages (for orders with eBay links):")
    print(f"Average Revenue: ${avg_revenue:.2f}")
    print(f"Average Cost: ${avg_cost:.2f}")
    print(f"Average Profit: ${avg_profit:.2f}")
    print(f"Average Margin: {avg_margin:.1f}%")

async def run():
    # Capture output
    output = StringIO()
    original_stdout = sys.stdout
    
    # Create a custom stdout that writes to both output and terminal
    class TeeOutput:
        def write(self, text):
            output.write(text)
            original_stdout.write(text)
            
        def flush(self):
            output.flush()
            original_stdout.flush()
    
    sys.stdout = TeeOutput()
    
    try:
        # Generate report for last 180 days by default
        await generate_profit_report(days_back=180)
        
    except Exception as e:
        print(f"Error generating report: {str(e)}")
        print(f"Error type: {type(e).__name__}")
    finally:
        # Restore stdout
        sys.stdout = original_stdout
        output_text = output.getvalue()
        
        # Copy to clipboard (optional)
        try:
            import pyperclip
            pyperclip.copy(output_text)
            print("\nOutput copied to clipboard!")
        except ImportError:
            print("\nInstall pyperclip to enable automatic clipboard copy: pip install pyperclip")

if __name__ == "__main__":
    asyncio.run(run()) 