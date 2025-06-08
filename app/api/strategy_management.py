"""
Strategy Management API - Database Control Interface

This API provides database-driven control over independent strategy processes.
All operations go through the database command queue for decoupled execution.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID, uuid4
import json
import asyncpg

router = APIRouter(prefix="/api/strategies", tags=["Strategy Management"])

# Pydantic Models
class StrategyConfig(BaseModel):
    name: str = Field(..., description="Strategy name")
    class_name: str = Field(..., description="Strategy class name")
    module_path: str = Field(..., description="Python module path")
    config: Dict[str, Any] = Field(default_factory=dict, description="Strategy configuration")
    auto_start: bool = Field(default=True, description="Auto-start on system startup")

class StrategyCommand(BaseModel):
    command: str = Field(..., description="Command: start, stop, restart, update")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Command parameters")

class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    auto_start: Optional[bool] = None

class StrategyResponse(BaseModel):
    id: UUID
    name: str
    class_name: str
    module_path: str
    config: Dict[str, Any]
    status: str
    auto_start: bool
    created_at: datetime
    updated_at: datetime

class StrategyMetrics(BaseModel):
    strategy_id: UUID
    timestamp: datetime
    pnl: float
    positions_count: int
    orders_count: int
    success_rate: float
    metrics: Dict[str, Any]

# Database dependency
async def get_db_pool():
    # This would be injected from your main app
    pass

@router.post("/", response_model=StrategyResponse)
async def create_strategy(
    strategy: StrategyConfig,
    db_pool = Depends(get_db_pool)
):
    """Create a new strategy configuration"""
    
    strategy_id = uuid4()
    
    async with db_pool.acquire() as conn:
        try:
            # Insert strategy configuration
            await conn.execute("""
                INSERT INTO strategy_configs 
                (id, name, class_name, module_path, config_json, status, auto_start, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, 'active', $6, NOW(), NOW())
            """, 
                strategy_id,
                strategy.name,
                strategy.class_name,
                strategy.module_path,
                json.dumps(strategy.config),
                strategy.auto_start
            )
            
            # Auto-start if requested
            if strategy.auto_start:
                await conn.execute("""
                    INSERT INTO strategy_commands (id, strategy_id, command, parameters, status, created_at)
                    VALUES ($1, $2, 'start', '{}', 'pending', NOW())
                """, uuid4(), strategy_id)
            
            # Return created strategy
            return StrategyResponse(
                id=strategy_id,
                name=strategy.name,
                class_name=strategy.class_name,
                module_path=strategy.module_path,
                config=strategy.config,
                status='active',
                auto_start=strategy.auto_start,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
        except asyncpg.UniqueViolationError:
            raise HTTPException(status_code=400, detail="Strategy name already exists")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create strategy: {str(e)}")

@router.get("/", response_model=List[StrategyResponse])
async def list_strategies(
    status: Optional[str] = None,
    db_pool = Depends(get_db_pool)
):
    """List all strategies with optional status filter"""
    
    async with db_pool.acquire() as conn:
        if status:
            strategies = await conn.fetch("""
                SELECT id, name, class_name, module_path, config_json, status, auto_start, created_at, updated_at
                FROM strategy_configs 
                WHERE status = $1
                ORDER BY created_at DESC
            """, status)
        else:
            strategies = await conn.fetch("""
                SELECT id, name, class_name, module_path, config_json, status, auto_start, created_at, updated_at
                FROM strategy_configs 
                ORDER BY created_at DESC
            """)
        
        return [
            StrategyResponse(
                id=s['id'],
                name=s['name'],
                class_name=s['class_name'],
                module_path=s['module_path'],
                config=json.loads(s['config_json']) if s['config_json'] else {},
                status=s['status'],
                auto_start=s['auto_start'],
                created_at=s['created_at'],
                updated_at=s['updated_at']
            )
            for s in strategies
        ]

@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: UUID,
    db_pool = Depends(get_db_pool)
):
    """Get specific strategy by ID"""
    
    async with db_pool.acquire() as conn:
        strategy = await conn.fetchrow("""
            SELECT id, name, class_name, module_path, config_json, status, auto_start, created_at, updated_at
            FROM strategy_configs 
            WHERE id = $1
        """, strategy_id)
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        return StrategyResponse(
            id=strategy['id'],
            name=strategy['name'],
            class_name=strategy['class_name'],
            module_path=strategy['module_path'],
            config=json.loads(strategy['config_json']) if strategy['config_json'] else {},
            status=strategy['status'],
            auto_start=strategy['auto_start'],
            created_at=strategy['created_at'],
            updated_at=strategy['updated_at']
        )

@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: UUID,
    strategy_update: StrategyUpdate,
    db_pool = Depends(get_db_pool)
):
    """Update strategy configuration"""
    
    async with db_pool.acquire() as conn:
        # Check if strategy exists
        existing = await conn.fetchrow("""
            SELECT id, name, class_name, module_path, config_json, status, auto_start, created_at
            FROM strategy_configs WHERE id = $1
        """, strategy_id)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Build update query dynamically
        updates = []
        values = []
        param_count = 1
        
        if strategy_update.name is not None:
            updates.append(f"name = ${param_count}")
            values.append(strategy_update.name)
            param_count += 1
            
        if strategy_update.config is not None:
            updates.append(f"config_json = ${param_count}")
            values.append(json.dumps(strategy_update.config))
            param_count += 1
            
        if strategy_update.auto_start is not None:
            updates.append(f"auto_start = ${param_count}")
            values.append(strategy_update.auto_start)
            param_count += 1
        
        if updates:
            updates.append(f"updated_at = NOW()")
            values.append(strategy_id)
            
            query = f"""
                UPDATE strategy_configs 
                SET {', '.join(updates)}
                WHERE id = ${param_count}
                RETURNING id, name, class_name, module_path, config_json, status, auto_start, created_at, updated_at
            """
            
            updated = await conn.fetchrow(query, *values)
            
            # Send update command if strategy is running
            if strategy_update.config is not None:
                await conn.execute("""
                    INSERT INTO strategy_commands (id, strategy_id, command, parameters, status, created_at)
                    VALUES ($1, $2, 'update', $3, 'pending', NOW())
                """, 
                    uuid4(), 
                    strategy_id, 
                    json.dumps({'config': strategy_update.config})
                )
            
            return StrategyResponse(
                id=updated['id'],
                name=updated['name'],
                class_name=updated['class_name'],
                module_path=updated['module_path'],
                config=json.loads(updated['config_json']) if updated['config_json'] else {},
                status=updated['status'],
                auto_start=updated['auto_start'],
                created_at=updated['created_at'],
                updated_at=updated['updated_at']
            )
        else:
            raise HTTPException(status_code=400, detail="No updates provided")

@router.post("/{strategy_id}/commands")
async def send_strategy_command(
    strategy_id: UUID,
    command: StrategyCommand,
    db_pool = Depends(get_db_pool)
):
    """Send command to strategy (start, stop, restart, pause, resume)"""
    
    # Validate command
    valid_commands = ['start', 'stop', 'restart', 'pause', 'resume']
    if command.command not in valid_commands:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid command. Valid commands: {valid_commands}"
        )
    
    async with db_pool.acquire() as conn:
        # Check if strategy exists
        strategy = await conn.fetchrow("""
            SELECT id, name FROM strategy_configs WHERE id = $1
        """, strategy_id)
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Insert command
        command_id = uuid4()
        await conn.execute("""
            INSERT INTO strategy_commands (id, strategy_id, command, parameters, status, created_at)
            VALUES ($1, $2, $3, $4, 'pending', NOW())
        """, 
            command_id,
            strategy_id,
            command.command,
            json.dumps(command.parameters)
        )
        
        return {
            "command_id": command_id,
            "strategy_id": strategy_id,
            "command": command.command,
            "status": "pending",
            "message": f"Command '{command.command}' queued for strategy '{strategy['name']}'"
        }

@router.get("/{strategy_id}/status")
async def get_strategy_status(
    strategy_id: UUID,
    db_pool = Depends(get_db_pool)
):
    """Get current strategy status and recent commands"""
    
    async with db_pool.acquire() as conn:
        # Get strategy info
        strategy = await conn.fetchrow("""
            SELECT id, name, status, updated_at FROM strategy_configs WHERE id = $1
        """, strategy_id)
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Get recent commands
        commands = await conn.fetch("""
            SELECT id, command, parameters, status, created_at, executed_at
            FROM strategy_commands 
            WHERE strategy_id = $1
            ORDER BY created_at DESC 
            LIMIT 10
        """, strategy_id)
        
        # Get recent metrics
        metrics = await conn.fetch("""
            SELECT timestamp, pnl, positions_count, orders_count, success_rate
            FROM strategy_metrics 
            WHERE strategy_id = $1
            ORDER BY timestamp DESC 
            LIMIT 5
        """, strategy_id)
        
        return {
            "strategy": {
                "id": strategy['id'],
                "name": strategy['name'],
                "status": strategy['status'],
                "updated_at": strategy['updated_at']
            },
            "recent_commands": [
                {
                    "id": cmd['id'],
                    "command": cmd['command'],
                    "parameters": json.loads(cmd['parameters']) if cmd['parameters'] else {},
                    "status": cmd['status'],
                    "created_at": cmd['created_at'],
                    "executed_at": cmd['executed_at']
                }
                for cmd in commands
            ],
            "recent_metrics": [
                {
                    "timestamp": m['timestamp'],
                    "pnl": float(m['pnl']) if m['pnl'] else 0,
                    "positions_count": m['positions_count'],
                    "orders_count": m['orders_count'],
                    "success_rate": float(m['success_rate']) if m['success_rate'] else 0
                }
                for m in metrics
            ]
        }

@router.get("/{strategy_id}/metrics")
async def get_strategy_metrics(
    strategy_id: UUID,
    hours: int = 24,
    db_pool = Depends(get_db_pool)
):
    """Get strategy performance metrics for specified time period"""
    
    async with db_pool.acquire() as conn:
        metrics = await conn.fetch("""
            SELECT timestamp, pnl, positions_count, orders_count, success_rate, metrics_json
            FROM strategy_metrics 
            WHERE strategy_id = $1 
            AND timestamp >= NOW() - INTERVAL '%s hours'
            ORDER BY timestamp DESC
        """, strategy_id, hours)
        
        return {
            "strategy_id": strategy_id,
            "period_hours": hours,
            "metrics": [
                {
                    "timestamp": m['timestamp'],
                    "pnl": float(m['pnl']) if m['pnl'] else 0,
                    "positions_count": m['positions_count'],
                    "orders_count": m['orders_count'],
                    "success_rate": float(m['success_rate']) if m['success_rate'] else 0,
                    "details": json.loads(m['metrics_json']) if m['metrics_json'] else {}
                }
                for m in metrics
            ]
        }

@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: UUID,
    force: bool = False,
    db_pool = Depends(get_db_pool)
):
    """Delete strategy (stops it first if running)"""
    
    async with db_pool.acquire() as conn:
        # Check if strategy exists
        strategy = await conn.fetchrow("""
            SELECT id, name, status FROM strategy_configs WHERE id = $1
        """, strategy_id)
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Stop strategy if running (unless force delete)
        if strategy['status'] == 'running' and not force:
            await conn.execute("""
                INSERT INTO strategy_commands (id, strategy_id, command, parameters, status, created_at)
                VALUES ($1, $2, 'stop', '{}', 'pending', NOW())
            """, uuid4(), strategy_id)
            
            return {
                "message": f"Stop command sent to strategy '{strategy['name']}'. Delete again with force=true after it stops."
            }
        
        # Delete strategy and related data
        await conn.execute("DELETE FROM strategy_metrics WHERE strategy_id = $1", strategy_id)
        await conn.execute("DELETE FROM strategy_commands WHERE strategy_id = $1", strategy_id)
        await conn.execute("DELETE FROM strategy_configs WHERE id = $1", strategy_id)
        
        return {
            "message": f"Strategy '{strategy['name']}' deleted successfully"
        }

@router.get("/")
async def get_system_overview(db_pool = Depends(get_db_pool)):
    """Get system-wide strategy overview"""
    
    async with db_pool.acquire() as conn:
        # Get strategy counts by status
        status_counts = await conn.fetch("""
            SELECT status, COUNT(*) as count
            FROM strategy_configs 
            GROUP BY status
        """)
        
        # Get recent commands
        recent_commands = await conn.fetch("""
            SELECT sc.id, sc.command, sc.status, sc.created_at, sc.executed_at, cfg.name as strategy_name
            FROM strategy_commands sc
            JOIN strategy_configs cfg ON sc.strategy_id = cfg.id
            ORDER BY sc.created_at DESC 
            LIMIT 20
        """)
        
        # Get system metrics
        system_metrics = await conn.fetchrow("""
            SELECT 
                COUNT(DISTINCT strategy_id) as active_strategies,
                AVG(pnl) as avg_pnl,
                SUM(positions_count) as total_positions,
                SUM(orders_count) as total_orders
            FROM strategy_metrics 
            WHERE timestamp >= NOW() - INTERVAL '1 hour'
        """)
        
        return {
            "status_summary": {row['status']: row['count'] for row in status_counts},
            "recent_commands": [
                {
                    "id": cmd['id'],
                    "strategy_name": cmd['strategy_name'],
                    "command": cmd['command'],
                    "status": cmd['status'],
                    "created_at": cmd['created_at'],
                    "executed_at": cmd['executed_at']
                }
                for cmd in recent_commands
            ],
            "system_metrics": {
                "active_strategies": system_metrics['active_strategies'] or 0,
                "avg_pnl": float(system_metrics['avg_pnl']) if system_metrics['avg_pnl'] else 0,
                "total_positions": system_metrics['total_positions'] or 0,
                "total_orders": system_metrics['total_orders'] or 0
            }
        } 