from dotenv import load_dotenv
from meta import Meta
import json
from datetime import datetime, timedelta
import argparse

def format_currency(amount: float) -> str:
    return f"${amount:,.2f}"

def format_metric(value: float, suffix: str = "") -> str:
    return f"{value:,.2f}{suffix}"

def parse_date(date_str: str) -> datetime:
    """Parse date string in YYYY-MM-DD format"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")

def test_portfolio_roas(start_date: str = None, end_date: str = None, days: int = 7):
    try:
        load_dotenv()
        meta = Meta()
        
        BUSINESS_ID = "243895028000703"  # Local Aussie Store Delta
        
        # Calculate date range
        if start_date and end_date:
            date_range = f"{start_date} to {end_date}"
            days = (parse_date(end_date) - parse_date(start_date)).days + 1
        else:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days-1)).strftime('%Y-%m-%d')
            if days == 1:
                date_range = f"{end_date} (Today)"
            else:
                date_range = f"{start_date} to {end_date}"
        
        print(f"\nFetching ROAS breakdown for {date_range}...")
        metrics = meta.get_portfolio_roas_breakdown(
            BUSINESS_ID,
            start_date=start_date,
            end_date=end_date
        )
        
        # Portfolio Summary
        print(f"\nPortfolio Summary for {date_range}")
        print("=" * 120)
        summary = metrics['portfolio_summary']
        print(f"{'Metric':<20} {'Value':<20} {'Per Day':<20}")
        print("-" * 60)
        print(f"{'Total Spend':<20} {format_currency(summary['total_spend']):<20} {format_currency(summary['total_spend']/days):<20}")
        print(f"{'Total Revenue':<20} {format_currency(summary['total_revenue']):<20} {format_currency(summary['total_revenue']/days):<20}")
        print(f"{'ROAS':<20} {format_metric(summary['portfolio_roas'], 'x'):<20}")
        print(f"{'Purchases':<20} {summary['total_purchases']:<20} {format_metric(summary['total_purchases']/days):<20}")
        print(f"{'Avg Order Value':<20} {format_currency(summary['total_revenue']/summary['total_purchases'] if summary['total_purchases'] > 0 else 0):<20}")
        print(f"{'CTR':<20} {format_metric(summary['average_ctr'], '%'):<20}")
        print(f"{'CPC':<20} {format_currency(summary['average_cpc']):<20}")
        
        # Account Level Breakdown
        for account in metrics['accounts']:
            print(f"\nAccount: {account['account_name']}")
            print("-" * 120)
            m = account['metrics']
            daily_spend = m['spend'] / days
            daily_revenue = m['revenue'] / days
            aov = m['revenue'] / m['purchases'] if m['purchases'] > 0 else 0
            
            print(f"{'Metric':<15} {'Total':<15} {'Daily Avg':<15} {'Share of Portfolio':<15}")
            print(f"{'Spend':<15} {format_currency(m['spend']):<15} {format_currency(daily_spend):<15} {format_metric(m['spend']/summary['total_spend']*100 if summary['total_spend'] > 0 else 0, '%'):<15}")
            print(f"{'Revenue':<15} {format_currency(m['revenue']):<15} {format_currency(daily_revenue):<15} {format_metric(m['revenue']/summary['total_revenue']*100 if summary['total_revenue'] > 0 else 0, '%'):<15}")
            print(f"{'ROAS':<15} {format_metric(m['roas'], 'x'):<15}")
            print(f"{'Purchases':<15} {m['purchases']:<15} {format_metric(m['purchases']/days):<15} {format_metric(m['purchases']/summary['total_purchases']*100 if summary['total_purchases'] > 0 else 0, '%'):<15}")
            print(f"{'AOV':<15} {format_currency(aov):<15}")
            print(f"{'CTR':<15} {format_metric(m['ctr'], '%'):<15}")
            print(f"{'CPC':<15} {format_currency(m['cpc']):<15}")
            
            # Campaign Level
            if account['campaigns']:
                print("\n  Campaigns:")
                for campaign in account['campaigns']:
                    if campaign['metrics']:
                        cm = campaign['metrics']
                        print(f"\n  {campaign['campaign_name']} ({campaign['status']})")
                        print(f"  {'Spend:':<10} {format_currency(cm['spend']):<15} {'Revenue:':<10} {format_currency(cm['revenue']):<15} {'ROAS:':<10} {format_metric(cm['roas'], 'x'):<15}")
                        print(f"  {'CTR:':<10} {format_metric(cm['ctr'], '%'):<15} {'CPC:':<10} {format_currency(cm['cpc']):<15} {'Purchases:':<10} {cm['purchases']}")

    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate Meta Ads ROAS report')
    parser.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, default=7, help='Number of days to look back (default: 7)')
    
    args = parser.parse_args()
    
    if bool(args.start) != bool(args.end):
        parser.error('Both --start and --end must be provided together')
    
    test_portfolio_roas(
        start_date=args.start,
        end_date=args.end,
        days=args.days
    ) 