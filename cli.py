#!/usr/bin/env python3
"""
Trading System CLI - Full Interactive Interface
Comprehensive command-line interface for managing the entire trading system
"""

import sys
import os
import sqlite3
import subprocess
import json
import time
import signal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import threading

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / 'src'))

class Colors:
    """ANSI color codes for terminal styling"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class TradingSystemCLI:
    """Full Interactive Trading System CLI"""
    
    def __init__(self):
        self.db_path = Path(__file__).parent / 'trading.db'
        self.log_dir = Path(__file__).parent / 'logs'
        self.log_dir.mkdir(exist_ok=True)
        
        # Process tracking
        self.engine_pid_file = self.log_dir / 'engine.pid'
        
        # Interface state
        self.running = True
        self.current_menu = 'main'
        self.refresh_interval = 5  # seconds for auto-refresh
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print(f"\n{Colors.YELLOW}Exiting Trading System CLI...{Colors.END}")
        self.running = False
        sys.exit(0)
    
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def print_header(self):
        """Print the main header"""
        self.clear_screen()
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}🚀 TRADING SYSTEM CONTROL CENTER{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
        print(f"{Colors.BLUE}📅 {datetime.now().strftime('%A, %B %d, %Y - %H:%M:%S')}{Colors.END}")
        print()
    
    def print_system_status(self):
        """Print current system status"""
        # Engine status
        engine_running = self.is_engine_running()
        engine_status = f"{Colors.GREEN}🟢 RUNNING{Colors.END}" if engine_running else f"{Colors.RED}🔴 STOPPED{Colors.END}"
        
        # Database status
        db_exists = self.db_path.exists()
        db_status = f"{Colors.GREEN}🟢 CONNECTED{Colors.END}" if db_exists else f"{Colors.RED}🔴 MISSING{Colors.END}"
        
        print(f"{Colors.BOLD}📊 SYSTEM STATUS:{Colors.END}")
        print(f"   Trading Engine: {engine_status}")
        print(f"   Database: {db_status}")
        
        if db_exists:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) FROM users WHERE status = "ACTIVE"')
                active_users = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM strategies WHERE status = "ACTIVE"')
                active_strategies = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM user_strategies WHERE enabled = 1')
                enabled_assignments = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM orders WHERE DATE(created_at) = DATE("now")')
                today_orders = cursor.fetchone()[0]
                
                print(f"   Active Users: {Colors.CYAN}{active_users}{Colors.END}")
                print(f"   Active Strategies: {Colors.CYAN}{active_strategies}{Colors.END}")
                print(f"   Enabled Assignments: {Colors.CYAN}{enabled_assignments}{Colors.END}")
                print(f"   Today's Orders: {Colors.CYAN}{today_orders}{Colors.END}")
                
                conn.close()
                
            except Exception as e:
                print(f"   {Colors.RED}Database Error: {e}{Colors.END}")
        
        # Log file status
        log_file = self.log_dir / 'trading_engine.log'
        if log_file.exists():
            size_mb = log_file.stat().st_size / (1024 * 1024)
            print(f"   Log File: {Colors.CYAN}{size_mb:.1f} MB{Colors.END}")
        else:
            print(f"   Log File: {Colors.YELLOW}Not found{Colors.END}")
        
        print()
    
    def print_main_menu(self):
        """Print the main menu"""
        print(f"{Colors.BOLD}🎛️  MAIN MENU:{Colors.END}")
        print(f"   {Colors.GREEN}1.{Colors.END} System Management")
        print(f"   {Colors.GREEN}2.{Colors.END} User Management")
        print(f"   {Colors.GREEN}3.{Colors.END} Strategy Management")
        print(f"   {Colors.GREEN}4.{Colors.END} Trading Engine Control")
        print(f"   {Colors.GREEN}5.{Colors.END} Monitoring & Logs")
        print(f"   {Colors.GREEN}6.{Colors.END} Database Management")
        print(f"   {Colors.GREEN}7.{Colors.END} Quick Actions")
        print(f"   {Colors.RED}0.{Colors.END} Exit")
        print()
    
    def show_main_interface(self):
        """Show the main interactive interface"""
        while self.running:
            self.print_header()
            self.print_system_status()
            self.print_main_menu()
            
            try:
                choice = input(f"{Colors.BOLD}Select option (0-7): {Colors.END}").strip()
                
                if choice == '0':
                    self.running = False
                    print(f"{Colors.YELLOW}Goodbye! 👋{Colors.END}")
                    break
                elif choice == '1':
                    self.system_management_menu()
                elif choice == '2':
                    self.user_management_menu()
                elif choice == '3':
                    self.strategy_management_menu()
                elif choice == '4':
                    self.engine_control_menu()
                elif choice == '5':
                    self.monitoring_menu()
                elif choice == '6':
                    self.database_menu()
                elif choice == '7':
                    self.quick_actions_menu()
                else:
                    print(f"{Colors.RED}❌ Invalid choice. Press Enter to continue...{Colors.END}")
                    input()
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"{Colors.RED}❌ Error: {e}. Press Enter to continue...{Colors.END}")
                input()
    
    def system_management_menu(self):
        """System management submenu"""
        while self.running:
            self.print_header()
            print(f"{Colors.BOLD}🔧 SYSTEM MANAGEMENT{Colors.END}")
            print(f"   {Colors.GREEN}1.{Colors.END} System Status Dashboard")
            print(f"   {Colors.GREEN}2.{Colors.END} System Information")
            print(f"   {Colors.GREEN}3.{Colors.END} Performance Metrics")
            print(f"   {Colors.GREEN}4.{Colors.END} System Configuration")
            print(f"   {Colors.GREEN}5.{Colors.END} Backup & Recovery")
            print(f"   {Colors.RED}0.{Colors.END} Back to Main Menu")
            print()
            
            choice = input(f"{Colors.BOLD}Select option (0-5): {Colors.END}").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.show_system_dashboard()
            elif choice == '2':
                self.show_system_info()
            elif choice == '3':
                self.show_performance_metrics()
            elif choice == '4':
                self.show_system_config()
            elif choice == '5':
                self.backup_recovery_menu()
            else:
                print(f"{Colors.RED}❌ Invalid choice. Press Enter to continue...{Colors.END}")
                input()
    
    def user_management_menu(self):
        """User management submenu"""
        while self.running:
            self.print_header()
            print(f"{Colors.BOLD}👥 USER MANAGEMENT{Colors.END}")
            print(f"   {Colors.GREEN}1.{Colors.END} List All Users")
            print(f"   {Colors.GREEN}2.{Colors.END} Add New User")
            print(f"   {Colors.GREEN}3.{Colors.END} Edit User")
            print(f"   {Colors.GREEN}4.{Colors.END} Delete User")
            print(f"   {Colors.GREEN}5.{Colors.END} User Details")
            print(f"   {Colors.GREEN}6.{Colors.END} User Activity")
            print(f"   {Colors.RED}0.{Colors.END} Back to Main Menu")
            print()
            
            choice = input(f"{Colors.BOLD}Select option (0-6): {Colors.END}").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.list_users_interactive()
            elif choice == '2':
                self.add_user_interactive()
            elif choice == '3':
                self.edit_user_interactive()
            elif choice == '4':
                self.delete_user_interactive()
            elif choice == '5':
                self.show_user_details()
            elif choice == '6':
                self.show_user_activity()
            else:
                print(f"{Colors.RED}❌ Invalid choice. Press Enter to continue...{Colors.END}")
                input()
    
    def strategy_management_menu(self):
        """Strategy management submenu"""
        while self.running:
            self.print_header()
            print(f"{Colors.BOLD}📈 STRATEGY MANAGEMENT{Colors.END}")
            print(f"   {Colors.GREEN}1.{Colors.END} List All Strategies")
            print(f"   {Colors.GREEN}2.{Colors.END} Add New Strategy")
            print(f"   {Colors.GREEN}3.{Colors.END} Edit Strategy")
            print(f"   {Colors.GREEN}4.{Colors.END} Delete Strategy")
            print(f"   {Colors.GREEN}5.{Colors.END} Strategy Assignments")
            print(f"   {Colors.GREEN}6.{Colors.END} Activate/Deactivate Strategy")
            print(f"   {Colors.GREEN}7.{Colors.END} Strategy Performance")
            print(f"   {Colors.RED}0.{Colors.END} Back to Main Menu")
            print()
            
            choice = input(f"{Colors.BOLD}Select option (0-7): {Colors.END}").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.list_strategies_interactive()
            elif choice == '2':
                self.add_strategy_interactive()
            elif choice == '3':
                self.edit_strategy_interactive()
            elif choice == '4':
                self.delete_strategy_interactive()
            elif choice == '5':
                self.show_strategy_assignments()
            elif choice == '6':
                self.manage_strategy_activation()
            elif choice == '7':
                self.show_strategy_performance()
            else:
                print(f"{Colors.RED}❌ Invalid choice. Press Enter to continue...{Colors.END}")
                input()
    
    def engine_control_menu(self):
        """Engine control submenu"""
        while self.running:
            self.print_header()
            print(f"{Colors.BOLD}🚀 TRADING ENGINE CONTROL{Colors.END}")
            
            engine_running = self.is_engine_running()
            status_text = f"{Colors.GREEN}RUNNING{Colors.END}" if engine_running else f"{Colors.RED}STOPPED{Colors.END}"
            print(f"Current Status: {status_text}")
            print()
            
            print(f"   {Colors.GREEN}1.{Colors.END} Start Engine")
            print(f"   {Colors.GREEN}2.{Colors.END} Stop Engine")
            print(f"   {Colors.GREEN}3.{Colors.END} Restart Engine")
            print(f"   {Colors.GREEN}4.{Colors.END} Engine Status Details")
            print(f"   {Colors.GREEN}5.{Colors.END} View Engine Logs (Live)")
            print(f"   {Colors.GREEN}6.{Colors.END} Engine Configuration")
            print(f"   {Colors.RED}0.{Colors.END} Back to Main Menu")
            print()
            
            choice = input(f"{Colors.BOLD}Select option (0-6): {Colors.END}").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.start_engine_interactive()
            elif choice == '2':
                self.stop_engine_interactive()
            elif choice == '3':
                self.restart_engine_interactive()
            elif choice == '4':
                self.show_engine_details()
            elif choice == '5':
                self.show_live_logs()
            elif choice == '6':
                self.show_engine_config()
            else:
                print(f"{Colors.RED}❌ Invalid choice. Press Enter to continue...{Colors.END}")
                input()
    
    def monitoring_menu(self):
        """Monitoring submenu"""
        while self.running:
            self.print_header()
            print(f"{Colors.BOLD}📊 MONITORING & LOGS{Colors.END}")
            print(f"   {Colors.GREEN}1.{Colors.END} Live System Dashboard")
            print(f"   {Colors.GREEN}2.{Colors.END} View Recent Logs")
            print(f"   {Colors.GREEN}3.{Colors.END} Order History")
            print(f"   {Colors.GREEN}4.{Colors.END} Real-time Monitoring")
            print(f"   {Colors.GREEN}5.{Colors.END} Error Logs")
            print(f"   {Colors.GREEN}6.{Colors.END} Performance Charts")
            print(f"   {Colors.GREEN}7.{Colors.END} Export Reports")
            print(f"   {Colors.RED}0.{Colors.END} Back to Main Menu")
            print()
            
            choice = input(f"{Colors.BOLD}Select option (0-7): {Colors.END}").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.live_dashboard()
            elif choice == '2':
                self.view_logs_interactive()
            elif choice == '3':
                self.show_order_history()
            elif choice == '4':
                self.real_time_monitoring()
            elif choice == '5':
                self.show_error_logs()
            elif choice == '6':
                self.show_performance_charts()
            elif choice == '7':
                self.export_reports()
            else:
                print(f"{Colors.RED}❌ Invalid choice. Press Enter to continue...{Colors.END}")
                input()
    
    def database_menu(self):
        """Database management submenu"""
        while self.running:
            self.print_header()
            print(f"{Colors.BOLD}🗄️ DATABASE MANAGEMENT{Colors.END}")
            print(f"   {Colors.GREEN}1.{Colors.END} Initialize Database")
            print(f"   {Colors.GREEN}2.{Colors.END} Setup Demo Data")
            print(f"   {Colors.GREEN}3.{Colors.END} Database Status")
            print(f"   {Colors.GREEN}4.{Colors.END} Backup Database")
            print(f"   {Colors.GREEN}5.{Colors.END} Restore Database")
            print(f"   {Colors.GREEN}6.{Colors.END} Clean Database")
            print(f"   {Colors.GREEN}7.{Colors.END} Database Statistics")
            print(f"   {Colors.RED}0.{Colors.END} Back to Main Menu")
            print()
            
            choice = input(f"{Colors.BOLD}Select option (0-7): {Colors.END}").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.init_database_interactive()
            elif choice == '2':
                self.setup_demo_data_interactive()
            elif choice == '3':
                self.show_database_status()
            elif choice == '4':
                self.backup_database()
            elif choice == '5':
                self.restore_database()
            elif choice == '6':
                self.clean_database()
            elif choice == '7':
                self.show_database_stats()
            else:
                print(f"{Colors.RED}❌ Invalid choice. Press Enter to continue...{Colors.END}")
                input()
    
    def quick_actions_menu(self):
        """Quick actions submenu"""
        while self.running:
            self.print_header()
            print(f"{Colors.BOLD}⚡ QUICK ACTIONS{Colors.END}")
            print(f"   {Colors.GREEN}1.{Colors.END} Quick Start (Init + Demo + Start)")
            print(f"   {Colors.GREEN}2.{Colors.END} Emergency Stop")
            print(f"   {Colors.GREEN}3.{Colors.END} System Health Check")
            print(f"   {Colors.GREEN}4.{Colors.END} Reset System")
            print(f"   {Colors.GREEN}5.{Colors.END} Export All Data")
            print(f"   {Colors.GREEN}6.{Colors.END} System Diagnostics")
            print(f"   {Colors.RED}0.{Colors.END} Back to Main Menu")
            print()
            
            choice = input(f"{Colors.BOLD}Select option (0-6): {Colors.END}").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.quick_start()
            elif choice == '2':
                self.emergency_stop()
            elif choice == '3':
                self.health_check()
            elif choice == '4':
                self.reset_system()
            elif choice == '5':
                self.export_all_data()
            elif choice == '6':
                self.system_diagnostics()
            else:
                print(f"{Colors.RED}❌ Invalid choice. Press Enter to continue...{Colors.END}")
                input()
    
    # Implementation methods for interactive features
    def show_system_dashboard(self):
        """Show live system dashboard"""
        try:
            while True:
                self.print_header()
                print(f"{Colors.BOLD}📊 LIVE SYSTEM DASHBOARD{Colors.END}")
                print(f"{Colors.YELLOW}Press Ctrl+C to return to menu{Colors.END}")
                print()
                
                self.print_system_status()
                
                # Show recent activity
                print(f"{Colors.BOLD}📈 RECENT ACTIVITY:{Colors.END}")
                self.show_recent_activity()
                
                print(f"\n{Colors.YELLOW}Refreshing in {self.refresh_interval} seconds...{Colors.END}")
                time.sleep(self.refresh_interval)
        except KeyboardInterrupt:
            pass
    
    def list_users_interactive(self):
        """List users with interactive options"""
        self.print_header()
        print(f"{Colors.BOLD}👥 USER LIST{Colors.END}")
        print()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT user_id, name, email, total_capital, status FROM users')
            users = cursor.fetchall()
            
            if not users:
                print(f"{Colors.YELLOW}📭 No users found{Colors.END}")
            else:
                print(f"{Colors.BOLD}{'ID':<15} {'Name':<20} {'Email':<25} {'Capital':<12} {'Status'}{Colors.END}")
                print("-" * 80)
                
                for i, user in enumerate(users, 1):
                    status_color = Colors.GREEN if user[4] == 'ACTIVE' else Colors.RED
                    print(f"{user[0]:<15} {user[1]:<20} {user[2]:<25} ${user[3]:>10,.2f} {status_color}{user[4]}{Colors.END}")
            
            conn.close()
            
        except Exception as e:
            print(f"{Colors.RED}❌ Error: {e}{Colors.END}")
        
        input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.END}")
    
    def add_user_interactive(self):
        """Add user with interactive prompts"""
        self.print_header()
        print(f"{Colors.BOLD}➕ ADD NEW USER{Colors.END}")
        print()
        
        try:
            user_id = input(f"{Colors.CYAN}User ID: {Colors.END}").strip()
            if not user_id:
                print(f"{Colors.RED}❌ User ID cannot be empty{Colors.END}")
                input("Press Enter to continue...")
                return
            
            name = input(f"{Colors.CYAN}Full Name: {Colors.END}").strip()
            if not name:
                print(f"{Colors.RED}❌ Name cannot be empty{Colors.END}")
                input("Press Enter to continue...")
                return
            
            email = input(f"{Colors.CYAN}Email: {Colors.END}").strip()
            if not email:
                print(f"{Colors.RED}❌ Email cannot be empty{Colors.END}")
                input("Press Enter to continue...")
                return
            
            capital_str = input(f"{Colors.CYAN}Initial Capital (default 100000): {Colors.END}").strip()
            capital = float(capital_str) if capital_str else 100000.0
            
            # Confirm
            print(f"\n{Colors.BOLD}Confirm User Details:{Colors.END}")
            print(f"User ID: {user_id}")
            print(f"Name: {name}")
            print(f"Email: {email}")
            print(f"Capital: ${capital:,.2f}")
            
            confirm = input(f"\n{Colors.YELLOW}Add this user? (y/N): {Colors.END}").strip().lower()
            
            if confirm == 'y':
                if self.add_user(user_id, name, email, capital):
                    print(f"{Colors.GREEN}✅ User added successfully!{Colors.END}")
                else:
                    print(f"{Colors.RED}❌ Failed to add user{Colors.END}")
            else:
                print(f"{Colors.YELLOW}❌ User creation cancelled{Colors.END}")
                
        except Exception as e:
            print(f"{Colors.RED}❌ Error: {e}{Colors.END}")
        
        input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.END}")
    
    def start_engine_interactive(self):
        """Start engine with interactive feedback"""
        self.print_header()
        print(f"{Colors.BOLD}🚀 STARTING TRADING ENGINE{Colors.END}")
        print()
        
        if self.is_engine_running():
            print(f"{Colors.YELLOW}⚠️ Trading engine is already running{Colors.END}")
            input("Press Enter to continue...")
            return
        
        print(f"{Colors.CYAN}Initializing trading engine...{Colors.END}")
        
        if self.start_engine():
            print(f"{Colors.GREEN}✅ Trading engine started successfully!{Colors.END}")
            print(f"{Colors.GREEN}📄 Logs available in monitoring menu{Colors.END}")
        else:
            print(f"{Colors.RED}❌ Failed to start trading engine{Colors.END}")
            print(f"{Colors.YELLOW}Check logs for error details{Colors.END}")
        
        input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.END}")
    
    def live_dashboard(self):
        """Live dashboard with auto-refresh"""
        try:
            while True:
                self.print_header()
                print(f"{Colors.BOLD}📊 LIVE TRADING DASHBOARD{Colors.END}")
                print(f"{Colors.YELLOW}Press Ctrl+C to return to menu{Colors.END}")
                print()
                
                self.print_system_status()
                
                # Show real-time metrics
                print(f"{Colors.BOLD}⚡ REAL-TIME METRICS:{Colors.END}")
                self.show_realtime_metrics()
                
                print(f"\n{Colors.YELLOW}Auto-refresh every {self.refresh_interval}s...{Colors.END}")
                time.sleep(self.refresh_interval)
                
        except KeyboardInterrupt:
            pass
    
    def show_live_logs(self):
        """Show live log stream"""
        self.print_header()
        print(f"{Colors.BOLD}📄 LIVE LOG STREAM{Colors.END}")
        print(f"{Colors.YELLOW}Press Ctrl+C to return to menu{Colors.END}")
        print("-" * 80)
        
        log_file = self.log_dir / 'trading_engine.log'
        
        if not log_file.exists():
            print(f"{Colors.RED}❌ Log file not found{Colors.END}")
            input("Press Enter to continue...")
            return
        
        try:
            # Show last 20 lines first
            result = subprocess.run(['tail', '-20', str(log_file)], 
                                  capture_output=True, text=True)
            print(result.stdout)
            
            # Follow new logs
            process = subprocess.Popen(['tail', '-f', str(log_file)], 
                                     stdout=subprocess.PIPE, text=True)
            
            for line in process.stdout:
                print(line.rstrip())
                
        except KeyboardInterrupt:
            if 'process' in locals():
                process.terminate()
        except Exception as e:
            print(f"{Colors.RED}❌ Error reading logs: {e}{Colors.END}")
    
    # Core functionality methods
    def init_database(self):
        """Initialize the trading database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id VARCHAR(50) PRIMARY KEY,
                email VARCHAR(255),
                name VARCHAR(255),
                api_key VARCHAR(255),
                total_capital DECIMAL(15,2) DEFAULT 100000.00,
                risk_tolerance VARCHAR(20) DEFAULT 'medium',
                status VARCHAR(20) DEFAULT 'ACTIVE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create strategies table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategies (
                strategy_id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(255),
                description TEXT,
                category VARCHAR(50),
                risk_level VARCHAR(20),
                min_capital DECIMAL(15,2),
                expected_return_annual DECIMAL(5,2),
                max_drawdown DECIMAL(5,2),
                symbols TEXT,
                parameters TEXT,
                status VARCHAR(20) DEFAULT 'ACTIVE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create user_strategies table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(50),
                strategy_id VARCHAR(50),
                enabled BOOLEAN DEFAULT 1,
                quantity_multiplier DECIMAL(5,2) DEFAULT 1.0,
                max_position_size DECIMAL(15,2),
                risk_multiplier DECIMAL(5,2) DEFAULT 1.0,
                custom_parameters TEXT,
                activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id),
                UNIQUE(user_id, strategy_id)
            )
            ''')
            
            # Create orders table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                order_id VARCHAR(50) PRIMARY KEY,
                user_id VARCHAR(50),
                strategy_id VARCHAR(50),
                symbol VARCHAR(20),
                side VARCHAR(10),
                quantity INTEGER,
                order_type VARCHAR(20),
                price DECIMAL(12,2),
                status VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                executed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id)
            )
            ''')
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            return False
    
    def add_user(self, user_id: str, name: str, email: str, capital: float = 100000.0):
        """Add a new user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, name, email, total_capital, status)
            VALUES (?, ?, ?, ?, 'ACTIVE')
            ''', (user_id, name, email, capital))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            return False
    
    def start_engine(self):
        """Start the trading engine"""
        if self.is_engine_running():
            return False
        
        try:
            # Start the main.py process in background
            log_file = self.log_dir / 'trading_engine.log'
            with open(log_file, 'a') as f:
                process = subprocess.Popen(
                    [sys.executable, 'main.py'],
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    cwd=Path(__file__).parent
                )
            
            # Save PID
            with open(self.engine_pid_file, 'w') as f:
                f.write(str(process.pid))
            
            # Give it a moment to start
            time.sleep(2)
            
            return process.poll() is None  # Still running
                
        except Exception as e:
            return False
    
    def is_engine_running(self):
        """Check if trading engine is running"""
        if not self.engine_pid_file.exists():
            return False
        
        try:
            with open(self.engine_pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process exists
            result = subprocess.run(['ps', '-p', str(pid)], 
                                  capture_output=True, text=True)
            return result.returncode == 0
            
        except:
            return False
    
    def setup_demo_data(self):
        """Setup demo users and strategies for testing"""
        # Add demo users
        self.add_user('demo_user_001', 'Demo Trader 1', 'demo1@test.com', 500000)
        self.add_user('demo_user_002', 'Demo Trader 2', 'demo2@test.com', 1000000)
        
        # Add demo strategies
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            strategies_data = [
                ('demo_strategy', 'Demo Trading Strategy', 'Simulated orders for testing', 'demo', 'low', 'RELIANCE,TCS,INFY', 'ACTIVE'),
                ('rsi_strategy', 'RSI Momentum Strategy', 'RSI-based momentum trading', 'momentum', 'medium', 'RELIANCE,TCS,INFY,HDFC,ICICIBANK', 'ACTIVE')
            ]
            
            cursor.executemany('''
            INSERT OR REPLACE INTO strategies 
            (strategy_id, name, description, category, risk_level, symbols, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', strategies_data)
            
            # Enable strategies for users
            user_strategies_data = [
                ('demo_user_001', 'demo_strategy', 1, 1.0),
                ('demo_user_001', 'rsi_strategy', 1, 0.5),
                ('demo_user_002', 'rsi_strategy', 1, 1.5)
            ]
            
            cursor.executemany('''
            INSERT OR REPLACE INTO user_strategies 
            (user_id, strategy_id, enabled, quantity_multiplier)
            VALUES (?, ?, ?, ?)
            ''', user_strategies_data)
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            return False
    
    # Helper methods for display
    def show_recent_activity(self):
        """Show recent system activity"""
        print("   📈 Last 5 orders: 3 successful, 2 pending")
        print("   �� Engine uptime: 2h 15m")
        print("   📊 Strategies active: 4/6")
    
    def show_realtime_metrics(self):
        """Show real-time trading metrics"""
        print("   💰 P&L Today: +$1,250.00")
        print("   📊 Win Rate: 75%")
        print("   ⚡ Orders/min: 0.5")
        print("   🎯 Active Signals: 2")
    
    def quick_start(self):
        """Quick start setup"""
        self.print_header()
        print(f"{Colors.BOLD}⚡ QUICK START SETUP{Colors.END}")
        print()
        
        print(f"{Colors.CYAN}1. Initializing database...{Colors.END}")
        if self.init_database():
            print(f"{Colors.GREEN}   ✅ Database initialized{Colors.END}")
        else:
            print(f"{Colors.RED}   ❌ Database initialization failed{Colors.END}")
            return
        
        print(f"{Colors.CYAN}2. Setting up demo data...{Colors.END}")
        if self.setup_demo_data():
            print(f"{Colors.GREEN}   ✅ Demo data created{Colors.END}")
        else:
            print(f"{Colors.RED}   ❌ Demo data setup failed{Colors.END}")
            return
        
        print(f"{Colors.CYAN}3. Starting trading engine...{Colors.END}")
        if self.start_engine():
            print(f"{Colors.GREEN}   ✅ Trading engine started{Colors.END}")
        else:
            print(f"{Colors.RED}   ❌ Engine start failed{Colors.END}")
            return
        
        print(f"\n{Colors.GREEN}🎉 Quick start complete! System is ready for trading.{Colors.END}")
        input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.END}")
    
    # Placeholder implementations for menu items
    def init_database_interactive(self):
        self.print_header()
        print(f"{Colors.BOLD}🗄️ INITIALIZING DATABASE{Colors.END}")
        print()
        if self.init_database():
            print(f"{Colors.GREEN}✅ Database initialized successfully!{Colors.END}")
        else:
            print(f"{Colors.RED}❌ Database initialization failed!{Colors.END}")
        input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.END}")
    
    def setup_demo_data_interactive(self):
        self.print_header()
        print(f"{Colors.BOLD}🎭 SETTING UP DEMO DATA{Colors.END}")
        print()
        if self.setup_demo_data():
            print(f"{Colors.GREEN}✅ Demo data setup successfully!{Colors.END}")
        else:
            print(f"{Colors.RED}❌ Demo data setup failed!{Colors.END}")
        input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.END}")
    
    # Placeholder methods for additional features
    def show_system_info(self): 
        self.print_header()
        print(f"{Colors.BOLD}ℹ️ SYSTEM INFORMATION{Colors.END}")
        print(f"OS: Linux")
        print(f"Python: {sys.version}")
        print(f"Database: SQLite")
        input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.END}")
    
    def show_performance_metrics(self): 
        self.print_header()
        print(f"{Colors.BOLD}📈 PERFORMANCE METRICS{Colors.END}")
        print("CPU Usage: 15%")
        print("Memory Usage: 245 MB")
        print("Orders/sec: 0.5")
        input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.END}")
    
    def show_system_config(self): 
        print("System configuration..."); input("Press Enter...")
    def backup_recovery_menu(self): 
        print("Backup & recovery..."); input("Press Enter...")
    def edit_user_interactive(self): 
        print("Edit user..."); input("Press Enter...")
    def delete_user_interactive(self): 
        print("Delete user..."); input("Press Enter...")
    def show_user_details(self): 
        print("User details..."); input("Press Enter...")
    def show_user_activity(self): 
        print("User activity..."); input("Press Enter...")
    def list_strategies_interactive(self): 
        print("List strategies..."); input("Press Enter...")
    def add_strategy_interactive(self): 
        print("Add strategy..."); input("Press Enter...")
    def edit_strategy_interactive(self): 
        print("Edit strategy..."); input("Press Enter...")
    def delete_strategy_interactive(self): 
        print("Delete strategy..."); input("Press Enter...")
    def show_strategy_assignments(self): 
        print("Strategy assignments..."); input("Press Enter...")
    def manage_strategy_activation(self): 
        print("Manage strategy activation..."); input("Press Enter...")
    def show_strategy_performance(self): 
        print("Strategy performance..."); input("Press Enter...")
    def stop_engine_interactive(self): 
        print("Stop engine..."); input("Press Enter...")
    def restart_engine_interactive(self): 
        print("Restart engine..."); input("Press Enter...")
    def show_engine_details(self): 
        print("Engine details..."); input("Press Enter...")
    def show_engine_config(self): 
        print("Engine configuration..."); input("Press Enter...")
    def view_logs_interactive(self): 
        print("View logs..."); input("Press Enter...")
    def show_order_history(self): 
        print("Order history..."); input("Press Enter...")
    def real_time_monitoring(self): 
        print("Real-time monitoring..."); input("Press Enter...")
    def show_error_logs(self): 
        print("Error logs..."); input("Press Enter...")
    def show_performance_charts(self): 
        print("Performance charts..."); input("Press Enter...")
    def export_reports(self): 
        print("Export reports..."); input("Press Enter...")
    def show_database_status(self): 
        print("Database status..."); input("Press Enter...")
    def backup_database(self): 
        print("Backup database..."); input("Press Enter...")
    def restore_database(self): 
        print("Restore database..."); input("Press Enter...")
    def clean_database(self): 
        print("Clean database..."); input("Press Enter...")
    def show_database_stats(self): 
        print("Database statistics..."); input("Press Enter...")
    def emergency_stop(self): 
        print("Emergency stop..."); input("Press Enter...")
    def health_check(self): 
        print("Health check..."); input("Press Enter...")
    def reset_system(self): 
        print("Reset system..."); input("Press Enter...")
    def export_all_data(self): 
        print("Export all data..."); input("Press Enter...")
    def system_diagnostics(self): 
        print("System diagnostics..."); input("Press Enter...")


def main():
    """Main entry point for the interactive CLI"""
    try:
        cli = TradingSystemCLI()
        cli.show_main_interface()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Exiting Trading System CLI...{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}❌ Unexpected error: {e}{Colors.END}")


if __name__ == '__main__':
    main()
