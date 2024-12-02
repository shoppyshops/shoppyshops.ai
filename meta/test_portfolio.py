from dotenv import load_dotenv
from meta import Meta
import json
from datetime import datetime, timedelta

def test_portfolio_metrics():
    try:
        load_dotenv()
        meta = Meta()
        
        BUSINESS_ID = "243895028000703"  # Local Aussie Store Delta
        
        print("\nFetching portfolio metrics...")
        metrics = meta.get_portfolio_daily_metrics(BUSINESS_ID, include_disabled=True)
        
        # Display daily spend per account
        print("\nDaily Spend per Account (Last 7 Days):")
        print("=" * 100)
        dates = sorted(metrics['daily_spend'].keys())
        accounts = sorted(set(acc for daily in metrics['daily_spend'].values() for acc in daily.keys()))
        
        # Header
        print(f"{'Date':<12}", end="")
        for account in accounts:
            status = "🟢" if metrics['account_statuses'][account] == 1 else "🔴"
            print(f"{account} {status}".ljust(20), end="")
        print("Daily Total")
        
        # Daily data
        for date in dates:
            print(f"{date:<12}", end="")
            daily_total = 0
            for account in accounts:
                spend = metrics['daily_spend'][date].get(account, 0)
                daily_total += spend
                print(f"${spend:>19.2f}", end="")
            print(f"${daily_total:>19.2f}")
        
        # Display current daily budgets
        print("\nCurrent Daily Budgets:")
        print("=" * 100)
        total_active_accounts = sum(1 for status in metrics['account_statuses'].values() if status == 1)
        print(f"Active Accounts: {total_active_accounts}")
        for account, budget in metrics['current_budgets'].items():
            status = "🟢 Active" if metrics['account_statuses'][account] == 1 else "🔴 Disabled"
            print(f"{account:<30} {status:<12} ${budget:>10.2f} AUD")
        print("-" * 100)
        print(f"{'Portfolio Total Budget (Active Accounts)':<44} ${metrics['portfolio_total_budget']:>10.2f} AUD")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    test_portfolio_metrics() 