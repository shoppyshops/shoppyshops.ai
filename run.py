import asyncio
import os
from shopify import Shopify
from ebay import Ebay
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
    def __init__(self, shopify_access_token, shopify_url, api_version):
        self.shopify = Shopify(
            shop_url=shopify_url, 
            access_token=shopify_access_token, 
            api_version=api_version
        )
        self.ebay = Ebay()

    async def get_orders(self, first=100):
        return await self.shopify.get_orders(first)

    async def get_order_fulfillments(self, order_id):
        return await self.shopify.get_order_fulfillments(order_id)


async def run():
    local_aussie_store = ShoppyShops(
        shopify_access_token=os.getenv("SHOPIFY_ACCESS_TOKEN"),
        shopify_url=os.getenv("SHOPIFY_URL"),
        api_version=os.getenv("SHOPIFY_API_VERSION")
    ) 

    try:
        orders = await local_aussie_store.get_orders()
        for order in orders:
            print("================================================")
            print(f"Order ID: {order.order_id}\n"
                  f"Name: {order.name}\n"
                  f"Email: {order.email}\n"
                  f"Total Price: {order.total_price} {order.currency}")
            fulfillments = await local_aussie_store.get_order_fulfillments(order.order_id)
            print("--------------------------------")
            if fulfillments:
                for fulfillment in fulfillments:
                    print(f"Fulfillment ID: {fulfillment.fulfillment_id} \n"
                          f"Fulfillment Created At: {fulfillment.created_at} \n"
                          f"Tracking Number: {fulfillment.tracking_number} \n"
                          f"Tracking URL: {fulfillment.tracking_url}")
            else:
                print(f"No fulfillments found for order {order.order_id}")
                if "Ordered" in order.tags:
                    print(f"Order has been ordered with eBay: {order.note}")
                else:
                    print(f"No supplier order found, ordering with eBay")
                    await local_aussie_store.ebay.purchase_product(order)
    except Exception as e:
        print("--------------------------------")
        print(f"    An error occurred while fetching orders: {str(e)}")
        print(f"    Error type: {type(e).__name__}")
        print(f"    Error details: {repr(e)}")
        print("--------------------------------")

if __name__ == "__main__":
    asyncio.run(run())