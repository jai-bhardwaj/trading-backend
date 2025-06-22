"""
Critical Error Handling System
Handles critical trading errors that should stop execution vs recoverable errors
"""

import asyncio
import logging
import time
import traceback
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "LOW"           # Recoverable, continue trading
    MEDIUM = "MEDIUM"     # Recoverable with warnings, continue with caution
    HIGH = "HIGH"         # Critical but recoverable, pause trading briefly
    CRITICAL = "CRITICAL" # System must stop trading immediately
    FATAL = "FATAL"       # System must shutdown completely

class ErrorCategory(Enum):
    """Categories of trading errors"""
    MARKET_DATA = "MARKET_DATA"         # Market data feed issues
    BROKER_CONNECTION = "BROKER_CONNECTION"  # Broker API issues
    ORDER_EXECUTION = "ORDER_EXECUTION"     # Order placement/execution issues
    STRATEGY = "STRATEGY"               # Strategy calculation errors
    DATABASE = "DATABASE"               # Database connection/query errors
    AUTHENTICATION = "AUTH"             # Authentication/authorization errors
    SYSTEM = "SYSTEM"                   # System resource issues
    FINANCIAL = "FINANCIAL"             # Financial calculation errors

@dataclass
class CriticalError:
    """Critical error record"""
    error_id: str
    timestamp: datetime
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    exception: Optional[Exception]
    traceback_str: str
    context: Dict[str, Any] = field(default_factory=dict)
    financial_impact: float = 0.0  # Estimated financial impact
    affected_users: List[str] = field(default_factory=list)
    recovery_attempted: bool = False
    recovery_successful: bool = False
    resolution_notes: str = ""

class TradingAction(Enum):
    """Actions to take based on error severity"""
    CONTINUE = "CONTINUE"           # Continue normal trading
    PAUSE_USER = "PAUSE_USER"       # Pause trading for specific user
    PAUSE_STRATEGY = "PAUSE_STRATEGY"  # Pause specific strategy
    PAUSE_SYMBOL = "PAUSE_SYMBOL"   # Pause trading for specific symbol
    PAUSE_ALL = "PAUSE_ALL"         # Pause all trading
    SHUTDOWN = "SHUTDOWN"           # Shutdown trading system

@dataclass
class ErrorRule:
    """Rule for handling specific error types"""
    error_pattern: str
    category: ErrorCategory
    severity: ErrorSeverity
    action: TradingAction
    max_occurrences: int = 5        # Max occurrences before escalation
    time_window_minutes: int = 15   # Time window for counting occurrences
    escalation_severity: ErrorSeverity = ErrorSeverity.CRITICAL
    recovery_function: Optional[Callable] = None
    requires_human_intervention: bool = False

class CriticalErrorHandler:
    """
    Comprehensive critical error handling system
    Determines when to stop trading vs continue with errors
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Error storage and tracking
        self.error_history: List[CriticalError] = []
        self.error_counts: Dict[str, List[datetime]] = defaultdict(list)
        self.critical_errors_active: Set[str] = set()
        
        # Trading state control
        self.trading_paused = False
        self.trading_shutdown = False
        self.paused_users: Set[str] = set()
        self.paused_strategies: Set[str] = set()
        self.paused_symbols: Set[str] = set()
        
        # Performance tracking
        self.total_errors_handled = 0
        self.critical_errors_prevented = 0
        self.financial_losses_prevented = 0.0
        
        # Notification settings
        self.email_enabled = self.config.get('email_notifications', True)
        self.email_config = self.config.get('email_config', {})
        
        # Initialize error rules
        self.error_rules: List[ErrorRule] = []
        self._setup_default_error_rules()
        
        logger.info("🚨 Critical Error Handler initialized")
    
    def _setup_default_error_rules(self):
        """Setup default error handling rules for common trading errors"""
        
        # CRITICAL FINANCIAL ERRORS - Must stop trading
        self.error_rules.extend([
            ErrorRule(
                error_pattern="insufficient.*fund",
                category=ErrorCategory.FINANCIAL,
                severity=ErrorSeverity.CRITICAL,
                action=TradingAction.PAUSE_ALL,
                max_occurrences=1,
                requires_human_intervention=True
            ),
            ErrorRule(
                error_pattern="margin.*call",
                category=ErrorCategory.FINANCIAL,
                severity=ErrorSeverity.CRITICAL,
                action=TradingAction.PAUSE_ALL,
                max_occurrences=1,
                requires_human_intervention=True
            ),
            ErrorRule(
                error_pattern="position.*limit.*exceeded",
                category=ErrorCategory.FINANCIAL,
                severity=ErrorSeverity.CRITICAL,
                action=TradingAction.PAUSE_ALL,
                max_occurrences=1,
                requires_human_intervention=True
            ),
            ErrorRule(
                error_pattern="risk.*limit.*breach",
                category=ErrorCategory.FINANCIAL,
                severity=ErrorSeverity.CRITICAL,
                action=TradingAction.PAUSE_ALL,
                max_occurrences=1,
                requires_human_intervention=True
            )
        ])
        
        # BROKER CONNECTION ERRORS
        self.error_rules.extend([
            ErrorRule(
                error_pattern="broker.*not.*authenticated",
                category=ErrorCategory.BROKER_CONNECTION,
                severity=ErrorSeverity.CRITICAL,
                action=TradingAction.PAUSE_ALL,
                max_occurrences=1,
                requires_human_intervention=True
            ),
            ErrorRule(
                error_pattern="api.*key.*invalid",
                category=ErrorCategory.BROKER_CONNECTION,
                severity=ErrorSeverity.CRITICAL,
                action=TradingAction.PAUSE_ALL,
                max_occurrences=1,
                requires_human_intervention=True
            ),
            ErrorRule(
                error_pattern="connection.*timeout",
                category=ErrorCategory.BROKER_CONNECTION,
                severity=ErrorSeverity.HIGH,
                action=TradingAction.PAUSE_ALL,
                max_occurrences=3,
                time_window_minutes=5
            )
        ])
        
        # ORDER EXECUTION ERRORS
        self.error_rules.extend([
            ErrorRule(
                error_pattern="order.*rejected.*repeatedly",
                category=ErrorCategory.ORDER_EXECUTION,
                severity=ErrorSeverity.HIGH,
                action=TradingAction.PAUSE_STRATEGY,
                max_occurrences=5,
                time_window_minutes=10
            ),
            ErrorRule(
                error_pattern="duplicate.*order",
                category=ErrorCategory.ORDER_EXECUTION,
                severity=ErrorSeverity.HIGH,
                action=TradingAction.PAUSE_USER,
                max_occurrences=3,
                time_window_minutes=5
            )
        ])
        
        # MARKET DATA ERRORS
        self.error_rules.extend([
            ErrorRule(
                error_pattern="market.*data.*unavailable",
                category=ErrorCategory.MARKET_DATA,
                severity=ErrorSeverity.HIGH,
                action=TradingAction.PAUSE_ALL,
                max_occurrences=10,
                time_window_minutes=5
            ),
            ErrorRule(
                error_pattern="stale.*market.*data",
                category=ErrorCategory.MARKET_DATA,
                severity=ErrorSeverity.MEDIUM,
                action=TradingAction.CONTINUE,
                max_occurrences=20,
                time_window_minutes=10
            )
        ])
        
        # STRATEGY ERRORS
        self.error_rules.extend([
            ErrorRule(
                error_pattern="division.*by.*zero",
                category=ErrorCategory.STRATEGY,
                severity=ErrorSeverity.HIGH,
                action=TradingAction.PAUSE_STRATEGY,
                max_occurrences=1
            ),
            ErrorRule(
                error_pattern="strategy.*calculation.*error",
                category=ErrorCategory.STRATEGY,
                severity=ErrorSeverity.MEDIUM,
                action=TradingAction.PAUSE_STRATEGY,
                max_occurrences=5,
                time_window_minutes=15
            )
        ])
        
        # DATABASE ERRORS
        self.error_rules.extend([
            ErrorRule(
                error_pattern="database.*connection.*lost",
                category=ErrorCategory.DATABASE,
                severity=ErrorSeverity.CRITICAL,
                action=TradingAction.PAUSE_ALL,
                max_occurrences=3,
                time_window_minutes=10,
                requires_human_intervention=True
            )
        ])
        
        # SYSTEM ERRORS
        self.error_rules.extend([
            ErrorRule(
                error_pattern="memory.*exhausted",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                action=TradingAction.SHUTDOWN,
                max_occurrences=1,
                requires_human_intervention=True
            ),
            ErrorRule(
                error_pattern="disk.*space.*full",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                action=TradingAction.PAUSE_ALL,
                max_occurrences=1,
                requires_human_intervention=True
            )
        ])
    
    async def handle_error(self, exception: Exception, context: Dict[str, Any] = None) -> TradingAction:
        """
        Main error handling function - determines if trading should continue or stop
        """
        try:
            # Create error record
            error_record = self._create_error_record(exception, context)
            
            # Find matching rule
            matching_rule = self._find_matching_rule(error_record)
            
            if not matching_rule:
                # No specific rule - use default handling
                return await self._handle_unknown_error(error_record)
            
            # Check occurrence frequency
            should_escalate = self._should_escalate_error(error_record, matching_rule)
            
            if should_escalate:
                error_record.severity = matching_rule.escalation_severity
                action = TradingAction.CRITICAL if matching_rule.escalation_severity == ErrorSeverity.CRITICAL else matching_rule.action
            else:
                action = matching_rule.action
            
            # Execute the action
            await self._execute_action(action, error_record, matching_rule)
            
            # Store error record
            self.error_history.append(error_record)
            self.total_errors_handled += 1
            
            # Send notifications if critical
            if error_record.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]:
                await self._send_critical_error_notification(error_record, action)
                self.critical_errors_prevented += 1
            
            logger.info(f"🚨 Error handled: {error_record.severity.value} - Action: {action.value}")
            
            return action
            
        except Exception as e:
            logger.error(f"❌ Error in error handler: {e}")
            # If error handler fails, take safest action
            return TradingAction.PAUSE_ALL
    
    def _create_error_record(self, exception: Exception, context: Dict[str, Any] = None) -> CriticalError:
        """Create a detailed error record"""
        import uuid
        
        error_message = str(exception).lower()
        
        # Determine category and severity based on error message
        category = self._categorize_error(error_message)
        severity = self._assess_severity(error_message, category)
        
        # Estimate financial impact
        financial_impact = self._estimate_financial_impact(exception, context)
        
        # Get affected users from context
        affected_users = context.get('affected_users', []) if context else []
        
        return CriticalError(
            error_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            severity=severity,
            category=category,
            message=str(exception),
            exception=exception,
            traceback_str=traceback.format_exc(),
            context=context or {},
            financial_impact=financial_impact,
            affected_users=affected_users
        )
    
    def _find_matching_rule(self, error_record: CriticalError) -> Optional[ErrorRule]:
        """Find the first matching error rule"""
        import re
        
        error_message = error_record.message.lower()
        
        for rule in self.error_rules:
            if re.search(rule.error_pattern, error_message):
                return rule
        
        return None
    
    def _should_escalate_error(self, error_record: CriticalError, rule: ErrorRule) -> bool:
        """Check if error should be escalated based on frequency"""
        now = datetime.now()
        time_window = timedelta(minutes=rule.time_window_minutes)
        cutoff_time = now - time_window
        
        # Count recent occurrences of this error pattern
        pattern_key = f"{rule.error_pattern}_{rule.category.value}"
        recent_occurrences = [
            ts for ts in self.error_counts[pattern_key] 
            if ts > cutoff_time
        ]
        
        # Add current occurrence
        self.error_counts[pattern_key].append(now)
        
        # Clean old occurrences
        self.error_counts[pattern_key] = [
            ts for ts in self.error_counts[pattern_key] 
            if ts > cutoff_time
        ]
        
        return len(recent_occurrences) >= rule.max_occurrences
    
    async def _handle_unknown_error(self, error_record: CriticalError) -> TradingAction:
        """Handle errors that don't match any specific rule"""
        
        # Default to medium severity for unknown errors
        if error_record.severity == ErrorSeverity.LOW:
            error_record.severity = ErrorSeverity.MEDIUM
        
        # Check for keywords that suggest critical issues
        error_msg_lower = error_record.message.lower()
        
        critical_keywords = [
            'fund', 'margin', 'balance', 'position', 'risk',
            'authentication', 'unauthorized', 'forbidden',
            'memory', 'disk', 'cpu', 'system'
        ]
        
        if any(keyword in error_msg_lower for keyword in critical_keywords):
            error_record.severity = ErrorSeverity.CRITICAL
            logger.warning(f"🚨 Unknown error escalated to CRITICAL due to keywords: {error_record.message}")
            return TradingAction.PAUSE_ALL
        
        # For unknown medium severity errors, pause briefly
        return TradingAction.CONTINUE
    
    async def _execute_action(self, action: TradingAction, error_record: CriticalError, rule: ErrorRule = None):
        """Execute the determined action"""
        
        if action == TradingAction.CONTINUE:
            logger.info(f"✅ Continuing trading despite error: {error_record.message[:100]}...")
            return
        
        elif action == TradingAction.PAUSE_USER:
            for user_id in error_record.affected_users:
                self.paused_users.add(user_id)
            logger.warning(f"⏸️ Paused trading for users: {error_record.affected_users}")
        
        elif action == TradingAction.PAUSE_STRATEGY:
            strategy_id = error_record.context.get('strategy_id')
            if strategy_id:
                self.paused_strategies.add(strategy_id)
                logger.warning(f"⏸️ Paused strategy: {strategy_id}")
        
        elif action == TradingAction.PAUSE_SYMBOL:
            symbol = error_record.context.get('symbol')
            if symbol:
                self.paused_symbols.add(symbol)
                logger.warning(f"⏸️ Paused trading for symbol: {symbol}")
        
        elif action == TradingAction.PAUSE_ALL:
            self.trading_paused = True
            self.critical_errors_active.add(error_record.error_id)
            logger.error(f"🛑 ALL TRADING PAUSED due to critical error: {error_record.message}")
        
        elif action == TradingAction.SHUTDOWN:
            self.trading_shutdown = True
            self.critical_errors_active.add(error_record.error_id)
            logger.critical(f"🚨 TRADING SYSTEM SHUTDOWN due to fatal error: {error_record.message}")
    
    def _categorize_error(self, error_message: str) -> ErrorCategory:
        """Categorize error based on message content"""
        
        if any(keyword in error_message for keyword in ['market', 'data', 'price', 'quote']):
            return ErrorCategory.MARKET_DATA
        elif any(keyword in error_message for keyword in ['broker', 'api', 'connection', 'timeout']):
            return ErrorCategory.BROKER_CONNECTION
        elif any(keyword in error_message for keyword in ['order', 'execution', 'fill', 'reject']):
            return ErrorCategory.ORDER_EXECUTION
        elif any(keyword in error_message for keyword in ['strategy', 'calculation', 'signal']):
            return ErrorCategory.STRATEGY
        elif any(keyword in error_message for keyword in ['database', 'sql', 'query', 'connection']):
            return ErrorCategory.DATABASE
        elif any(keyword in error_message for keyword in ['auth', 'token', 'permission', 'unauthorized']):
            return ErrorCategory.AUTHENTICATION
        elif any(keyword in error_message for keyword in ['fund', 'balance', 'margin', 'position', 'risk']):
            return ErrorCategory.FINANCIAL
        else:
            return ErrorCategory.SYSTEM
    
    def _assess_severity(self, error_message: str, category: ErrorCategory) -> ErrorSeverity:
        """Assess error severity based on message and category"""
        
        # Financial errors are always critical
        if category == ErrorCategory.FINANCIAL:
            return ErrorSeverity.CRITICAL
        
        # Authentication errors are critical
        if category == ErrorCategory.AUTHENTICATION:
            return ErrorSeverity.CRITICAL
        
        # System errors vary
        if category == ErrorCategory.SYSTEM:
            if any(keyword in error_message for keyword in ['memory', 'disk', 'cpu', 'crash']):
                return ErrorSeverity.FATAL
            else:
                return ErrorSeverity.HIGH
        
        # Database connection issues are critical
        if category == ErrorCategory.DATABASE and 'connection' in error_message:
            return ErrorSeverity.CRITICAL
        
        # Broker authentication is critical
        if category == ErrorCategory.BROKER_CONNECTION and any(keyword in error_message for keyword in ['auth', 'key', 'token']):
            return ErrorSeverity.CRITICAL
        
        # Default to medium for other errors
        return ErrorSeverity.MEDIUM
    
    def _estimate_financial_impact(self, exception: Exception, context: Dict[str, Any] = None) -> float:
        """Estimate potential financial impact of the error"""
        
        if not context:
            return 0.0
        
        # Estimate based on order values, user counts, etc.
        order_value = context.get('order_value', 0.0)
        affected_users_count = len(context.get('affected_users', []))
        
        # Simple estimation - could be more sophisticated
        estimated_impact = order_value * affected_users_count * 0.1  # 10% potential loss
        
        return min(estimated_impact, 100000.0)  # Cap at 1 lakh
    
    async def _send_critical_error_notification(self, error_record: CriticalError, action: TradingAction):
        """Send email notification for critical errors"""
        
        if not self.email_enabled or not self.email_config:
            return
        
        try:
            subject = f"🚨 CRITICAL TRADING ERROR - {action.value}"
            
            body = f"""
            CRITICAL TRADING SYSTEM ERROR ALERT
            
            Timestamp: {error_record.timestamp}
            Severity: {error_record.severity.value}
            Category: {error_record.category.value}
            Action Taken: {action.value}
            
            Error Message:
            {error_record.message}
            
            Context:
            {error_record.context}
            
            Financial Impact (Estimated): ₹{error_record.financial_impact:,.2f}
            Affected Users: {len(error_record.affected_users)}
            
            System Status:
            - Trading Paused: {self.trading_paused}
            - Trading Shutdown: {self.trading_shutdown}
            - Paused Users: {len(self.paused_users)}
            - Paused Strategies: {len(self.paused_strategies)}
            
            Please take immediate action to resolve this issue.
            
            Trading System Error Handler
            """
            
            await self._send_email(subject, body)
            
        except Exception as e:
            logger.error(f"❌ Failed to send error notification: {e}")
    
    async def _send_email(self, subject: str, body: str):
        """Send email notification"""
        
        try:
            smtp_host = self.email_config.get('smtp_host', 'smtp.gmail.com')
            smtp_port = self.email_config.get('smtp_port', 587)
            username = self.email_config.get('username')
            password = self.email_config.get('password')
            to_emails = self.email_config.get('alert_emails', [])
            
            if not all([username, password, to_emails]):
                logger.warning("⚠️ Email configuration incomplete, skipping notification")
                return
            
            msg = MIMEMultipart()
            msg['From'] = username
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
            server.login(username, password)
            
            for to_email in to_emails:
                msg['To'] = to_email
                server.send_message(msg)
                del msg['To']
            
            server.quit()
            logger.info(f"📧 Critical error notification sent to {len(to_emails)} recipients")
            
        except Exception as e:
            logger.error(f"❌ Email sending failed: {e}")
    
    def should_allow_trading(self, user_id: str = None, strategy_id: str = None, symbol: str = None) -> bool:
        """Check if trading should be allowed for given parameters"""
        
        # System-wide checks
        if self.trading_shutdown:
            return False
        
        if self.trading_paused:
            return False
        
        # User-specific check
        if user_id and user_id in self.paused_users:
            return False
        
        # Strategy-specific check
        if strategy_id and strategy_id in self.paused_strategies:
            return False
        
        # Symbol-specific check
        if symbol and symbol in self.paused_symbols:
            return False
        
        return True
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current error handling system status"""
        
        recent_errors = [
            error for error in self.error_history 
            if error.timestamp > datetime.now() - timedelta(hours=24)
        ]
        
        critical_errors_24h = [
            error for error in recent_errors 
            if error.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]
        ]
        
        return {
            'trading_allowed': not (self.trading_paused or self.trading_shutdown),
            'trading_paused': self.trading_paused,
            'trading_shutdown': self.trading_shutdown,
            'active_critical_errors': len(self.critical_errors_active),
            'paused_users_count': len(self.paused_users),
            'paused_strategies_count': len(self.paused_strategies),
            'paused_symbols_count': len(self.paused_symbols),
            'total_errors_handled': self.total_errors_handled,
            'critical_errors_prevented': self.critical_errors_prevented,
            'errors_last_24h': len(recent_errors),
            'critical_errors_last_24h': len(critical_errors_24h),
            'financial_losses_prevented': self.financial_losses_prevented,
            'error_rules_active': len(self.error_rules)
        }
    
    async def resolve_critical_error(self, error_id: str, resolution_notes: str = "") -> bool:
        """Mark a critical error as resolved and potentially resume trading"""
        
        # Find the error
        error_record = None
        for error in self.error_history:
            if error.error_id == error_id:
                error_record = error
                break
        
        if not error_record:
            logger.error(f"❌ Error {error_id} not found")
            return False
        
        # Mark as resolved
        error_record.recovery_successful = True
        error_record.resolution_notes = resolution_notes
        
        # Remove from active critical errors
        self.critical_errors_active.discard(error_id)
        
        # Check if we can resume trading
        if not self.critical_errors_active:
            self.trading_paused = False
            self.trading_shutdown = False
            logger.info(f"✅ Critical error {error_id} resolved - Trading can resume")
            return True
        else:
            logger.info(f"✅ Critical error {error_id} resolved - {len(self.critical_errors_active)} critical errors still active")
            return False

# Global critical error handler
_critical_error_handler = None

def get_critical_error_handler() -> CriticalErrorHandler:
    """Get global critical error handler instance"""
    global _critical_error_handler
    if _critical_error_handler is None:
        _critical_error_handler = CriticalErrorHandler()
    return _critical_error_handler 