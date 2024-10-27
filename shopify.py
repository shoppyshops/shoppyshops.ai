import aiohttp
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Order:
    def __init__(self, order_id, name, email, total_price, currency):
        self.order_id = order_id
        self.name = name
        self.email = email
        self.total_price = total_price
        self.currency = currency

class Shopify:
    def __init__(self, shop_url, access_token, api_version):
        self.shop_url = shop_url
        self.access_token = access_token
        self.api_version = api_version
        self.graphql_endpoint = f"https://{self.shop_url}/admin/api/{self.api_version}/graphql.json"
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token
        }

        if not self.shop_url or not self.access_token:
            raise ValueError("Shop URL and Access Token must be provided.")

    async def execute_graphql(self, query, variables):
        return await self._post_request({"query": query, "variables": variables})

    async def _post_request(self, payload):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.graphql_endpoint,
                json=payload,
                headers=self.headers
            ) as response:
                return await self._handle_response(response)

    async def _handle_response(self, response):
        if response.status != 200:
            response_text = await response.text()
            raise Exception(f"Request failed with status {response.status}: {response_text}")
        return await response.json()
    

    async def get_orders(self, first=100):
        response = await self._fetch_orders(first)
        return self._hydrate_orders(response) 

    async def _fetch_orders(self, first=100):
        query = """
        query ($first: Int!) {
            orders(first: $first) {
                edges {
                    node {
                        id
                        name
                        email
                        totalPriceSet {
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                    }
                }
            }
        }
        """
        variables = {"first": first}
        return await self.execute_graphql(query, variables)
    
    def _hydrate_orders(self, data):
        orders = data['data']['orders']['edges']
        return [
            Order(
                order_id=order_node['id'],
                name=order_node['name'],
                email=order_node['email'],
                total_price=order_node['totalPriceSet']['shopMoney']['amount'],
                currency=order_node['totalPriceSet']['shopMoney']['currencyCode']
            )
            for order_edge in orders
            for order_node in [order_edge['node']]
        ]
