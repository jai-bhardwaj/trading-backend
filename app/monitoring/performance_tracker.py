"""
Performance Tracker - Advanced performance analytics for trading strategies

This module provides detailed performance tracking and analytics including:
- Advanced performance metrics (Sharpe ratio, Sortino ratio, Calmar ratio)
- Risk-adjusted returns analysis
- Drawdown analysis and recovery tracking
- Performance attribution and benchmarking
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from app.database import DatabaseManager
from app.models.base import Strategy as StrategyModel, Trade, Order, Position

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics for a strategy"""
    strategy_id: str
    strategy_name: str
    calculation_date: datetime
    
    # Basic Performance
    total_return: float = 0.0
    annualized_return: float = 0.0
    total_pnl: float = 0.0
    
    # Risk Metrics
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Drawdown Analysis
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0  # days
    current_drawdown: float = 0.0
    recovery_factor: float = 0.0
    
    # Trading Statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Time-based Performance
    daily_returns: List[float] = field(default_factory=list)
    monthly_returns: List[float] = field(default_factory=list)
    
    # Risk-Adjusted Metrics
    var_95: float = 0.0  # Value at Risk (95%)
    cvar_95: float = 0.0  # Conditional Value at Risk (95%)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'strategy_id': self.strategy_id,
            'strategy_name': self.strategy_name,
            'calculation_date': self.calculation_date.isoformat(),
            'basic_performance': {
                'total_return': self.total_return,
                'annualized_return': self.annualized_return,
                'total_pnl': self.total_pnl
            },
            'risk_metrics': {
                'volatility': self.volatility,
                'sharpe_ratio': self.sharpe_ratio,
                'sortino_ratio': self.sortino_ratio,
                'calmar_ratio': self.calmar_ratio
            },
            'drawdown_analysis': {
                'max_drawdown': self.max_drawdown,
                'max_drawdown_duration': self.max_drawdown_duration,
                'current_drawdown': self.current_drawdown,
                'recovery_factor': self.recovery_factor
            },
            'trading_statistics': {
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'losing_trades': self.losing_trades,
                'win_rate': self.win_rate,
                'profit_factor': self.profit_factor,
                'avg_win': self.avg_win,
                'avg_loss': self.avg_loss,
                'largest_win': self.largest_win,
                'largest_loss': self.largest_loss
            },
            'risk_adjusted': {
                'var_95': self.var_95,
                'cvar_95': self.cvar_95
            }
        }

class PerformanceTracker:
    """
    Advanced performance tracking and analytics system
    
    Provides detailed performance analysis including risk-adjusted returns,
    drawdown analysis, and comprehensive trading statistics.
    """
    
    def __init__(self, risk_free_rate: float = 0.05):
        self.risk_free_rate = risk_free_rate  # Annual risk-free rate
        self._performance_cache: Dict[str, PerformanceMetrics] = {}
        self._cache_expiry = timedelta(hours=1)  # Cache for 1 hour
    
    async def calculate_performance_metrics(self, strategy_id: str) -> Optional[PerformanceMetrics]:
        """Calculate comprehensive performance metrics for a strategy"""
        # Check cache first
        if strategy_id in self._performance_cache:
            cached_metrics = self._performance_cache[strategy_id]
            if datetime.utcnow() - cached_metrics.calculation_date < self._cache_expiry:
                return cached_metrics
        
        db_manager = DatabaseManager()
        try:
            async with db_manager.get_session() as db:
                strategy = await db.query(StrategyModel).filter(StrategyModel.id == strategy_id).first()
                if not strategy:
                    return None
                
                # Get all trades for this strategy
                trades = await db.query(Trade).join(Order).filter(
                    Order.strategy_id == strategy_id
                ).order_by(Trade.trade_timestamp).all()
                
                if not trades:
                    return PerformanceMetrics(
                        strategy_id=strategy_id,
                        strategy_name=strategy.name,
                        calculation_date=datetime.utcnow()
                    )
                
                # Calculate metrics
                metrics = self._calculate_comprehensive_metrics(strategy, trades)
                
                # Cache the results
                self._performance_cache[strategy_id] = metrics
                
                return metrics
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics for strategy {strategy_id}: {e}")
            return None
    
    def _calculate_comprehensive_metrics(self, strategy: StrategyModel, trades: List[Trade]) -> PerformanceMetrics:
        """Calculate all performance metrics from trade data"""
        metrics = PerformanceMetrics(
            strategy_id=strategy.id,
            strategy_name=strategy.name,
            calculation_date=datetime.utcnow()
        )
        
        # Convert trades to DataFrame for easier analysis
        trade_data = []
        for trade in trades:
            pnl = self._calculate_trade_pnl(trade)
            trade_data.append({
                'timestamp': trade.trade_timestamp or trade.created_at,
                'pnl': pnl,
                'symbol': trade.symbol,
                'quantity': trade.quantity,
                'price': trade.price
            })
        
        if not trade_data:
            return metrics
        
        df = pd.DataFrame(trade_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # Calculate basic performance metrics
        self._calculate_basic_performance(df, metrics)
        
        # Calculate risk metrics
        self._calculate_risk_metrics(df, metrics)
        
        # Calculate drawdown analysis
        self._calculate_drawdown_analysis(df, metrics)
        
        # Calculate trading statistics
        self._calculate_trading_statistics(df, metrics)
        
        # Calculate time-based returns
        self._calculate_time_based_returns(df, metrics)
        
        # Calculate risk-adjusted metrics
        self._calculate_risk_adjusted_metrics(df, metrics)
        
        return metrics
    
    def _calculate_trade_pnl(self, trade: Trade) -> float:
        """Calculate P&L for a single trade"""
        # This is a simplified calculation - you might need to adjust based on your trade structure
        # Assuming trade has netAmount or calculate from quantity * price
        if hasattr(trade, 'netAmount'):
            return trade.netAmount - (trade.quantity * trade.price)
        else:
            # For buy trades, negative cash flow; for sell trades, positive cash flow
            # This is simplified - you'd need proper position tracking for accurate P&L
            return 0.0  # Placeholder
    
    def _calculate_basic_performance(self, df: pd.DataFrame, metrics: PerformanceMetrics):
        """Calculate basic performance metrics"""
        metrics.total_pnl = df['pnl'].sum()
        
        # Calculate cumulative returns
        df['cumulative_pnl'] = df['pnl'].cumsum()
        
        if len(df) > 1:
            # Calculate total return (assuming starting capital)
            starting_capital = 100000  # Default starting capital
            metrics.total_return = metrics.total_pnl / starting_capital
            
            # Calculate annualized return
            days = (df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).days
            if days > 0:
                years = days / 365.25
                metrics.annualized_return = (1 + metrics.total_return) ** (1/years) - 1
    
    def _calculate_risk_metrics(self, df: pd.DataFrame, metrics: PerformanceMetrics):
        """Calculate risk-related metrics"""
        if len(df) < 2:
            return
        
        # Calculate daily returns
        df_daily = df.set_index('timestamp').resample('D')['pnl'].sum()
        daily_returns = df_daily[df_daily != 0]  # Remove zero days
        
        if len(daily_returns) < 2:
            return
        
        # Volatility (annualized)
        metrics.volatility = daily_returns.std() * np.sqrt(252)  # 252 trading days
        
        # Sharpe Ratio
        if metrics.volatility > 0:
            excess_return = metrics.annualized_return - self.risk_free_rate
            metrics.sharpe_ratio = excess_return / metrics.volatility
        
        # Sortino Ratio (using downside deviation)
        negative_returns = daily_returns[daily_returns < 0]
        if len(negative_returns) > 0:
            downside_deviation = negative_returns.std() * np.sqrt(252)
            if downside_deviation > 0:
                excess_return = metrics.annualized_return - self.risk_free_rate
                metrics.sortino_ratio = excess_return / downside_deviation
    
    def _calculate_drawdown_analysis(self, df: pd.DataFrame, metrics: PerformanceMetrics):
        """Calculate drawdown analysis"""
        if len(df) < 2:
            return
        
        # Calculate running maximum and drawdown
        df['cumulative_pnl'] = df['pnl'].cumsum()
        df['running_max'] = df['cumulative_pnl'].expanding().max()
        df['drawdown'] = df['cumulative_pnl'] - df['running_max']
        
        # Max drawdown
        metrics.max_drawdown = df['drawdown'].min()
        
        # Current drawdown
        metrics.current_drawdown = df['drawdown'].iloc[-1]
        
        # Max drawdown duration
        in_drawdown = df['drawdown'] < 0
        if in_drawdown.any():
            # Find longest consecutive drawdown period
            drawdown_periods = []
            current_period = 0
            
            for is_dd in in_drawdown:
                if is_dd:
                    current_period += 1
                else:
                    if current_period > 0:
                        drawdown_periods.append(current_period)
                    current_period = 0
            
            if current_period > 0:
                drawdown_periods.append(current_period)
            
            if drawdown_periods:
                metrics.max_drawdown_duration = max(drawdown_periods)
        
        # Recovery factor
        if metrics.max_drawdown < 0:
            metrics.recovery_factor = metrics.total_pnl / abs(metrics.max_drawdown)
        
        # Calmar Ratio
        if metrics.max_drawdown < 0:
            metrics.calmar_ratio = metrics.annualized_return / abs(metrics.max_drawdown)
    
    def _calculate_trading_statistics(self, df: pd.DataFrame, metrics: PerformanceMetrics):
        """Calculate trading statistics"""
        metrics.total_trades = len(df)
        
        winning_trades = df[df['pnl'] > 0]
        losing_trades = df[df['pnl'] < 0]
        
        metrics.winning_trades = len(winning_trades)
        metrics.losing_trades = len(losing_trades)
        
        if metrics.total_trades > 0:
            metrics.win_rate = metrics.winning_trades / metrics.total_trades
        
        # Average win/loss
        if len(winning_trades) > 0:
            metrics.avg_win = winning_trades['pnl'].mean()
            metrics.largest_win = winning_trades['pnl'].max()
        
        if len(losing_trades) > 0:
            metrics.avg_loss = losing_trades['pnl'].mean()
            metrics.largest_loss = losing_trades['pnl'].min()
        
        # Profit factor
        gross_profit = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 0
        
        if gross_loss > 0:
            metrics.profit_factor = gross_profit / gross_loss
    
    def _calculate_time_based_returns(self, df: pd.DataFrame, metrics: PerformanceMetrics):
        """Calculate time-based returns"""
        if len(df) < 2:
            return
        
        # Daily returns
        df_daily = df.set_index('timestamp').resample('D')['pnl'].sum()
        metrics.daily_returns = df_daily[df_daily != 0].tolist()
        
        # Monthly returns
        df_monthly = df.set_index('timestamp').resample('M')['pnl'].sum()
        metrics.monthly_returns = df_monthly[df_monthly != 0].tolist()
    
    def _calculate_risk_adjusted_metrics(self, df: pd.DataFrame, metrics: PerformanceMetrics):
        """Calculate risk-adjusted metrics like VaR and CVaR"""
        if len(metrics.daily_returns) < 10:  # Need sufficient data
            return
        
        daily_returns = np.array(metrics.daily_returns)
        
        # Value at Risk (95% confidence)
        metrics.var_95 = np.percentile(daily_returns, 5)
        
        # Conditional Value at Risk (95% confidence)
        var_threshold = metrics.var_95
        tail_losses = daily_returns[daily_returns <= var_threshold]
        if len(tail_losses) > 0:
            metrics.cvar_95 = tail_losses.mean()
    
    def get_performance_comparison(self, strategy_ids: List[str]) -> Dict[str, Any]:
        """Compare performance across multiple strategies"""
        comparison_data = {}
        
        for strategy_id in strategy_ids:
            metrics = self.calculate_performance_metrics(strategy_id)
            if metrics:
                comparison_data[strategy_id] = {
                    'name': metrics.strategy_name,
                    'total_return': metrics.total_return,
                    'annualized_return': metrics.annualized_return,
                    'sharpe_ratio': metrics.sharpe_ratio,
                    'max_drawdown': metrics.max_drawdown,
                    'win_rate': metrics.win_rate,
                    'total_trades': metrics.total_trades
                }
        
        # Calculate rankings
        if comparison_data:
            # Rank by Sharpe ratio
            sorted_by_sharpe = sorted(
                comparison_data.items(),
                key=lambda x: x[1]['sharpe_ratio'],
                reverse=True
            )
            
            # Rank by total return
            sorted_by_return = sorted(
                comparison_data.items(),
                key=lambda x: x[1]['total_return'],
                reverse=True
            )
            
            return {
                'strategies': comparison_data,
                'rankings': {
                    'by_sharpe_ratio': [item[0] for item in sorted_by_sharpe],
                    'by_total_return': [item[0] for item in sorted_by_return]
                },
                'summary': {
                    'best_sharpe': sorted_by_sharpe[0] if sorted_by_sharpe else None,
                    'best_return': sorted_by_return[0] if sorted_by_return else None,
                    'total_strategies': len(comparison_data)
                }
            }
        
        return {'strategies': {}, 'rankings': {}, 'summary': {}}
    
    async def get_performance_attribution(self, strategy_id: str) -> Dict[str, Any]:
        """Analyze performance attribution by symbol, time period, etc."""
        db_manager = DatabaseManager()
        try:
            async with db_manager.get_session() as db:
                trades = await db.query(Trade).join(Order).filter(
                    Order.strategy_id == strategy_id
                ).all()
                
                if not trades:
                    return {}
                
                attribution = {
                    'by_symbol': {},
                    'by_month': {},
                    'by_day_of_week': {}
                }
                
                for trade in trades:
                    pnl = self._calculate_trade_pnl(trade)
                    
                    # By symbol
                    symbol = trade.symbol
                    if symbol not in attribution['by_symbol']:
                        attribution['by_symbol'][symbol] = {'pnl': 0, 'trades': 0}
                    attribution['by_symbol'][symbol]['pnl'] += pnl
                    attribution['by_symbol'][symbol]['trades'] += 1
                    
                    # By month
                    if trade.trade_timestamp:
                        month_key = trade.trade_timestamp.strftime('%Y-%m')
                        if month_key not in attribution['by_month']:
                            attribution['by_month'][month_key] = {'pnl': 0, 'trades': 0}
                        attribution['by_month'][month_key]['pnl'] += pnl
                        attribution['by_month'][month_key]['trades'] += 1
                        
                        # By day of week
                        day_name = trade.trade_timestamp.strftime('%A')
                        if day_name not in attribution['by_day_of_week']:
                            attribution['by_day_of_week'][day_name] = {'pnl': 0, 'trades': 0}
                        attribution['by_day_of_week'][day_name]['pnl'] += pnl
                        attribution['by_day_of_week'][day_name]['trades'] += 1
                
                return attribution
            
        except Exception as e:
            logger.error(f"Error calculating performance attribution for strategy {strategy_id}: {e}")
            return {}
    
    def clear_cache(self):
        """Clear the performance metrics cache"""
        self._performance_cache.clear()
    
    def get_cached_metrics(self) -> Dict[str, PerformanceMetrics]:
        """Get all cached performance metrics"""
        return self._performance_cache.copy()

# Global performance tracker instance
performance_tracker = PerformanceTracker()

# Ensure db_manager.initialize() is called at startup (e.g., in main()) 