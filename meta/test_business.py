from dotenv import load_dotenv
from meta import Meta
import json
from datetime import datetime, timedelta

def test_business_accounts():
    try:
        load_dotenv()
        meta = Meta()
        
        BUSINESS_ID = "243895028000703"  # Local Aussie Store Delta
        
        # Get all accounts under the business
        print("\nFetching ad accounts for Local Aussie Store Delta...")
        accounts = meta.get_business_ad_accounts(BUSINESS_ID)
        print(f"\nFound {len(accounts)} ad accounts:")
        print(json.dumps(accounts, indent=2))
        
        # Get spending summary
        print("\nFetching spending summary...")
        summary = meta.get_business_spending_summary(BUSINESS_ID)
        
        print(f"\nBusiness Spending Summary:")
        print(f"Total Accounts: {summary['account_count']}")
        print(f"Active Accounts: {summary['active_account_count']}")
        print(f"Total Spend: ${summary['total_spend']:.2f}")
        
        print("\nPer Account Breakdown:")
        for account in summary['accounts']:
            print(f"\nAccount: {account['name']}")
            print(f"Status: {'Active' if account['status'] == 1 else 'Inactive'}")
            print(f"Spend: ${account['spend']:.2f} {account['currency']}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    test_business_accounts() 