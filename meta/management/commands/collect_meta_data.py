from django.core.management.base import BaseCommand
from django.db import transaction
from meta.models import MetaPortfolio, MetaAdAccount, MetaCampaign, MetaAdSet, MetaSpend
from meta import Meta
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

class Command(BaseCommand):
    help = 'Collects Meta Ads data and stores in database'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7)
        parser.add_argument('--start', type=str, help='YYYY-MM-DD')
        parser.add_argument('--end', type=str, help='YYYY-MM-DD')

    def handle(self, *args, **options):
        # Load environment variables
        load_dotenv()
        
        # Debug: Print environment variables
        self.stdout.write("\nEnvironment variables:")
        self.stdout.write(f"META_APP_ID: {os.getenv('META_APP_ID')}")
        self.stdout.write(f"META_APP_SECRET: {os.getenv('META_APP_SECRET')}")
        self.stdout.write(f"META_ACCESS_TOKEN: {os.getenv('META_ACCESS_TOKEN')}")

        meta = Meta()
        
        # Calculate date range
        if options['start'] and options['end']:
            start_date = options['start']
            end_date = options['end']
        else:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=options['days']-1)).strftime('%Y-%m-%d')

        # Step 1: Get/Create Portfolio
        PORTFOLIO_ID = "243895028000703"  # Local Aussie Store Delta
        portfolio, _ = MetaPortfolio.objects.get_or_create(
            portfolio_id=PORTFOLIO_ID,
            defaults={'name': 'Local Aussie Store Delta'}
        )
        self.stdout.write(f"Portfolio: {portfolio}")

        # Step 2: Get/Update Ad Accounts
        accounts = meta.get_business_ad_accounts(PORTFOLIO_ID)
        for acc_data in accounts:
            account, _ = MetaAdAccount.objects.update_or_create(
                account_id=acc_data['id'],
                defaults={
                    'portfolio': portfolio,
                    'name': acc_data['name'],
                    'status': acc_data['account_status'],
                    'currency': acc_data['currency'],
                    'timezone': acc_data['timezone_name']
                }
            )
            self.stdout.write(f"Account: {account}")

            # Step 3: Get/Update Campaigns
            campaigns_response = meta.client.get(
                f"{meta.base_url}/{account.account_id}/campaigns",
                params={
                    'access_token': meta.access_token,
                    'fields': 'id,name,status,daily_budget,objective,budget_optimization_type'
                }
            )
            campaigns = campaigns_response.json().get('data', [])
            
            for camp_data in campaigns:
                campaign, _ = MetaCampaign.objects.update_or_create(
                    campaign_id=camp_data['id'],
                    defaults={
                        'account': account,
                        'name': camp_data['name'],
                        'status': camp_data['status'],
                        'daily_budget': float(camp_data.get('daily_budget', 0)) / 100,
                        'budget_optimization': camp_data.get('budget_optimization_type') == 'CAMPAIGN_BUDGET_OPTIMIZATION',
                        'objective': camp_data.get('objective', 'UNKNOWN')
                    }
                )
                self.stdout.write(f"Campaign: {campaign}")

                # Step 4: Get/Update Ad Sets
                adsets_response = meta.client.get(
                    f"{meta.base_url}/{campaign.campaign_id}/adsets",
                    params={
                        'access_token': meta.access_token,
                        'fields': 'id,name,status,targeting'
                    }
                )
                adsets = adsets_response.json().get('data', [])
                
                for adset_data in adsets:
                    adset, _ = MetaAdSet.objects.update_or_create(
                        adset_id=adset_data['id'],
                        defaults={
                            'campaign': campaign,
                            'name': adset_data['name'],
                            'status': adset_data['status'],
                            'targeting': adset_data.get('targeting')
                        }
                    )
                    self.stdout.write(f"Ad Set: {adset}")

                    # Step 5: Get/Store Daily Spend
                    insights_response = meta.client.get(
                        f"{meta.base_url}/{adset.adset_id}/insights",
                        params={
                            'access_token': meta.access_token,
                            'fields': 'spend,impressions,clicks,ctr,cpc,actions',
                            'time_range': {'since': start_date, 'until': end_date},
                            'time_increment': 1
                        }
                    )
                    insights = insights_response.json().get('data', [])
                    
                    for insight in insights:
                        # Get conversion count from actions
                        conversions = 0
                        for action in insight.get('actions', []):
                            if action.get('action_type') in ['purchase', 'offsite_conversion.purchase']:
                                conversions += int(action.get('value', 0))
                        
                        # Get basic metrics with fallbacks
                        spend = float(insight.get('spend', 0))
                        impressions = int(insight.get('impressions', 0))
                        clicks = int(insight.get('clicks', 0))
                        
                        # Calculate CTR and CPC if not provided
                        ctr = float(insight.get('ctr', 0))
                        if ctr == 0 and impressions > 0:
                            ctr = (clicks / impressions) * 100
                            
                        cpc = float(insight.get('cpc', 0))
                        if cpc == 0 and clicks > 0:
                            cpc = spend / clicks
                        
                        MetaSpend.objects.update_or_create(
                            date=insight['date_start'],
                            campaign=campaign,
                            adset=adset,
                            defaults={
                                'spend': spend,
                                'impressions': impressions,
                                'clicks': clicks,
                                'ctr': ctr,
                                'cpc': cpc,
                                'conversions': conversions
                            }
                        )
                        self.stdout.write(
                            f"Spend recorded for {adset.name} on {insight['date_start']}: "
                            f"${spend:.2f}, {impressions} impr, {clicks} clicks"
                        ) 