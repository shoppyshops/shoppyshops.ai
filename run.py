import aiohttp
import asyncio 


class ShoppyShops:
    def __init__(self):
        self.session = aiohttp.ClientSession()

    async def get_shops(self):
        async with self.session.get("https://shoppy.gg/api/v1/shops") as response:
            return await response.json()


async def run():
    shops = ShoppyShops()
    print(await shops.get_shops())

if __name__ == "__main__":
    asyncio.run(run())

