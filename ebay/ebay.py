import os
import sys
import xml.etree.ElementTree as ET
import asyncio
import httpx
from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Dict, Any

class Ebay:
    def __init__(self, app_id=None, dev_id=None, cert_id=None, user_token=None, sandbox=False, client=None):
        """Initialize eBay API client"""
        self.sandbox = sandbox
        
        # Use passed credentials or fall back to environment variables
        self.app_id = app_id or os.getenv('EBAY_PROD_APP_ID')
        self.dev_id = dev_id or os.getenv('EBAY_DEV_ID')
        self.cert_id = cert_id or os.getenv('EBAY_PROD_CERT_ID')
        self.user_token = user_token or os.getenv('LOCAL_AUSSIE_STORE_EBAY_USER_TOKEN')
        
        # Initialize HTTP client
        self.client = client or httpx.AsyncClient(timeout=30.0)
        self.url = 'https://api.ebay.com/ws/api.dll' if not self.sandbox else 'https://api.sandbox.ebay.com/ws/api.dll'
        
        # Debug output
        print("Debug - eBay credentials loaded:")
        print(f"App ID: {'Set' if self.app_id else 'Missing'}")
        print(f"Dev ID: {'Set' if self.dev_id else 'Missing'}")
        print(f"Cert ID: {'Set' if self.cert_id else 'Missing'}")
        print(f"User Token: {'Set' if self.user_token else 'Missing'}")

    async def __aenter__(self):
        if not self.client:
            self.client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client and not hasattr(self.client, '_is_external'):
            await self.client.aclose()

    async def get_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific eBay order by ID using the Trading API"""
        if not self.user_token:
            print("Missing eBay user token!")
            return None

        headers = {
            'X-EBAY-API-SITEID': '15',
            'X-EBAY-API-COMPATIBILITY-LEVEL': '967',
            'X-EBAY-API-CALL-NAME': 'GetOrders',
            'X-EBAY-API-IAF-TOKEN': self.user_token,
            'Content-Type': 'text/xml'
        }

        xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
        <GetOrdersRequest xmlns="urn:ebay:apis:eBLBaseComponents">
            <RequesterCredentials>
                <eBayAuthToken>{self.user_token}</eBayAuthToken>
            </RequesterCredentials>
            <OrderIDArray>
                <OrderID>{order_id}</OrderID>
            </OrderIDArray>
            <OrderRole>Buyer</OrderRole>
            <DetailLevel>ReturnAll</DetailLevel>
            <IncludeNotes>true</IncludeNotes>
        </GetOrdersRequest>"""

        for attempt in range(3):
            try:
                response = await self.client.post(
                    self.url,
                    headers=headers,
                    content=xml_request
                )
                response.raise_for_status()
                # Parse XML response
                root = ET.fromstring(response.text)
                # Define namespace
                ns = {'ns': 'urn:ebay:apis:eBLBaseComponents'}
                
                # Check for errors
                ack = root.find('.//ns:Ack', ns)
                if ack is not None and ack.text != 'Success':
                    error = root.find('.//ns:Errors/ns:LongMessage', ns)
                    if error is not None:
                        print(f"eBay API Error: {error.text}")
                    return None

                # Find orders
                orders = root.findall('.//ns:OrderArray/ns:Order', ns)
                print(f"Debug - Found {len(orders)} orders")
                
                if not orders:
                    print("No orders found in response")
                    return None

                # Find matching order
                order = None
                for o in orders:
                    order_id_elem = o.find('ns:OrderID', ns)
                    if order_id_elem is not None:
                        print(f"Debug - Found order ID: {order_id_elem.text}")
                        if order_id_elem.text == order_id:
                            order = o
                            break

                if order is None:
                    print(f"Order {order_id} not found in response")
                    return None

                # Get the first transaction
                transaction = order.find('.//ns:TransactionArray/ns:Transaction', ns)
                if transaction is None:
                    print("No transaction found in order")
                    return None

                # Extract order details
                return {
                    'order_id': self._get_text(order, 'OrderID', ns),
                    'status': self._get_text(order, 'OrderStatus', ns),
                    'total': self._get_text(order, 'Total', ns),
                    'created_at': self._get_text(order, 'CreatedTime', ns),
                    'currency': self._get_text(order, 'Total', ns, '@currencyID', 'AUD'),
                    'title': self._get_text(transaction, 'Item/Title', ns),
                    'item_id': self._get_text(transaction, 'Item/ItemID', ns),
                    'seller_id': self._get_text(order, 'SellerUserID', ns),
                    'transaction_id': self._get_text(transaction, 'TransactionID', ns),
                    'price': self._get_text(transaction, 'TransactionPrice', ns),
                    'quantity': self._get_text(transaction, 'QuantityPurchased', ns, default='1'),
                    'shipping_cost': self._get_text(transaction, 'ShippingServiceSelected/ShippingServiceCost', ns, default='0.00'),
                    'actual_shipping_cost': self._get_text(transaction, 'ActualShippingCost', ns, default='0.00')
                }
                
            except httpx.HTTPError as e:
                print(f"HTTP error: {str(e)}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return None
                
        print(f"Could not find eBay order: {order_id}")
        return None

    def _get_text(self, element, tag_path, ns, attribute=None, default=''):
        """Helper to safely get text from XML element or its attribute"""
        try:
            # Add namespace prefix to each tag in the path
            ns_path = '/'.join(f'ns:{tag}' for tag in tag_path.split('/'))
            child = element.find(f'.//{ns_path}', ns)
            if child is not None:
                if attribute:
                    return child.get(attribute, default)
                return child.text or default
            return default
        except Exception as e:
            print(f"Error getting text for {tag_path}: {str(e)}")
            return default
