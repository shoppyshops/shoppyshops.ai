import os
from typing import Optional, Dict, Any, List
import httpx

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