from django.core.management.base import BaseCommand
from django.db.models import Sum, F, Count
from django.db import models
from meta.models import MetaSpend
from shopify.models import ShopifyOrder
from ebay.models import EbayOrder
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Generate daily ROAS report with profitability metrics'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7)
        parser.add_argument('--start', type=str, help='YYYY-MM-DD')
        parser.add_argument('--end', type=str, help='YYYY-MM-DD')

    def handle(self, *args, **options):
        # Calculate date range
        if options['start'] and options['end']:
            start_date = datetime.strptime(options['start'], '%Y-%m-%d').date()
            end_date = datetime.strptime(options['end'], '%Y-%m-%d').date()
        else:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=options['days']-1)

        self.stdout.write(f"\nDaily Performance Report ({start_date} to {end_date})")
        self.stdout.write("=" * 160)
        
        # Header
        self.stdout.write(
            f"{'Date':<12} "
            f"{'Ord':>5} "
            f"{'Revenue':>12} "
            f"{'Cost':>12} "
            f"{'Ad Spend':>12} "
            f"{'Net Pre':>12} "
            f"{'Net Post':>12} "
            f"{'ROAS':>6} "
            f"{'BROAS':>6} "
            f"{'Cost%':>6} "
            f"{'Ad%':>6} "
            f"{'Margin%':>7} "
            f"{'AOV':>10}"
        )
        self.stdout.write("-" * 160)

        totals = {
            'orders': 0,
            'revenue': 0,
            'cost': 0,
            'ad_spend': 0,
            'net_before_ads': 0,
            'net_after_ads': 0
        }

        # Process each day
        current_date = start_date
        while current_date <= end_date:
            # Get daily metrics
            daily_orders = ShopifyOrder.objects.filter(
                created_at__date=current_date
            ).count()

            daily_revenue = ShopifyOrder.objects.filter(
                created_at__date=current_date
            ).aggregate(
                total=Sum('total_price')
            )['total'] or 0

            daily_cost = EbayOrder.objects.filter(
                shopify_order__created_at__date=current_date
            ).aggregate(
                total=Sum('order_total')
            )['total'] or 0

            daily_ad_spend = MetaSpend.objects.filter(
                date=current_date
            ).aggregate(
                total=Sum('spend')
            )['total'] or 0

            # Calculate metrics
            net_before_ads = daily_revenue - daily_cost
            net_after_ads = net_before_ads - daily_ad_spend
            roas = (daily_revenue / daily_ad_spend) if daily_ad_spend > 0 else 0
            broas = (net_before_ads / daily_ad_spend) if daily_ad_spend > 0 else 0
            cost_percentage = (daily_cost / daily_revenue * 100) if daily_revenue > 0 else 0
            ad_percentage = (daily_ad_spend / daily_revenue * 100) if daily_revenue > 0 else 0
            margin_percentage = (net_after_ads / daily_revenue * 100) if daily_revenue > 0 else 0
            aov = (daily_revenue / daily_orders) if daily_orders > 0 else 0

            # Print daily row
            self.stdout.write(
                f"{current_date.strftime('%Y-%m-%d'):<12} "
                f"{daily_orders:>5} "
                f"${daily_revenue:>11,.2f} "
                f"${daily_cost:>11,.2f} "
                f"${daily_ad_spend:>11,.2f} "
                f"${net_before_ads:>11,.2f} "
                f"${net_after_ads:>11,.2f} "
                f"{roas:>5.1f}x "
                f"{broas:>5.1f}x "
                f"{cost_percentage:>5.1f}% "
                f"{ad_percentage:>5.1f}% "
                f"{margin_percentage:>6.1f}% "
                f"${aov:>9,.2f}"
            )

            # Update totals
            totals['orders'] += daily_orders
            totals['revenue'] += daily_revenue
            totals['cost'] += daily_cost
            totals['ad_spend'] += daily_ad_spend
            totals['net_before_ads'] = totals['revenue'] - totals['cost']
            totals['net_after_ads'] = totals['net_before_ads'] - totals['ad_spend']

            current_date += timedelta(days=1)

        # Calculate overall metrics
        self.stdout.write("=" * 160)
        overall_roas = (totals['revenue'] / totals['ad_spend']) if totals['ad_spend'] > 0 else 0
        overall_broas = (totals['net_before_ads'] / totals['ad_spend']) if totals['ad_spend'] > 0 else 0
        overall_cost_pct = (totals['cost'] / totals['revenue'] * 100) if totals['revenue'] > 0 else 0
        overall_ad_pct = (totals['ad_spend'] / totals['revenue'] * 100) if totals['revenue'] > 0 else 0
        overall_margin = (totals['net_after_ads'] / totals['revenue'] * 100) if totals['revenue'] > 0 else 0
        overall_aov = (totals['revenue'] / totals['orders']) if totals['orders'] > 0 else 0

        # Print totals in one line
        self.stdout.write("=" * 160)
        self.stdout.write(
            f"{'TOTAL':12} "
            f"{totals['orders']:>5} "
            f"${totals['revenue']:>11,.2f} "
            f"${totals['cost']:>11,.2f} "
            f"${totals['ad_spend']:>11,.2f} "
            f"${totals['net_before_ads']:>11,.2f} "
            f"${totals['net_after_ads']:>11,.2f} "
            f"{overall_roas:>5.1f}x "
            f"{overall_broas:>5.1f}x "
            f"{overall_cost_pct:>5.1f}% "
            f"{overall_ad_pct:>5.1f}% "
            f"{overall_margin:>6.1f}% "
            f"${overall_aov:>9,.2f}"
        ) 