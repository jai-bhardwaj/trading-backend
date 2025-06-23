"""
Input Validation System for Trading API
Comprehensive validation for all API endpoints to prevent injection attacks and data corruption
"""

import re
import uuid
import html
import urllib.parse
from typing import Dict, Any, List, Optional, Union, Set, Tuple
from decimal import Decimal, InvalidOperation
from datetime import datetime
from pydantic import BaseModel, Field, validator, ValidationError
from enum import Enum
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom validation error"""
    pass

class SecurityLevel(Enum):
    """Security validation levels"""
    LOW = "low"           # Basic type checking
    MEDIUM = "medium"     # Type + format validation
    HIGH = "high"         # Type + format + business logic
    CRITICAL = "critical" # Full validation with security checks

class TradingValidationRules:
    """Trading-specific validation rules and constants"""
    
    # User validation
    USER_ID_PATTERN = r'^[a-zA-Z0-9_-]{3,50}$'
    API_KEY_PATTERN = r'^[a-zA-Z0-9]{32,}$'
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    # Strategy validation
    STRATEGY_ID_PATTERN = r'^[a-zA-Z0-9_-]{3,100}$'
    STRATEGY_NAME_PATTERN = r'^[a-zA-Z0-9\s_-]{3,200}$'
    
    # Symbol validation
    SYMBOL_PATTERN = r'^[A-Z0-9]{1,20}$'
    EXCHANGE_PATTERN = r'^(NSE|BSE|MCX|NCDEX)$'
    
    # Financial validation
    MIN_CAPITAL = Decimal('1000.0')      # Minimum ₹1,000
    MAX_CAPITAL = Decimal('10000000.0')  # Maximum ₹1 crore
    MIN_ALLOCATION = Decimal('100.0')    # Minimum ₹100
    MAX_ALLOCATION = Decimal('1000000.0') # Maximum ₹10 lakh
    MIN_QUANTITY = 1
    MAX_QUANTITY = 100000
    
    # Rate limiting
    MAX_SYMBOLS_PER_REQUEST = 100
    MAX_STRATEGIES_PER_USER = 20
    MAX_ORDERS_PER_MINUTE = 60
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\bor\b|\band\b)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?",
        r"union\s+select",
        r"insert\s+into",
        r"delete\s+from",
        r"drop\s+table",
        r"alter\s+table",
        r"create\s+table",
        r"exec(\s|\+)+(s|x)p\w+",
        r"script\s*:",
        r"javascript\s*:",
        r"vbscript\s*:",
        r"onload\s*=",
        r"onerror\s*=",
        r"<\s*script",
        r"eval\s*\(",
        r"expression\s*\(",
        r"--\s*$",
        r"/\*.*\*/"
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'onload\s*=',
        r'onerror\s*=',
        r'onmouseover\s*=',
        r'onfocus\s*=',
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
        r'<form[^>]*>',
        r'<img[^>]*onerror'
    ]

class InputSanitizer:
    """Sanitizes and validates input data"""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000, allow_html: bool = False) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            raise ValidationError(f"Expected string, got {type(value)}")
        
        # Length check
        if len(value) > max_length:
            raise ValidationError(f"String too long. Max length: {max_length}")
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Check for SQL injection
        for pattern in TradingValidationRules.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValidationError(f"Potential SQL injection detected")
        
        # Check for XSS if HTML not allowed
        if not allow_html:
            for pattern in TradingValidationRules.XSS_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    raise ValidationError(f"Potential XSS attack detected")
        
        return value.strip()
    
    @staticmethod
    def validate_decimal(value: Union[str, int, float, Decimal], 
                        min_value: Optional[Decimal] = None,
                        max_value: Optional[Decimal] = None,
                        max_decimal_places: int = 2) -> Decimal:
        """Validate and convert to Decimal"""
        try:
            if isinstance(value, str):
                # Remove currency symbols and commas
                value = re.sub(r'[₹,$\s]', '', value)
            
            decimal_value = Decimal(str(value))
            
            # Check decimal places
            if decimal_value.as_tuple().exponent < -max_decimal_places:
                raise ValidationError(f"Too many decimal places. Max: {max_decimal_places}")
            
            # Range validation
            if min_value is not None and decimal_value < min_value:
                raise ValidationError(f"Value too low. Minimum: {min_value}")
            
            if max_value is not None and decimal_value > max_value:
                raise ValidationError(f"Value too high. Maximum: {max_value}")
            
            return decimal_value
            
        except (InvalidOperation, ValueError) as e:
            raise ValidationError(f"Invalid decimal value: {value}")
    
    @staticmethod
    def validate_integer(value: Union[str, int], 
                        min_value: Optional[int] = None,
                        max_value: Optional[int] = None) -> int:
        """Validate integer input"""
        try:
            int_value = int(value)
            
            if min_value is not None and int_value < min_value:
                raise ValidationError(f"Value too low. Minimum: {min_value}")
            
            if max_value is not None and int_value > max_value:
                raise ValidationError(f"Value too high. Maximum: {max_value}")
            
            return int_value
            
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid integer value: {value}")
    
    @staticmethod
    def validate_pattern(value: str, pattern: str, field_name: str) -> str:
        """Validate string against regex pattern"""
        if not re.match(pattern, value):
            raise ValidationError(f"Invalid {field_name} format")
        return value
    
    @staticmethod
    def validate_enum(value: str, valid_values: Set[str], field_name: str) -> str:
        """Validate enum value"""
        if value not in valid_values:
            raise ValidationError(f"Invalid {field_name}. Valid values: {', '.join(valid_values)}")
        return value

class UserValidationModels:
    """Pydantic models for user-related validation"""
    
    class UserRegistration(BaseModel):
        user_id: str = Field(..., min_length=3, max_length=50, regex=TradingValidationRules.USER_ID_PATTERN)
        name: str = Field(..., min_length=2, max_length=100)
        email: str = Field(..., regex=TradingValidationRules.EMAIL_PATTERN)
        total_capital: Decimal = Field(..., ge=TradingValidationRules.MIN_CAPITAL, le=TradingValidationRules.MAX_CAPITAL)
        risk_tolerance: str = Field(..., regex=r'^(conservative|moderate|aggressive)$')
        
        @validator('name')
        def validate_name(cls, v):
            return InputSanitizer.sanitize_string(v, max_length=100)
        
        @validator('total_capital')
        def validate_capital(cls, v):
            return InputSanitizer.validate_decimal(
                v,
                min_value=TradingValidationRules.MIN_CAPITAL,
                max_value=TradingValidationRules.MAX_CAPITAL
            )
    
    class StrategyActivation(BaseModel):
        strategy_id: str = Field(..., regex=TradingValidationRules.STRATEGY_ID_PATTERN)
        allocation_amount: Optional[Decimal] = Field(None, ge=TradingValidationRules.MIN_ALLOCATION, le=TradingValidationRules.MAX_ALLOCATION)
        custom_parameters: Optional[Dict[str, Any]] = None
        
        @validator('allocation_amount')
        def validate_allocation(cls, v):
            if v is not None:
                return InputSanitizer.validate_decimal(
                    v,
                    min_value=TradingValidationRules.MIN_ALLOCATION,
                    max_value=TradingValidationRules.MAX_ALLOCATION
                )
            return v
        
        @validator('custom_parameters')
        def validate_parameters(cls, v):
            if v is not None:
                # Validate parameter structure
                if not isinstance(v, dict):
                    raise ValueError("Parameters must be a dictionary")
                
                # Limit parameter count
                if len(v) > 20:
                    raise ValueError("Too many parameters. Maximum: 20")
                
                # Validate parameter values
                for key, value in v.items():
                    if not isinstance(key, str) or len(key) > 50:
                        raise ValueError("Parameter keys must be strings under 50 characters")
                    
                    # Sanitize string values
                    if isinstance(value, str):
                        InputSanitizer.sanitize_string(value, max_length=500)
            
            return v

class AdminValidationModels:
    """Pydantic models for admin-related validation"""
    
    class StrategyCreation(BaseModel):
        name: str = Field(..., min_length=3, max_length=200, regex=TradingValidationRules.STRATEGY_NAME_PATTERN)
        description: str = Field(..., min_length=10, max_length=2000)
        category: str = Field(..., regex=r'^(momentum|mean_reversion|arbitrage|scalping|swing)$')
        risk_level: str = Field(..., regex=r'^(low|medium|high)$')
        min_capital: Decimal = Field(..., ge=TradingValidationRules.MIN_CAPITAL)
        expected_return_annual: Decimal = Field(..., ge=-100, le=1000)  # -100% to 1000%
        max_drawdown: Decimal = Field(..., ge=0, le=100)  # 0% to 100%
        symbols: List[str] = Field(..., min_items=1, max_items=TradingValidationRules.MAX_SYMBOLS_PER_REQUEST)
        parameters: Dict[str, Any] = Field(default_factory=dict)
        
        @validator('name', 'description')
        def validate_strings(cls, v):
            return InputSanitizer.sanitize_string(v)
        
        @validator('symbols')
        def validate_symbols(cls, v):
            validated_symbols = []
            for symbol in v:
                if not isinstance(symbol, str):
                    raise ValueError("All symbols must be strings")
                
                validated_symbol = InputSanitizer.validate_pattern(
                    symbol.upper(),
                    TradingValidationRules.SYMBOL_PATTERN,
                    "symbol"
                )
                validated_symbols.append(validated_symbol)
            
            # Check for duplicates
            if len(set(validated_symbols)) != len(validated_symbols):
                raise ValueError("Duplicate symbols not allowed")
            
            return validated_symbols
        
        @validator('parameters')
        def validate_parameters(cls, v):
            if len(v) > 50:
                raise ValueError("Too many parameters. Maximum: 50")
            
            for key, value in v.items():
                InputSanitizer.sanitize_string(key, max_length=100)
                if isinstance(value, str):
                    InputSanitizer.sanitize_string(value, max_length=1000)
            
            return v
    
    class SymbolSubscription(BaseModel):
        tokens: List[str] = Field(..., min_items=1, max_items=TradingValidationRules.MAX_SYMBOLS_PER_REQUEST)
        
        @validator('tokens')
        def validate_tokens(cls, v):
            validated_tokens = []
            for token in v:
                if not isinstance(token, str):
                    raise ValueError("All tokens must be strings")
                
                # Token should be numeric or alphanumeric
                if not re.match(r'^[a-zA-Z0-9]{1,20}$', token):
                    raise ValueError(f"Invalid token format: {token}")
                
                validated_tokens.append(token)
            
            return validated_tokens

class ErrorHandlerValidationModels:
    """Pydantic models for error handler validation"""
    
    class ErrorResolution(BaseModel):
        error_id: str = Field(..., min_length=32, max_length=64)
        resolution_notes: str = Field("", max_length=2000)
        
        @validator('error_id')
        def validate_error_id(cls, v):
            # Should be a UUID-like string
            try:
                uuid.UUID(v)
                return v
            except ValueError:
                # Check if it's at least a valid hex string
                if not re.match(r'^[a-f0-9-]{32,}$', v, re.IGNORECASE):
                    raise ValueError("Invalid error ID format")
                return v
        
        @validator('resolution_notes')
        def validate_notes(cls, v):
            return InputSanitizer.sanitize_string(v, max_length=2000)

class SecurityValidator:
    """Advanced security validation"""
    
    @staticmethod
    def validate_request_size(data: Dict[str, Any], max_size_mb: float = 1.0) -> Dict[str, Any]:
        """Validate request size to prevent DoS attacks"""
        import json
        import sys
        
        try:
            data_size = len(json.dumps(data, default=str).encode('utf-8'))
            max_size_bytes = max_size_mb * 1024 * 1024
            
            if data_size > max_size_bytes:
                raise ValidationError(f"Request too large: {data_size/1024/1024:.2f}MB > {max_size_mb}MB")
            
            return data
            
        except (TypeError, ValueError) as e:
            raise ValidationError(f"Invalid request data: {e}")
    
    @staticmethod
    def validate_nested_depth(data: Any, max_depth: int = 10, current_depth: int = 0) -> Any:
        """Prevent deeply nested objects that could cause stack overflow"""
        if current_depth > max_depth:
            raise ValidationError(f"Object nesting too deep. Maximum depth: {max_depth}")
        
        if isinstance(data, dict):
            return {k: SecurityValidator.validate_nested_depth(v, max_depth, current_depth + 1) 
                   for k, v in data.items()}
        elif isinstance(data, list):
            return [SecurityValidator.validate_nested_depth(item, max_depth, current_depth + 1) 
                   for item in data]
        else:
            return data
    
    @staticmethod
    def validate_array_length(data: List[Any], max_length: int = 1000) -> List[Any]:
        """Prevent oversized arrays"""
        if len(data) > max_length:
            raise ValidationError(f"Array too long: {len(data)} > {max_length}")
        return data

class TradingInputValidator:
    """Comprehensive input validation system"""
    
    # Regex patterns for validation
    PATTERNS = {
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'symbol': r'^[A-Z]{1,10}$',
        'user_id': r'^[a-zA-Z0-9_-]{3,50}$',
        'order_id': r'^[A-Z0-9_-]{5,100}$',
        'numeric': r'^-?[0-9]+\.?[0-9]*$',
        'alphanumeric': r'^[a-zA-Z0-9]+$',
        'safe_string': r'^[a-zA-Z0-9\s\-_.,!?()]+$'
    }
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """Validate email address"""
        if not email or not isinstance(email, str):
            return False, "Email is required and must be a string"
        
        if len(email) > 254:
            return False, "Email is too long (max 254 characters)"
        
        if not re.match(TradingInputValidator.PATTERNS['email'], email.lower()):
            return False, "Invalid email format"
        
        return True, ""
    
    @staticmethod
    def validate_symbol(symbol: str) -> Tuple[bool, str]:
        """Validate trading symbol"""
        if not symbol or not isinstance(symbol, str):
            return False, "Symbol is required and must be a string"
        
        symbol = symbol.upper().strip()
        
        if not re.match(TradingInputValidator.PATTERNS['symbol'], symbol):
            return False, "Symbol must be 1-10 uppercase letters only"
        
        return True, symbol
    
    @staticmethod
    def validate_user_id(user_id: str) -> Tuple[bool, str]:
        """Validate user ID"""
        if not user_id or not isinstance(user_id, str):
            return False, "User ID is required and must be a string"
        
        user_id = user_id.strip()
        
        if not re.match(TradingInputValidator.PATTERNS['user_id'], user_id):
            return False, "User ID must be 3-50 characters (letters, numbers, hyphens, underscores only)"
        
        return True, user_id
    
    @staticmethod
    def validate_quantity(quantity: Union[str, int, float, Decimal]) -> Tuple[bool, Union[Decimal, str]]:
        """Validate trading quantity"""
        try:
            if isinstance(quantity, str):
                quantity = quantity.strip()
                if not quantity:
                    return False, "Quantity cannot be empty"
            
            decimal_qty = Decimal(str(quantity))
            
            if decimal_qty <= 0:
                return False, "Quantity must be positive"
            
            if decimal_qty > Decimal('1000000000'):  # 1 billion max
                return False, "Quantity is too large (max 1 billion)"
            
            # Check decimal places (max 8)
            if decimal_qty.as_tuple().exponent < -8:
                return False, "Quantity cannot have more than 8 decimal places"
            
            return True, decimal_qty
            
        except (InvalidOperation, ValueError, TypeError):
            return False, "Quantity must be a valid number"
    
    @staticmethod
    def validate_price(price: Union[str, int, float, Decimal]) -> Tuple[bool, Union[Decimal, str]]:
        """Validate price"""
        try:
            if isinstance(price, str):
                price = price.strip()
                if not price:
                    return False, "Price cannot be empty"
            
            decimal_price = Decimal(str(price))
            
            if decimal_price <= 0:
                return False, "Price must be positive"
            
            if decimal_price > Decimal('1000000'):  # 1 million max
                return False, "Price is too large (max 1 million)"
            
            # Check decimal places (max 6)
            if decimal_price.as_tuple().exponent < -6:
                return False, "Price cannot have more than 6 decimal places"
            
            return True, decimal_price
            
        except (InvalidOperation, ValueError, TypeError):
            return False, "Price must be a valid number"
    
    @staticmethod
    def validate_order_side(side: str) -> Tuple[bool, str]:
        """Validate order side"""
        if not side or not isinstance(side, str):
            return False, "Order side is required and must be a string"
        
        side = side.lower().strip()
        
        if side not in ['buy', 'sell']:
            return False, "Order side must be 'buy' or 'sell'"
        
        return True, side
    
    @staticmethod
    def validate_order_type(order_type: str) -> Tuple[bool, str]:
        """Validate order type"""
        if not order_type or not isinstance(order_type, str):
            return False, "Order type is required and must be a string"
        
        order_type = order_type.lower().strip()
        
        valid_types = ['market', 'limit', 'stop', 'stop_limit']
        if order_type not in valid_types:
            return False, f"Order type must be one of: {', '.join(valid_types)}"
        
        return True, order_type
    
    @staticmethod
    def validate_safe_string(value: str, max_length: int = 255, allow_empty: bool = False) -> Tuple[bool, str]:
        """Validate string for safety (no injection patterns)"""
        if not isinstance(value, str):
            return False, "Value must be a string"
        
        if not value.strip() and not allow_empty:
            return False, "Value cannot be empty"
        
        if len(value) > max_length:
            return False, f"Value is too long (max {max_length} characters)"
        
        # Check for SQL injection patterns
        value_lower = value.lower()
        for pattern in TradingValidationRules.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                logger.warning(f"Potential injection attempt detected: {pattern}")
                return False, "Invalid characters detected"
        
        # Check for basic XSS patterns
        if '<' in value or '>' in value or 'script' in value_lower:
            return False, "HTML/script content not allowed"
        
        return True, value.strip()
    
    @staticmethod
    def sanitize_string(value: str) -> str:
        """Sanitize string for safe output"""
        if not isinstance(value, str):
            return str(value)
        
        # HTML escape
        sanitized = html.escape(value)
        
        # URL decode any encoded content
        sanitized = urllib.parse.unquote(sanitized)
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        return sanitized
    
    @staticmethod
    def validate_datetime_string(dt_string: str) -> Tuple[bool, Union[datetime, str]]:
        """Validate datetime string"""
        if not dt_string or not isinstance(dt_string, str):
            return False, "Datetime string is required"
        
        # Try common datetime formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%d',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(dt_string, fmt)
                return True, dt
            except ValueError:
                continue
        
        return False, "Invalid datetime format"
    
    @staticmethod
    def validate_json_structure(data: Dict[str, Any], required_fields: List[str], 
                              optional_fields: Optional[List[str]] = None) -> Tuple[bool, str]:
        """Validate JSON structure has required fields"""
        if not isinstance(data, dict):
            return False, "Data must be a dictionary"
        
        # Check required fields
        missing_fields = []
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
        
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
        
        # Check for unexpected fields
        all_allowed_fields = set(required_fields)
        if optional_fields:
            all_allowed_fields.update(optional_fields)
        
        unexpected_fields = set(data.keys()) - all_allowed_fields
        if unexpected_fields:
            return False, f"Unexpected fields: {', '.join(unexpected_fields)}"
        
        return True, ""
    
    @staticmethod
    def validate_order_request(data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Comprehensive order request validation"""
        # Define required and optional fields
        required_fields = ['user_id', 'symbol', 'side', 'quantity', 'order_type']
        optional_fields = ['price', 'stop_price', 'signal_id', 'strategy_id']
        
        # Validate JSON structure
        valid_structure, structure_error = TradingInputValidator.validate_json_structure(
            data, required_fields, optional_fields
        )
        if not valid_structure:
            return False, structure_error, {}
        
        validated_data = {}
        
        # Validate user_id
        valid_user, user_result = TradingInputValidator.validate_user_id(data['user_id'])
        if not valid_user:
            return False, f"Invalid user_id: {user_result}", {}
        validated_data['user_id'] = user_result
        
        # Validate symbol
        valid_symbol, symbol_result = TradingInputValidator.validate_symbol(data['symbol'])
        if not valid_symbol:
            return False, f"Invalid symbol: {symbol_result}", {}
        validated_data['symbol'] = symbol_result
        
        # Validate side
        valid_side, side_result = TradingInputValidator.validate_order_side(data['side'])
        if not valid_side:
            return False, f"Invalid side: {side_result}", {}
        validated_data['side'] = side_result
        
        # Validate quantity
        valid_qty, qty_result = TradingInputValidator.validate_quantity(data['quantity'])
        if not valid_qty:
            return False, f"Invalid quantity: {qty_result}", {}
        validated_data['quantity'] = float(qty_result)
        
        # Validate order_type
        valid_type, type_result = TradingInputValidator.validate_order_type(data['order_type'])
        if not valid_type:
            return False, f"Invalid order_type: {type_result}", {}
        validated_data['order_type'] = type_result
        
        # Validate optional price
        if 'price' in data and data['price'] is not None:
            valid_price, price_result = TradingInputValidator.validate_price(data['price'])
            if not valid_price:
                return False, f"Invalid price: {price_result}", {}
            validated_data['price'] = float(price_result)
        
        # Validate optional stop_price
        if 'stop_price' in data and data['stop_price'] is not None:
            valid_stop, stop_result = TradingInputValidator.validate_price(data['stop_price'])
            if not valid_stop:
                return False, f"Invalid stop_price: {stop_result}", {}
            validated_data['stop_price'] = float(stop_result)
        
        # Validate optional signal_id
        if 'signal_id' in data and data['signal_id'] is not None:
            valid_signal, signal_result = TradingInputValidator.validate_safe_string(data['signal_id'], 100)
            if not valid_signal:
                return False, f"Invalid signal_id: {signal_result}", {}
            validated_data['signal_id'] = signal_result
        
        # Validate optional strategy_id
        if 'strategy_id' in data and data['strategy_id'] is not None:
            valid_strategy, strategy_result = TradingInputValidator.validate_safe_string(data['strategy_id'], 100)
            if not valid_strategy:
                return False, f"Invalid strategy_id: {strategy_result}", {}
            validated_data['strategy_id'] = strategy_result
        
        # Business logic validation
        if validated_data['order_type'] in ['limit', 'stop_limit'] and 'price' not in validated_data:
            return False, f"{validated_data['order_type']} orders require a price", {}
        
        if validated_data['order_type'] in ['stop', 'stop_limit'] and 'stop_price' not in validated_data:
            return False, f"{validated_data['order_type']} orders require a stop_price", {}
        
        return True, "", validated_data

# Global validator instance
_global_validator = None

def get_input_validator(security_level: SecurityLevel = SecurityLevel.HIGH) -> TradingInputValidator:
    """Get global input validator instance"""
    global _global_validator
    if _global_validator is None:
        _global_validator = TradingInputValidator()
    return _global_validator

# Validation decorators
def validate_json_body(validation_func):
    """Decorator to validate JSON request body"""
    def decorator(original_func):
        async def wrapper(*args, **kwargs):
            # Extract the request body data
            for arg in args:
                if isinstance(arg, dict):
                    validated_data = validation_func(arg)
                    # Replace the original argument with validated data
                    args = tuple(validated_data if x is arg else x for x in args)
                    break
            
            return await original_func(*args, **kwargs)
        return wrapper
    return decorator

def validate_path_params(**param_validations):
    """Decorator to validate path parameters"""
    def decorator(original_func):
        async def wrapper(*args, **kwargs):
            validator = get_input_validator()
            validated_params = validator.validate_path_parameters(**kwargs)
            kwargs.update(validated_params)
            return await original_func(*args, **kwargs)
        return wrapper
    return decorator 