"""
Angel One WebSocket Client - Class-based implementation
Refactored from working angel_one_socket.py into a reusable class
"""

from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
import threading
import pyotp
import time
import config
from datetime import datetime
import logging
import sys

# Configure logging
td = datetime.today().date()
logging.basicConfig(
    filename=f"ANGEL_WEBSOCKET_{td}.log", 
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

stdout_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stdout_handler)

class AngelOneWebSocketClient:
    """Angel One WebSocket client for real-time market data"""
    
    def __init__(self, api_key=None, username=None, pin=None, token=None):
        """
        Initialize the Angel One WebSocket client
        
        Args:
            api_key: Angel One API key (uses config.API_KEY if None)
            username: Angel One username (uses config.USERNAME if None)
            pin: Angel One PIN (uses config.PIN if None)
            token: Angel One TOTP secret (uses config.TOKEN if None)
        """
        # Use provided credentials or fall back to config
        self.api_key = api_key or config.API_KEY
        self.username = username or config.USERNAME
        self.pin = pin or config.PIN
        self.token = token or config.TOKEN
        
        # WebSocket objects
        self.smart_api_obj = None
        self.smart_web = None
        
        # Connection state
        self.connected = False
        self.subscribed_tokens = []
        
        # Callbacks
        self.on_data_callback = None
        self.on_error_callback = None
        self.on_close_callback = None
        self.on_open_callback = None
        
        # Configuration
        self.correlation_id = config.CORRELATION_ID
        self.feed_mode = config.FEED_MODE
        self.max_retry_attempts = 5
        
        logger.info("AngelOneWebSocketClient initialized")
    
    def set_callbacks(self, on_data=None, on_error=None, on_close=None, on_open=None):
        """
        Set callback functions for WebSocket events
        
        Args:
            on_data: Function to handle incoming data (wsapp, msg)
            on_error: Function to handle errors (wsapp, error)
            on_close: Function to handle connection close (wsapp, *args)
            on_open: Function to handle connection open (wsapp)
        """
        if on_data:
            self.on_data_callback = on_data
        if on_error:
            self.on_error_callback = on_error
        if on_close:
            self.on_close_callback = on_close
        if on_open:
            self.on_open_callback = on_open
        
        logger.info("Callbacks set")
    
    def login(self):
        """
        Authenticate with Angel One and get WebSocket tokens
        
        Returns:
            tuple: (smart_api_obj, smart_web) or (None, None) if failed
        """
        try:
            logger.info("🔐 Authenticating with Angel One...")

            logger.info(f"API Key: {self.api_key}")
            logger.info(f"Username: {self.username}")
            logger.info(f"PIN: {self.pin}")
            logger.info(f"Token: {self.token}")
            
            # Initialize SmartConnect
            obj = SmartConnect(api_key=self.api_key)
            
            # Generate session with TOTP
            totp_token = pyotp.TOTP(self.token).now()
            data = obj.generateSession(
                self.username, 
                self.pin,
                totp_token
            )
            
            if not data or not data.get('data'):
                logger.error("❌ Failed to generate session")
                return None, None
            
            # Extract tokens
            AUTH_TOKEN = data['data']['jwtToken']
            refreshToken = data['data']['refreshToken']
            
            # Get feed token
            FEED_TOKEN = obj.getfeedToken()
            
            # Get profile info
            res = obj.getProfile(refreshToken)
            logger.info(f'Profile products: {res["data"]["products"]}')
            
            # Create WebSocket instance
            sws = SmartWebSocketV2(
                AUTH_TOKEN, 
                self.api_key, 
                self.username, 
                FEED_TOKEN, 
                max_retry_attempt=self.max_retry_attempts
            )
            
            self.smart_api_obj = obj
            self.smart_web = sws
            
            logger.info("✅ Authentication successful")
            return obj, sws
            
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            return None, None
    
    def _on_data(self, wsapp, msg):
        """Internal data handler"""
        try:
            logger.info(f"Received tick: {msg}")
            
            # Call user-defined callback if set
            if self.on_data_callback:
                self.on_data_callback(wsapp, msg)
                
        except Exception as e:
            logger.error(f"Error in data handler: {e}")
    
    def _on_error(self, wsapp, error):
        """Internal error handler"""
        logger.error(f"---------Connection Error {error}-----------")
        
        # Call user-defined callback if set
        if self.on_error_callback:
            self.on_error_callback(wsapp, error)
    
    def _on_close(self, wsapp, *args):
        """Internal close handler"""
        logger.info("---------Connection Close-----------")
        self.connected = False
        
        # Call user-defined callback if set
        if self.on_close_callback:
            self.on_close_callback(wsapp, *args)
    
    def _on_open(self, wsapp):
        """Internal open handler"""
        logger.info("✅ WebSocket connection opened")
        self.connected = True
        
        # Subscribe to tokens if any are set
        if self.subscribed_tokens:
            try:
                self.smart_web.subscribe(
                    self.correlation_id, 
                    self.feed_mode, 
                    self.subscribed_tokens
                )
                logger.info(f"✅ Subscribed to {len(self.subscribed_tokens)} token groups")
            except Exception as e:
                logger.error(f"Failed to subscribe: {e}")
        
        # Call user-defined callback if set
        if self.on_open_callback:
            self.on_open_callback(wsapp)
    
    def connect(self, tokens=None):
        """
        Connect to Angel One WebSocket
        
        Args:
            tokens: List of token groups to subscribe to
                   Format: [{"exchangeType": 1, "tokens": ["2881", "11536"]}]
        """
        try:
            # Authenticate first
            api_obj, web_obj = self.login()
            if not api_obj or not web_obj:
                logger.error("❌ Cannot connect - authentication failed")
                return False
            
            # Set tokens to subscribe to
            if tokens:
                self.subscribed_tokens = tokens
            
            # Set up default token if none provided
            if not self.subscribed_tokens:
                self.subscribed_tokens = [
                    {
                        "exchangeType": 1,  # NSE CM
                        "tokens": ["26009"]  # Default token
                    }
                ]
            
            # Assign callbacks
            self.smart_web.on_open = self._on_open
            self.smart_web.on_data = self._on_data
            self.smart_web.on_error = self._on_error
            self.smart_web.on_close = self._on_close
            
            # Start connection in separate thread
            def run_websocket():
                try:
                    logger.info("🔌 Connecting to Angel One WebSocket...")
                    self.smart_web.connect()
                except Exception as e:
                    logger.error(f"WebSocket connection error: {e}")
            
            ws_thread = threading.Thread(target=run_websocket, daemon=True)
            ws_thread.start()
            
            # Give it time to connect
            time.sleep(3)
            
            logger.info("✅ WebSocket connection initiated")
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False
    
    def subscribe(self, tokens):
        """
        Subscribe to additional tokens
        
        Args:
            tokens: List of token groups
        """
        if not self.smart_web or not self.connected:
            logger.error("❌ Cannot subscribe - not connected")
            return False
        
        try:
            self.smart_web.subscribe(self.correlation_id, self.feed_mode, tokens)
            self.subscribed_tokens.extend(tokens)
            logger.info(f"✅ Subscribed to additional tokens: {tokens}")
            return True
        except Exception as e:
            logger.error(f"❌ Subscription failed: {e}")
            return False
    
    def unsubscribe(self, tokens):
        """
        Unsubscribe from tokens
        
        Args:
            tokens: List of token groups to unsubscribe from
        """
        if not self.smart_web or not self.connected:
            logger.error("❌ Cannot unsubscribe - not connected")
            return False
        
        try:
            self.smart_web.unsubscribe(self.correlation_id, self.feed_mode, tokens)
            # Remove from subscribed list
            for token_group in tokens:
                if token_group in self.subscribed_tokens:
                    self.subscribed_tokens.remove(token_group)
            logger.info(f"✅ Unsubscribed from tokens: {tokens}")
            return True
        except Exception as e:
            logger.error(f"❌ Unsubscription failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from WebSocket"""
        try:
            if self.smart_web:
                self.smart_web.MAX_RETRY_ATTEMPT = 0
                self.smart_web.close_connection()
                self.connected = False
                logger.info("✅ Disconnected from WebSocket")
            return True
        except Exception as e:
            logger.error(f"❌ Disconnect failed: {e}")
            return False
    
    def is_connected(self):
        """Check if WebSocket is connected"""
        return self.connected
    
    def get_subscribed_tokens(self):
        """Get list of currently subscribed tokens"""
        return self.subscribed_tokens.copy()
    
    def get_stats(self):
        """Get connection statistics"""
        return {
            "connected": self.connected,
            "subscribed_tokens": len(self.subscribed_tokens),
            "token_groups": self.subscribed_tokens,
            "correlation_id": self.correlation_id,
            "feed_mode": self.feed_mode
        }


# Example usage
if __name__ == "__main__":
    # Create client instance
    client = AngelOneWebSocketClient()
    
    # Set up callbacks
    def handle_data(wsapp, msg):
        print(f"Received tick: {msg}")
    
    def handle_error(wsapp, error):
        print(f"Error: {error}")
    
    def handle_close(wsapp, *args):
        print("Connection closed")
    
    def handle_open(wsapp):
        print("Connection opened")
    
    client.set_callbacks(
        on_data=handle_data,
        on_error=handle_error,
        on_close=handle_close,
        on_open=handle_open
    )
    
    # Define tokens to subscribe to
    tokens = [
        {
            "exchangeType": 1,  # NSE CM
            "tokens": ["2881", "11536", "408065"]  # RELIANCE, TCS, INFY
        }
    ]
    
    # Connect and subscribe
    if client.connect(tokens):
        print("✅ Connected successfully")
        
        # Keep running
        try:
            while True:
                time.sleep(1)
                if not client.is_connected():
                    print("Connection lost, attempting to reconnect...")
                    client.connect(tokens)
        except KeyboardInterrupt:
            print("Shutting down...")
            client.disconnect()
    else:
        print("❌ Failed to connect")
