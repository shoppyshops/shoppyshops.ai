import os
import sys
from pathlib import Path
import argparse

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
    total_shipping_cost = Decimal('0.00')
    total_actual_shipping = Decimal('0.00')
    total_profit = Decimal('0.00')
    
    print("\nDetailed Order Analysis:")
    print("="*50)
    
    # Add lists to track shipping costs
    actual_shipping_costs = []
    charged_shipping_costs = []
    
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
            order_cost = Decimal('0.00')
            order_shipping = Decimal('0.00')
            order_actual_shipping = Decimal('0.00')
            
            # Itemize costs for each eBay order
            for ebay_order in ebay_orders:
                async for item in ebay_order.items.all().aiterator():
                    order_cost += item.price * item.quantity
                    order_shipping += item.shipping_cost
                    order_actual_shipping += item.actual_shipping_cost
            
            # Track shipping costs when they are non-zero
            if order_shipping > 0:
                charged_shipping_costs.append(float(order_shipping))
            if order_actual_shipping > 0:
                actual_shipping_costs.append(float(order_actual_shipping))
            
            order_total_cost = order_cost + order_shipping
            order_profit = shopify_order.total_price - order_total_cost
            
            print(f"eBay Item Cost: ${order_cost:.2f}")
            print(f"eBay Shipping Cost: ${order_shipping:.2f}")
            print(f"eBay Actual Shipping: ${order_actual_shipping:.2f}")
            print(f"Total Cost: ${order_total_cost:.2f}")
            print(f"Profit: ${order_profit:.2f}")
            print(f"Margin: {(order_profit / shopify_order.total_price * 100):.1f}%")
            
            total_revenue += shopify_order.total_price
            total_cost += order_cost
            total_shipping_cost += order_shipping
            total_actual_shipping += order_actual_shipping
            total_profit += order_profit
        else:
            print("No linked eBay orders found")
    
    # Calculate averages
    if orders_with_ebay > 0:
        avg_revenue = total_revenue / orders_with_ebay
        avg_cost = total_cost / orders_with_ebay
        avg_shipping = total_shipping_cost / orders_with_ebay
        avg_actual_shipping = total_actual_shipping / orders_with_ebay
        avg_profit = total_profit / orders_with_ebay
        avg_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    else:
        avg_revenue = avg_cost = avg_shipping = avg_actual_shipping = avg_profit = avg_margin = 0
    
    total_all_costs = total_cost + total_shipping_cost
    
    # Calculate total revenue for all orders, regardless of eBay links
    total_all_revenue = Decimal('0.00')
    unfulfilled_revenue = Decimal('0.00')
    async for shopify_order in shopify_orders.aiterator():
        total_all_revenue += shopify_order.total_price
        if not shopify_order.ebay_orders.exists():
            unfulfilled_revenue += shopify_order.total_price
    
    # Calculate predicted costs for unfulfilled orders
    unfulfilled_orders = total_orders - orders_with_ebay
    if orders_with_ebay > 0 and unfulfilled_orders > 0:
        # Use averages from fulfilled orders to predict costs
        predicted_item_cost = (total_cost / orders_with_ebay) * unfulfilled_orders
        # Use actual shipping instead of charged shipping for prediction
        predicted_shipping = (total_actual_shipping / orders_with_ebay) * unfulfilled_orders
        predicted_total_cost = predicted_item_cost + predicted_shipping
        predicted_profit = unfulfilled_revenue - predicted_total_cost
    else:
        predicted_item_cost = predicted_shipping = predicted_total_cost = predicted_profit = Decimal('0.00')
    
    # Print summary
    print("\nSummary Report")
    print("="*50)
    print(f"Time Period: {days_back} days")
    print(f"Total Shopify Orders: {total_orders}")
    print(f"Orders with eBay Links: {orders_with_ebay}")
    print(f"Orders Missing eBay Links: {total_orders - orders_with_ebay}")
    
    print("\nFinancials:")
    print(f"Total Revenue (All Orders): ${total_all_revenue:.2f}")
    print(f"Total Revenue (Fulfilled Orders): ${total_revenue:.2f}")
    print(f"Total Item Cost: ${total_cost:.2f}")
    print(f"Total Shipping Cost: ${total_shipping_cost:.2f}")
    print(f"Total Actual Shipping: ${total_actual_shipping:.2f}")
    print(f"Total All Costs: ${total_all_costs:.2f}")
    print(f"Total Profit: ${total_profit:.2f}")
    if total_revenue > 0:
        print(f"Overall Margin: {(total_profit / total_revenue * 100):.1f}% (profit/revenue)")
    else:
        print("Overall Margin: N/A (no fulfilled orders)")
    
    print("\nUnfulfilled Orders Prediction:")
    print(f"Unfulfilled Orders: {unfulfilled_orders}")
    print(f"Unfulfilled Revenue: ${unfulfilled_revenue:.2f}")
    print(f"Predicted Item Cost: ${predicted_item_cost:.2f}")
    print(f"Predicted Shipping: ${predicted_shipping:.2f}")
    print(f"Predicted Total Cost: ${predicted_total_cost:.2f}")
    print(f"Predicted Profit: ${predicted_profit:.2f}")
    if unfulfilled_revenue > 0:
        print(f"Predicted Margin: {(predicted_profit / unfulfilled_revenue * 100):.1f}%")
    else:
        print("Predicted Margin: N/A (no unfulfilled revenue)")
    
    print("\nAverages (for orders with eBay links):")
    print(f"Average Revenue: ${avg_revenue:.2f}")
    print(f"Average Item Cost: ${avg_cost:.2f}")
    print(f"Average Shipping Cost: ${avg_shipping:.2f}")
    print(f"Average Actual Shipping: ${avg_actual_shipping:.2f}")
    print(f"Average Profit: ${avg_profit:.2f}")
    print(f"Average Margin: {avg_margin:.1f}%")
    
    print("\nShipping Analysis:")
    if total_revenue > 0:
        print(f"Shipping Cost vs Revenue: {(total_actual_shipping / total_revenue * 100):.4f}%")
    else:
        print("Shipping Cost vs Revenue: N/A (no revenue)")
        
    if total_profit > 0:
        print(f"Shipping Cost vs Profit: {(total_actual_shipping / total_profit * 100):.4f}%")
    else:
        print("Shipping Cost vs Profit: N/A (no profit)")
        
    if total_shipping_cost > 0:
        print(f"Actual vs Charged Shipping: {(total_actual_shipping / total_shipping_cost * 100):.4f}%")
        print(f"Average Shipping Difference: ${(total_actual_shipping - total_shipping_cost) / orders_with_ebay:.2f}")
    
    if charged_shipping_costs:
        charged_shipping_costs.sort()
        median_idx = len(charged_shipping_costs) // 2
        median_charged = (charged_shipping_costs[median_idx] + charged_shipping_costs[~median_idx]) / 2
        
        print("\nCharged Shipping Statistics:")
        print(f"Highest Charged: ${max(charged_shipping_costs):.2f}")
        print(f"Lowest Charged: ${min(charged_shipping_costs):.2f}")
        print(f"Median Charged: ${median_charged:.2f}")
        print(f"Average Charged: ${sum(charged_shipping_costs) / len(charged_shipping_costs):.2f}")
        print(f"Orders with Charged Shipping: {len(charged_shipping_costs)}")
    
    if actual_shipping_costs:
        actual_shipping_costs.sort()
        median_idx = len(actual_shipping_costs) // 2
        median_actual = (actual_shipping_costs[median_idx] + actual_shipping_costs[~median_idx]) / 2
        
        print("\nActual Shipping Statistics:")
        print(f"Highest Actual: ${max(actual_shipping_costs):.2f}")
        print(f"Lowest Actual: ${min(actual_shipping_costs):.2f}")
        print(f"Median Actual: ${median_actual:.2f}")
        print(f"Average Actual: ${sum(actual_shipping_costs) / len(actual_shipping_costs):.2f}")
        print(f"Orders with Actual Shipping: {len(actual_shipping_costs)}")

async def run():
    # Add argument parsing
    parser = argparse.ArgumentParser(description='Generate profit report')
    parser.add_argument('--days', type=int, default=180,
                      help='Number of days to look back (default: 180)')
    args = parser.parse_args()
    
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
        # Use the days argument from command line
        await generate_profit_report(days_back=args.days)
        
    except Exception as e:
        print(f"Error generating report: {str(e)}")
        print(f"Error type: {type(e).__name__}")
    finally:
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