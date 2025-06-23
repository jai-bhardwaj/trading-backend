"""
Critical Error Handling System

This module provides fail-fast error handling to prevent the system from
continuing with corrupted state. It includes:
- Circuit breaker pattern for external services
- System health monitoring
- Graceful degradation strategies
- Error categorization and routing
- Emergency shutdown capabilities
"""

import logging
import threading
import time
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import traceback
import sys
import signal
import os

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"

class SystemComponent(Enum):
    """System components for error tracking"""
    DATABASE = "database"
    BROKER_API = "broker_api"
    MARKET_DATA = "market_data"
    ORDER_MANAGEMENT = "order_management"
    AUTHENTICATION = "authentication"
    STRATEGY_ENGINE = "strategy_engine"
    RISK_MANAGEMENT = "risk_management"
    MEMORY_MANAGER = "memory_manager"
    WEBSOCKET = "websocket"
    GENERAL = "general"

class ErrorAction(Enum):
    """Actions to take when errors occur"""
    CONTINUE = "continue"           # Log and continue
    RETRY = "retry"                 # Retry operation
    DEGRADE = "degrade"            # Switch to degraded mode
    CIRCUIT_BREAK = "circuit_break" # Open circuit breaker
    SHUTDOWN = "shutdown"           # Graceful shutdown
    EMERGENCY_STOP = "emergency_stop" # Immediate stop

@dataclass
class ErrorRule:
    """Error handling rule"""
    component: SystemComponent
    error_pattern: str  # Regex pattern or error type
    max_occurrences: int
    time_window_seconds: int
    action: ErrorAction
    description: str = ""

@dataclass
class ErrorEvent:
    """Error event record"""
    timestamp: float
    component: SystemComponent
    severity: ErrorSeverity
    error_type: str
    message: str
    traceback_str: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False

class CircuitBreaker:
    """Circuit breaker for external service calls"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60,
                 expected_exception: Exception = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap functions with circuit breaker"""
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call function with circuit breaker protection"""
        with self._lock:
            if self.state == 'OPEN':
                if self._should_attempt_reset():
                    self.state = 'HALF_OPEN'
                else:
                    raise Exception(f"Circuit breaker is OPEN. Service unavailable.")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit breaker"""
        return (self.last_failure_time and 
                time.time() - self.last_failure_time >= self.recovery_timeout)
    
    def _on_success(self):
        """Handle successful operation"""
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def _on_failure(self):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'

class CriticalErrorHandler:
    """
    Critical error handling system with fail-fast capabilities
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        self._error_events: deque = deque(maxlen=10000)  # Rolling error log
        self._component_errors: Dict[SystemComponent, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._error_rules: List[ErrorRule] = []
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._system_health: Dict[SystemComponent, bool] = {comp: True for comp in SystemComponent}
        self._shutdown_callbacks: List[Callable] = []
        self._emergency_mode = False
        self._shutdown_initiated = False
        
        # Setup default error rules
        self._setup_default_rules()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _setup_default_rules(self):
        """Setup default error handling rules"""
        default_rules = [
            # Database connection errors
            ErrorRule(
                component=SystemComponent.DATABASE,
                error_pattern="connection.*error|timeout",
                max_occurrences=3,
                time_window_seconds=300,
                action=ErrorAction.CIRCUIT_BREAK,
                description="Database connection failures"
            ),
            
            # Broker API errors
            ErrorRule(
                component=SystemComponent.BROKER_API,
                error_pattern="unauthorized|forbidden|api.*error",
                max_occurrences=5,
                time_window_seconds=300,
                action=ErrorAction.CIRCUIT_BREAK,
                description="Broker API authentication/permission errors"
            ),
            
            # Market data errors
            ErrorRule(
                component=SystemComponent.MARKET_DATA,
                error_pattern="websocket.*disconnect|stream.*error",
                max_occurrences=10,
                time_window_seconds=600,
                action=ErrorAction.DEGRADE,
                description="Market data connectivity issues"
            ),
            
            # Order management critical errors
            ErrorRule(
                component=SystemComponent.ORDER_MANAGEMENT,
                error_pattern="order.*validation.*failed|duplicate.*order",
                max_occurrences=20,
                time_window_seconds=300,
                action=ErrorAction.DEGRADE,
                description="Order validation failures"
            ),
            
            # Memory errors
            ErrorRule(
                component=SystemComponent.MEMORY_MANAGER,
                error_pattern="memory.*error|out.*of.*memory",
                max_occurrences=1,
                time_window_seconds=60,
                action=ErrorAction.EMERGENCY_STOP,
                description="Critical memory issues"
            ),
            
            # Authentication failures
            ErrorRule(
                component=SystemComponent.AUTHENTICATION,
                error_pattern="authentication.*failed|token.*invalid",
                max_occurrences=50,
                time_window_seconds=300,
                action=ErrorAction.CIRCUIT_BREAK,
                description="Authentication system failures"
            )
        ]
        
        self._error_rules.extend(default_rules)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.warning(f"Received signal {signum}, initiating graceful shutdown")
        self.initiate_shutdown("Signal received")
    
    def add_error_rule(self, rule: ErrorRule):
        """Add custom error handling rule"""
        with self._lock:
            self._error_rules.append(rule)
            logger.info(f"Added error rule for {rule.component.value}: {rule.description}")
    
    def get_circuit_breaker(self, name: str, failure_threshold: int = 5, 
                           recovery_timeout: int = 60) -> CircuitBreaker:
        """Get or create circuit breaker for a service"""
        with self._lock:
            if name not in self._circuit_breakers:
                self._circuit_breakers[name] = CircuitBreaker(
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout
                )
            return self._circuit_breakers[name]
    
    def report_error(self, component: SystemComponent, severity: ErrorSeverity,
                    error: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Report error and determine if system should continue
        
        Returns:
            True if system can continue, False if should stop
        """
        try:
            with self._lock:
                # Create error event
                error_event = ErrorEvent(
                    timestamp=time.time(),
                    component=component,
                    severity=severity,
                    error_type=type(error).__name__,
                    message=str(error),
                    traceback_str=traceback.format_exc(),
                    context=context or {}
                )
                
                # Store error event
                self._error_events.append(error_event)
                self._component_errors[component].append(error_event)
                
                # Log error
                log_msg = f"[{component.value}] {severity.value.upper()}: {error_event.message}"
                if severity == ErrorSeverity.FATAL:
                    logger.critical(log_msg)
                elif severity == ErrorSeverity.CRITICAL:
                    logger.error(log_msg)
                elif severity == ErrorSeverity.ERROR:
                    logger.error(log_msg)
                elif severity == ErrorSeverity.WARNING:
                    logger.warning(log_msg)
                else:
                    logger.info(log_msg)
                
                # Check error rules and take action
                action = self._evaluate_error_rules(error_event)
                return self._execute_error_action(action, error_event)
                
        except Exception as e:
            # Error in error handler - log and continue
            logger.critical(f"Error in error handler: {e}")
            return True
    
    def _evaluate_error_rules(self, error_event: ErrorEvent) -> ErrorAction:
        """Evaluate error against rules and determine action"""
        import re
        
        current_time = error_event.timestamp
        
        for rule in self._error_rules:
            if rule.component != error_event.component:
                continue
            
            # Check if error matches pattern
            pattern_match = (
                re.search(rule.error_pattern, error_event.message, re.IGNORECASE) or
                re.search(rule.error_pattern, error_event.error_type, re.IGNORECASE)
            )
            
            if not pattern_match:
                continue
            
            # Count matching errors in time window
            cutoff_time = current_time - rule.time_window_seconds
            matching_errors = [
                event for event in self._component_errors[rule.component]
                if (event.timestamp >= cutoff_time and 
                    (re.search(rule.error_pattern, event.message, re.IGNORECASE) or
                     re.search(rule.error_pattern, event.error_type, re.IGNORECASE)))
            ]
            
            if len(matching_errors) >= rule.max_occurrences:
                logger.warning(f"Error rule triggered: {rule.description} "
                             f"({len(matching_errors)} occurrences in {rule.time_window_seconds}s)")
                return rule.action
        
        # Default action based on severity
        if error_event.severity == ErrorSeverity.FATAL:
            return ErrorAction.EMERGENCY_STOP
        elif error_event.severity == ErrorSeverity.CRITICAL:
            return ErrorAction.SHUTDOWN
        elif error_event.severity == ErrorSeverity.ERROR:
            return ErrorAction.DEGRADE
        else:
            return ErrorAction.CONTINUE
    
    def _execute_error_action(self, action: ErrorAction, error_event: ErrorEvent) -> bool:
        """
        Execute error action
        
        Returns:
            True if system can continue, False if should stop
        """
        component = error_event.component
        
        if action == ErrorAction.CONTINUE:
            return True
        
        elif action == ErrorAction.RETRY:
            logger.info(f"Retrying operation for {component.value}")
            return True
        
        elif action == ErrorAction.DEGRADE:
            logger.warning(f"Degrading {component.value} due to errors")
            self._system_health[component] = False
            return True
        
        elif action == ErrorAction.CIRCUIT_BREAK:
            logger.error(f"Circuit breaking {component.value}")
            self._system_health[component] = False
            # Mark circuit breaker for this component as open
            cb_name = f"component_{component.value}"
            cb = self.get_circuit_breaker(cb_name)
            cb.state = 'OPEN'
            cb.last_failure_time = time.time()
            return True
        
        elif action == ErrorAction.SHUTDOWN:
            logger.critical(f"Initiating graceful shutdown due to {component.value} errors")
            self.initiate_shutdown(f"Critical error in {component.value}")
            return False
        
        elif action == ErrorAction.EMERGENCY_STOP:
            logger.critical(f"EMERGENCY STOP due to {component.value} errors")
            self.emergency_stop(f"Fatal error in {component.value}")
            return False
        
        return True
    
    def add_shutdown_callback(self, callback: Callable):
        """Add callback to execute during shutdown"""
        with self._lock:
            self._shutdown_callbacks.append(callback)
    
    def initiate_shutdown(self, reason: str):
        """Initiate graceful shutdown"""
        if self._shutdown_initiated:
            return
        
        with self._lock:
            self._shutdown_initiated = True
            logger.critical(f"Initiating graceful shutdown: {reason}")
            
            # Execute shutdown callbacks
            for callback in self._shutdown_callbacks:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Error in shutdown callback: {e}")
            
            # Give time for cleanup
            time.sleep(2)
            
            logger.critical("Graceful shutdown complete")
            os._exit(1)
    
    def emergency_stop(self, reason: str):
        """Immediate emergency stop"""
        with self._lock:
            self._emergency_mode = True
            logger.critical(f"EMERGENCY STOP: {reason}")
            
            # Immediate exit without cleanup
            os._exit(2)
    
    def is_component_healthy(self, component: SystemComponent) -> bool:
        """Check if component is healthy"""
        with self._lock:
            return self._system_health.get(component, False)
    
    def get_system_health(self) -> Dict[str, bool]:
        """Get overall system health status"""
        with self._lock:
            return {comp.value: health for comp, health in self._system_health.items()}
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics"""
        with self._lock:
            component_error_counts = {}
            severity_counts = defaultdict(int)
            
            for event in self._error_events:
                component_error_counts[event.component.value] = component_error_counts.get(event.component.value, 0) + 1
                severity_counts[event.severity.value] += 1
            
            return {
                'total_errors': len(self._error_events),
                'component_errors': component_error_counts,
                'severity_distribution': dict(severity_counts),
                'system_health': self.get_system_health(),
                'circuit_breaker_status': {
                    name: {'state': cb.state, 'failure_count': cb.failure_count}
                    for name, cb in self._circuit_breakers.items()
                },
                'emergency_mode': self._emergency_mode,
                'shutdown_initiated': self._shutdown_initiated
            }
    
    def reset_component_health(self, component: SystemComponent):
        """Reset component health status"""
        with self._lock:
            self._system_health[component] = True
            logger.info(f"Reset health status for {component.value}")
    
    def clear_old_errors(self, older_than_hours: int = 24):
        """Clear old error events to prevent memory growth"""
        if older_than_hours <= 0:
            return
        
        cutoff_time = time.time() - (older_than_hours * 3600)
        
        with self._lock:
            # Clear from main error log
            self._error_events = deque(
                [event for event in self._error_events if event.timestamp >= cutoff_time],
                maxlen=self._error_events.maxlen
            )
            
            # Clear from component error logs
            for component, events in self._component_errors.items():
                self._component_errors[component] = deque(
                    [event for event in events if event.timestamp >= cutoff_time],
                    maxlen=events.maxlen
                )
            
            logger.info(f"Cleared error events older than {older_than_hours} hours")

# Global error handler instance
error_handler = CriticalErrorHandler()

# Convenience functions
def report_error(component: SystemComponent, severity: ErrorSeverity, 
                error: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
    """Report error to global error handler"""
    return error_handler.report_error(component, severity, error, context)

def get_circuit_breaker(name: str, failure_threshold: int = 5, 
                       recovery_timeout: int = 60) -> CircuitBreaker:
    """Get circuit breaker from global error handler"""
    return error_handler.get_circuit_breaker(name, failure_threshold, recovery_timeout)

def is_system_healthy() -> bool:
    """Check if all system components are healthy"""
    health_status = error_handler.get_system_health()
    return all(health_status.values()) 