import httpx
import asyncio


class Order:
    def __init__(self, order_id, name, email, total_price, currency, tags, note, created_at, line_items=None):
        self.order_id = order_id
        self.name = name
        self.email = email
        self.total_price = total_price
        self.currency = currency
        self.tags = tags
        self.note = note
        self.created_at = created_at
        self.line_items = line_items if line_items else []

    def __str__(self):
        return f"Order {self.name} - {self.total_price} {self.currency}"

class OrderFulfillment:
    def __init__(self, order_id, fulfillment_id, created_at, tracking_number, tracking_url):
        self.order_id = order_id
        self.fulfillment_id = fulfillment_id
        self.created_at = created_at
        self.tracking_number = tracking_number
        self.tracking_url = tracking_url

class LineItem:
    def __init__(self, title, quantity, price, currency, sku, variant_id, variant_sku, variant_title):
        self.title = title
        self.quantity = quantity
        self.price = price
        self.currency = currency
        self.sku = sku
        self.variant_id = variant_id
        self.variant_sku = variant_sku
        self.variant_title = variant_title

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

    async def _retry_with_backoff(self, func, *args, max_retries=3, initial_delay=1):
        """Helper function to retry operations with exponential backoff"""
        for attempt in range(max_retries):
            try:
                return await func(*args)
            except Exception as e:
                if attempt == max_retries - 1:  # Last attempt
                    raise  # Re-raise the last exception
                
                delay = initial_delay * (2 ** attempt)  # Exponential backoff
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                print(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)

    async def _post_request(self, payload):
        """Make a POST request to Shopify with retry logic"""
        return await self._retry_with_backoff(
            self._make_request,
            payload
        )

    async def _make_request(self, payload):
        """Actually perform the HTTP request"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.graphql_endpoint,
                json=payload,
                headers=self.headers
            )
            if response.status_code != 200:
                raise Exception(f"Request failed with status {response.status_code}: {response.text}")
            return response.json()

    async def get_orders(self, first=200):
        print(f"Querying Shopify for {first} orders...")
        query = """
        {
            orders(first: %d, sortKey: ID, reverse: true) {
                edges {
                    node {
                        id
                        name
                        email
                        createdAt
                        totalPriceSet {
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                        tags
                        note
                        lineItems(first: 10) {
                            edges {
                                node {
                                    title
                                    quantity
                                    originalUnitPriceSet {
                                        shopMoney {
                                            amount
                                            currencyCode
                                        }
                                    }
                                    sku
                                    variant {
                                        id
                                        sku
                                        title
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """ % first

        response = await self._post_request({"query": query})
        print(f"Shopify API Response Status: {response.get('data') is not None}")
        
        if response and "data" in response and "orders" in response["data"]:
            orders = [Order(
                order_id=edge["node"]["id"],
                name=edge["node"]["name"],
                email=edge["node"]["email"],
                total_price=edge["node"]["totalPriceSet"]["shopMoney"]["amount"],
                currency=edge["node"]["totalPriceSet"]["shopMoney"]["currencyCode"],
                tags=edge["node"]["tags"],
                note=edge["node"]["note"],
                created_at=edge["node"]["createdAt"],
                line_items=[LineItem(
                    title=item["node"]["title"],
                    quantity=item["node"]["quantity"],
                    price=item["node"]["originalUnitPriceSet"]["shopMoney"]["amount"],
                    currency=item["node"]["originalUnitPriceSet"]["shopMoney"]["currencyCode"],
                    sku=item["node"]["sku"] if "sku" in item["node"] else None,
                    variant_id=item["node"]["variant"]["id"] if item["node"]["variant"] else None,
                    variant_sku=item["node"]["variant"]["sku"] if item["node"]["variant"] and "sku" in item["node"]["variant"] else None,
                    variant_title=item["node"]["variant"]["title"] if item["node"]["variant"] and "title" in item["node"]["variant"] else None
                ) for item in edge["node"]["lineItems"]["edges"]]
            ) for edge in response["data"]["orders"]["edges"]]
            print(f"Found {len(orders)} orders in Shopify response")
            return orders
        print("No orders found in Shopify response")
        return []

    async def get_order_fulfillments(self, order_id):
        response = await self._query_order_fulfillments(order_id)
        return self._hydrate_order_fulfillments(response)

    async def _query_order_fulfillments(self, order_id):
        query = """
        query ($order_id: ID!) {
            order(id: $order_id) {
                id
                fulfillments {
                    id
                    status
                    createdAt
                    trackingInfo {
                        number
                        url
                    }
                }
            }
        }
        """
        variables = {"order_id": order_id}
        return await self.execute_graphql(query, variables)

    def _hydrate_order_fulfillments(self, data):
        order_id = data['data']['order']['id']
        fulfillments = data['data']['order']['fulfillments']
        return [
            OrderFulfillment(
                order_id=order_id,
                fulfillment_id=fulfillment['id'],
                created_at=fulfillment['createdAt'],
                tracking_number=fulfillment['trackingInfo'][0]['number'] if fulfillment['trackingInfo'] else None,
                tracking_url=fulfillment['trackingInfo'][0]['url'] if fulfillment['trackingInfo'] else None
            )
            for fulfillment in fulfillments
        ]

    async def get_order(self, order_name: str = None):
        """
        Get a single order by name (e.g., '#1102') or the latest order if no name provided.
        Returns None if no order is found.
        """
        if order_name:
            print(f"Fetching Shopify order: {order_name}")
            query_filter = f'query: "name:{order_name}"'
        else:
            print("Fetching latest Shopify order")
            query_filter = "sortKey: CREATED_AT, reverse: true"
        
        query = f"""
        query {{
            orders(first: 1, {query_filter}) {{
                edges {{
                    node {{
                        id
                        name
                        email
                        createdAt
                        totalPriceSet {{
                            shopMoney {{
                                amount
                                currencyCode
                            }}
                        }}
                        tags
                        note
                        lineItems(first: 10) {{
                            edges {{
                                node {{
                                    title
                                    quantity
                                    originalUnitPriceSet {{
                                        shopMoney {{
                                            amount
                                            currencyCode
                                        }}
                                    }}
                                    sku
                                    variant {{
                                        id
                                        sku
                                        title
                                    }}
                                }}
                            }}
                        }}
                    }}
                }}
            }}
        }}
        """
        
        response = await self._post_request({"query": query})
        
        if response and "data" in response and "orders" in response["data"]:
            edges = response["data"]["orders"]["edges"]
            if edges:
                order_data = edges[0]["node"]
                return Order(
                    order_id=order_data["id"],
                    name=order_data["name"],
                    email=order_data["email"],
                    total_price=order_data["totalPriceSet"]["shopMoney"]["amount"],
                    currency=order_data["totalPriceSet"]["shopMoney"]["currencyCode"],
                    tags=order_data["tags"],
                    note=order_data["note"],
                    created_at=order_data["createdAt"],
                    line_items=[LineItem(
                        title=item["node"]["title"],
                        quantity=item["node"]["quantity"],
                        price=item["node"]["originalUnitPriceSet"]["shopMoney"]["amount"],
                        currency=item["node"]["originalUnitPriceSet"]["shopMoney"]["currencyCode"],
                        sku=item["node"]["sku"] if "sku" in item["node"] else None,
                        variant_id=item["node"]["variant"]["id"] if item["node"]["variant"] else None,
                        variant_sku=item["node"]["variant"]["sku"] if item["node"]["variant"] and "sku" in item["node"]["variant"] else None,
                        variant_title=item["node"]["variant"]["title"] if item["node"]["variant"] and "title" in item["node"]["variant"] else None
                    ) for item in order_data["lineItems"]["edges"]]
                )
        
        return None

