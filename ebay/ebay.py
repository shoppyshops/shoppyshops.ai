import aiohttp


class Ebay:
    """
    Ebay API Wrapper that enables Shoppy Shops to automate purchasing
    from preferred eBay stores.

    The product description will come from the Shopify store, and the
    purchase will be made from the eBay store.  Once we have a successful
    purchase, we will store the product page for next time, and, 
    we will update the order status in Shopify.
    """
    def __init__(self, app_id, dev_id, cert_id):
        self.app_id = app_id
        self.dev_id = dev_id
        self.cert_id = cert_id
        
        pass
    
    async def purchase_product(self, order):
        pass