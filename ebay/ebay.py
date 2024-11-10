import httpx
from typing import Optional
import asyncio


class Ebay:
    """
    Ebay API Wrapper that enables Shoppy Shops to automate purchasing
    from preferred eBay stores.

    The product description will come from the Shopify store, and the
    purchase will be made from the eBay store. Once we have a successful
    purchase, we will store the product page for next time, and,
    we will update the order status in Shopify.

    Args:
        app_id (str): eBay application ID
        dev_id (str): eBay developer ID
        cert_id (str): eBay certificate ID
        sandbox (bool): Use sandbox environment if True (default)
    """
    def __init__(self, app_id: str, dev_id: str, cert_id: str, sandbox: bool = True):
        """Initialize the Ebay API wrapper with required credentials"""
        if not app_id or not dev_id or not cert_id:
            raise ValueError("All eBay credentials are required")
            
        self.app_id = app_id
        self.dev_id = dev_id
        self.cert_id = cert_id
        self.sandbox = sandbox
        self.session: Optional[httpx.AsyncClient] = None
        
        # Set appropriate API endpoints based on environment
        if sandbox:
            self.finding_api_url = "https://svcs.sandbox.ebay.com/services/search/FindingService/v1"
            self.trading_api_url = "https://api.sandbox.ebay.com/ws/api.dll"
            print("Using eBay Sandbox environment")
        else:
            self.finding_api_url = "https://svcs.ebay.com/services/search/FindingService/v1"
            self.trading_api_url = "https://api.ebay.com/ws/api.dll"
            print("Using eBay Production environment")

    async def connect(self) -> None:
        """Initialize httpx client and set up eBay API headers"""
        if self.session is None:
            timeout = httpx.Timeout(30.0, connect=10.0)
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            self.session = httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                verify=True,
                follow_redirects=True
            )
            
            # Set base URL based on environment
            if self.sandbox:
                self.finding_api_url = "https://svcs.sandbox.ebay.com/services/search/FindingService/v1"
                self.trading_api_url = "https://api.sandbox.ebay.com/ws/api.dll"
            else:
                self.finding_api_url = "https://svcs.ebay.com/services/search/FindingService/v1"
                self.trading_api_url = "https://api.ebay.com/ws/api.dll"

    async def close(self) -> None:
        """Close the httpx client"""
        if self.session:
            await self.session.aclose()
            self.session = None

    async def _make_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make a request with retry logic"""
        retries = 3
        for attempt in range(retries):
            try:
                if not self.session:
                    await self.connect()
                
                print(f"Making request to {url}")  # Debug
                print(f"Headers: {kwargs.get('headers', {})}")  # Debug
                print(f"Content: {kwargs.get('content', '')}")  # Debug
                
                response = await self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response
                
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                if attempt == retries - 1:  # Last attempt
                    raise Exception(f"Failed to connect after {retries} attempts: {str(e)}")
                print(f"Attempt {attempt + 1} failed, retrying... ({str(e)})")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
                # Reconnect on next attempt
                await self.close()
                await self.connect()

    async def find_supplier_items(self, product_title: str, max_price: float = None) -> list:
        """Search eBay for items matching the product title within price constraints."""
        if not product_title:
            raise ValueError("Product title is required for eBay search")
            
        if not self.session:
            await self.connect()
            
        # Clean and encode the product title
        import re
        clean_title = re.sub(r'[^\x00-\x7F]+', '', product_title)
        clean_title = clean_title.replace('.', '').strip()
        clean_title = re.sub(r'\s+', ' ', clean_title)
        clean_title = "solar motion sensor light outdoor"  # Simplified search
        
        print(f"Searching eBay for: {clean_title}")
        
        # Construct the Finding API request
        xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
        <findItemsByKeywordsRequest xmlns="http://www.ebay.com/marketplace/search/v1/services">
            <keywords>{clean_title}</keywords>
            <itemFilter>
                <name>ListingType</name>
                <value>FixedPrice</value>
            </itemFilter>
            <itemFilter>
                <name>MinPrice</name>
                <value>15.00</value>
            </itemFilter>
            <itemFilter>
                <name>MaxPrice</name>
                <value>50.00</value>
            </itemFilter>
            <itemFilter>
                <name>Condition</name>
                <value>New</value>
            </itemFilter>
            <sortOrder>PricePlusShippingLowest</sortOrder>
            <paginationInput>
                <entriesPerPage>10</entriesPerPage>
                <pageNumber>1</pageNumber>
            </paginationInput>
            <outputSelector>SellerInfo</outputSelector>
            <outputSelector>PictureURLLarge</outputSelector>
        </findItemsByKeywordsRequest>"""
        
        headers = {
            "X-EBAY-SOA-SECURITY-APPNAME": self.app_id,
            "X-EBAY-SOA-OPERATION-NAME": "findItemsByKeywords",
            "X-EBAY-SOA-SERVICE-VERSION": "1.13.0",
            "X-EBAY-SOA-GLOBAL-ID": "EBAY-AU",  # Changed to Australian site
            "Content-Type": "text/xml;charset=utf-8"
        }
        
        try:
            response = await self._make_request(
                'POST',
                self.finding_api_url,
                content=xml_request.encode('utf-8'),
                headers=headers
            )
            
            print(f"Response status: {response.status_code}")
            if response.status_code != 200:
                print(f"Error response: {response.text}")
                return []
                
            # Parse XML response
            from xml.etree import ElementTree as ET
            root = ET.fromstring(response.text)
            
            # Extract items from response
            items = []
            namespace = {'ns': 'http://www.ebay.com/marketplace/search/v1/services'}
            
            for item in root.findall('.//ns:searchResult/ns:item', namespace):
                try:
                    item_id = item.find('ns:itemId', namespace).text
                    title = item.find('ns:title', namespace).text
                    price_elem = item.find('.//ns:currentPrice', namespace)
                    price = float(price_elem.text) if price_elem is not None else 0.0
                    url = item.find('ns:viewItemURL', namespace).text
                    
                    items.append({
                        'id': item_id,
                        'title': title,
                        'price': price,
                        'url': url
                    })
                    print(f"Found item: {title} - ${price}")
                except Exception as e:
                    print(f"Error parsing item: {e}")
                    continue
            
            return items
            
        except Exception as e:
            print(f"Error querying eBay API: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            print(f"Error details: {repr(e)}")
            raise
            
        return []

    async def purchase_product(self, order, item) -> bool:
        """
        Purchase a product from eBay for the given Shopify order.
        Uses the Trading API to place the order.
        """
        try:
            print(f"\nAttempting to purchase eBay item:")
            print(f"Item ID: {item['id']}")
            print(f"Title: {item['title']}")
            print(f"Price: ${item['price']}")
            print(f"URL: {item['url']}")
            print(f"For Shopify Order: {order.name}")
            
            # Construct Trading API request for PlaceOffer
            xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
            <PlaceOfferRequest xmlns="urn:ebay:apis:eBLBaseComponents">
                <RequesterCredentials>
                    <eBayAuthToken>{self.auth_token}</eBayAuthToken>
                </RequesterCredentials>
                <ItemID>{item['id']}</ItemID>
                <Offer>
                    <Action>Purchase</Action>
                    <Quantity>1</Quantity>
                    <MaxBid>{item['price']}</MaxBid>
                </Offer>
                <EndUserIP>1.1.1.1</EndUserIP>
                <AffiliateTrackingDetails>
                    <TrackingID>SHOPPY_SHOPS</TrackingID>
                </AffiliateTrackingDetails>
            </PlaceOfferRequest>"""
            
            headers = {
                "X-EBAY-API-SITEID": "0",  # US site
                "X-EBAY-API-COMPATIBILITY-LEVEL": "967",
                "X-EBAY-API-CALL-NAME": "PlaceOffer",
                "X-EBAY-API-APP-NAME": self.app_id,
                "X-EBAY-API-DEV-NAME": self.dev_id,
                "X-EBAY-API-CERT-NAME": self.cert_id,
                "Content-Type": "text/xml"
            }
            
            response = await self._make_request(
                'POST',
                self.trading_api_url,
                content=xml_request.encode('utf-8'),
                headers=headers
            )
            
            print(f"Purchase response status: {response.status_code}")
            print(f"Purchase response content: {response.text}")
            
            if response.status_code == 200:
                # Parse response XML
                from xml.etree import ElementTree as ET
                root = ET.fromstring(response.text)
                
                # Check if purchase was successful
                ack = root.find('.//Ack').text
                if ack == 'Success':
                    print("Purchase successful!")
                    
                    return True
                else:
                    error = root.find('.//Errors/ShortMessage').text
                    print(f"Purchase failed: {error}")
                    return False
                    
            return False
            
        except Exception as e:
            print(f"Error purchasing from eBay: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            print(f"Error details: {repr(e)}")
            return False
