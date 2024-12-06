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
        
        # Display daily spend vs budget per account
        print("\nDaily Spend vs Budget per Account (Last 7 Days):")
        print("=" * 120)
        dates = sorted(metrics['daily_metrics'].keys())
        accounts = sorted(set(acc for daily in metrics['daily_metrics'].values() for acc in daily.keys()))
        
        # Header
        print(f"{'Date':<12}", end="")
        for account in accounts:
            status = "🟢" if metrics['account_statuses'][account] == 1 else "🔴"
            print(f"{account} {status}".ljust(25), end="")
        print("Portfolio")
        
        # Subheader
        print(f"{'':12}", end="")
        for _ in accounts:
            print(f"{'Spend/Budget/Util%':25}", end="")
        print(f"{'Total S/B/U%'}")
        print("-" * 120)
        
        # Daily data
        for date in dates:
            print(f"{date:<12}", end="")
            daily_total_spend = 0
            daily_total_budget = 0
            
            for account in accounts:
                metrics_for_day = metrics['daily_metrics'][date].get(account, {})
                spend = metrics_for_day.get('spend', 0)
                budget = metrics_for_day.get('budget', 0)
                util = metrics_for_day.get('utilization', 0)
                
                print(f"${spend:>6.2f}/${budget:>6.2f}/{util:>5.1f}%", end="  ")
                
                daily_total_spend += spend
                daily_total_budget += budget
            
            # Print daily totals
            total_util = (daily_total_spend / daily_total_budget * 100) if daily_total_budget > 0 else 0
            print(f"${daily_total_spend:>7.2f}/${daily_total_budget:>7.2f}/{total_util:>5.1f}%")
        
        # Display current daily budgets
        print("\nCurrent Daily Budgets:")
        print("=" * 120)
        total_active_accounts = sum(1 for status in metrics['account_statuses'].values() if status == 1)
        print(f"Active Accounts: {total_active_accounts}")
        for account, budget in metrics['current_budgets'].items():
            status = "🟢 Active" if metrics['account_statuses'][account] == 1 else "🔴 Disabled"
            print(f"{account:<30} {status:<12} ${budget:>10.2f} AUD")
        print("-" * 120)
        print(f"{'Portfolio Total Budget (Active Accounts)':<44} ${metrics['portfolio_total_budget']:>10.2f} AUD")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    test_portfolio_metrics() 