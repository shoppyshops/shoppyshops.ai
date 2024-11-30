import os
import sys
import xml.etree.ElementTree as ET
import asyncio
import aiohttp
from decimal import Decimal
from datetime import datetime

class Ebay:
    def __init__(self, app_id=None, dev_id=None, cert_id=None, user_token=None, sandbox=False):
        """Initialize eBay API client"""
        self.sandbox = sandbox
        
        # Use passed credentials or fall back to environment variables
        self.app_id = app_id or os.getenv('EBAY_PROD_APP_ID')
        self.dev_id = dev_id or os.getenv('EBAY_DEV_ID')
        self.cert_id = cert_id or os.getenv('EBAY_PROD_CERT_ID')
        self.user_token = user_token or os.getenv('LOCAL_AUSSIE_STORE_EBAY_USER_TOKEN')
        
        # Debug output
        print("Debug - eBay credentials loaded:")
        print(f"App ID: {'Set' if self.app_id else 'Missing'}")
        print(f"Dev ID: {'Set' if self.dev_id else 'Missing'}")
        print(f"Cert ID: {'Set' if self.cert_id else 'Missing'}")
        print(f"User Token: {'Set' if self.user_token else 'Missing'}")

    async def get_order_by_id(self, order_id):
        """Get a specific eBay order by ID using the Trading API"""
        if not self.user_token:
            print("Missing eBay user token!")
            return None

        url = 'https://api.ebay.com/ws/api.dll' if not self.sandbox else 'https://api.sandbox.ebay.com/ws/api.dll'
        
        headers = {
            'X-EBAY-API-SITEID': '15',  # Australia site ID
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

        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=headers, data=xml_request) as response:
                        response_text = await response.text()
                        print(f"eBay API Response Status: {response.status}")
                        print(f"eBay API Response: {response_text}")  # Debug output
                        
                        if response.status != 200:
                            print(f"eBay API Error: {response_text}")
                            return None

                        # Parse XML response
                        root = ET.fromstring(response_text)
                        
                        # Check for errors
                        ack = root.find('.//Ack')
                        if ack is not None and ack.text != 'Success':
                            error = root.find('.//Errors/LongMessage')
                            if error is not None:
                                print(f"eBay API Error: {error.text}")
                            return None

                        # Find order
                        order = root.find('.//OrderArray/Order')
                        if order is None:
                            print("No order found in response")
                            return None

                        # Extract transaction details
                        transaction = order.find('.//TransactionArray/Transaction')
                        if transaction is None:
                            print("No transaction found in order")
                            return None

                        # Extract order details
                        return {
                            'order_id': order_id,
                            'status': self._get_text(transaction, 'Status/PaymentStatus'),
                            'total': self._get_text(transaction, 'TotalPrice'),
                            'created_at': self._get_text(order, 'CreatedTime'),
                            'currency': 'AUD',  # Default for Australian orders
                            'title': self._get_text(transaction, 'Item/Title'),
                            'item_id': self._get_text(transaction, 'Item/ItemID'),
                            'seller_id': self._get_text(transaction, 'Seller/UserID'),
                            'transaction_id': self._get_text(transaction, 'TransactionID'),
                            'price': self._get_text(transaction, 'TransactionPrice'),
                            'quantity': self._get_text(transaction, 'QuantityPurchased', '1')
                        }
                        
            except aiohttp.ClientError as e:
                print(f"Network error: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                return None
                    
            except Exception as e:
                print(f"Error processing eBay order: {str(e)}")
                print(f"Error type: {type(e).__name__}")
                return None
                
        print(f"Could not find eBay order: {order_id}")
        return None
            
    def _get_text(self, element, tag_name, default=''):
        """Helper to safely get text from XML element"""
        child = element.find(f'.//{tag_name}')
        return child.text if child is not None else default
