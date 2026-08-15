import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

class Database:
    def __init__(self, db_path: str = "leads.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Leads table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    status TEXT DEFAULT 'new',
                    notes TEXT
                )
            ''')
            
            # Email events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS email_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id INTEGER,
                    event_type TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (lead_id) REFERENCES leads (id)
                )
            ''')
            
            # Analysis results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id INTEGER,
                    total_cost REAL,
                    waste_amount REAL,
                    savings_percentage REAL,
                    patterns TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (lead_id) REFERENCES leads (id)
                )
            ''')
            
            conn.commit()
    
    def add_lead(self, 
                 email: str, 
                 source: str = 'landing_page',
                 ip_address: Optional[str] = None,
                 user_agent: Optional[str] = None) -> Optional[int]:
        """Add new lead or update existing"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO leads (email, source, ip_address, user_agent)
                    VALUES (?, ?, ?, ?)
                ''', (email, source, ip_address, user_agent))
                
                lead_id = cursor.lastrowid
                
                # Log email capture event
                cursor.execute('''
                    INSERT INTO email_events (lead_id, event_type, metadata)
                    VALUES (?, 'captured', ?)
                ''', (lead_id, json.dumps({'source': source})))
                
                conn.commit()
                return lead_id
                
            except sqlite3.IntegrityError:
                # Email already exists, update timestamp
                cursor.execute('''
                    UPDATE leads 
                    SET updated_at = CURRENT_TIMESTAMP
                    WHERE email = ?
                ''', (email,))
                
                cursor.execute('SELECT id FROM leads WHERE email = ?', (email,))
                return cursor.fetchone()[0]
    
    def log_email_event(self, 
                        email: str, 
                        event_type: str, 
                        metadata: Optional[Dict] = None):
        """Log email events (sent, opened, clicked, etc.)"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM leads WHERE email = ?', (email,))
            result = cursor.fetchone()
            
            if result:
                lead_id = result[0]
                cursor.execute('''
                    INSERT INTO email_events (lead_id, event_type, metadata)
                    VALUES (?, ?, ?)
                ''', (lead_id, event_type, json.dumps(metadata or {})))
                conn.commit()
    
    def save_analysis_results(self, 
                              email: str, 
                              results: Dict):
        """Save analysis results for a lead"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM leads WHERE email = ?', (email,))
            result = cursor.fetchone()
            
            if result:
                lead_id = result[0]
                
                # Update lead status
                cursor.execute('''
                    UPDATE leads 
                    SET status = 'analyzed', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (lead_id,))
                
                # Save results
                cursor.execute('''
                    INSERT INTO analysis_results 
                    (lead_id, total_cost, waste_amount, savings_percentage, patterns)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    lead_id,
                    results['total_cost'],
                    results['waste_identified'],
                    results['savings_potential'],
                    json.dumps(results['patterns'])
                ))
                
                conn.commit()
    
    def get_lead_stats(self) -> Dict:
        """Get lead statistics"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total leads
            cursor.execute('SELECT COUNT(*) FROM leads')
            total_leads = cursor.fetchone()[0]
            
            # Today's leads
            today = datetime.now().date()
            cursor.execute('''
                SELECT COUNT(*) FROM leads 
                WHERE DATE(created_at) = DATE(?)
            ''', (today,))
            today_leads = cursor.fetchone()[0]
            
            # Analyzed leads
            cursor.execute('SELECT COUNT(*) FROM leads WHERE status = "analyzed"')
            analyzed_leads = cursor.fetchone()[0]
            
            # Total waste found
            cursor.execute('SELECT SUM(waste_amount) FROM analysis_results')
            total_waste = cursor.fetchone()[0] or 0
            
            # Average savings percentage
            cursor.execute('SELECT AVG(savings_percentage) FROM analysis_results')
            avg_savings = cursor.fetchone()[0] or 0
            
            return {
                'total_leads': total_leads,
                'today_leads': today_leads,
                'analyzed_leads': analyzed_leads,
                'total_waste_found': total_waste,
                'average_savings_percentage': avg_savings,
                'conversion_rate': (analyzed_leads / total_leads * 100) if total_leads > 0 else 0
            }
    
    def get_recent_leads(self, limit: int = 10) -> List[Dict]:
        """Get recent leads"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM leads 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def init_admin_table(self):
        """Initialize admin credentials table"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def init_api_keys_table(self):
        """Initialize API keys table for SDK integration"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_email TEXT NOT NULL,
                    key_prefix TEXT NOT NULL,
                    key_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            conn.commit()
    
    def init_usage_logs_table(self):
        """Initialize real-time usage tracking table"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_email TEXT NOT NULL,
                    team TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    cost REAL,
                    response_time REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT DEFAULT 'sdk'
                )
            ''')
            
            # Create index for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_usage_email_team 
                ON usage_logs(user_email, team)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_usage_timestamp 
                ON usage_logs(timestamp)
            ''')
            
            conn.commit()
    
    def create_api_key(self, email: str, key_prefix: str, key_hash: str) -> bool:
        """Create new API key for user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO api_keys (user_email, key_prefix, key_hash)
                    VALUES (?, ?, ?)
                ''', (email, key_prefix, key_hash))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_api_keys(self, email: str) -> list:
        """Return API keys for a given user (non-secret fields only)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, user_email, key_prefix, created_at, last_used, is_active
                FROM api_keys
                WHERE user_email = ?
                ORDER BY created_at DESC
            ''', (email,))
            return [dict(row) for row in cursor.fetchall()]

    def revoke_api_key(self, email: str, key_prefix: str) -> bool:
        """Deactivate an API key by prefix for a given user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE api_keys
                SET is_active = 0
                WHERE user_email = ? AND key_prefix = ?
            ''', (email, key_prefix))
            conn.commit()
            return cursor.rowcount > 0
    
    def verify_api_key(self, key_hash: str) -> Optional[str]:
        """Verify API key and return user email"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_email FROM api_keys 
                WHERE key_hash = ? AND is_active = 1
            ''', (key_hash,))
            
            result = cursor.fetchone()
            
            if result:
                # Update last_used timestamp
                cursor.execute('''
                    UPDATE api_keys 
                    SET last_used = CURRENT_TIMESTAMP 
                    WHERE key_hash = ?
                ''', (key_hash,))
                conn.commit()
                return result['user_email']
            
            return None
    
    def log_usage(self, user_email: str, team: str, model: str, 
                  prompt_tokens: int, completion_tokens: int, 
                  cost: float, response_time: float):
        """Log real-time API usage"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO usage_logs 
                (user_email, team, model, prompt_tokens, completion_tokens, cost, response_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_email, team, model, prompt_tokens, completion_tokens, cost, response_time))
            
            conn.commit()
    
    def get_realtime_team_costs(self, user_email: str, days: int = 30) -> Dict:
        """Get team cost breakdown for real-time tracking users"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                SELECT team, SUM(cost) as total_cost, COUNT(*) as call_count
                FROM usage_logs
                WHERE user_email = ? AND timestamp >= ?
                GROUP BY team
                ORDER BY total_cost DESC
            ''', (user_email, cutoff_date))
            
            results = cursor.fetchall()
            team_breakdown = {row['team']: row['total_cost'] for row in results}
            
            return team_breakdown
    
    def get_recent_usage(self, user_email: str, limit: int = 50) -> List[Dict]:
        """Get recent API calls for real-time dashboard"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT team, model, cost, timestamp, response_time
                FROM usage_logs
                WHERE user_email = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (user_email, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_admin_by_email(self, email: str) -> Optional[Dict]:
        """Get admin user by email"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM admin_users WHERE email = ? AND is_active = 1', (email,))
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def create_admin(self, email: str, password_hash: str) -> bool:
        """Create new admin user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO admin_users (email, password_hash)
                    VALUES (?, ?)
                ''', (email, password_hash))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
    
    def get_analysis_results_by_email(self, email: str) -> Optional[Dict]:
        """Get analysis results for a specific email"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT ar.* FROM analysis_results ar
                JOIN leads l ON ar.lead_id = l.id
                WHERE l.email = ?
                ORDER BY ar.timestamp DESC
                LIMIT 1
            ''', (email,))
            
            result = cursor.fetchone()
            if result:
                row_dict = dict(result)
                # Parse patterns and team_breakdown from JSON
                if row_dict.get('patterns'):
                    row_dict['patterns'] = json.loads(row_dict['patterns'])
                # Try to get team_breakdown from the JSON patterns or set default
                row_dict['team_breakdown'] = {}
                return row_dict
            return None
