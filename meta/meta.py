import os
from typing import Optional, Dict, Any, List
import httpx
from datetime import datetime, timedelta

class Meta:
    """
    A class to interact with Meta (Facebook) Marketing APIs.
    Handles authentication and basic API operations.
    """
    def __init__(self):
        self.app_id = os.getenv("META_APP_ID")
        self.app_secret = os.getenv("META_APP_SECRET")
        self.access_token = os.getenv("META_ACCESS_TOKEN")
        self.base_url = "https://graph.facebook.com/v18.0"  # Using latest stable version
        self.client = httpx.Client(timeout=30.0)  # Create a reusable client with 30s timeout
        
        if not all([self.app_id, self.app_secret, self.access_token]):
            raise ValueError("Missing required Meta credentials in environment variables")

    def validate_token(self) -> Dict[str, Any]:
        """
        Validates the access token using Meta's debug_token endpoint.
        
        Returns:
            Dict containing token debug information
        
        Raises:
            httpx.HTTPError: If the API request fails
            ValueError: If the token is invalid
        """
        params = {
            'input_token': self.access_token,
            'access_token': f"{self.app_id}|{self.app_secret}"  # Use app access token
        }
        
        response = self.client.get(
            f"{self.base_url}/debug_token",
            params=params
        )
        response.raise_for_status()
        
        data = response.json()
        if not data.get('data', {}).get('is_valid', False):
            raise ValueError("Invalid access token")
            
        return data['data']

    def get_ad_account(self, account_id: str) -> Dict[str, Any]:
        """
        Get details for a specific ad account.
        
        Args:
            account_id: The ID of the ad account (format: act_XXXXXX)
            
        Returns:
            Dict containing account details
            
        Raises:
            httpx.HTTPError: If the API request fails
        """
        response = self.client.get(
            f"{self.base_url}/{account_id}",
            params={'access_token': self.access_token}
        )
        response.raise_for_status()
        return response.json()

    def list_ad_accounts(self, user_id: str = 'me') -> List[Dict[str, Any]]:
        """
        List all ad accounts accessible to the authenticated user.
        
        Args:
            user_id: The user ID to get accounts for, defaults to 'me'
            
        Returns:
            List of dictionaries containing account details
            
        Raises:
            httpx.HTTPError: If the API request fails
        """
        response = self.client.get(
            f"{self.base_url}/{user_id}/adaccounts",
            params={
                'access_token': self.access_token,
                'fields': 'id,name,account_status,currency,timezone_name'
            }
        )
        response.raise_for_status()
        return response.json().get('data', [])

    def get_account_insights(
        self, 
        account_id: str,
        date_preset: str = 'last_30d',
        fields: List[str] = None
    ) -> Dict[str, Any]:
        """
        Get financial insights for a specific ad account.
        
        Args:
            account_id: The ID of the ad account (format: act_XXXXXX)
            date_preset: Predefined date range (e.g., 'last_30d', 'last_90d', 'lifetime')
            fields: List of fields to retrieve. Defaults to basic financial metrics
            
        Returns:
            Dict containing account insights data
            
        Raises:
            httpx.HTTPError: If the API request fails
        """
        if fields is None:
            fields = [
                'spend',
                'impressions',
                'clicks',
                'reach',
                'account_currency',
                'account_name',
                'date_start',
                'date_stop'
            ]

        response = self.client.get(
            f"{self.base_url}/{account_id}/insights",
            params={
                'access_token': self.access_token,
                'fields': ','.join(fields),
                'date_preset': date_preset,
                'level': 'account'
            }
        )
        response.raise_for_status()
        return response.json().get('data', [])

    def get_account_spending_summary(
        self,
        account_id: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        Get a summary of spending for an ad account within a specific date range.
        
        Args:
            account_id: The ID of the ad account (format: act_XXXXXX)
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Dict containing spending summary
            
        Raises:
            httpx.HTTPError: If the API request fails
        """
        response = self.client.get(
            f"{self.base_url}/{account_id}/insights",
            params={
                'access_token': self.access_token,
                'fields': 'spend,account_currency',
                'time_range': {
                    'since': start_date,
                    'until': end_date
                },
                'level': 'account',
                'time_increment': 1
            }
        )
        response.raise_for_status()
        return response.json().get('data', [])

    def get_daily_spending(
        self,
        account_id: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Get daily spending breakdown for an ad account.
        
        Args:
            account_id: The ID of the ad account
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        """
        response = self.client.get(
            f"{self.base_url}/{account_id}/insights",
            params={
                'access_token': self.access_token,
                'fields': 'spend,impressions,clicks,account_currency',
                'time_range': {'since': start_date, 'until': end_date},
                'time_increment': 1,  # Daily breakdown
                'level': 'account'
            }
        )
        response.raise_for_status()
        return response.json().get('data', [])

    def get_campaign_insights(
        self,
        account_id: str,
        date_preset: str = 'last_90d'
    ) -> List[Dict[str, Any]]:
        """
        Get insights broken down by campaign.
        """
        response = self.client.get(
            f"{self.base_url}/{account_id}/insights",
            params={
                'access_token': self.access_token,
                'fields': 'campaign_name,spend,impressions,clicks,reach',
                'date_preset': date_preset,
                'level': 'campaign'  # Break down by campaign
            }
        )
        response.raise_for_status()
        return response.json().get('data', [])

    def get_campaign_budgets(
        self,
        account_id: str,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get budget settings for all campaigns in an account.
        
        Args:
            account_id: The ID of the ad account (format: act_XXXXXX)
            include_inactive: Whether to include non-active campaigns
            
        Returns:
            List of campaign budget data containing:
            - id
            - name
            - status
            - daily_budget
            - lifetime_budget
            - spend_cap
            - effective_status
            
        Raises:
            httpx.HTTPError: If the API request fails
        """
        fields = [
            'id',
            'name',
            'objective',
            'daily_budget',
            'lifetime_budget',
            'spend_cap',
            'status',
            'effective_status',
            'created_time',
            'updated_time'
        ]
        
        params = {
            'access_token': self.access_token,
            'fields': ','.join(fields)
        }
        
        response = self.client.get(
            f"{self.base_url}/act_{account_id.replace('act_', '')}/campaigns",
            params=params
        )
        response.raise_for_status()
        return response.json().get('data', [])

    def get_business_ad_accounts(
        self,
        business_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all ad accounts owned by a specific business.
        
        Args:
            business_id: The ID of the business/portfolio
            
        Returns:
            List of ad accounts with their details
            
        Raises:
            httpx.HTTPError: If the API request fails
        """
        response = self.client.get(
            f"{self.base_url}/{business_id}/owned_ad_accounts",
            params={
                'access_token': self.access_token,
                'fields': 'id,name,account_status,currency,timezone_name,amount_spent,balance'
            }
        )
        response.raise_for_status()
        return response.json().get('data', [])

    def get_business_spending_summary(
        self,
        business_id: str,
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, Any]:
        """
        Get aggregated spending data for all ad accounts under a business.
        
        Args:
            business_id: The ID of the business/portfolio
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            
        Returns:
            Dict containing:
            - total_spend
            - account_count
            - active_account_count
            - accounts: List of account summaries
            
        Raises:
            httpx.HTTPError: If the API request fails
        """
        accounts = self.get_business_ad_accounts(business_id)
        
        # Initialize summary
        summary = {
            'total_spend': 0.0,
            'account_count': len(accounts),
            'active_account_count': 0,
            'accounts': []
        }
        
        for account in accounts:
            account_id = account['id']
            
            # Get account insights
            insights = self.get_account_insights(
                account_id,
                date_preset='last_90d' if not start_date else None,
                fields=['spend', 'account_currency']
            )
            
            account_summary = {
                'id': account_id,
                'name': account['name'],
                'status': account['account_status'],
                'currency': account['currency'],
                'spend': sum(float(insight['spend']) for insight in insights) if insights else 0.0
            }
            
            if account['account_status'] == 1:  # Active account
                summary['active_account_count'] += 1
            
            summary['total_spend'] += account_summary['spend']
            summary['accounts'].append(account_summary)
        
        return summary

    def get_portfolio_daily_metrics(
        self,
        business_id: str,
        days: int = 7,
        include_disabled: bool = False
    ) -> Dict[str, Any]:
        """
        Get daily spend and budget data for all accounts in a business portfolio.
        
        Args:
            business_id: The ID of the business/portfolio
            days: Number of days to look back
            include_disabled: Whether to include disabled accounts
            
        Returns:
            Dict containing:
            - daily_metrics: Dict of dates with spend and budget per account
              Format: {
                date: {
                    account_name: {
                        'spend': float,
                        'budget': float,
                        'utilization': float  # spend as percentage of budget
                    }
                }
              }
            - current_budgets: Dict of current daily budgets per account
            - portfolio_total_budget: Total current daily budget across portfolio (active accounts only)
            - account_statuses: Dict of account statuses
        """
        accounts = self.get_business_ad_accounts(business_id)
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        result = {
            'daily_metrics': {},
            'current_budgets': {},
            'portfolio_total_budget': 0.0,
            'account_statuses': {}
        }
        
        for account in accounts:
            account_id = account['id']
            account_name = account['name']
            account_status = account['account_status']
            
            result['account_statuses'][account_name] = account_status
            
            if include_disabled or account_status == 1:
                # Get daily spending
                daily_spend = self.get_daily_spending(account_id, start_date, end_date)
                
                # Get campaign budgets for each day
                campaigns = self.get_campaign_budgets(account_id)
                current_account_budget = 0.0
                
                for campaign in campaigns:
                    if campaign.get('effective_status') == 'ACTIVE':
                        daily_budget = float(campaign.get('daily_budget', 0)) / 100
                        current_account_budget += daily_budget
                
                # Record daily metrics
                for day in daily_spend:
                    date = day['date_start']
                    if date not in result['daily_metrics']:
                        result['daily_metrics'][date] = {}
                    
                    spend = float(day['spend'])
                    result['daily_metrics'][date][account_name] = {
                        'spend': spend,
                        'budget': current_account_budget,
                        'utilization': (spend / current_account_budget * 100) if current_account_budget > 0 else 0
                    }
                
                result['current_budgets'][account_name] = current_account_budget
                
                if account_status == 1:
                    result['portfolio_total_budget'] += current_account_budget
        
        return result

    def get_portfolio_roas_breakdown(
        self,
        business_id: str,
        start_date: str = None,
        end_date: str = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get ROAS breakdown for all levels across the portfolio.
        
        Args:
            business_id: The ID of the business/portfolio
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            days: Number of days to look back (used if start_date/end_date not provided)
        """
        if not start_date or not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days-1)).strftime('%Y-%m-%d')
        
        result = {
            'portfolio_summary': {
                'total_spend': 0,
                'total_revenue': 0,
                'total_purchases': 0,
                'portfolio_roas': 0,
                'total_impressions': 0,
                'total_clicks': 0,
                'average_ctr': 0,
                'average_cpc': 0
            },
            'accounts': []
        }
        
        accounts = self.get_business_ad_accounts(business_id)
        
        for account in accounts:
            if account['account_status'] != 1:  # Skip inactive accounts
                continue
            
            account_id = account['id']
            account_metrics = {
                'account_id': account_id,
                'account_name': account['name'],
                'metrics': {
                    'spend': 0,
                    'revenue': 0,
                    'purchases': 0,
                    'roas': 0,
                    'impressions': 0,
                    'clicks': 0,
                    'ctr': 0,
                    'cpc': 0
                },
                'campaigns': []
            }
            
            # Get account level insights
            try:
                insights_fields = [
                    'spend',
                    'actions',
                    'action_values',
                    'impressions',
                    'clicks',
                    'conversion_values',
                    'conversions'
                ]
                
                # Use time_range instead of date_preset
                params = {
                    'access_token': self.access_token,
                    'fields': ','.join(insights_fields),
                    'time_range': {
                        'since': start_date,
                        'until': end_date
                    }
                }
                
                response = self.client.get(
                    f"{self.base_url}/{account_id}/insights",
                    params=params
                )
                response.raise_for_status()
                account_insights = response.json().get('data', [])
                
                if account_insights:
                    insight = account_insights[0]
                    spend = float(insight.get('spend', 0))
                    impressions = int(insight.get('impressions', 0))
                    clicks = int(insight.get('clicks', 0))
                    
                    # Process actions to get purchases and revenue
                    actions = insight.get('actions', [])
                    action_values = insight.get('action_values', [])
                    purchases = 0
                    revenue = 0.0
                    
                    # Look for purchase data in actions
                    for action in actions:
                        if action.get('action_type') in ['purchase', 'offsite_conversion.purchase']:
                            purchases += int(action.get('value', 0))
                    
                    # Look for revenue data in action_values
                    for value in action_values:
                        if value.get('action_type') in ['purchase', 'offsite_conversion.purchase']:
                            revenue += float(value.get('value', 0))
                    
                    # Fallback to conversion_values if available
                    if revenue == 0 and insight.get('conversion_values'):
                        revenue = float(insight.get('conversion_values', 0))
                    
                    metrics = {
                        'spend': spend,
                        'revenue': revenue,
                        'purchases': purchases,
                        'roas': revenue / spend if spend > 0 else 0,
                        'impressions': impressions,
                        'clicks': clicks,
                        'ctr': clicks / impressions * 100 if impressions > 0 else 0,
                        'cpc': spend / clicks if clicks > 0 else 0
                    }
                    
                    account_metrics['metrics'] = metrics
                    
                    # Add to portfolio totals
                    result['portfolio_summary']['total_spend'] += spend
                    result['portfolio_summary']['total_revenue'] += revenue
                    result['portfolio_summary']['total_purchases'] += purchases
                    result['portfolio_summary']['total_impressions'] += impressions
                    result['portfolio_summary']['total_clicks'] += clicks
                
                # Get campaign level data
                campaigns_response = self.client.get(
                    f"{self.base_url}/{account_id}/campaigns",
                    params={
                        'access_token': self.access_token,
                        'fields': 'id,name,status',
                        'effective_status': ['ACTIVE', 'PAUSED']
                    }
                )
                campaigns = campaigns_response.json().get('data', [])
                
                for campaign in campaigns:
                    campaign_id = campaign['id']
                    campaign_metrics = {
                        'campaign_id': campaign_id,
                        'campaign_name': campaign['name'],
                        'status': campaign['status'],
                        'metrics': {}
                    }
                    
                    # Get campaign insights
                    try:
                        campaign_insights = self.client.get(
                            f"{self.base_url}/{campaign_id}/insights",
                            params={
                                'access_token': self.access_token,
                                'fields': ','.join(insights_fields),
                                'time_range': {'since': start_date, 'until': end_date}
                            }
                        ).json().get('data', [])
                        
                        if campaign_insights:
                            campaign_metrics['metrics'] = self._process_insights_with_actions(campaign_insights[0])
                    except Exception as e:
                        print(f"Warning: Could not get insights for campaign {campaign_id}: {str(e)}")
                    
                    account_metrics['campaigns'].append(campaign_metrics)
                
            except Exception as e:
                print(f"Warning: Could not get complete data for account {account_id}: {str(e)}")
            
            result['accounts'].append(account_metrics)
        
        # Calculate portfolio level metrics
        if result['portfolio_summary']['total_spend'] > 0:
            result['portfolio_summary']['portfolio_roas'] = (
                result['portfolio_summary']['total_revenue'] / 
                result['portfolio_summary']['total_spend']
            )
            result['portfolio_summary']['average_ctr'] = (
                result['portfolio_summary']['total_clicks'] / 
                result['portfolio_summary']['total_impressions'] * 100
                if result['portfolio_summary']['total_impressions'] > 0 else 0
            )
            result['portfolio_summary']['average_cpc'] = (
                result['portfolio_summary']['total_spend'] / 
                result['portfolio_summary']['total_clicks']
                if result['portfolio_summary']['total_clicks'] > 0 else 0
            )
        
        return result

    def _process_insights_with_actions(self, insights: Dict[str, Any]) -> Dict[str, Any]:
        """Helper method to process insights data including actions"""
        spend = float(insights.get('spend', 0))
        impressions = int(insights.get('impressions', 0))
        clicks = int(insights.get('clicks', 0))
        
        # Process actions to get purchases and revenue
        actions = insights.get('actions', [])
        action_values = insights.get('action_values', [])
        purchases = 0
        revenue = 0.0
        
        # Look for purchase data in actions
        for action in actions:
            if action.get('action_type') in ['purchase', 'offsite_conversion.purchase']:
                purchases += int(action.get('value', 0))
        
        # Look for revenue data in action_values
        for value in action_values:
            if value.get('action_type') in ['purchase', 'offsite_conversion.purchase']:
                revenue += float(value.get('value', 0))
                
        # Fallback to conversion_values if available
        if revenue == 0 and insights.get('conversion_values'):
            revenue = float(insights.get('conversion_values', 0))
        
        return {
            'spend': spend,
            'revenue': revenue,
            'purchases': purchases,
            'roas': revenue / spend if spend > 0 else 0,
            'impressions': impressions,
            'clicks': clicks,
            'ctr': clicks / impressions * 100 if impressions > 0 else 0,
            'cpc': spend / clicks if clicks > 0 else 0
        }