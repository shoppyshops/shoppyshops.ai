from dotenv import load_dotenv
from meta import Meta
import json
import os
from datetime import datetime, timedelta

def test_real_connection():
    try:
        # Load environment variables from .env file
        load_dotenv()
        
        # Print environment variables for debugging (optional)
        print("\nEnvironment variables:")
        print(f"META_APP_ID: {os.getenv('META_APP_ID')}")
        print(f"META_APP_SECRET: {os.getenv('META_APP_SECRET')}")
        print(f"META_ACCESS_TOKEN: {os.getenv('META_ACCESS_TOKEN')}")
        
        # Initialize Meta client
        meta = Meta()
        
        # Test token validation
        token_info = meta.validate_token()
        print("\nToken validation successful:")
        print(json.dumps(token_info, indent=2))
        
        # Test listing ad accounts
        accounts = meta.list_ad_accounts()
        print("\nFound ad accounts:")
        print(json.dumps(accounts, indent=2))
        
        if accounts:
            active_account = next(
                (acc for acc in accounts 
                 if acc['account_status'] == 1 and 'Aussie Store' in acc['name']),
                accounts[0]
            )
            account_id = active_account['id']
            
            # Get insights with more specific parameters
            insights = meta.get_account_insights(
                account_id,
                date_preset='last_90d',
                fields=[
                    'spend',
                    'impressions',
                    'clicks',
                    'reach',
                    'cpc',
                    'cpm',
                    'account_currency',
                    'account_name',
                    'date_start',
                    'date_stop'
                ]
            )
            print(f"\nInsights for account {active_account['name']} ({account_id}):")
            print(json.dumps(insights, indent=2))
            
            # Get daily spending for last 7 days
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            daily_spend = meta.get_daily_spending(account_id, start_date, end_date)
            print(f"\nDaily spending for last 7 days:")
            print(json.dumps(daily_spend, indent=2))
            
            # Get campaign insights
            campaign_insights = meta.get_campaign_insights(account_id)
            print(f"\nCampaign insights for last 90 days:")
            print(json.dumps(campaign_insights, indent=2))
            
            # Get campaign budgets
            print(f"\nCampaign budgets for account {active_account['name']}:")
            campaign_budgets = meta.get_campaign_budgets(account_id)
            
            # Format the budget data for better readability
            for campaign in campaign_budgets:
                print("\nCampaign:", campaign.get('name'))
                print("Status:", campaign.get('effective_status', 'Unknown'))
                print("Objective:", campaign.get('objective', 'Unknown'))
                if campaign.get('daily_budget'):
                    print("Daily Budget:", f"{float(campaign.get('daily_budget'))/100:.2f} {active_account['currency']}")
                if campaign.get('lifetime_budget'):
                    print("Lifetime Budget:", f"{float(campaign.get('lifetime_budget'))/100:.2f} {active_account['currency']}")
                if campaign.get('spend_cap'):
                    print("Spend Cap:", f"{float(campaign.get('spend_cap'))/100:.2f} {active_account['currency']}")
                print("Created:", campaign.get('created_time', 'Unknown'))
                print("Last Updated:", campaign.get('updated_time', 'Unknown'))
            
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    test_real_connection() 