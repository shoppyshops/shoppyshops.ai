import aiohttp
import asyncio
import shopify
import dotenv
import os

dotenv.load_dotenv()

class ShoppyShops:
    def __init__(
        self,
        shopify_api_secret,
        shopify_shop_url,
    ):
        self.shopify = shopify.Session(
            private_app_password=shopify_api_secret,
            api_version="2024-10",
            shop_url=shopify_shop_url,
        )

    async def get_orders(self):
        return await self.shopify.get("orders.json")


async def run():
    local_aussie_store = ShoppyShops(
        shopify_api_secret=os.getenv("SHOPIFY_API_SECRET"),
        shopify_shop_url=os.getenv("SHOPIFY_SHOP_URL")
    )

    print(await local_aussie_store.get_orders())

if __name__ == "__main__":
    asyncio.run(run())


