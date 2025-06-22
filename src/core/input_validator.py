"""
Input Validation System for Trading API
Comprehensive validation for all API endpoints to prevent injection attacks and data corruption
"""

import re
import uuid
from typing import Dict, Any, List, Optional, Union, Set
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
        r'union\s+select',
        r'drop\s+table',
        r'delete\s+from',
        r'insert\s+into',
        r'update\s+set',
        r'exec\s*\(',
        r'script\s*>',
        r'<\s*script',
        r'javascript:',
        r'vbscript:',
        r'onload\s*=',
        r'onerror\s*=',
        r'--\s*$',
        r'/\*.*\*/',
        r'xp_cmdshell',
        r'sp_executesql'
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
    """Main input validation class for trading system"""
    
    def __init__(self, security_level: SecurityLevel = SecurityLevel.HIGH):
        self.security_level = security_level
        self.sanitizer = InputSanitizer()
    
    def validate_user_activation_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate strategy activation data"""
        try:
            # Security checks
            if self.security_level in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
                SecurityValidator.validate_request_size(data)
                SecurityValidator.validate_nested_depth(data)
            
            # Validate using Pydantic model
            if data:
                validated = UserValidationModels.StrategyActivation(**data)
                return validated.dict()
            
            return {}
            
        except ValidationError as e:
            logger.warning(f"🚫 Validation failed: {e}")
            raise HTTPException(status_code=400, detail=f"Validation error: {e}")
        except Exception as e:
            logger.error(f"❌ Validation error: {e}")
            raise HTTPException(status_code=400, detail="Invalid input data")
    
    def validate_strategy_creation_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate strategy creation data"""
        try:
            # Security checks
            SecurityValidator.validate_request_size(data, max_size_mb=5.0)  # Larger for strategy data
            SecurityValidator.validate_nested_depth(data)
            
            # Validate using Pydantic model
            validated = AdminValidationModels.StrategyCreation(**data)
            return validated.dict()
            
        except ValidationError as e:
            logger.warning(f"🚫 Strategy validation failed: {e}")
            raise HTTPException(status_code=400, detail=f"Strategy validation error: {e}")
        except Exception as e:
            logger.error(f"❌ Strategy validation error: {e}")
            raise HTTPException(status_code=400, detail="Invalid strategy data")
    
    def validate_symbol_subscription_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate symbol subscription data"""
        try:
            SecurityValidator.validate_request_size(data)
            
            validated = AdminValidationModels.SymbolSubscription(**data)
            return validated.dict()
            
        except ValidationError as e:
            logger.warning(f"🚫 Symbol validation failed: {e}")
            raise HTTPException(status_code=400, detail=f"Symbol validation error: {e}")
        except Exception as e:
            logger.error(f"❌ Symbol validation error: {e}")
            raise HTTPException(status_code=400, detail="Invalid symbol data")
    
    def validate_error_resolution_data(self, error_id: str, resolution_notes: str = "") -> Dict[str, Any]:
        """Validate error resolution data"""
        try:
            data = {
                "error_id": error_id,
                "resolution_notes": resolution_notes
            }
            
            validated = ErrorHandlerValidationModels.ErrorResolution(**data)
            return validated.dict()
            
        except ValidationError as e:
            logger.warning(f"🚫 Error resolution validation failed: {e}")
            raise HTTPException(status_code=400, detail=f"Error resolution validation error: {e}")
        except Exception as e:
            logger.error(f"❌ Error resolution validation error: {e}")
            raise HTTPException(status_code=400, detail="Invalid error resolution data")
    
    def validate_path_parameters(self, **params) -> Dict[str, Any]:
        """Validate path parameters"""
        validated = {}
        
        for param_name, param_value in params.items():
            if param_value is None:
                continue
            
            # Sanitize the parameter
            if isinstance(param_value, str):
                sanitized = self.sanitizer.sanitize_string(param_value, max_length=200)
                
                # Specific validation based on parameter name
                if 'user_id' in param_name:
                    sanitized = self.sanitizer.validate_pattern(
                        sanitized, 
                        TradingValidationRules.USER_ID_PATTERN,
                        "user_id"
                    )
                elif 'strategy_id' in param_name:
                    sanitized = self.sanitizer.validate_pattern(
                        sanitized,
                        TradingValidationRules.STRATEGY_ID_PATTERN,
                        "strategy_id"
                    )
                elif 'symbol' in param_name:
                    sanitized = self.sanitizer.validate_pattern(
                        sanitized.upper(),
                        TradingValidationRules.SYMBOL_PATTERN,
                        "symbol"
                    )
                
                validated[param_name] = sanitized
            else:
                validated[param_name] = param_value
        
        return validated
    
    def validate_query_parameters(self, **params) -> Dict[str, Any]:
        """Validate query parameters"""
        validated = {}
        
        for param_name, param_value in params.items():
            if param_value is None:
                continue
            
            # Type-specific validation
            if param_name in ['limit', 'offset', 'hours']:
                validated[param_name] = self.sanitizer.validate_integer(
                    param_value, 
                    min_value=0, 
                    max_value=10000
                )
            elif param_name in ['query', 'search']:
                validated[param_name] = self.sanitizer.sanitize_string(
                    param_value, 
                    max_length=500
                )
            else:
                if isinstance(param_value, str):
                    validated[param_name] = self.sanitizer.sanitize_string(
                        param_value, 
                        max_length=1000
                    )
                else:
                    validated[param_name] = param_value
        
        return validated
    
    def detect_sql_injection(self, value: str) -> bool:
        """Detect potential SQL injection in input"""
        try:
            # Check against SQL injection patterns
            for pattern in TradingValidationRules.SQL_INJECTION_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    logger.warning(f"🚫 SQL injection detected: {pattern}")
                    return True
            return False
        except Exception as e:
            logger.error(f"❌ Error in SQL injection detection: {e}")
            return False
    
    def detect_xss_attack(self, value: str) -> bool:
        """Detect potential XSS attack in input"""
        try:
            # Check against XSS patterns
            for pattern in TradingValidationRules.XSS_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    logger.warning(f"🚫 XSS attack detected: {pattern}")
                    return True
            return False
        except Exception as e:
            logger.error(f"❌ Error in XSS detection: {e}")
            return False

# Global validator instance
_global_validator = None

def get_input_validator(security_level: SecurityLevel = SecurityLevel.HIGH) -> TradingInputValidator:
    """Get global input validator instance"""
    global _global_validator
    if _global_validator is None:
        _global_validator = TradingInputValidator(security_level)
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