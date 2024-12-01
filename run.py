import os
import sys
import django
from io import StringIO
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shoppyshops.settings')
django.setup()

import asyncio
from shopify.shopify import Shopify
from ebay.ebay import Ebay
from dotenv import load_dotenv
from decimal import Decimal
from django.utils import timezone
import re
import httpx

from shopify.models import ShopifyOrder
from ebay.models import EbayOrder, EbayOrderItem

load_dotenv()

def clear_terminal():
    # Clear screen command based on OS
    os.system('cls' if os.name == 'nt' else 'clear')

def mask_string(s: str, visible_chars: int = 6) -> str:
    """Mask a string, showing only the first few characters"""
    if not s:
        return "Not set"
    return s[:visible_chars] + "..."

class ShoppyShops:
    """
    A Shoppy Shop is a combination of a Shopify store and other services that we are using to manage the store
    it's products, advertising, bank accounts, customer support etc.

    In our case a Shoppy Shop is a combination of:

    - Shopify store
    - Shopify Payments
    - PayPal
    - Airwallex
    - Facebook Ads
    - Whatsapp

    Later, we might add:
    - X (Twitter) Ads
    - Google Ads
    - Xero
    """
    def __init__(
            self, 
            shopify_access_token: str, 
            shopify_url: str, 
            api_version: str, 
            ebay_app_id: str, 
            ebay_dev_id: str, 
            ebay_cert_id: str, 
            ebay_user_token: str, 
            ebay_sandbox: bool
        ):
        # Validate eBay credentials
        if not all([ebay_app_id, ebay_dev_id, ebay_cert_id, ebay_user_token]):
            raise ValueError("All eBay credentials are required")
            
        print("eBay credentials:")  # Debug
        print(f"App ID: {ebay_app_id[:6]}..." if ebay_app_id else "Not set")
        print(f"Dev ID: {ebay_dev_id[:6]}..." if ebay_dev_id else "Not set")
        print(f"Cert ID: {ebay_cert_id[:6]}..." if ebay_cert_id else "Not set")
        print(f"User Token: {ebay_user_token[:6]}..." if ebay_user_token else "Not set")

        self.shopify = Shopify(
            shop_url=shopify_url, 
            access_token=shopify_access_token, 
            api_version=api_version
        )
        self.ebay = Ebay(
            app_id=ebay_app_id,
            dev_id=ebay_dev_id,
            cert_id=ebay_cert_id,
            user_token=ebay_user_token,
            sandbox=ebay_sandbox
        )

    async def get_orders(self, first=200):  # Increased from 100 to 200
        """Get recent unfulfilled orders that haven't been ordered from eBay yet"""
        orders = await self.shopify.get_orders(first)
        
        # Filter for orders that are:
        # 1. Not fulfilled
        # 2. Not already ordered from eBay
        # 3. Order number >= 1001
        unfulfilled_orders = []
        for order in orders:
            # Extract order number from name (e.g., "#1102" -> 1102)
            try:
                order_num = int(order.name.replace('#', ''))
                if order_num >= 1001:  # Only process orders >= #1001
                    fulfillments = await self.get_order_fulfillments(order.order_id)
                    if not fulfillments and "Ordered" not in order.tags:
                        unfulfilled_orders.append(order)
                        print(f"Found unfulfilled order: {order.name} - {order.total_price} {order.currency}")
            except ValueError:
                print(f"Couldn't parse order number from name: {order.name}")
                continue
        
        if not unfulfilled_orders:
            print("No unfulfilled orders found >= #1102")
        else:
            print(f"Found {len(unfulfilled_orders)} unfulfilled orders to process")
            
        return unfulfilled_orders

    async def get_order_fulfillments(self, order_id):
        return await self.shopify.get_order_fulfillments(order_id)

    async def process_order(self, order):
        """Process a single order by checking fulfillments and ordering from eBay if needed."""
        try:
            print("================================================")
            print(f"Processing Order ID: {order.order_id}\n"
                  f"Name: {order.name}\n"
                  f"Email: {order.email}\n"
                  f"Total Price: {order.total_price} {order.currency}")
            
            fulfillments = await self.get_order_fulfillments(order.order_id)
            print("--------------------------------")
            
            # Skip if order is already fulfilled or ordered
            if fulfillments:
                print("Order already fulfilled, skipping...")
                return
            if "Ordered" in order.tags:
                print("Order already ordered from eBay, skipping...")
                return
                
            print("Unfulfilled order found - starting eBay supplier search")
            print(f"Order line items: {order.line_items}")
            
            if not order.line_items:
                print("No line items found in order, skipping...")
                return
                
            # Get the first line item's title
            product_title = order.line_items[0].title
            print(f"Searching for product: {product_title}")
            
            try:
                supplier_items = await self.ebay.find_supplier_items(product_title)
                print(f"Found {len(supplier_items) if supplier_items else 0} potential suppliers")
                
                if supplier_items and len(supplier_items) > 0:
                    selected_item = supplier_items[0]
                    print(f"Selected supplier item: {selected_item}")
                    await self.ebay.purchase_product(order, selected_item)
                    print("Successfully ordered from eBay supplier")
                else:
                    print("No suitable suppliers found on eBay")
            except Exception as e:
                print(f"Error in eBay process: {str(e)}")
                print(f"Error type: {type(e).__name__}")
                print(f"Error details: {repr(e)}")
                
        except Exception as e:
            print(f"Error processing order {order.order_id}: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            print(f"Error details: {repr(e)}")

async def test_order_sync(shopify_client, ebay_client, start_order: int = None):
    """Process all orders from latest down to #1000, storing Shopify orders and their linked eBay orders in the DB"""
    try:
        if start_order:
            print(f"\nStarting from order #{start_order}...")
            latest_order = await shopify_client.get_order(f"#{start_order}")
            current_num = start_order
        else:
            print("\nFetching latest order...")
            latest_order = await shopify_client.get_order()
            if latest_order:
                current_num = int(latest_order.name.replace('#', ''))
                print(f"Latest order is: {latest_order.name}")
            
        if not latest_order:
            print("No orders found!")
            return
            
        orders_checked = 0
        orders_with_ebay = 0
        ebay_orders_found = 0
        
        while current_num >= 1000:
            print(f"\n{'='*50}")
            print(f"Processing order #{current_num}...")
            
            order = await shopify_client.get_order(f"#{current_num}")
            if order:
                print(f"Found Shopify order {order.name}")
                
                # Store Shopify order in DB
                db_shopify_order, created = await ShopifyOrder.objects.aupdate_or_create(
                    order_id=order.order_id,
                    defaults={
                        'name': order.name,
                        'email': order.email,
                        'total_price': Decimal(str(order.total_price)),
                        'currency': order.currency,
                        'note': order.note,
                        'created_at': timezone.datetime.fromisoformat(order.created_at.replace('Z', '+00:00'))
                    }
                )
                
                if order.note:
                    # Find all eBay order IDs
                    ebay_order_ids = re.findall(r'\b\d{2}-\d{5}-\d{5}\b', order.note)
                    if ebay_order_ids:
                        print(f"\nFound eBay order IDs: {ebay_order_ids}")
                        
                        # Fetch all eBay orders in parallel
                        ebay_orders = await asyncio.gather(
                            *[ebay_client.get_order_by_id(ebay_id) for ebay_id in ebay_order_ids],
                            return_exceptions=True
                        )
                        
                        # Process results
                        for ebay_id, ebay_order in zip(ebay_order_ids, ebay_orders):
                            if isinstance(ebay_order, Exception):
                                print(f"Error fetching eBay order {ebay_id}: {str(ebay_order)}")
                                continue
                            
                            if ebay_order:
                                print(f"Processing eBay order: {ebay_order['title']}")
                                
                                # Store eBay order in DB
                                db_ebay_order, created = await EbayOrder.objects.aupdate_or_create(
                                    order_id=ebay_order['order_id'],
                                    defaults={
                                        'order_status': ebay_order.get('status', 'Unknown'),
                                        'order_total': Decimal(str(ebay_order['price'])),
                                        'currency': ebay_order['currency'],
                                        'created_at': timezone.datetime.fromisoformat(ebay_order['created_at'].replace('Z', '+00:00')),
                                        'payment_status': 'Completed',
                                        'shopify_order': db_shopify_order  # Link to Shopify order
                                    }
                                )
                                
                                # Create or update order item
                                await EbayOrderItem.objects.aupdate_or_create(
                                    order=db_ebay_order,
                                    item_id=ebay_order['item_id'],
                                    defaults={
                                        'title': ebay_order['title'],
                                        'price': Decimal(str(ebay_order['price'])),
                                        'quantity': ebay_order.get('quantity', 1),
                                        'seller_id': ebay_order.get('seller_id', 'unknown'),
                                        'transaction_id': ebay_order.get('transaction_id', ''),
                                        'shipping_cost': Decimal(str(ebay_order.get('shipping_cost', '0.00'))),
                                        'actual_shipping_cost': Decimal(str(ebay_order.get('actual_shipping_cost', '0.00')))
                                    }
                                )
            
            current_num -= 1
            # Removed sleep delay since we're now running in parallel
            
        # Print final summary
        print(f"\n{'='*50}")
        print(f"Processing Complete!")
        print(f"Orders checked: {orders_checked}")
        print(f"Orders with eBay numbers: {orders_with_ebay}")
        print(f"eBay orders found and linked: {ebay_orders_found}")
            
    except Exception as e:
        print(f"Error in test_order_sync: {str(e)}")
        print(f"Error type: {type(e).__name__}")

async def run():
    clear_terminal()
    
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
        load_dotenv()
        
        async with httpx.AsyncClient() as shopify_client, httpx.AsyncClient() as ebay_client:
            shopify = Shopify(
                access_token=os.getenv('SHOPIFY_ACCESS_TOKEN'),
                shop_url=os.getenv('SHOPIFY_URL'),
                api_version=os.getenv('SHOPIFY_API_VERSION'),
                client=shopify_client
            )
            
            ebay = Ebay(
                app_id=os.getenv('EBAY_PROD_APP_ID'),
                dev_id=os.getenv('EBAY_DEV_ID'),
                cert_id=os.getenv('EBAY_PROD_CERT_ID'),
                user_token=os.getenv('LOCAL_AUSSIE_STORE_EBAY_USER_TOKEN'),
                sandbox=False,
                client=ebay_client
            )
            
            await test_order_sync(shopify, ebay)
    
    except Exception as e:
        print(f"Error in run: {str(e)}")
        print(f"Error type: {type(e).__name__}")
    finally:
        # Restore stdout
        sys.stdout = original_stdout
        output_text = output.getvalue()
        
        # Copy to clipboard
        try:
            import pyperclip
            pyperclip.copy(output_text)
            print("\nOutput copied to clipboard!")
        except ImportError:
            print("\nInstall pyperclip to enable automatic clipboard copy: pip install pyperclip")

if __name__ == "__main__":
    asyncio.run(run())