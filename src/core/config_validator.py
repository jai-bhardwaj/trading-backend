"""
Configuration Validation System
Validates all configuration files and environment variables
"""

import os
import json
from datetime import datetime
import yaml
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ConfigSeverity(Enum):
    """Configuration issue severity"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class ConfigIssue:
    """Configuration validation issue"""
    severity: ConfigSeverity
    category: str
    field: str
    message: str
    current_value: Any = None
    recommended_value: Any = None

class TradingConfigValidator:
    """Validates trading system configuration"""
    
    def __init__(self):
        self.issues: List[ConfigIssue] = []
        self.config_files_checked = []
        
    def validate_environment_variables(self) -> List[ConfigIssue]:
        """Validate critical environment variables"""
        issues = []
        
        # Critical trading environment variables
        critical_vars = [
            'ANGEL_ONE_API_KEY',
            'ANGEL_ONE_SECRET_KEY', 
            'ANGEL_ONE_CLIENT_ID',
            'ANGEL_ONE_PIN'
        ]
        
        # Optional but recommended
        recommended_vars = [
            'ANGEL_ONE_TOTP_SECRET',
            'DATABASE_URL',
            'JWT_SECRET_KEY',
            'TRADING_MODE'  # LIVE or PAPER
        ]
        
        # Check critical variables
        for var in critical_vars:
            value = os.getenv(var)
            if not value:
                issues.append(ConfigIssue(
                    severity=ConfigSeverity.CRITICAL,
                    category="environment",
                    field=var,
                    message=f"Critical environment variable {var} is missing",
                    recommended_value="<your_broker_credential>"
                ))
            elif len(value) < 8:
                issues.append(ConfigIssue(
                    severity=ConfigSeverity.ERROR,
                    category="environment", 
                    field=var,
                    message=f"Environment variable {var} appears too short",
                    current_value=f"'{value[:3]}***' (length: {len(value)})",
                    recommended_value="Valid credential string"
                ))
        
        # Check recommended variables
        for var in recommended_vars:
            value = os.getenv(var)
            if not value:
                issues.append(ConfigIssue(
                    severity=ConfigSeverity.WARNING,
                    category="environment",
                    field=var,
                    message=f"Recommended environment variable {var} is missing",
                    recommended_value="<appropriate_value>"
                ))
        
        # Validate trading mode
        trading_mode = os.getenv('TRADING_MODE', 'PAPER').upper()
        if trading_mode not in ['LIVE', 'PAPER']:
            issues.append(ConfigIssue(
                severity=ConfigSeverity.ERROR,
                category="environment",
                field="TRADING_MODE",
                message=f"Invalid TRADING_MODE: {trading_mode}",
                current_value=trading_mode,
                recommended_value="LIVE or PAPER"
            ))
        
        # Security check for production
        if trading_mode == 'LIVE':
            if not os.getenv('JWT_SECRET_KEY'):
                issues.append(ConfigIssue(
                    severity=ConfigSeverity.CRITICAL,
                    category="security",
                    field="JWT_SECRET_KEY",
                    message="JWT_SECRET_KEY required for live trading",
                    recommended_value="Strong random secret"
                ))
        
        return issues
    
    def validate_config_files(self) -> List[ConfigIssue]:
        """Validate configuration files"""
        issues = []
        config_dir = Path("config")
        
        if not config_dir.exists():
            issues.append(ConfigIssue(
                severity=ConfigSeverity.WARNING,
                category="files",
                field="config_directory",
                message="Config directory 'config/' not found",
                recommended_value="Create config/ directory"
            ))
            return issues
        
        # Check for required config files
        required_files = [
            'trading_config.json',
            'strategy_config.json'
        ]
        
        for file_name in required_files:
            file_path = config_dir / file_name
            if not file_path.exists():
                issues.append(ConfigIssue(
                    severity=ConfigSeverity.WARNING,
                    category="files",
                    field=file_name,
                    message=f"Configuration file {file_name} not found",
                    recommended_value=f"Create {file_path}"
                ))
            else:
                # Validate file content
                try:
                    with open(file_path, 'r') as f:
                        config_data = json.load(f)
                    
                    file_issues = self._validate_config_content(file_name, config_data)
                    issues.extend(file_issues)
                    self.config_files_checked.append(file_name)
                    
                except json.JSONDecodeError as e:
                    issues.append(ConfigIssue(
                        severity=ConfigSeverity.ERROR,
                        category="files",
                        field=file_name,
                        message=f"Invalid JSON in {file_name}: {e}",
                        recommended_value="Fix JSON syntax"
                    ))
                except Exception as e:
                    issues.append(ConfigIssue(
                        severity=ConfigSeverity.ERROR,
                        category="files",
                        field=file_name,
                        message=f"Error reading {file_name}: {e}",
                        recommended_value="Check file permissions"
                    ))
        
        return issues
    
    def _validate_config_content(self, file_name: str, config_data: Dict[str, Any]) -> List[ConfigIssue]:
        """Validate configuration file content"""
        issues = []
        
        if file_name == 'trading_config.json':
            issues.extend(self._validate_trading_config(config_data))
        elif file_name == 'strategy_config.json':
            issues.extend(self._validate_strategy_config(config_data))
        
        return issues
    
    def _validate_trading_config(self, config: Dict[str, Any]) -> List[ConfigIssue]:
        """Validate trading configuration"""
        issues = []
        
        # Check required fields
        required_fields = {
            'max_capital_per_trade': (int, float),
            'max_positions': int,
            'risk_percentage': (int, float),
            'enable_paper_trading': bool
        }
        
        for field, expected_type in required_fields.items():
            if field not in config:
                issues.append(ConfigIssue(
                    severity=ConfigSeverity.ERROR,
                    category="trading_config",
                    field=field,
                    message=f"Required field '{field}' missing from trading config",
                    recommended_value=f"Add {field} with appropriate value"
                ))
            else:
                value = config[field]
                if not isinstance(value, expected_type):
                    issues.append(ConfigIssue(
                        severity=ConfigSeverity.ERROR,
                        category="trading_config",
                        field=field,
                        message=f"Field '{field}' has wrong type",
                        current_value=f"{type(value).__name__}: {value}",
                        recommended_value=f"{expected_type.__name__ if not isinstance(expected_type, tuple) else ' or '.join(t.__name__ for t in expected_type)}"
                    ))
        
        # Validate value ranges
        if 'risk_percentage' in config:
            risk = config['risk_percentage']
            if isinstance(risk, (int, float)):
                if risk < 0 or risk > 100:
                    issues.append(ConfigIssue(
                        severity=ConfigSeverity.ERROR,
                        category="trading_config",
                        field="risk_percentage",
                        message="Risk percentage must be between 0-100",
                        current_value=risk,
                        recommended_value="1-10 for conservative, 10-25 for moderate"
                    ))
                elif risk > 50:
                    issues.append(ConfigIssue(
                        severity=ConfigSeverity.WARNING,
                        category="trading_config",
                        field="risk_percentage",
                        message="Risk percentage is very high",
                        current_value=risk,
                        recommended_value="Consider reducing to <25%"
                    ))
        
        if 'max_positions' in config:
            max_pos = config['max_positions']
            if isinstance(max_pos, int):
                if max_pos < 1:
                    issues.append(ConfigIssue(
                        severity=ConfigSeverity.ERROR,
                        category="trading_config",
                        field="max_positions",
                        message="Max positions must be at least 1",
                        current_value=max_pos,
                        recommended_value="5-20 depending on capital"
                    ))
                elif max_pos > 100:
                    issues.append(ConfigIssue(
                        severity=ConfigSeverity.WARNING,
                        category="trading_config",
                        field="max_positions",
                        message="Max positions is very high",
                        current_value=max_pos,
                        recommended_value="Consider reducing for better risk management"
                    ))
        
        return issues
    
    def _validate_strategy_config(self, config: Dict[str, Any]) -> List[ConfigIssue]:
        """Validate strategy configuration"""
        issues = []
        
        if 'strategies' not in config:
            issues.append(ConfigIssue(
                severity=ConfigSeverity.WARNING,
                category="strategy_config",
                field="strategies",
                message="No strategies defined in strategy config",
                recommended_value="Add at least one strategy configuration"
            ))
            return issues
        
        strategies = config['strategies']
        if not isinstance(strategies, dict):
            issues.append(ConfigIssue(
                severity=ConfigSeverity.ERROR,
                category="strategy_config",
                field="strategies",
                message="Strategies should be a dictionary",
                current_value=type(strategies).__name__,
                recommended_value="Dictionary with strategy_id as keys"
            ))
            return issues
        
        # Validate each strategy
        for strategy_id, strategy_config in strategies.items():
            if not isinstance(strategy_config, dict):
                issues.append(ConfigIssue(
                    severity=ConfigSeverity.ERROR,
                    category="strategy_config",
                    field=f"strategies.{strategy_id}",
                    message=f"Strategy {strategy_id} config should be a dictionary",
                    current_value=type(strategy_config).__name__,
                    recommended_value="Dictionary with strategy parameters"
                ))
                continue
            
            # Check required strategy fields
            required_strategy_fields = ['enabled', 'risk_level', 'symbols']
            for field in required_strategy_fields:
                if field not in strategy_config:
                    issues.append(ConfigIssue(
                        severity=ConfigSeverity.WARNING,
                        category="strategy_config",
                        field=f"strategies.{strategy_id}.{field}",
                        message=f"Strategy {strategy_id} missing field '{field}'",
                        recommended_value="Add required field"
                    ))
        
        return issues
    
    def validate_docker_config(self) -> List[ConfigIssue]:
        """Validate Docker configuration"""
        issues = []
        
        # Check for docker-compose.yml
        docker_compose_files = ['docker-compose.yml', 'docker-compose.yaml']
        docker_compose_found = False
        
        for file_name in docker_compose_files:
            if Path(file_name).exists():
                docker_compose_found = True
                try:
                    with open(file_name, 'r') as f:
                        docker_config = yaml.safe_load(f)
                    
                    # Validate Docker Compose content
                    if 'services' not in docker_config:
                        issues.append(ConfigIssue(
                            severity=ConfigSeverity.ERROR,
                            category="docker",
                            field="services",
                            message="No services defined in docker-compose.yml",
                            recommended_value="Add service definitions"
                        ))
                    
                    # Check for security issues
                    services = docker_config.get('services', {})
                    for service_name, service_config in services.items():
                        if isinstance(service_config, dict):
                            # Check for exposed ports
                            if 'ports' in service_config:
                                ports = service_config['ports']
                                for port_mapping in ports:
                                    if '0.0.0.0:' in str(port_mapping):
                                        issues.append(ConfigIssue(
                                            severity=ConfigSeverity.WARNING,
                                            category="docker_security",
                                            field=f"services.{service_name}.ports",
                                            message=f"Service {service_name} binds to all interfaces (0.0.0.0)",
                                            current_value=port_mapping,
                                            recommended_value="Bind to localhost (127.0.0.1) for security"
                                        ))
                            
                            # Check for privileged mode
                            if service_config.get('privileged'):
                                issues.append(ConfigIssue(
                                    severity=ConfigSeverity.WARNING,
                                    category="docker_security",
                                    field=f"services.{service_name}.privileged",
                                    message=f"Service {service_name} runs in privileged mode",
                                    current_value=True,
                                    recommended_value="Remove privileged mode unless absolutely necessary"
                                ))
                                
                except yaml.YAMLError as e:
                    issues.append(ConfigIssue(
                        severity=ConfigSeverity.ERROR,
                        category="docker",
                        field=file_name,
                        message=f"Invalid YAML in {file_name}: {e}",
                        recommended_value="Fix YAML syntax"
                    ))
                break
        
        if not docker_compose_found:
            issues.append(ConfigIssue(
                severity=ConfigSeverity.INFO,
                category="docker",
                field="docker-compose.yml",
                message="Docker Compose file not found",
                recommended_value="Consider adding docker-compose.yml for easier deployment"
            ))
        
        return issues
    
    def perform_full_validation(self) -> Dict[str, Any]:
        """Perform comprehensive configuration validation"""
        self.issues.clear()
        self.config_files_checked.clear()
        
        logger.info("🔍 Starting comprehensive configuration validation...")
        
        # Validate all configuration aspects
        env_issues = self.validate_environment_variables()
        file_issues = self.validate_config_files()
        docker_issues = self.validate_docker_config()
        
        all_issues = env_issues + file_issues + docker_issues
        self.issues = all_issues
        
        # Categorize issues by severity
        critical_issues = [i for i in all_issues if i.severity == ConfigSeverity.CRITICAL]
        error_issues = [i for i in all_issues if i.severity == ConfigSeverity.ERROR]
        warning_issues = [i for i in all_issues if i.severity == ConfigSeverity.WARNING]
        info_issues = [i for i in all_issues if i.severity == ConfigSeverity.INFO]
        
        # Log summary
        logger.info(f"📊 Configuration validation complete:")
        logger.info(f"   🔴 Critical issues: {len(critical_issues)}")
        logger.info(f"   ❌ Error issues: {len(error_issues)}")
        logger.info(f"   ⚠️ Warning issues: {len(warning_issues)}")
        logger.info(f"   ℹ️ Info issues: {len(info_issues)}")
        
        return {
            'total_issues': len(all_issues),
            'critical_issues': len(critical_issues),
            'error_issues': len(error_issues),
            'warning_issues': len(warning_issues),
            'info_issues': len(info_issues),
            'config_files_checked': self.config_files_checked,
            'issues': [
                {
                    'severity': issue.severity.value,
                    'category': issue.category,
                    'field': issue.field,
                    'message': issue.message,
                    'current_value': issue.current_value,
                    'recommended_value': issue.recommended_value
                }
                for issue in all_issues
            ],
            'validation_timestamp': datetime.now().isoformat(),
            'production_ready': len(critical_issues) == 0 and len(error_issues) == 0
        }

# Global instance
_config_validator = None

def get_config_validator() -> TradingConfigValidator:
    """Get global configuration validator"""
    global _config_validator
    if _config_validator is None:
        _config_validator = TradingConfigValidator()
    return _config_validator
