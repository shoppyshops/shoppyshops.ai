import os
import sys
import xml.etree.ElementTree as ET
import asyncio
import aiohttp
from decimal import Decimal
from datetime import datetime

class Ebay:
    def __init__(self, app_id, dev_id, cert_id, user_token, sandbox=False):
        self.app_id = app_id
        self.dev_id = dev_id
        self.cert_id = cert_id
        self.user_token = user_token
        self.sandbox = sandbox

    async def get_order_by_id(self, order_id):
        """Get a specific eBay order by ID"""
        if not all([self.app_id, self.dev_id, self.cert_id, self.user_token]):
            print("Missing eBay credentials!")
            return None

        headers = {
            'X-EBAY-API-SITEID': '15',  # Australia site ID
            'X-EBAY-API-COMPATIBILITY-LEVEL': '967',
            'X-EBAY-API-CALL-NAME': 'GetOrders',
            'Content-Type': 'text/xml',
            'X-EBAY-API-APP-NAME': str(self.app_id),
            'X-EBAY-API-DEV-NAME': str(self.dev_id),
            'X-EBAY-API-CERT-NAME': str(self.cert_id)
        }
            
        xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
        <GetOrdersRequest xmlns="urn:ebay:apis:eBLBaseComponents">
            <RequesterCredentials>
                <eBayAuthToken>{self.user_token}</eBayAuthToken>
            </RequesterCredentials>
            <OrderIDArray>
                <OrderID>{order_id}</OrderID>
            </OrderIDArray>
            <OrderRole>Seller</OrderRole>
            <DetailLevel>ReturnAll</DetailLevel>
        </GetOrdersRequest>"""
        
        url = 'https://api.ebay.com/ws/api.dll' if not self.sandbox else 'https://api.sandbox.ebay.com/ws/api.dll'
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=xml_request) as response:
                    response_text = await response.text()
                    print(f"eBay API Response Status: {response.status}")
                    
                    # Basic XML parsing
                    root = ET.fromstring(response_text)
                    
                    # Check for errors
                    ack = root.find('.//Ack')
                    if ack is not None and ack.text != 'Success':
                        error = root.find('.//Errors/LongMessage')
                        if error is not None:
                            print(f"eBay API Error: {error.text}")
                        return None
                    
                    # Find order
                    order = root.find('.//Order')
                    if order is None:
                        print("No order found in response")
                        return None
                        
                    # Extract basic order details
                    return {
                        'order_id': self._get_text(order, 'OrderID'),
                        'status': self._get_text(order, 'OrderStatus'),
                        'total': self._get_text(order, 'Total'),
                        'created_at': self._get_text(order, 'CreatedTime'),
                        'currency': 'AUD'  # Default for now
                    }
                    
        except Exception as e:
            print(f"Error processing eBay order: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            return None
            
    def _get_text(self, element, tag_name, default=''):
        """Helper to safely get text from XML element"""
        child = element.find(f'.//{tag_name}')
        return child.text if child is not None else default
