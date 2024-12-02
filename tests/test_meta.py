import pytest
from meta.meta import Meta
import os
import httpx
from unittest.mock import patch

def test_meta_init_missing_credentials():
    """Test that Meta raises ValueError when credentials are missing"""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="Missing required Meta credentials"):
            Meta()

def test_meta_init_success():
    """Test successful Meta initialization"""
    with patch.dict(os.environ, {
        'META_APP_ID': 'test_id',
        'META_APP_SECRET': 'test_secret',
        'META_ACCESS_TOKEN': 'test_token'
    }):
        meta = Meta()
        assert meta.app_id == 'test_id'
        assert meta.app_secret == 'test_secret'
        assert meta.access_token == 'test_token'

def test_validate_token_success():
    """Test successful token validation"""
    with patch.dict(os.environ, {
        'META_APP_ID': 'test_id',
        'META_APP_SECRET': 'test_secret',
        'META_ACCESS_TOKEN': 'test_token'
    }):
        meta = Meta()
        
        # Mock the httpx client response
        mock_response = {
            'data': {
                'is_valid': True,
                'app_id': 'test_id',
                'expires_at': 1234567890,
                'scopes': ['email', 'public_profile']
            }
        }
        
        with patch.object(meta.client, 'get') as mock_get:
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status = lambda: None
            
            result = meta.validate_token()
            
            assert result['is_valid'] is True
            assert result['app_id'] == 'test_id'
            
            # Verify the API was called correctly
            mock_get.assert_called_once()
            call_args = mock_get.call_args[0][0]
            assert 'debug_token' in call_args

def test_validate_token_invalid():
    """Test invalid token validation"""
    with patch.dict(os.environ, {
        'META_APP_ID': 'test_id',
        'META_APP_SECRET': 'test_secret',
        'META_ACCESS_TOKEN': 'test_token'
    }):
        meta = Meta()
        
        mock_response = {
            'data': {
                'is_valid': False,
                'error': {
                    'code': 190,
                    'message': 'Invalid OAuth access token.'
                }
            }
        }
        
        with patch.object(meta.client, 'get') as mock_get:
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status = lambda: None
            
            with pytest.raises(ValueError, match="Invalid access token"):
                meta.validate_token()

def test_get_ad_account_success():
    """Test successful ad account retrieval"""
    with patch.dict(os.environ, {
        'META_APP_ID': 'test_id',
        'META_APP_SECRET': 'test_secret',
        'META_ACCESS_TOKEN': 'test_token'
    }):
        meta = Meta()
        
        mock_response = {
            'id': 'act_123456',
            'name': 'Test Account',
            'account_status': 1,
            'currency': 'USD',
            'timezone_name': 'America/Los_Angeles'
        }
        
        with patch.object(meta.client, 'get') as mock_get:
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status = lambda: None
            
            result = meta.get_ad_account('act_123456')
            
            assert result['id'] == 'act_123456'
            assert result['name'] == 'Test Account'
            
            mock_get.assert_called_once()
            assert 'act_123456' in mock_get.call_args[0][0]

def test_list_ad_accounts_success():
    """Test successful ad accounts listing"""
    with patch.dict(os.environ, {
        'META_APP_ID': 'test_id',
        'META_APP_SECRET': 'test_secret',
        'META_ACCESS_TOKEN': 'test_token'
    }):
        meta = Meta()
        
        mock_response = {
            'data': [
                {
                    'id': 'act_123456',
                    'name': 'Test Account 1',
                    'account_status': 1
                },
                {
                    'id': 'act_789012',
                    'name': 'Test Account 2',
                    'account_status': 1
                }
            ]
        }
        
        with patch.object(meta.client, 'get') as mock_get:
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status = lambda: None
            
            result = meta.list_ad_accounts()
            
            assert len(result) == 2
            assert result[0]['id'] == 'act_123456'
            assert result[1]['name'] == 'Test Account 2'
            
            mock_get.assert_called_once()
            assert 'adaccounts' in mock_get.call_args[0][0]

def test_get_account_insights_success():
    """Test successful account insights retrieval"""
    with patch.dict(os.environ, {
        'META_APP_ID': 'test_id',
        'META_APP_SECRET': 'test_secret',
        'META_ACCESS_TOKEN': 'test_token'
    }):
        meta = Meta()
        
        mock_response = {
            'data': [{
                'spend': '1000.00',
                'impressions': '50000',
                'clicks': '2500',
                'reach': '40000',
                'account_currency': 'USD',
                'account_name': 'Test Account',
                'date_start': '2024-01-01',
                'date_stop': '2024-01-30'
            }]
        }
        
        with patch.object(meta.client, 'get') as mock_get:
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status = lambda: None
            
            result = meta.get_account_insights('act_123456')
            
            assert len(result) == 1
            assert result[0]['spend'] == '1000.00'
            assert result[0]['account_currency'] == 'USD'
            
            mock_get.assert_called_once()
            assert 'insights' in mock_get.call_args[0][0]

def test_get_account_spending_summary_success():
    """Test successful account spending summary retrieval"""
    with patch.dict(os.environ, {
        'META_APP_ID': 'test_id',
        'META_APP_SECRET': 'test_secret',
        'META_ACCESS_TOKEN': 'test_token'
    }):
        meta = Meta()
        
        mock_response = {
            'data': [
                {
                    'spend': '500.00',
                    'account_currency': 'USD',
                    'date_start': '2024-01-01',
                    'date_stop': '2024-01-01'
                },
                {
                    'spend': '600.00',
                    'account_currency': 'USD',
                    'date_start': '2024-01-02',
                    'date_stop': '2024-01-02'
                }
            ]
        }
        
        with patch.object(meta.client, 'get') as mock_get:
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status = lambda: None
            
            result = meta.get_account_spending_summary(
                'act_123456',
                '2024-01-01',
                '2024-01-02'
            )
            
            assert len(result) == 2
            assert float(result[0]['spend']) == 500.00
            assert float(result[1]['spend']) == 600.00
            
            mock_get.assert_called_once()
            assert 'insights' in mock_get.call_args[0][0]
