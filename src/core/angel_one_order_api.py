"""
Angel One Order API
Uses user-specific credentials from database for order placement
Each user has their own Angel One account credentials
"""

import os
import asyncio
import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class AngelOneOrderAPI:
    """
    User-specific Angel One Order API
    Uses user credentials from database for:
    - Order placement
    - Order status
    - Portfolio positions
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.user_credentials = None
        self.access_token = None
        self.is_connected = False
        
        logger.info(f"🔐 Angel One Order API initialized for user: {user_id}")
    
    async def connect_with_user_credentials(self, credentials: Dict[str, str]) -> bool:
        """Connect to Angel One with user-specific credentials"""
        
        self.user_credentials = credentials
        api_key = credentials.get('api_key')
        secret_key = credentials.get('secret_key')
        client_id = credentials.get('client_id')
        pin = credentials.get('pin')
        
        if not all([api_key, secret_key, client_id, pin]):
            logger.error(f"❌ Incomplete credentials for user {self.user_id}")
            return False
        
        try:
            login_url = "https://smartapi.angelbroking.com/rest/auth/angelbroking/user/v1/loginByPassword"
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-UserType': 'USER',
                'X-SourceID': 'WEB',
                'X-ClientLocalIP': '127.0.0.1',
                'X-ClientPublicIP': '127.0.0.1',
                'X-MACAddress': '00:00:00:00:00:00',
                'X-PrivateKey': api_key
            }
            
            payload = {
                "clientcode": client_id,
                "password": pin
            }
            
            logger.info(f"🔑 Connecting to Angel One for user {self.user_id}...")
            response = requests.post(login_url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') and data.get('data'):
                    self.access_token = data['data'].get('jwtToken')
                    
                    if self.access_token:
                        self.is_connected = True
                        logger.info(f"✅ User {self.user_id} connected to Angel One successfully")
                        return True
                    
                logger.error(f"❌ Invalid response for user {self.user_id}: {data}")
                return False
            else:
                logger.error(f"❌ Login failed for user {self.user_id}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error connecting user {self.user_id} to Angel One: {e}")
            return False
    
    async def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Place an order for the user"""
        
        if not self.is_connected:
            logger.error(f"❌ User {self.user_id} not connected - cannot place order")
            return {
                'status': 'error',
                'message': 'User not connected to Angel One',
                'order_id': None
            }
        
        try:
            order_url = "https://smartapi.angelbroking.com/rest/secure/angelbroking/order/v1/placeOrder"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-UserType': 'USER',
                'X-SourceID': 'WEB',
                'X-ClientLocalIP': '127.0.0.1',
                'X-ClientPublicIP': '127.0.0.1',
                'X-MACAddress': '00:00:00:00:00:00',
                'X-PrivateKey': self.user_credentials['api_key']
            }
            
            # Convert order data to Angel One format
            angel_order = {
                "variety": "NORMAL",
                "tradingsymbol": order_data['symbol'],
                "symboltoken": str(hash(order_data['symbol']) % 100000),
                "transactiontype": order_data['side'],  # BUY or SELL
                "exchange": "NSE",
                "ordertype": order_data.get('order_type', 'MARKET'),
                "producttype": order_data.get('product_type', 'INTRADAY'),
                "duration": "DAY",
                "price": str(order_data.get('price', 0)),
                "squareoff": "0",
                "stoploss": "0",
                "quantity": str(order_data['quantity'])
            }
            
            logger.info(f"🔥 PLACING LIVE ORDER for user {self.user_id}: {order_data['side']} {order_data['quantity']} {order_data['symbol']}")
            
            response = requests.post(order_url, json=angel_order, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status'):
                    order_id = data.get('data', {}).get('orderid')
                    logger.info(f"✅ Order placed successfully for user {self.user_id}: Order ID {order_id}")
                    
                    return {
                        'status': 'success',
                        'order_id': order_id,
                        'message': 'Order placed successfully',
                        'timestamp': datetime.now().isoformat(),
                        'user_id': self.user_id
                    }
                else:
                    error_msg = data.get('message', 'Unknown error')
                    logger.error(f"❌ Order placement failed for user {self.user_id}: {error_msg}")
                    
                    return {
                        'status': 'error',
                        'message': error_msg,
                        'order_id': None
                    }
            else:
                logger.error(f"❌ Order API failed for user {self.user_id}: {response.status_code} - {response.text}")
                return {
                    'status': 'error',
                    'message': f'API error: {response.status_code}',
                    'order_id': None
                }
                
        except Exception as e:
            logger.error(f"❌ Error placing order for user {self.user_id}: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'order_id': None
            }

# User order API cache
_user_order_apis: Dict[str, AngelOneOrderAPI] = {}

def get_user_order_api(user_id: str) -> AngelOneOrderAPI:
    """Get order API instance for a specific user"""
    global _user_order_apis
    
    if user_id not in _user_order_apis:
        _user_order_apis[user_id] = AngelOneOrderAPI(user_id)
    
    return _user_order_apis[user_id]

async def place_user_order(user_id: str, user_credentials: Dict[str, str], order_data: Dict[str, Any]) -> Dict[str, Any]:
    """Place an order for a specific user"""
    
    # Get user's order API
    order_api = get_user_order_api(user_id)
    
    # Connect if not already connected
    if not order_api.is_connected:
        connected = await order_api.connect_with_user_credentials(user_credentials)
        if not connected:
            return {
                'status': 'error',
                'message': 'Failed to connect to Angel One',
                'order_id': None
            }
    
    # Place the order
    return await order_api.place_order(order_data)
