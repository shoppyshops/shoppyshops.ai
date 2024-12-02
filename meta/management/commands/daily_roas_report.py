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

        # Create date range for iteration
        date_range = [
            start_date + timedelta(days=x) 
            for x in range((end_date - start_date).days + 1)
        ]

        self.stdout.write(f"\nDaily Performance Report ({start_date} to {end_date})")
        self.stdout.write("=" * 200)
        
        # Header with adjusted widths
        self.stdout.write(
            f"{'Date':<12} "
            f"{'Ord':>4} "
            f"{'Unf':>4} "
            f"{'Revenue':>14} "
            f"{'Cost':>14} "
            f"{'Est Cost*':>14} "
            f"{'Ad Spend':>14} "
            f"{'Net Pre':>14} "
            f"{'Net Post':>14} "
            f"{'Est Post*':>14} "
            f"{'ROAS':>7} "
            f"{'BROAS':>7} "
            f"{'BROAS*':>7} "
            f"{'Cost%':>7} "
            f"{'Ad%':>7} "
            f"{'Margin%':>8} "
            f"{'AOV':>12} "
            f"{'AFC':>12}"
        )
        self.stdout.write("-" * 200)

        totals = {
            'orders': 0,
            'revenue': 0,
            'cost': 0,
            'ad_spend': 0,
            'net_before_ads': 0,
            'net_after_ads': 0
        }

        # Calculate historical average fulfillment cost
        historical_orders = EbayOrder.objects.filter(
            order_total__gt=0  # Only consider fulfilled orders
        ).aggregate(
            total_cost=Sum('order_total'),
            count=Count('id')
        )
        avg_fulfillment_cost = (
            historical_orders['total_cost'] / historical_orders['count']
            if historical_orders['count'] > 0 else 0
        )

        # Process each day
        current_date = start_date
        while current_date <= end_date:
            # Get orders and unfulfilled count
            daily_orders = ShopifyOrder.objects.filter(
                created_at__date=current_date
            ).count()

            unfulfilled_orders = ShopifyOrder.objects.filter(
                created_at__date=current_date,
                ebay_orders__isnull=True  # No linked eBay fulfillment
            ).count()

            # Actual costs from fulfilled orders
            daily_actual_cost = EbayOrder.objects.filter(
                shopify_order__created_at__date=current_date
            ).aggregate(
                total=Sum('order_total')
            )['total'] or 0

            # Estimated costs for unfulfilled orders
            daily_estimated_cost = unfulfilled_orders * avg_fulfillment_cost

            # Calculate AFC (Average Fulfillment Cost) for the day
            fulfilled_orders = daily_orders - unfulfilled_orders
            daily_afc = (
                daily_actual_cost / fulfilled_orders
                if fulfilled_orders > 0 else avg_fulfillment_cost
            )

            # Get daily metrics
            daily_revenue = ShopifyOrder.objects.filter(
                created_at__date=current_date
            ).aggregate(
                total=Sum('total_price')
            )['total'] or 0

            daily_ad_spend = MetaSpend.objects.filter(
                date=current_date
            ).aggregate(
                total=Sum('spend')
            )['total'] or 0

            # Calculate actual metrics
            net_before_ads = daily_revenue - daily_actual_cost
            net_after_ads = net_before_ads - daily_ad_spend
            roas = (daily_revenue / daily_ad_spend) if daily_ad_spend > 0 else 0
            broas = (net_before_ads / daily_ad_spend) if daily_ad_spend > 0 else 0

            # Calculate estimated metrics
            est_net_before_ads = daily_revenue - (daily_actual_cost + daily_estimated_cost)
            est_net_after_ads = est_net_before_ads - daily_ad_spend
            est_broas = (est_net_before_ads / daily_ad_spend) if daily_ad_spend > 0 else 0

            # Calculate percentages
            cost_percentage = (daily_actual_cost / daily_revenue * 100) if daily_revenue > 0 else 0
            ad_percentage = (daily_ad_spend / daily_revenue * 100) if daily_revenue > 0 else 0
            margin_percentage = (net_after_ads / daily_revenue * 100) if daily_revenue > 0 else 0
            aov = (daily_revenue / daily_orders) if daily_orders > 0 else 0

            # Print daily row
            self.stdout.write(
                f"{current_date.strftime('%Y-%m-%d'):<12} "
                f"{daily_orders:>4} "
                f"{unfulfilled_orders:>4} "
                f"${daily_revenue:>13,.2f} "
                f"${daily_actual_cost:>13,.2f} "
                f"${daily_estimated_cost:>13,.2f}* "
                f"${daily_ad_spend:>13,.2f} "
                f"${net_before_ads:>13,.2f} "
                f"${net_after_ads:>13,.2f} "
                f"${est_net_after_ads:>13,.2f}* "
                f"{roas:>6.1f}x "
                f"{broas:>6.1f}x "
                f"{est_broas:>6.1f}x* "
                f"{cost_percentage:>6.1f}% "
                f"{ad_percentage:>6.1f}% "
                f"{margin_percentage:>7.1f}% "
                f"${aov:>11,.2f} "
                f"${daily_afc:>11,.2f}"
            )

            # Update totals
            totals['orders'] += daily_orders
            totals['revenue'] += daily_revenue
            totals['cost'] += daily_actual_cost
            totals['ad_spend'] += daily_ad_spend
            totals['net_before_ads'] = totals['revenue'] - totals['cost']
            totals['net_after_ads'] = totals['net_before_ads'] - totals['ad_spend']

            current_date += timedelta(days=1)

        # Calculate overall metrics
        self.stdout.write("=" * 200)
        overall_roas = (totals['revenue'] / totals['ad_spend']) if totals['ad_spend'] > 0 else 0
        overall_broas = (totals['net_before_ads'] / totals['ad_spend']) if totals['ad_spend'] > 0 else 0
        overall_cost_pct = (totals['cost'] / totals['revenue'] * 100) if totals['revenue'] > 0 else 0
        overall_ad_pct = (totals['ad_spend'] / totals['revenue'] * 100) if totals['revenue'] > 0 else 0
        overall_margin = (totals['net_after_ads'] / totals['revenue'] * 100) if totals['revenue'] > 0 else 0
        overall_aov = (totals['revenue'] / totals['orders']) if totals['orders'] > 0 else 0

        # Calculate totals for estimates
        total_unfulfilled = sum(1 for date in date_range for order in ShopifyOrder.objects.filter(
            created_at__date=date,
            ebay_orders__isnull=True
        ))
        total_estimated_cost = total_unfulfilled * avg_fulfillment_cost
        total_est_net_before = totals['revenue'] - (totals['cost'] + total_estimated_cost)
        total_est_net_after = total_est_net_before - totals['ad_spend']
        total_est_broas = (total_est_net_before / totals['ad_spend']) if totals['ad_spend'] > 0 else 0
        total_afc = (totals['cost'] / (totals['orders'] - total_unfulfilled)) if (totals['orders'] - total_unfulfilled) > 0 else avg_fulfillment_cost

        # Print totals line with all metrics
        self.stdout.write(
            f"{'TOTAL':12} "
            f"{totals['orders']:>4} "
            f"{total_unfulfilled:>4} "
            f"${totals['revenue']:>13,.2f} "
            f"${totals['cost']:>13,.2f} "
            f"${total_estimated_cost:>13,.2f}* "
            f"${totals['ad_spend']:>13,.2f} "
            f"${totals['net_before_ads']:>13,.2f} "
            f"${totals['net_after_ads']:>13,.2f} "
            f"${total_est_net_after:>13,.2f}* "
            f"{overall_roas:>6.1f}x "
            f"{overall_broas:>6.1f}x "
            f"{total_est_broas:>6.1f}x* "
            f"{overall_cost_pct:>6.1f}% "
            f"{overall_ad_pct:>6.1f}% "
            f"{overall_margin:>7.1f}% "
            f"${overall_aov:>11,.2f} "
            f"${total_afc:>11,.2f}"
        ) 