"""
Enhanced Automatic Strategy Registry for Dynamic Strategy Discovery and Management

This module provides an advanced registry system that automatically discovers,
registers, and manages trading strategy implementations without manual intervention.
"""

import os
import sys
import importlib
import inspect
import logging
from typing import Dict, Type, List, Optional, Set, Any
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from .base import BaseStrategy, AssetClass

logger = logging.getLogger(__name__)

@dataclass
class StrategyMetadata:
    """Comprehensive metadata for registered strategies"""
    name: str
    class_name: str
    module_path: str
    asset_class: Optional[AssetClass]
    file_path: str
    description: str
    version: str
    author: str
    created_date: datetime
    last_modified: datetime
    dependencies: List[str]
    parameters: Dict[str, Any]
    is_active: bool = True

class AutomaticStrategyRegistry:
    """
    Enhanced automatic strategy registry with intelligent discovery
    
    Features:
    - Automatic strategy discovery by scanning directories
    - Multiple inheritance support (BaseStrategy and base_strategy.BaseStrategy)
    - Metadata extraction and validation
    - Hot-reload capability for development
    - Conflict resolution and versioning
    - Performance monitoring
    """
    
    _strategies: Dict[str, Type[BaseStrategy]] = {}
    _metadata: Dict[str, StrategyMetadata] = {}
    _asset_class_strategies: Dict[AssetClass, Set[str]] = {}
    _file_timestamps: Dict[str, float] = {}
    _discovery_paths: List[str] = []
    _initialized = False
    
    @classmethod
    def initialize(cls, base_path: str = None, auto_discover: bool = True):
        """
        Initialize the automatic strategy registry
        
        Args:
            base_path: Base path for strategy discovery (defaults to strategies directory)
            auto_discover: Whether to automatically discover strategies
        """
        if cls._initialized:
            logger.info("Strategy registry already initialized")
            return
        
        try:
            # Check if strategies are already manually registered
            manually_registered_count = len(cls._strategies)
            if manually_registered_count > 0:
                logger.info(f"📝 Found {manually_registered_count} manually registered strategies")
                auto_discover = False  # Disable auto-discovery to preserve manual registrations
            
            # Set up discovery paths
            if base_path is None:
                base_path = Path(__file__).parent
            
            cls._discovery_paths = [
                str(base_path),
                str(base_path / "equity"),
                str(base_path / "derivatives"), 
                str(base_path / "crypto"),
                str(base_path / "commodities"),
                str(base_path / "forex"),
            ]
            
            # Initialize asset class mapping
            for asset_class in AssetClass:
                cls._asset_class_strategies[asset_class] = set()
            
            if auto_discover:
                cls.discover_strategies()
            
            cls._initialized = True
            logger.info(f"✅ Automatic Strategy Registry initialized with {len(cls._strategies)} strategies")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize strategy registry: {e}")
            raise
    
    @classmethod
    def discover_strategies(cls, force_reload: bool = False):
        """
        Automatically discover and register all strategy classes
        
        Args:
            force_reload: Force reload even if files haven't changed
        """
        # Skip discovery if manually registered strategies exist
        if len(cls._strategies) > 0 and not force_reload:
            logger.info(f"📝 Skipping discovery - {len(cls._strategies)} manually registered strategies found")
            cls._log_registry_summary()
            return
        
        discovered_count = 0
        
        try:
            for discovery_path in cls._discovery_paths:
                if not os.path.exists(discovery_path):
                    continue
                
                logger.debug(f"🔍 Scanning directory: {discovery_path}")
                
                # Scan for Python files
                for root, dirs, files in os.walk(discovery_path):
                    # Skip __pycache__ and .git directories
                    dirs[:] = [d for d in dirs if not d.startswith('__') and d != '.git']
                    
                    for file in files:
                        if file.endswith('.py') and not file.startswith('__'):
                            file_path = os.path.join(root, file)
                            
                            # Check if file needs to be processed
                            if cls._should_process_file(file_path, force_reload):
                                strategies_found = cls._discover_strategies_in_file(file_path)
                                discovered_count += strategies_found
            
            logger.info(f"🎯 Discovery complete: {discovered_count} strategies found/updated")
            cls._log_registry_summary()
            
        except Exception as e:
            logger.error(f"❌ Error during strategy discovery: {e}")
    
    @classmethod
    def _should_process_file(cls, file_path: str, force_reload: bool) -> bool:
        """Check if a file should be processed for strategy discovery"""
        if force_reload:
            return True
        
        try:
            current_mtime = os.path.getmtime(file_path)
            last_processed = cls._file_timestamps.get(file_path, 0)
            return current_mtime > last_processed
        except OSError:
            return False
    
    @classmethod
    def _discover_strategies_in_file(cls, file_path: str) -> int:
        """Discover strategies in a specific file"""
        strategies_found = 0
        
        try:
            # Update file timestamp
            cls._file_timestamps[file_path] = os.path.getmtime(file_path)
            
            # Convert file path to module path
            module_path = cls._file_path_to_module_path(file_path)
            if not module_path:
                return 0
            
            # Import the module
            try:
                if module_path in sys.modules:
                    # Reload if already imported
                    module = importlib.reload(sys.modules[module_path])
                else:
                    module = importlib.import_module(module_path)
            except ImportError as e:
                logger.debug(f"Could not import {module_path}: {e}")
                return 0
            
            # Scan for strategy classes
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if cls._is_strategy_class(obj):
                    strategy_name = cls._generate_strategy_name(obj, name)
                    if cls._register_strategy_class(strategy_name, obj, file_path, module_path):
                        strategies_found += 1
                        logger.debug(f"✓ Registered strategy: {strategy_name}")
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
        
        return strategies_found
    
    @classmethod
    def _file_path_to_module_path(cls, file_path: str) -> Optional[str]:
        """Convert file path to Python module path"""
        try:
            # Find the app/strategies part in the path
            path_parts = Path(file_path).parts
            
            # Look for 'app' and 'strategies' in the path
            app_index = None
            for i, part in enumerate(path_parts):
                if part == 'app':
                    app_index = i
                    break
            
            if app_index is None:
                return None
            
            # Build module path from app onwards
            module_parts = path_parts[app_index:]
            
            # Remove .py extension from the last part
            if module_parts[-1].endswith('.py'):
                module_parts = module_parts[:-1] + (module_parts[-1][:-3],)
            
            return '.'.join(module_parts)
            
        except Exception as e:
            logger.debug(f"Could not convert {file_path} to module path: {e}")
            return None
    
    @classmethod
    def _is_strategy_class(cls, obj: type) -> bool:
        """Check if a class is a valid strategy class"""
        try:
            # Check if it's a class and not abstract
            if not inspect.isclass(obj) or inspect.isabstract(obj):
                return False
            
            # Check if it inherits from BaseStrategy (from any module)
            for base in inspect.getmro(obj):
                if base.__name__ == 'BaseStrategy':
                    return True
            
            return False
            
        except Exception:
            return False
    
    @classmethod
    def _generate_strategy_name(cls, strategy_class: Type, class_name: str) -> str:
        """Generate a unique strategy name"""
        # Try to get name from class attribute first
        if hasattr(strategy_class, 'STRATEGY_NAME'):
            return strategy_class.STRATEGY_NAME
        
        # Generate from class name
        strategy_name = class_name
        if strategy_name.endswith('Strategy'):
            strategy_name = strategy_name[:-8]  # Remove 'Strategy' suffix
        
        # Convert CamelCase to snake_case for consistency
        import re
        strategy_name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', strategy_name)
        strategy_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', strategy_name).lower()
        
        return strategy_name
    
    @classmethod
    def _register_strategy_class(cls, strategy_name: str, strategy_class: Type, 
                               file_path: str, module_path: str) -> bool:
        """Register a strategy class with metadata"""
        try:
            # Extract metadata first
            metadata = cls._extract_strategy_metadata(
                strategy_name, strategy_class, file_path, module_path
            )
            
            # Check for conflicts
            if strategy_name in cls._strategies:
                logger.warning(f"Strategy {strategy_name} already registered, updating...")
            
            # Register strategy
            cls._strategies[strategy_name] = strategy_class
            cls._metadata[strategy_name] = metadata
            
            # Update asset class mapping
            if metadata.asset_class:
                if metadata.asset_class not in cls._asset_class_strategies:
                    cls._asset_class_strategies[metadata.asset_class] = set()
                cls._asset_class_strategies[metadata.asset_class].add(strategy_name)
            
            logger.debug(f"✓ Successfully registered strategy: {strategy_name} with asset class: {metadata.asset_class}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering strategy {strategy_name}: {e}")
            logger.exception("Full traceback:")
            return False
    
    @classmethod
    def _extract_strategy_metadata(cls, strategy_name: str, strategy_class: Type,
                                 file_path: str, module_path: str) -> StrategyMetadata:
        """Extract comprehensive metadata from strategy class"""
        try:
            # Get file timestamps
            file_stat = os.stat(file_path)
            created_date = datetime.fromtimestamp(file_stat.st_ctime)
            last_modified = datetime.fromtimestamp(file_stat.st_mtime)
            
            # Extract class information
            description = inspect.getdoc(strategy_class) or "No description available"
            
            # Try to extract asset class from class attributes or docstring
            asset_class = getattr(strategy_class, 'ASSET_CLASS', None)
            
            # Ensure asset_class is actually an AssetClass enum instance
            if asset_class and not isinstance(asset_class, AssetClass):
                if isinstance(asset_class, str):
                    try:
                        asset_class = AssetClass(asset_class.upper())
                    except ValueError:
                        asset_class = None
                else:
                    asset_class = None
            
            # If no asset class found, try to infer from module path
            if not asset_class:
                module_lower = module_path.lower()
                if 'equity' in module_lower:
                    asset_class = AssetClass.EQUITY
                elif 'derivatives' in module_lower:
                    asset_class = AssetClass.DERIVATIVES
                elif 'crypto' in module_lower:
                    asset_class = AssetClass.CRYPTO
                elif 'forex' in module_lower:
                    asset_class = AssetClass.FOREX
                elif 'commodities' in module_lower:
                    asset_class = AssetClass.COMMODITIES
            
            # Extract other metadata
            version = getattr(strategy_class, 'VERSION', '1.0.0')
            author = getattr(strategy_class, 'AUTHOR', 'Unknown')
            dependencies = getattr(strategy_class, 'DEPENDENCIES', [])
            parameters = getattr(strategy_class, 'DEFAULT_PARAMETERS', {})
            
            return StrategyMetadata(
                name=strategy_name,
                class_name=strategy_class.__name__,
                module_path=module_path,
                asset_class=asset_class,
                file_path=file_path,
                description=description.split('\n')[0][:200] if description else "No description available",
                version=str(version),
                author=str(author),
                created_date=created_date,
                last_modified=last_modified,
                dependencies=list(dependencies) if dependencies else [],
                parameters=dict(parameters) if parameters else {},
                is_active=True
            )
            
        except Exception as e:
            logger.error(f"Error extracting metadata for {strategy_name}: {e}")
            # Return minimal metadata
            return StrategyMetadata(
                name=strategy_name,
                class_name=strategy_class.__name__,
                module_path=module_path,
                asset_class=None,
                file_path=file_path,
                description="Metadata extraction failed",
                version="1.0.0",
                author="Unknown",
                created_date=datetime.now(),
                last_modified=datetime.now(),
                dependencies=[],
                parameters={}
            )
    
    @classmethod
    def register(cls, strategy_name: str, asset_class: AssetClass = None):
        """
        Decorator to manually register a strategy class
        
        Usage:
            @AutomaticStrategyRegistry.register("my_strategy", AssetClass.EQUITY)
            class MyStrategy(BaseStrategy):
                pass
        """
        def decorator(strategy_class: Type[BaseStrategy]):
            try:
                # Set metadata attributes on class
                strategy_class.STRATEGY_NAME = strategy_name
                strategy_class.ASSET_CLASS = asset_class
                
                # Always register immediately (don't wait for initialization)
                file_path = inspect.getfile(strategy_class)
                module_path = strategy_class.__module__
                cls._register_strategy_class(strategy_name, strategy_class, file_path, module_path)
                
                logger.info(f"✓ Manually registered strategy: {strategy_name}")
                return strategy_class
                
            except Exception as e:
                logger.error(f"Error in register decorator for {strategy_name}: {e}")
                return strategy_class
        
        return decorator
    
    @classmethod
    def get_strategy_class(cls, strategy_name: str) -> Optional[Type[BaseStrategy]]:
        """Get strategy class by name"""
        return cls._strategies.get(strategy_name)
    
    @classmethod
    def create_strategy(cls, strategy_name: str, config: Any) -> Optional[BaseStrategy]:
        """Create strategy instance by name"""
        strategy_class = cls.get_strategy_class(strategy_name)
        if strategy_class:
            try:
                return strategy_class(config)
            except Exception as e:
                logger.error(f"Error creating strategy {strategy_name}: {e}")
                return None
        else:
            logger.error(f"Strategy {strategy_name} not found in registry")
            logger.info(f"Available strategies: {list(cls._strategies.keys())}")
            return None
    
    @classmethod
    def list_strategies(cls) -> List[str]:
        """Get list of all registered strategy names"""
        return list(cls._strategies.keys())
    
    @classmethod
    def list_strategies_by_asset_class(cls, asset_class: AssetClass) -> List[str]:
        """Get list of strategies for specific asset class"""
        return list(cls._asset_class_strategies.get(asset_class, set()))
    
    @classmethod
    def get_strategy_metadata(cls, strategy_name: str) -> Optional[StrategyMetadata]:
        """Get comprehensive metadata for a strategy"""
        return cls._metadata.get(strategy_name)
    
    @classmethod
    def get_all_metadata(cls) -> Dict[str, StrategyMetadata]:
        """Get metadata for all registered strategies"""
        return cls._metadata.copy()
    
    @classmethod
    def reload_strategy(cls, strategy_name: str) -> bool:
        """Reload a specific strategy from file"""
        try:
            metadata = cls._metadata.get(strategy_name)
            if not metadata:
                logger.error(f"Strategy {strategy_name} not found")
                return False
            
            # Force reload the file
            strategies_found = cls._discover_strategies_in_file(metadata.file_path)
            logger.info(f"Reloaded strategy {strategy_name}: {strategies_found} strategies updated")
            return strategies_found > 0
            
        except Exception as e:
            logger.error(f"Error reloading strategy {strategy_name}: {e}")
            return False
    
    @classmethod
    def hot_reload(cls) -> int:
        """Hot reload all changed strategy files"""
        logger.info("🔄 Starting hot reload...")
        cls.discover_strategies(force_reload=False)
        return len(cls._strategies)
    
    @classmethod
    def validate_strategy(cls, strategy_name: str) -> bool:
        """Validate that a strategy is properly implemented"""
        try:
            strategy_class = cls.get_strategy_class(strategy_name)
            if not strategy_class:
                return False
            
            # Check required methods
            required_methods = ['initialize', 'process_market_data', 'calculate_position_size']
            for method in required_methods:
                if not hasattr(strategy_class, method):
                    logger.warning(f"Strategy {strategy_name} missing required method: {method}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating strategy {strategy_name}: {e}")
            return False
    
    @classmethod
    def get_asset_classes(cls) -> List[AssetClass]:
        """Get list of all asset classes with registered strategies"""
        return [ac for ac, strategies in cls._asset_class_strategies.items() if strategies]
    
    @classmethod
    def clear_registry(cls):
        """Clear all registered strategies (mainly for testing)"""
        cls._strategies.clear()
        cls._metadata.clear()
        cls._asset_class_strategies.clear()
        cls._file_timestamps.clear()
        cls._initialized = False
        logger.info("Strategy registry cleared")
    
    @classmethod
    def _log_registry_summary(cls):
        """Log a summary of the current registry state"""
        logger.info("📊 STRATEGY REGISTRY SUMMARY:")
        logger.info(f"   Total Strategies: {len(cls._strategies)}")
        
        for asset_class, strategies in cls._asset_class_strategies.items():
            if strategies:
                logger.info(f"   {asset_class.value}: {len(strategies)} strategies")
        
        logger.info(f"   Discovery Paths: {len(cls._discovery_paths)}")
        logger.info(f"   Files Tracked: {len(cls._file_timestamps)}")

# Maintain backward compatibility
StrategyRegistry = AutomaticStrategyRegistry 