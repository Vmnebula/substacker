import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from supabase import create_client, Client
import logging

logger = logging.getLogger(__name__)

class SupabaseDatabase:
    def __init__(self):
        """Initialize Supabase connection"""
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables are required")
        
        self.client: Client = create_client(self.url, self.key)
    
    def init_admin_table(self):
        """Initialize admin credentials table (already exists in Supabase schema)"""
        # Tables are created in Supabase dashboard
        logger.info("Admin table initialized (Supabase)")
    
    def init_api_keys_table(self):
        """Initialize API keys table (already exists in Supabase schema)"""
        logger.info("API keys table initialized (Supabase)")
    
    def init_usage_logs_table(self):
        """Initialize real-time usage tracking table (already exists in Supabase schema)"""
        logger.info("Usage logs table initialized (Supabase)")
    
    def add_lead(self, 
                 email: str, 
                 source: str = 'landing_page',
                 ip_address: Optional[str] = None,
                 user_agent: Optional[str] = None) -> Optional[int]:
        """Add new lead or update existing"""
        try:
            # Check if lead already exists
            response = self.client.table("leads").select("id").eq("email", email).execute()
            
            if response.data:
                # Lead exists, update timestamp
                lead_id = response.data[0]["id"]
                self.client.table("leads").update({
                    "updated_at": datetime.now().isoformat()
                }).eq("id", lead_id).execute()
                return lead_id
            
            # Create new lead
            insert_response = self.client.table("leads").insert({
                "email": email,
                "source": source,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "status": "new"
            }).execute()
            
            if insert_response.data:
                lead_id = insert_response.data[0]["id"]
                
                # Log email capture event
                self.client.table("email_events").insert({
                    "lead_id": lead_id,
                    "event_type": "captured",
                    "metadata": json.dumps({"source": source})
                }).execute()
                
                return lead_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error adding lead: {e}")
            return None
    
    def log_email_event(self, 
                        email: str, 
                        event_type: str, 
                        metadata: Optional[Dict] = None):
        """Log email events (sent, opened, clicked, etc.)"""
        try:
            # Get lead ID by email
            response = self.client.table("leads").select("id").eq("email", email).execute()
            
            if response.data:
                lead_id = response.data[0]["id"]
                self.client.table("email_events").insert({
                    "lead_id": lead_id,
                    "event_type": event_type,
                    "metadata": json.dumps(metadata or {})
                }).execute()
        except Exception as e:
            logger.error(f"Error logging email event: {e}")
    
    def save_analysis_results(self, 
                              email: str, 
                              results: Dict):
        """Save analysis results for a lead"""
        try:
            # Get lead ID by email
            response = self.client.table("leads").select("id").eq("email", email).execute()
            
            if response.data:
                lead_id = response.data[0]["id"]
                
                # Update lead status
                self.client.table("leads").update({
                    "status": "analyzed",
                    "updated_at": datetime.now().isoformat()
                }).eq("id", lead_id).execute()
                
                # Save results
                self.client.table("analysis_results").insert({
                    "lead_id": lead_id,
                    "total_cost": results.get('total_cost'),
                    "waste_amount": results.get('waste_identified'),
                    "savings_percentage": results.get('savings_potential'),
                    "patterns": json.dumps(results.get('patterns', {}))
                }).execute()
        except Exception as e:
            logger.error(f"Error saving analysis results: {e}")
    
    def get_lead_stats(self) -> Dict:
        """Get lead statistics"""
        try:
            # Total leads - count by getting all IDs (more reliable than COUNT)
            total_response = self.client.table("leads").select("id").execute()
            total_leads = len(total_response.data) if total_response.data else 0
            
            # Today's leads
            today = datetime.now().date()
            today_response = self.client.table("leads").select("id").gte(
                "created_at", 
                f"{today}T00:00:00"
            ).execute()
            today_leads = len(today_response.data) if today_response.data else 0
            
            # Analyzed leads
            analyzed_response = self.client.table("leads").select("id").eq("status", "analyzed").execute()
            analyzed_leads = len(analyzed_response.data) if analyzed_response.data else 0
            
            # Total waste found
            waste_response = self.client.table("analysis_results").select("waste_amount").execute()
            total_waste = sum([row.get("waste_amount", 0) or 0 for row in waste_response.data]) if waste_response.data else 0
            
            # Average savings percentage
            savings_response = self.client.table("analysis_results").select("savings_percentage").execute()
            if savings_response.data:
                avg_savings = sum([row.get("savings_percentage", 0) or 0 for row in savings_response.data]) / len(savings_response.data)
            else:
                avg_savings = 0
            
            return {
                'total_leads': total_leads,
                'today_leads': today_leads,
                'analyzed_leads': analyzed_leads,
                'total_waste_found': total_waste,
                'average_savings_percentage': avg_savings,
                'conversion_rate': (analyzed_leads / total_leads * 100) if total_leads > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error getting lead stats: {e}")
            return {
                'total_leads': 0,
                'today_leads': 0,
                'analyzed_leads': 0,
                'total_waste_found': 0,
                'average_savings_percentage': 0,
                'conversion_rate': 0
            }
    
    def get_recent_leads(self, limit: int = 10) -> List[Dict]:
        """Get recent leads"""
        try:
            response = self.client.table("leads").select("*").order(
                "created_at", 
                desc=True
            ).limit(limit).execute()
            
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error getting recent leads: {e}")
            return []
    
    def create_api_key(self, email: str, key_prefix: str, key_hash: str) -> bool:
        """Create new API key for user"""
        try:
            self.client.table("api_keys").insert({
                "user_email": email,
                "key_prefix": key_prefix,
                "key_hash": key_hash,
                "is_active": True
            }).execute()
            return True
        except Exception as e:
            logger.error(f"Error creating API key: {e}")
            return False

    def get_api_keys(self, email: str) -> list:
        """Return API keys for a given user (non-secret fields only)"""
        try:
            response = self.client.table("api_keys").select("id,user_email,key_prefix,created_at,last_used,is_active").eq(
                "user_email", email
            ).order("created_at", desc=True).execute()

            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching api keys: {e}")
            return []

    def revoke_api_key(self, email: str, key_prefix: str) -> bool:
        """Deactivate an API key by prefix for a given user"""
        try:
            resp = self.client.table("api_keys").update({
                "is_active": False
            }).eq("user_email", email).eq("key_prefix", key_prefix).execute()

            return True if resp and resp.data is not None else False
        except Exception as e:
            logger.error(f"Error revoking api key: {e}")
            return False
    
    def verify_api_key(self, key_hash: str) -> Optional[str]:
        """Verify API key and return user email"""
        try:
            response = self.client.table("api_keys").select("user_email").eq(
                "key_hash", key_hash
            ).eq("is_active", True).execute()
            
            if response.data:
                # Update last_used timestamp
                self.client.table("api_keys").update({
                    "last_used": datetime.now().isoformat()
                }).eq("key_hash", key_hash).execute()
                
                return response.data[0]["user_email"]
            
            return None
        except Exception as e:
            logger.error(f"Error verifying API key: {e}")
            return None
    
    def log_usage(self, user_email: str, team: str, model: str, 
                  prompt_tokens: int, completion_tokens: int, 
                  cost: float, response_time: float):
        """Log real-time API usage"""
        try:
            self.client.table("usage_logs").insert({
                "user_email": user_email,
                "team": team,
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost": cost,
                "response_time": response_time,
                "source": "sdk"
            }).execute()
        except Exception as e:
            logger.error(f"Error logging usage: {e}")
    
    def get_realtime_team_costs(self, user_email: str, days: int = 30) -> Dict:
        """Get team cost breakdown for real-time tracking users"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            response = self.client.table("usage_logs").select("team,cost").eq(
                "user_email", user_email
            ).gte("timestamp", cutoff_date).execute()
            
            team_breakdown = {}
            if response.data:
                for row in response.data:
                    team = row.get("team", "default")
                    cost = row.get("cost", 0) or 0
                    team_breakdown[team] = team_breakdown.get(team, 0) + cost
            
            return team_breakdown
        except Exception as e:
            logger.error(f"Error getting realtime team costs: {e}")
            return {}
    
    def get_recent_usage(self, user_email: str, limit: int = 50) -> List[Dict]:
        """Get recent API calls for real-time dashboard"""
        try:
            response = self.client.table("usage_logs").select(
                "team,model,cost,timestamp,response_time"
            ).eq("user_email", user_email).order("timestamp", desc=True).limit(limit).execute()
            
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error getting recent usage: {e}")
            return []
    
    def get_admin_by_email(self, email: str) -> Optional[Dict]:
        """Get admin user by email"""
        try:
            response = self.client.table("admin_users").select("*").eq(
                "email", email
            ).eq("is_active", True).execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting admin by email: {e}")
            return None
    
    def create_admin(self, email: str, password_hash: str) -> bool:
        """Create new admin user"""
        try:
            self.client.table("admin_users").insert({
                "email": email,
                "password_hash": password_hash,
                "is_active": True
            }).execute()
            return True
        except Exception as e:
            logger.error(f"Error creating admin: {e}")
            return False
    
    def get_analysis_results_by_email(self, email: str) -> Optional[Dict]:
        """Get analysis results for a specific email"""
        try:
            # Get lead ID first
            lead_response = self.client.table("leads").select("id").eq("email", email).execute()
            
            if not lead_response.data:
                return None
            
            lead_id = lead_response.data[0]["id"]
            
            # Get analysis results
            response = self.client.table("analysis_results").select("*").eq(
                "lead_id", lead_id
            ).order("timestamp", desc=True).limit(1).execute()
            
            if response.data:
                row_dict = response.data[0]
                # Parse patterns from JSON
                if row_dict.get('patterns'):
                    row_dict['patterns'] = json.loads(row_dict['patterns'])
                row_dict['team_breakdown'] = {}
                return row_dict
            
            return None
        except Exception as e:
            logger.error(f"Error getting analysis results: {e}")
            return None
