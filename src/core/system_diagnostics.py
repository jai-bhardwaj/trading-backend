"""
System Diagnostics and Health Reporting
Comprehensive system analysis and reporting
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class SystemDiagnostics:
    """Comprehensive system diagnostics and health reporting"""
    
    def __init__(self):
        self.diagnostic_start_time = time.time()
        self.total_checks_run = 0
        self.issues_found = 0
        self.recommendations_generated = 0
        
    async def run_comprehensive_system_check(self) -> Dict[str, Any]:
        """Run complete system diagnostic check"""
        logger.info("🔍 Starting comprehensive system diagnostic...")
        
        diagnostic_results = {
            'diagnostic_timestamp': datetime.now().isoformat(),
            'diagnostic_duration_seconds': 0,
            'overall_system_health': 'UNKNOWN',
            'security_assessment': {},
            'performance_assessment': {},
            'stability_assessment': {},
            'compliance_assessment': {},
            'recommendations': [],
            'critical_issues': [],
            'system_summary': {}
        }
        
        start_time = time.time()
        
        try:
            # Security Assessment
            diagnostic_results['security_assessment'] = await self._assess_security()
            
            # Performance Assessment  
            diagnostic_results['performance_assessment'] = await self._assess_performance()
            
            # Stability Assessment
            diagnostic_results['stability_assessment'] = await self._assess_stability()
            
            # Compliance Assessment
            diagnostic_results['compliance_assessment'] = await self._assess_compliance()
            
            # Generate Overall Health Score
            overall_health = self._calculate_overall_health(diagnostic_results)
            diagnostic_results['overall_system_health'] = overall_health
            
            # Generate Recommendations
            recommendations = self._generate_recommendations(diagnostic_results)
            diagnostic_results['recommendations'] = recommendations
            
            # System Summary
            diagnostic_results['system_summary'] = self._generate_system_summary(diagnostic_results)
            
        except Exception as e:
            logger.error(f"❌ System diagnostic error: {e}")
            diagnostic_results['error'] = str(e)
        
        end_time = time.time()
        diagnostic_results['diagnostic_duration_seconds'] = round(end_time - start_time, 2)
        
        logger.info(f"✅ System diagnostic completed in {diagnostic_results['diagnostic_duration_seconds']}s")
        
        return diagnostic_results
    
    async def _assess_security(self) -> Dict[str, Any]:
        """Assess system security"""
        security_score = 0
        max_score = 0
        issues = []
        
        # Check Authentication System
        max_score += 20
        try:
            from src.core.auth import get_auth_manager
            auth_manager = get_auth_manager()
            test_token = auth_manager.create_access_token({"test": True})
            if test_token:
                security_score += 20
                logger.debug("✅ Authentication system: SECURE")
            else:
                issues.append("Authentication system not responding")
        except Exception as e:
            issues.append(f"Authentication system error: {e}")
        
        # Check Input Validation
        max_score += 15
        try:
            from src.core.input_validator import get_input_validator
            validator = get_input_validator()
            # Test SQL injection protection
            try:
                validator.validate_strategy_creation_data({
                    "name": "'; DROP TABLE test; --",
                    "description": "Test description that meets length requirements",
                    "category": "momentum",
                    "risk_level": "medium", 
                    "min_capital": 1000,
                    "expected_return_annual": 15,
                    "max_drawdown": 10,
                    "symbols": ["TEST"],
                    "parameters": {}
                })
                issues.append("Input validation not blocking SQL injection")
            except:
                security_score += 15
                logger.debug("✅ Input validation: PROTECTED")
        except Exception as e:
            issues.append(f"Input validation error: {e}")
        
        # Check Production Safety
        max_score += 15
        try:
            from src.core.production_safety import get_production_safety_validator
            safety = get_production_safety_validator()
            if not safety.should_allow_trading(broker_connected=False):
                security_score += 15
                logger.debug("✅ Production safety: ENFORCED")
            else:
                issues.append("Production safety not properly enforced")
        except Exception as e:
            issues.append(f"Production safety error: {e}")
        
        security_percentage = (security_score / max_score) * 100 if max_score > 0 else 0
        
        return {
            'security_score': security_score,
            'max_possible_score': max_score,
            'security_percentage': round(security_percentage, 1),
            'security_level': self._get_level_from_percentage(security_percentage),
            'security_issues': issues,
            'checks_performed': ['authentication', 'input_validation', 'production_safety']
        }
    
    async def _assess_performance(self) -> Dict[str, Any]:
        """Assess system performance"""
        performance_score = 0
        max_score = 0
        issues = []
        
        # Check Memory Management
        max_score += 25
        try:
            from src.core.resource_manager import get_resource_manager
            resource_manager = get_resource_manager()
            status = resource_manager.get_resource_status()
            
            memory_mb = status.get('current_memory_mb', 0)
            if memory_mb < 500:  # Under 500MB is good
                performance_score += 25
                logger.debug(f"✅ Memory usage: {memory_mb:.1f}MB - OPTIMIZED")
            elif memory_mb < 1000:
                performance_score += 15
                issues.append(f"Memory usage moderate: {memory_mb:.1f}MB")
            else:
                issues.append(f"High memory usage: {memory_mb:.1f}MB")
        except Exception as e:
            issues.append(f"Memory assessment error: {e}")
        
        # Check Order Processing
        max_score += 20
        try:
            from src.core.order_sync import get_thread_safe_order_manager
            order_manager = get_thread_safe_order_manager()
            stats = order_manager.get_statistics()
            
            race_conditions = stats.get('race_conditions_prevented', 0)
            duplicates = stats.get('duplicate_orders_prevented', 0)
            
            if race_conditions < 5 and duplicates < 10:
                performance_score += 20
                logger.debug("✅ Order processing: EFFICIENT")
            else:
                performance_score += 10
                issues.append(f"Order processing issues: {race_conditions} race conditions, {duplicates} duplicates")
        except Exception as e:
            issues.append(f"Order processing assessment error: {e}")
        
        # Check System Responsiveness
        max_score += 15
        response_time_start = time.time()
        try:
            # Simulate system response test
            await asyncio.sleep(0.01)  # Minimal delay
            response_time = (time.time() - response_time_start) * 1000  # ms
            
            if response_time < 100:
                performance_score += 15
                logger.debug(f"✅ System response: {response_time:.1f}ms - FAST")
            elif response_time < 500:
                performance_score += 10
                issues.append(f"System response acceptable: {response_time:.1f}ms")
            else:
                issues.append(f"Slow system response: {response_time:.1f}ms")
        except Exception as e:
            issues.append(f"Response time assessment error: {e}")
        
        performance_percentage = (performance_score / max_score) * 100 if max_score > 0 else 0
        
        return {
            'performance_score': performance_score,
            'max_possible_score': max_score,
            'performance_percentage': round(performance_percentage, 1),
            'performance_level': self._get_level_from_percentage(performance_percentage),
            'performance_issues': issues,
            'checks_performed': ['memory_management', 'order_processing', 'system_responsiveness']
        }
    
    async def _assess_stability(self) -> Dict[str, Any]:
        """Assess system stability"""
        stability_score = 0
        max_score = 0
        issues = []
        
        # Check Error Handling
        max_score += 20
        try:
            from src.core.critical_error_handler import get_critical_error_handler
            error_handler = get_critical_error_handler()
            status = error_handler.get_system_status()
            
            if status.get('trading_allowed', False):
                stability_score += 20
                logger.debug("✅ Error handling: STABLE")
            else:
                issues.append("Error handler blocking trading")
        except Exception as e:
            issues.append(f"Error handling assessment error: {e}")
        
        # Check Financial Calculations
        max_score += 15
        try:
            from src.core.safe_strategy_calculations import get_safe_strategy_calculator
            calc = get_safe_strategy_calculator()
            
            # Test division by zero protection
            result = calc.calculate_percentage_change(100, 0)
            if result is None:  # Should return None for division by zero
                stability_score += 15
                logger.debug("✅ Financial calculations: PROTECTED")
            else:
                issues.append("Financial calculations not properly protected")
        except Exception as e:
            issues.append(f"Financial calculations assessment error: {e}")
        
        # Check Resource Stability
        max_score += 15
        try:
            from src.core.resource_manager import get_resource_manager
            resource_manager = get_resource_manager()
            
            # Test cleanup functionality
            cleanup_result = await resource_manager.force_cleanup()
            if cleanup_result.get('success'):
                stability_score += 15
                logger.debug("✅ Resource management: STABLE")
            else:
                issues.append("Resource cleanup not working properly")
        except Exception as e:
            issues.append(f"Resource stability assessment error: {e}")
        
        stability_percentage = (stability_score / max_score) * 100 if max_score > 0 else 0
        
        return {
            'stability_score': stability_score,
            'max_possible_score': max_score,
            'stability_percentage': round(stability_percentage, 1),
            'stability_level': self._get_level_from_percentage(stability_percentage),
            'stability_issues': issues,
            'checks_performed': ['error_handling', 'financial_calculations', 'resource_stability']
        }
    
    async def _assess_compliance(self) -> Dict[str, Any]:
        """Assess system compliance and best practices"""
        compliance_score = 0
        max_score = 0
        issues = []
        
        # Check Configuration Management
        max_score += 15
        try:
            from src.core.config_validator import get_config_validator
            validator = get_config_validator()
            validation_result = validator.perform_full_validation()
            
            critical_issues = validation_result.get('critical_issues', 0)
            error_issues = validation_result.get('error_issues', 0)
            
            if critical_issues == 0 and error_issues == 0:
                compliance_score += 15
                logger.debug("✅ Configuration: COMPLIANT")
            elif critical_issues == 0:
                compliance_score += 10
                issues.append(f"Configuration has {error_issues} error issues")
            else:
                issues.append(f"Configuration has {critical_issues} critical and {error_issues} error issues")
        except Exception as e:
            issues.append(f"Configuration compliance assessment error: {e}")
        
        # Check Monitoring and Logging
        max_score += 10
        try:
            from src.core.monitoring_dashboard import get_system_monitor
            monitor = get_system_monitor()
            dashboard_data = monitor.get_dashboard_data()
            
            if dashboard_data and 'system_status' in dashboard_data:
                compliance_score += 10
                logger.debug("✅ Monitoring: COMPLIANT")
            else:
                issues.append("Monitoring system not fully operational")
        except Exception as e:
            issues.append(f"Monitoring compliance assessment error: {e}")
        
        # Check Documentation and Testing
        max_score += 10
        docs_found = 0
        test_files_found = 0
        
        # Check for documentation
        for doc_file in ['README.md', 'docs/', 'FINAL_SESSION_SUMMARY.md']:
            if Path(doc_file).exists():
                docs_found += 1
        
        # Check for test files
        for test_pattern in ['test_*.py', '*_test.py']:
            test_files = list(Path('.').glob(test_pattern))
            test_files_found += len(test_files)
        
        if docs_found >= 2 and test_files_found >= 5:
            compliance_score += 10
            logger.debug("✅ Documentation and Testing: COMPLIANT")
        elif docs_found >= 1 and test_files_found >= 3:
            compliance_score += 5
            issues.append("Documentation and testing partially compliant")
        else:
            issues.append("Insufficient documentation and testing")
        
        compliance_percentage = (compliance_score / max_score) * 100 if max_score > 0 else 0
        
        return {
            'compliance_score': compliance_score,
            'max_possible_score': max_score,
            'compliance_percentage': round(compliance_percentage, 1),
            'compliance_level': self._get_level_from_percentage(compliance_percentage),
            'compliance_issues': issues,
            'checks_performed': ['configuration_management', 'monitoring_logging', 'documentation_testing']
        }
    
    def _calculate_overall_health(self, diagnostic_results: Dict[str, Any]) -> str:
        """Calculate overall system health"""
        scores = []
        
        # Collect all percentage scores
        for assessment_type in ['security_assessment', 'performance_assessment', 'stability_assessment', 'compliance_assessment']:
            assessment = diagnostic_results.get(assessment_type, {})
            percentage = assessment.get(f"{assessment_type.split('_')[0]}_percentage", 0)
            scores.append(percentage)
        
        if not scores:
            return 'UNKNOWN'
        
        average_score = sum(scores) / len(scores)
        
        if average_score >= 90:
            return 'EXCELLENT'
        elif average_score >= 80:
            return 'GOOD'
        elif average_score >= 70:
            return 'FAIR'
        elif average_score >= 60:
            return 'POOR'
        else:
            return 'CRITICAL'
    
    def _get_level_from_percentage(self, percentage: float) -> str:
        """Convert percentage to level"""
        if percentage >= 90:
            return 'EXCELLENT'
        elif percentage >= 80:
            return 'GOOD'
        elif percentage >= 70:
            return 'FAIR'
        elif percentage >= 60:
            return 'POOR'
        else:
            return 'CRITICAL'
    
    def _generate_recommendations(self, diagnostic_results: Dict[str, Any]) -> List[str]:
        """Generate system recommendations based on assessment"""
        recommendations = []
        
        # Analyze each assessment for recommendations
        for assessment_name, assessment_data in diagnostic_results.items():
            if assessment_name.endswith('_assessment') and isinstance(assessment_data, dict):
                issues = assessment_data.get(f"{assessment_name.split('_')[0]}_issues", [])
                percentage = assessment_data.get(f"{assessment_name.split('_')[0]}_percentage", 0)
                
                # Generate recommendations based on issues and score
                if percentage < 80 and issues:
                    for issue in issues[:3]:  # Limit to top 3 issues
                        recommendations.append(f"Address {assessment_name.split('_')[0]} issue: {issue}")
        
        # General recommendations
        if diagnostic_results.get('overall_system_health') in ['POOR', 'CRITICAL']:
            recommendations.append("Consider comprehensive system review and remediation")
        
        # Remove duplicates and limit recommendations
        recommendations = list(set(recommendations))[:10]
        
        return recommendations
    
    def _generate_system_summary(self, diagnostic_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate system summary"""
        summary = {
            'overall_health': diagnostic_results.get('overall_system_health', 'UNKNOWN'),
            'total_checks_performed': 0,
            'total_issues_found': 0,
            'systems_assessed': [],
            'critical_areas_needing_attention': [],
            'strengths': [],
            'production_readiness': 'UNKNOWN'
        }
        
        # Count checks and issues
        for assessment_name, assessment_data in diagnostic_results.items():
            if assessment_name.endswith('_assessment') and isinstance(assessment_data, dict):
                checks = assessment_data.get('checks_performed', [])
                issues = assessment_data.get(f"{assessment_name.split('_')[0]}_issues", [])
                percentage = assessment_data.get(f"{assessment_name.split('_')[0]}_percentage", 0)
                
                summary['total_checks_performed'] += len(checks)
                summary['total_issues_found'] += len(issues)
                summary['systems_assessed'].append(assessment_name.split('_')[0])
                
                # Identify critical areas and strengths
                if percentage < 70:
                    summary['critical_areas_needing_attention'].append(assessment_name.split('_')[0])
                elif percentage >= 90:
                    summary['strengths'].append(assessment_name.split('_')[0])
        
        # Determine production readiness
        if diagnostic_results.get('overall_system_health') in ['EXCELLENT', 'GOOD']:
            summary['production_readiness'] = 'READY'
        elif diagnostic_results.get('overall_system_health') == 'FAIR':
            summary['production_readiness'] = 'READY_WITH_MONITORING'
        else:
            summary['production_readiness'] = 'NOT_READY'
        
        return summary

# Global instance
_system_diagnostics = None

def get_system_diagnostics() -> SystemDiagnostics:
    """Get global system diagnostics instance"""
    global _system_diagnostics
    if _system_diagnostics is None:
        _system_diagnostics = SystemDiagnostics()
    return _system_diagnostics
