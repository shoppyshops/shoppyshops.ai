from decimal import Decimal
from django.utils import timezone
import re
from shopify.models import ShopifyOrder
from ebay.models import EbayOrder, EbayOrderItem
import logging
import asyncio

async def get_shopify_orders(shopify_client):
    try:
        print("Querying Shopify for orders...")
        print("Making API request...")
        
        orders = await shopify_client.get_orders(first=200)
        
        if orders:
            print(f"Retrieved {len(orders)} orders")
            return orders
        
    except Exception as e:
        print(f"Error fetching Shopify orders: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        return []
        
    return []

async def sync_shopify_orders(shopify_client):
    """Sync orders from Shopify to local database"""
    print("Fetching Shopify orders...")
    
    try:
        orders = await get_shopify_orders(shopify_client)
        print(f"Successfully retrieved {len(orders)} orders from Shopify")
        return orders
    except Exception as e:
        print(f"Error in sync_shopify_orders: {str(e)}")
        return []

async def sync_ebay_orders(ebay_client):
    """Sync orders from eBay to local database"""
    orders = await ebay_client.get_purchase_history()
    synced_orders = []
    
    for order in orders:
        try:
            # Parse purchase date if available
            created_at = timezone.now()
            if purchase_date := order.get('purchase_date'):
                try:
                    created_at = timezone.datetime.fromisoformat(purchase_date.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    print(f"Could not parse purchase date: {purchase_date}")

            ebay_order, created = await EbayOrder.objects.aupdate_or_create(
                order_id=order['order_id'],
                defaults={
                    'order_status': order.get('status', 'Unknown'),
                    'order_total': Decimal(str(order['price'])),
                    'currency': order['currency'],
                    'created_at': created_at,
                    'payment_status': order.get('payment_status', 'Completed')
                }
            )
            
            # Create or update order item
            await EbayOrderItem.objects.aupdate_or_create(
                order=ebay_order,
                item_id=order['item_id'],
                defaults={
                    'title': order['title'],
                    'price': Decimal(str(order['price'])),
                    'quantity': order.get('quantity', 1),
                    'seller_id': order.get('seller_id', 'unknown'),
                    'transaction_id': order.get('transaction_id', '')
                }
            )
            
            synced_orders.append(ebay_order)
            print(f"{'Created' if created else 'Updated'} eBay order: {order['order_id']}")
            
        except Exception as e:
            print(f"Error syncing eBay order {order.get('order_id')}: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            print(f"Error details: {repr(e)}")
    
    return synced_orders

async def link_orders():
    """Link Shopify orders with their corresponding eBay orders"""
    print("\nLinking Shopify orders with eBay orders...")
    linked_orders = []
    
    async for shopify_order in ShopifyOrder.objects.all():
        try:
            # Look for eBay order numbers in Shopify order notes
            note = shopify_order.note or ''
            print(f"\nProcessing Shopify order: {shopify_order.name}")
            print(f"Note content: {note}") 
            # Improved regex pattern to match eBay order IDs
            matches = re.findall(r'\b\d{2}-\d{5}-\d{5}\b', note)
            
            if matches:
                print(f"Found potential eBay order(s): {matches}")
            else:
                print("No eBay order IDs found in note or name")
            
            for ebay_order_id in matches:
                try:
                    ebay_order = await EbayOrder.objects.aget(order_id=ebay_order_id)
                    ebay_order.shopify_order = shopify_order
                    await ebay_order.asave()
                    linked_orders.append(ebay_order)
                    print(f"Linked Shopify order {shopify_order.name} with eBay order {ebay_order_id}")
                except EbayOrder.DoesNotExist:
                    print(f"eBay order {ebay_order_id} not found in database")
                    
        except Exception as e:
            print(f"Error processing order {shopify_order.name}: {str(e)}")
            continue

    return linked_orders


