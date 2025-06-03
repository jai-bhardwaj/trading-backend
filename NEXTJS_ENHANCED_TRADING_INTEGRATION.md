# Next.js Enhanced Trading Engine Integration

## 🎯 **Overview**

This document outlines how to integrate the **Enhanced Trading Engine Architecture** with your existing **Next.js + Prisma + tRPC** stack to achieve the same independent strategy execution with database control.

## 🏗️ **Hybrid Architecture**

```
┌─────────────────────────────────────────────────────────────────┐
│                    Next.js Frontend + tRPC API                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Dashboard     │  │  Strategy Mgmt  │  │   Monitoring    │ │
│  │     UI          │  │      UI         │  │       UI        │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          │ tRPC Calls
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                 Next.js API Layer (tRPC)                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Strategy      │  │    Commands     │  │    Metrics      │ │
│  │   Procedures    │  │   Procedures    │  │   Procedures    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          │ Prisma ORM
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                PostgreSQL Database                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ strategy_configs│  │strategy_commands│  │strategy_metrics │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          │ Commands & Status
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│              Python Strategy Engine Manager                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Process        │  │   Command       │  │    Health       │ │
│  │ Orchestrator    │  │   Executor      │  │   Monitor       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          │ Process Management
                          │
┌─────────┬─────────┬─────▼─────┬─────────┬─────────┬─────────┬───┐
│Strategy │Strategy │ Strategy  │Strategy │Strategy │Strategy │...│
│   A     │   B     │     C     │   D     │   E     │   F     │   │
│ (PID)   │ (PID)   │   (PID)   │ (PID)   │ (PID)   │ (PID)   │   │
└─────────┴─────────┴───────────┴─────────┴─────────┴─────────┴───┘
```

## 📊 **Required Prisma Schema Extensions**

Looking at your existing schema, you already have a great foundation! Here's what we need to add to integrate the enhanced strategy execution system with your existing structure:

```prisma
// ============================================================================
// ENHANCED STRATEGY EXECUTION (ADD TO YOUR EXISTING SCHEMA)
// ============================================================================

// Enhanced Strategy Configuration for Independent Execution
model StrategyConfig {
  id               String                @id @default(cuid())
  userId           String
  strategyId       String?               // Link to existing Strategy model
  name             String                @unique
  className        String                // Python class name
  modulePath       String                // Python module path
  configJson       Json                  // Configuration for the strategy
  status           StrategyConfigStatus  @default(ACTIVE)
  autoStart        Boolean               @default(true)
  createdAt        DateTime              @default(now())
  updatedAt        DateTime              @updatedAt

  // Relations
  user             User                  @relation(fields: [userId], references: [id], onDelete: Cascade)
  strategy         Strategy?             @relation(fields: [strategyId], references: [id], onDelete: SetNull)
  commands         StrategyCommand[]
  metrics          StrategyMetric[]

  @@map("strategy_configs")
}

model StrategyCommand {
  id               String                @id @default(cuid())
  strategyConfigId String
  command          StrategyCommandType
  parameters       Json?
  status           CommandStatus         @default(PENDING)
  createdAt        DateTime              @default(now())
  executedAt       DateTime?

  // Relations
  strategyConfig   StrategyConfig        @relation(fields: [strategyConfigId], references: [id], onDelete: Cascade)

  @@map("strategy_commands")
}

model StrategyMetric {
  id               String                @id @default(cuid())
  strategyConfigId String
  timestamp        DateTime              @default(now())
  pnl              Decimal               @default(0)
  positionsCount   Int                   @default(0)
  ordersCount      Int                   @default(0)
  successRate      Decimal               @default(0)
  metricsJson      Json?

  // Relations
  strategyConfig   StrategyConfig        @relation(fields: [strategyConfigId], references: [id], onDelete: Cascade)

  @@map("strategy_metrics")
}

// New Enums for Enhanced Strategy Execution
enum StrategyConfigStatus {
  ACTIVE
  STOPPED
  ERROR
  PAUSED
}

enum StrategyCommandType {
  START
  STOP
  RESTART
  PAUSE
  RESUME
  UPDATE_CONFIG
}

enum CommandStatus {
  PENDING
  EXECUTED
  FAILED
}

// ============================================================================
// UPDATES TO EXISTING MODELS
// ============================================================================

// Add to your existing User model (just add this relation)
model User {
  // ... all your existing fields stay the same ...
  
  // Add this new relation
  strategyConfigs  StrategyConfig[]

  @@map("users")
}

// Add to your existing Strategy model (just add this relation)
model Strategy {
  // ... all your existing fields stay the same ...
  
  // Add this new relation
  strategyConfigs  StrategyConfig[]

  @@map("strategies")
}
```

## 🔄 **Integration with Your Existing Models**

Your existing schema already has excellent coverage! Here's how the enhanced system integrates:

### **Existing Strategy Model** → **Enhanced Strategy Execution**
- Your existing `Strategy` model handles strategy design, backtesting, and configuration
- New `StrategyConfig` model handles independent process execution of those strategies
- One `Strategy` can have multiple `StrategyConfig` instances (e.g., different parameter sets, different environments)

### **Relationship Flow**
```
User (existing)
├── Strategy (existing) → Your strategy design & backtesting
│   ├── StrategyConfig → Independent execution configuration
│   │   ├── StrategyCommand → Start/stop/restart commands
│   │   └── StrategyMetric → Real-time execution metrics
│   └── Orders/Trades (existing) → Actual trade execution
└── Positions/Balance (existing) → Portfolio tracking
```

### **Enhanced Strategy Workflow**
1. **Design**: Create strategy using your existing `Strategy` model
2. **Deploy**: Create `StrategyConfig` linking to the strategy for independent execution
3. **Execute**: Python engine manager reads `StrategyConfig` and runs independent processes
4. **Monitor**: Track via `StrategyMetric` and existing `Order`/`Trade` tables
5. **Control**: Send commands via `StrategyCommand` table

## 🔧 **tRPC Procedures**

Updated tRPC procedures that work with your existing schema:

### 1. Strategy Configuration Procedures

```typescript
// lib/trpc/routers/strategy.ts
import { z } from 'zod';
import { router, protectedProcedure } from '../trpc';
import { TRPCError } from '@trpc/server';

const strategyConfigSchema = z.object({
  name: z.string().min(1).max(100),
  strategyId: z.string().optional(), // Link to existing Strategy
  className: z.string(),
  modulePath: z.string(),
  config: z.record(z.any()),
  autoStart: z.boolean().default(true),
});

const strategyCommandSchema = z.object({
  command: z.enum(['START', 'STOP', 'RESTART', 'PAUSE', 'RESUME', 'UPDATE_CONFIG']),
  parameters: z.record(z.any()).optional(),
});

export const strategyRouter = router({
  // Create strategy configuration from existing strategy
  create: protectedProcedure
    .input(strategyConfigSchema)
    .mutation(async ({ ctx, input }) => {
      try {
        // Verify strategy ownership if linking to existing strategy
        if (input.strategyId) {
          const strategy = await ctx.prisma.strategy.findFirst({
            where: {
              id: input.strategyId,
              userId: ctx.session.user.id,
            },
          });

          if (!strategy) {
            throw new TRPCError({
              code: 'NOT_FOUND',
              message: 'Strategy not found',
            });
          }
        }

        const strategyConfig = await ctx.prisma.strategyConfig.create({
          data: {
            ...input,
            configJson: input.config,
            userId: ctx.session.user.id,
          },
          include: {
            user: true,
            strategy: true,
            commands: true,
            metrics: {
              take: 5,
              orderBy: { timestamp: 'desc' },
            },
          },
        });

        // Auto-start if requested
        if (input.autoStart) {
          await ctx.prisma.strategyCommand.create({
            data: {
              strategyConfigId: strategyConfig.id,
              command: 'START',
              parameters: {},
            },
          });
        }

        return strategyConfig;
      } catch (error) {
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Failed to create strategy configuration',
        });
      }
    }),

  // Create strategy configuration from existing strategy template
  createFromStrategy: protectedProcedure
    .input(
      z.object({
        strategyId: z.string(),
        name: z.string(),
        className: z.string(),
        modulePath: z.string(),
        overrideConfig: z.record(z.any()).optional(),
        autoStart: z.boolean().default(false),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Get existing strategy
      const strategy = await ctx.prisma.strategy.findFirst({
        where: {
          id: input.strategyId,
          userId: ctx.session.user.id,
        },
      });

      if (!strategy) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Strategy not found',
        });
      }

      // Merge strategy parameters with overrides
      const config = {
        ...strategy.parameters,
        ...strategy.riskParameters,
        symbols: strategy.symbols,
        assetClass: strategy.assetClass,
        timeframe: strategy.timeframe,
        maxPositions: strategy.maxPositions,
        capitalAllocated: strategy.capitalAllocated,
        ...input.overrideConfig,
      };

      // Create strategy config
      return ctx.prisma.strategyConfig.create({
        data: {
          name: input.name,
          strategyId: strategy.id,
          className: input.className,
          modulePath: input.modulePath,
          configJson: config,
          autoStart: input.autoStart,
          userId: ctx.session.user.id,
        },
        include: {
          strategy: true,
          user: true,
        },
      });
    }),

  // List all strategy configurations with their linked strategies
  list: protectedProcedure
    .input(
      z.object({
        status: z.enum(['ACTIVE', 'STOPPED', 'ERROR', 'PAUSED']).optional(),
        limit: z.number().min(1).max(100).default(10),
        cursor: z.string().optional(),
      })
    )
    .query(async ({ ctx, input }) => {
      const strategyConfigs = await ctx.prisma.strategyConfig.findMany({
        where: {
          userId: ctx.session.user.id,
          ...(input.status && { status: input.status }),
        },
        include: {
          strategy: {
            select: {
              id: true,
              name: true,
              description: true,
              strategyType: true,
              assetClass: true,
              symbols: true,
              totalPnl: true,
              totalTrades: true,
              winRate: true,
            },
          },
          commands: {
            take: 3,
            orderBy: { createdAt: 'desc' },
          },
          metrics: {
            take: 1,
            orderBy: { timestamp: 'desc' },
          },
        },
        take: input.limit + 1,
        ...(input.cursor && {
          cursor: { id: input.cursor },
          skip: 1,
        }),
        orderBy: { createdAt: 'desc' },
      });

      let nextCursor: typeof input.cursor | undefined = undefined;
      if (strategyConfigs.length > input.limit) {
        const nextItem = strategyConfigs.pop();
        nextCursor = nextItem!.id;
      }

      return {
        strategyConfigs,
        nextCursor,
      };
    }),

  // Get available strategies for creating configurations
  getAvailableStrategies: protectedProcedure.query(async ({ ctx }) => {
    return ctx.prisma.strategy.findMany({
      where: {
        userId: ctx.session.user.id,
        status: 'ACTIVE', // Only show active strategies
      },
      select: {
        id: true,
        name: true,
        description: true,
        strategyType: true,
        assetClass: true,
        symbols: true,
        parameters: true,
        riskParameters: true,
        totalPnl: true,
        winRate: true,
        _count: {
          select: {
            strategyConfigs: true, // Count existing configs
          },
        },
      },
      orderBy: { updatedAt: 'desc' },
    });
  }),

  // Get strategy details
  getById: protectedProcedure
    .input(z.object({ id: z.string() }))
    .query(async ({ ctx, input }) => {
      const strategyConfig = await ctx.prisma.strategyConfig.findFirst({
        where: {
          id: input.id,
          userId: ctx.session.user.id,
        },
        include: {
          strategy: true,
          commands: {
            orderBy: { createdAt: 'desc' },
            take: 10,
          },
          metrics: {
            orderBy: { timestamp: 'desc' },
            take: 24,
          },
        },
      });

      if (!strategyConfig) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Strategy configuration not found',
        });
      }

      return strategyConfig;
    }),

  // Send command to strategy
  sendCommand: protectedProcedure
    .input(
      z.object({
        strategyConfigId: z.string(),
        command: strategyCommandSchema.shape.command,
        parameters: strategyCommandSchema.shape.parameters,
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Verify strategy config ownership
      const strategyConfig = await ctx.prisma.strategyConfig.findFirst({
        where: {
          id: input.strategyConfigId,
          userId: ctx.session.user.id,
        },
      });

      if (!strategyConfig) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Strategy configuration not found',
        });
      }

      // Create command
      const command = await ctx.prisma.strategyCommand.create({
        data: {
          strategyConfigId: input.strategyConfigId,
          command: input.command,
          parameters: input.parameters || {},
        },
      });

      return {
        commandId: command.id,
        status: 'pending',
        message: `Command '${input.command}' queued for strategy '${strategyConfig.name}'`,
      };
    }),

  // Get system overview including both strategies and configs
  getSystemOverview: protectedProcedure.query(async ({ ctx }) => {
    // Strategy config counts by status
    const configStatusCounts = await ctx.prisma.strategyConfig.groupBy({
      by: ['status'],
      where: { userId: ctx.session.user.id },
      _count: { status: true },
    });

    // Regular strategy counts  
    const strategyStatusCounts = await ctx.prisma.strategy.groupBy({
      by: ['status'],
      where: { userId: ctx.session.user.id },
      _count: { status: true },
    });

    // Recent commands
    const recentCommands = await ctx.prisma.strategyCommand.findMany({
      where: {
        strategyConfig: { userId: ctx.session.user.id },
      },
      include: {
        strategyConfig: { 
          select: { 
            name: true,
            strategy: { select: { name: true } },
          },
        },
      },
      orderBy: { createdAt: 'desc' },
      take: 20,
    });

    // System metrics (last hour)
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
    const systemMetrics = await ctx.prisma.strategyMetric.aggregate({
      where: {
        strategyConfig: { userId: ctx.session.user.id },
        timestamp: { gte: oneHourAgo },
      },
      _count: { strategyConfigId: true },
      _avg: { pnl: true },
      _sum: { positionsCount: true, ordersCount: true },
    });

    return {
      configStatusSummary: configStatusCounts.reduce(
        (acc, item) => ({ ...acc, [item.status]: item._count.status }),
        {}
      ),
      strategyStatusSummary: strategyStatusCounts.reduce(
        (acc, item) => ({ ...acc, [item.status]: item._count.status }),
        {}
      ),
      recentCommands: recentCommands.map((cmd) => ({
        id: cmd.id,
        strategyConfigName: cmd.strategyConfig.name,
        strategyName: cmd.strategyConfig.strategy?.name || 'N/A',
        command: cmd.command,
        status: cmd.status,
        createdAt: cmd.createdAt,
        executedAt: cmd.executedAt,
      })),
      systemMetrics: {
        activeConfigs: systemMetrics._count.strategyConfigId || 0,
        avgPnl: systemMetrics._avg.pnl || 0,
        totalPositions: systemMetrics._sum.positionsCount || 0,
        totalOrders: systemMetrics._sum.ordersCount || 0,
      },
    };
  }),
});
```

## 🖥️ **Frontend Components**

### 1. Strategy Management Dashboard

```tsx
// app/(product)/strategies/enhanced/page.tsx
'use client';

import { useState } from 'react';
import { api } from '@/lib/trpc/client';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CreateStrategyDialog } from '@/components/strategy/CreateStrategyDialog';
import { StrategyCommandDialog } from '@/components/strategy/StrategyCommandDialog';
import type { StrategyConfig } from '@prisma/client';

export default function EnhancedStrategiesPage() {
  const [selectedStrategy, setSelectedStrategy] = useState<StrategyConfig | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showCommandDialog, setShowCommandDialog] = useState(false);

  const { data: strategies, refetch } = api.strategy.list.useQuery({
    limit: 20,
  });

  const { data: systemOverview } = api.strategy.getSystemOverview.useQuery();

  const sendCommandMutation = api.strategy.sendCommand.useMutation({
    onSuccess: () => {
      refetch();
      setShowCommandDialog(false);
    },
  });

  const handleCommand = (command: string) => {
    if (!selectedStrategy) return;

    sendCommandMutation.mutate({
      strategyConfigId: selectedStrategy.id,
      command: command as any,
      parameters: {},
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ACTIVE': return 'bg-green-500';
      case 'STOPPED': return 'bg-gray-500';
      case 'ERROR': return 'bg-red-500';
      case 'PAUSED': return 'bg-yellow-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <div className="space-y-6">
      {/* System Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Active Strategies</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {systemOverview?.statusSummary?.ACTIVE || 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total P&L</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ₹{systemOverview?.systemMetrics?.avgPnl?.toFixed(2) || '0.00'}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Open Positions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {systemOverview?.systemMetrics?.totalPositions || 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Orders Today</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {systemOverview?.systemMetrics?.totalOrders || 0}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Strategies List */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Strategy Configurations</CardTitle>
          <Button onClick={() => setShowCreateDialog(true)}>
            Create Strategy
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {strategies?.strategies?.map((strategy) => (
              <div
                key={strategy.id}
                className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="font-semibold">{strategy.name}</h3>
                    <Badge
                      variant="secondary"
                      className={`text-white ${getStatusColor(strategy.status)}`}
                    >
                      {strategy.status}
                    </Badge>
                  </div>
                  <p className="text-sm text-gray-600 mt-1">
                    {strategy.className} • Auto-start: {strategy.autoStart ? 'Yes' : 'No'}
                  </p>
                  {strategy.metrics?.[0] && (
                    <p className="text-sm text-gray-500 mt-1">
                      Last P&L: ₹{Number(strategy.metrics[0].pnl).toFixed(2)} • 
                      Positions: {strategy.metrics[0].positionsCount}
                    </p>
                  )}
                </div>
                
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSelectedStrategy(strategy);
                      setShowCommandDialog(true);
                    }}
                  >
                    Commands
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      // Navigate to strategy details
                      window.location.href = `/strategies/enhanced/${strategy.id}`;
                    }}
                  >
                    View Details
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Recent Commands */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Commands</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {systemOverview?.recentCommands?.slice(0, 10).map((command) => (
              <div key={command.id} className="flex justify-between items-center py-2 border-b">
                <div>
                  <span className="font-medium">{command.strategyName}</span>
                  <span className="mx-2">•</span>
                  <span className="text-blue-600">{command.command}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={command.status === 'EXECUTED' ? 'default' : 'secondary'}>
                    {command.status}
                  </Badge>
                  <span className="text-sm text-gray-500">
                    {new Date(command.createdAt).toLocaleTimeString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Dialogs */}
      <CreateStrategyDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onSuccess={() => {
          refetch();
          setShowCreateDialog(false);
        }}
      />

      <StrategyCommandDialog
        open={showCommandDialog}
        onOpenChange={setShowCommandDialog}
        strategy={selectedStrategy}
        onCommand={handleCommand}
        isLoading={sendCommandMutation.isLoading}
      />
    </div>
  );
}
```

### 2. Strategy Command Dialog

```tsx
// components/strategy/StrategyCommandDialog.tsx
'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { StrategyConfig } from '@prisma/client';

interface StrategyCommandDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  strategy: StrategyConfig | null;
  onCommand: (command: string) => void;
  isLoading: boolean;
}

export function StrategyCommandDialog({
  open,
  onOpenChange,
  strategy,
  onCommand,
  isLoading,
}: StrategyCommandDialogProps) {
  const [selectedCommand, setSelectedCommand] = useState<string>('');

  const availableCommands = strategy?.status === 'ACTIVE' 
    ? ['PAUSE', 'STOP', 'RESTART', 'UPDATE_CONFIG']
    : strategy?.status === 'PAUSED'
    ? ['RESUME', 'STOP', 'RESTART']
    : ['START'];

  const commandDescriptions = {
    START: 'Start strategy execution',
    STOP: 'Stop strategy execution',
    PAUSE: 'Pause strategy (keeps process alive)',
    RESUME: 'Resume paused strategy',
    RESTART: 'Restart strategy process',
    UPDATE_CONFIG: 'Update strategy configuration',
  };

  const handleSubmit = () => {
    if (selectedCommand) {
      onCommand(selectedCommand);
      setSelectedCommand('');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            Send Command to {strategy?.name}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Current Status:</span>
            <Badge variant="secondary">{strategy?.status}</Badge>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Available Commands:</label>
            <div className="grid grid-cols-2 gap-2">
              {availableCommands.map((command) => (
                <Button
                  key={command}
                  variant={selectedCommand === command ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSelectedCommand(command)}
                >
                  {command}
                </Button>
              ))}
            </div>
          </div>

          {selectedCommand && (
            <div className="text-sm text-gray-600 p-3 bg-gray-50 rounded">
              {commandDescriptions[selectedCommand as keyof typeof commandDescriptions]}
            </div>
          )}

          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={!selectedCommand || isLoading}
            >
              {isLoading ? 'Sending...' : 'Send Command'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

### 3. Real-time Strategy Monitor

```tsx
// components/strategy/StrategyMonitor.tsx
'use client';

import { useEffect } from 'react';
import { api } from '@/lib/trpc/client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface StrategyMonitorProps {
  strategyId: string;
}

export function StrategyMonitor({ strategyId }: StrategyMonitorProps) {
  const { data: liveStatus, refetch } = api.metrics.getLiveStatus.useQuery(
    { strategyId },
    { refetchInterval: 5000 } // Refresh every 5 seconds
  );

  const { data: metrics } = api.metrics.getStrategyMetrics.useQuery(
    { strategyId, hours: 1 },
    { refetchInterval: 30000 } // Refresh every 30 seconds
  );

  return (
    <div className="space-y-6">
      {/* Live Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Live Status
            <Badge variant="secondary">
              {liveStatus?.strategy.status}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {liveStatus?.recentMetrics?.[0] && (
              <>
                <div>
                  <p className="text-sm text-gray-600">Current P&L</p>
                  <p className="text-lg font-semibold">
                    ₹{liveStatus.recentMetrics[0].pnl.toFixed(2)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Positions</p>
                  <p className="text-lg font-semibold">
                    {liveStatus.recentMetrics[0].positionsCount}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Orders</p>
                  <p className="text-lg font-semibold">
                    {liveStatus.recentMetrics[0].ordersCount}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Success Rate</p>
                  <p className="text-lg font-semibold">
                    {liveStatus.recentMetrics[0].successRate.toFixed(1)}%
                  </p>
                </div>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Recent Commands */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Commands</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {liveStatus?.recentCommands?.map((command) => (
              <div key={command.id} className="flex justify-between items-center py-2">
                <div>
                  <span className="font-medium">{command.command}</span>
                  <span className="text-sm text-gray-500 ml-2">
                    {new Date(command.createdAt).toLocaleString()}
                  </span>
                </div>
                <Badge variant={command.status === 'EXECUTED' ? 'default' : 'secondary'}>
                  {command.status}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Performance Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Last Hour Performance</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Add your preferred charting library here */}
          <div className="h-64 flex items-center justify-center border rounded">
            Performance Chart (integrate with Chart.js, Recharts, etc.)
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

## 🔧 **Python Strategy Engine Manager Adapter**

Create a Python service that monitors your PostgreSQL database and manages strategy processes:

```python
# strategy_engine_adapter.py
import asyncio
import asyncpg
import json
import subprocess
import psutil
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class NextJSStrategyEngineAdapter:
    """Adapter to work with Next.js/Prisma database"""
    
    def __init__(self, database_url: str, redis_url: str = "redis://localhost:6379"):
        self.database_url = database_url
        self.redis_url = redis_url
        self.running_strategies: Dict[str, Dict] = {}
        self.db_pool = None
        self.is_running = False
        
    async def initialize(self):
        """Initialize the adapter"""
        # Connect to PostgreSQL
        self.db_pool = await asyncpg.create_pool(self.database_url)
        
        # Start command listener
        asyncio.create_task(self.listen_for_commands())
        
        # Start health monitor
        asyncio.create_task(self.monitor_strategies())
        
        # Auto-start configured strategies
        await self.auto_start_strategies()
        
        self.is_running = True
        logger.info("🚀 NextJS Strategy Engine Adapter initialized")
    
    async def listen_for_commands(self):
        """Listen for commands from Next.js/Prisma database"""
        
        while self.is_running:
            try:
                async with self.db_pool.acquire() as conn:
                    # Check for pending commands
                    commands = await conn.fetch("""
                        SELECT 
                            sc.id,
                            sc."strategyConfigId",
                            sc.command,
                            sc.parameters,
                            cfg.name,
                            cfg."className",
                            cfg."modulePath",
                            cfg."configJson"
                        FROM strategy_commands sc
                        JOIN strategy_configs cfg ON sc."strategyConfigId" = cfg.id
                        WHERE sc.status = 'PENDING'
                        ORDER BY sc."createdAt" ASC
                    """)
                    
                    for cmd in commands:
                        await self.execute_command(cmd)
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"❌ Command listener error: {e}")
                await asyncio.sleep(5)
    
    async def execute_command(self, cmd):
        """Execute a strategy command"""
        try:
            command_id = cmd['id']
            strategy_id = cmd['strategyConfigId']
            command = cmd['command']
            
            success = False
            
            if command == 'START':
                success = await self.start_strategy(
                    strategy_id=strategy_id,
                    name=cmd['name'],
                    class_name=cmd['className'],
                    module_path=cmd['modulePath'],
                    config=cmd['configJson']
                )
            elif command == 'STOP':
                success = await self.stop_strategy(strategy_id)
            elif command == 'RESTART':
                await self.stop_strategy(strategy_id)
                await asyncio.sleep(2)
                success = await self.start_strategy(
                    strategy_id, cmd['name'], cmd['className'], 
                    cmd['modulePath'], cmd['configJson']
                )
            
            # Mark command as executed
            await self.mark_command_executed(
                command_id, 'EXECUTED' if success else 'FAILED'
            )
            
        except Exception as e:
            logger.error(f"❌ Command execution failed: {e}")
            await self.mark_command_executed(cmd['id'], 'FAILED')
    
    async def start_strategy(self, strategy_id: str, name: str, 
                           class_name: str, module_path: str, config: dict):
        """Start an independent strategy process"""
        
        if strategy_id in self.running_strategies:
            logger.warning(f"Strategy {name} already running")
            return False
        
        try:
            # Create strategy process
            cmd = [
                'python', '-m', 'app.core.strategy_executor',
                '--strategy-id', strategy_id,
                '--name', name,
                '--class-name', class_name,
                '--module-path', module_path,
                '--config', json.dumps(config)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Track the strategy
            self.running_strategies[strategy_id] = {
                'name': name,
                'process': process,
                'pid': process.pid,
                'started_at': datetime.now(),
                'status': 'running'
            }
            
            # Update database status
            await self.update_strategy_status(strategy_id, 'ACTIVE')
            
            logger.info(f"✅ Started strategy {name} (PID: {process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start strategy {name}: {e}")
            await self.update_strategy_status(strategy_id, 'ERROR')
            return False
    
    async def update_strategy_status(self, strategy_id: str, status: str):
        """Update strategy status in database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE strategy_configs 
                SET status = $1, "updatedAt" = NOW()
                WHERE id = $2
            """, status, strategy_id)
    
    async def mark_command_executed(self, command_id: str, status: str):
        """Mark command as executed in database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE strategy_commands 
                SET status = $1, "executedAt" = NOW()
                WHERE id = $2
            """, status, command_id)

# Run the adapter
async def main():
    adapter = NextJSStrategyEngineAdapter(
        database_url="postgresql://user:pass@localhost/db"
    )
    await adapter.initialize()
    
    # Keep running
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
```

## 🚀 **Implementation Steps**

1. **Update Prisma Schema**: Add the new tables to your `schema.prisma`
2. **Run Migration**: `npx prisma migrate dev --name enhanced-strategy-tables`
3. **Create tRPC Procedures**: Add the strategy and metrics routers
4. **Build Frontend Components**: Create the management interface
5. **Deploy Python Adapter**: Run the strategy engine adapter
6. **Test Integration**: Verify commands flow from Next.js → Database → Python

## ✅ **Benefits of This Hybrid Approach**

- 🔗 **Unified Database**: Everything controlled via your existing Prisma database
- 🖥️ **Rich UI**: Leverage your Next.js frontend for management
- 🔄 **Real-time Updates**: tRPC provides type-safe real-time data
- 🔧 **Independent Execution**: Python strategies run in separate processes
- 📊 **Integrated Monitoring**: All metrics accessible via your existing dashboard
- 🛡️ **Type Safety**: Full TypeScript support throughout the stack

This approach gives you the best of both worlds - the rich TypeScript ecosystem for your frontend and the powerful Python ecosystem for strategy execution! 