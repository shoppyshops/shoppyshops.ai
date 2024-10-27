import asyncio
import os
from shopify import Shopify

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
        self.client = Shopify(
            shop_url=shopify_url, 
            access_token=shopify_access_token, 
            api_version=api_version
        )

    async def get_orders(self, first=100):
        return await self.client.get_orders(first)

async def run():
    local_aussie_store = ShoppyShops(
        shopify_access_token=os.getenv("SHOPIFY_ACCESS_TOKEN"),
        shopify_url=os.getenv("SHOPIFY_URL"),
        api_version=os.getenv("SHOPIFY_API_VERSION")
    ) 

    try:
        orders = await local_aussie_store.get_orders()
        for order in orders:
            print(f"Order ID: {order.order_id}, Name: {order.name}, Email: {order.email}, Total Price: {order.total_price} {order.currency}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(run())