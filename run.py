import asyncio
import os
from shopify.shopify import Shopify
from ebay.ebay import Ebay
from dotenv import load_dotenv

load_dotenv()

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
            ebay_sandbox: bool
        ):
        # Validate eBay credentials
        if not ebay_app_id:
            raise ValueError("EBAY_APP_ID is required but not set in .env")
        if not ebay_dev_id:
            raise ValueError("EBAY_DEV_ID is required but not set in .env")
        if not ebay_cert_id:
            raise ValueError("EBAY_CERT_ID is required but not set in .env")
            
        print("eBay credentials:")  # Debug
        print(f"App ID: {ebay_app_id[:6]}..." if ebay_app_id else "Not set")
        print(f"Dev ID: {ebay_dev_id[:6]}..." if ebay_dev_id else "Not set")
        print(f"Cert ID: {ebay_cert_id[:6]}..." if ebay_cert_id else "Not set")

        self.shopify = Shopify(
            shop_url=shopify_url, 
            access_token=shopify_access_token, 
            api_version=api_version
        )
        self.ebay = Ebay(
            app_id=ebay_app_id,
            dev_id=ebay_dev_id,
            cert_id=ebay_cert_id,
            sandbox=ebay_sandbox
        )

    async def get_orders(self, first=200):  # Increased from 100 to 200
        """Get recent unfulfilled orders that haven't been ordered from eBay yet"""
        orders = await self.shopify.get_orders(first)
        
        # Filter for orders that are:
        # 1. Not fulfilled
        # 2. Not already ordered from eBay
        # 3. Order number >= 1102
        unfulfilled_orders = []
        for order in orders:
            # Extract order number from name (e.g., "#1102" -> 1102)
            try:
                order_num = int(order.name.replace('#', ''))
                if order_num >= 1102:  # Only process orders >= #1102
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

async def run():
    local_aussie_store = ShoppyShops(
        shopify_access_token=os.getenv("SHOPIFY_ACCESS_TOKEN"),
        shopify_url=os.getenv("SHOPIFY_URL"),
        api_version=os.getenv("SHOPIFY_API_VERSION"),
        ebay_app_id=os.getenv("EBAY_SANDBOX_APP_ID"),
        ebay_dev_id=os.getenv("EBAY_DEV_ID"),
        ebay_cert_id=os.getenv("EBAY_SANDBOX_CERT_ID"),
        ebay_sandbox=True
    ) 

    await local_aussie_store.ebay.connect()
    
    try:
        orders = await local_aussie_store.get_orders()
        # Create tasks for all orders to process them concurrently
        tasks = [local_aussie_store.process_order(order) for order in orders]
        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

    except Exception as e:
        print("--------------------------------")
        print(f"    An error occurred while fetching orders: {str(e)}")
        print(f"    Error type: {type(e).__name__}")
        print(f"    Error details: {repr(e)}")
        print("--------------------------------")

if __name__ == "__main__":
    asyncio.run(run())