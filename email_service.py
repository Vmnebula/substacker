import smtplib
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
import os
from datetime import datetime
import jinja2
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        # Gmail SMTP is whitelisted by Railway
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_pass = os.getenv('SMTP_PASS')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_user)
        self.from_name = os.getenv('FROM_NAME', 'Substacker')
        
        # Check if SMTP credentials are set
        if not self.smtp_user or not self.smtp_pass:
            logger.warning("⚠️  SMTP credentials not configured. Email sending will be disabled.")
            logger.warning("   Set SMTP_USER and SMTP_PASS environment variables to enable emails.")
        
        # Setup Jinja2 for email templates
        self.template_loader = jinja2.FileSystemLoader('templates/email_templates')
        self.template_env = jinja2.Environment(loader=self.template_loader)
    
    def is_configured(self) -> bool:
        """Check if SMTP is properly configured"""
        return bool(self.smtp_user and self.smtp_pass)
    
    def send_email(self, 
                   to_email: str, 
                   subject: str, 
                   template_name: str, 
                   context: Dict) -> bool:
        """Send email using SMTP with improved error handling for cloud environments"""
        
        # Check if SMTP is configured
        if not self.is_configured():
            logger.warning(f"Email service not configured. Skipping email to {to_email}")
            return False
        
        try:
            # Load template
            template = self.template_env.get_template(template_name)
            html_content = template.render(**context)
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email with timeout and retry
            logger.info(f"Connecting to {self.smtp_host}:{self.smtp_port}...")
            
            # Support both SSL (port 465) and STARTTLS (port 587)
            try:
                if self.smtp_port == 465:
                    # Use SMTP_SSL for port 465
                    with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30) as server:
                        server.set_debuglevel(0)
                        server.login(self.smtp_user, self.smtp_pass)
                        server.send_message(msg)
                else:
                    # Use SMTP with STARTTLS for port 587
                    with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                        server.set_debuglevel(0)
                        server.starttls()
                        server.login(self.smtp_user, self.smtp_pass)
                        server.send_message(msg)
                
                logger.info(f"✅ Email sent to {to_email}")
                return True
            
            except socket.timeout:
                logger.error(f"❌ Socket timeout connecting to {self.smtp_host}:{self.smtp_port}")
                logger.error(f"   Check if port {self.smtp_port} is accessible from Railway")
                return False
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ SMTP Authentication failed: {e}")
            logger.error("   Check SMTP_USER and SMTP_PASS credentials")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ SMTP error: {e}")
            return False
        except (TimeoutError, socket.timeout) as e:
            logger.error(f"❌ SMTP connection timeout: {e}")
            logger.error(f"   Unable to reach {self.smtp_host}:{self.smtp_port}")
            logger.error("   Railway platform is likely blocking outbound port 587 to private servers")
            logger.error("   ACTION REQUIRED: Switch to Gmail SMTP or API-based email service")
            return False
        except OSError as e:
            if e.errno == 110:  # Connection timed out
                logger.error(f"❌ Connection timed out to {self.smtp_host}:{self.smtp_port}")
                logger.error("   Railway is blocking port 587 to your private SMTP server")
                logger.error("   IMMEDIATE FIX: Update to Gmail SMTP relay:")
                logger.error("   SMTP_HOST=smtp.gmail.com")
                logger.error("   SMTP_PORT=587")
                logger.error("   SMTP_USER=your-gmail@gmail.com")
                logger.error("   SMTP_PASS=your-app-password")
                return False
            logger.error(f"❌ Network error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Email send error: {type(e).__name__}: {e}")
            logger.error(f"   Debug: SMTP={self.smtp_host}:{self.smtp_port}")
            return False
    
    def send_welcome_email(self, email: str, name: Optional[str] = None):
        """Send welcome email with tool access"""
        
        context = {
            'name': name or email.split('@')[0],
            'tool_url': f"{os.getenv('BASE_URL')}/analyzer?email={email}",
            'current_year': datetime.now().year
        }
        
        return self.send_email(
            to_email=email,
            subject="🔥 Your OpenAI Waste Analysis Tool is Ready",
            template_name='welcome.html',
            context=context
        )
    
    def send_results_email(self, email: str, results: Dict):
        """Send analysis results via email"""
        
        context = {
            'email': email,
            'total_waste': results['waste_identified'],
            'savings_percentage': results['savings_potential'],
            'monthly_savings': results['waste_identified'] * 30,
            'patterns': results['patterns'][:3],  # Top 3 patterns
            'recommendations': results['recommendations'][:3],
            'implementation_url': f"{os.getenv('BASE_URL')}/book-implementation?email={email}",
            'current_year': datetime.now().year
        }
        
        return self.send_email(
            to_email=email,
            subject=f"💰 We Found ${results['waste_identified']:.0f} in OpenAI Waste",
            template_name='results.html',
            context=context
        )
    
    def send_admin_notification(self, lead_email: str, lead_data: Dict):
        """Notify admin of new lead"""
        
        # Skip if SMTP not configured
        if not self.is_configured():
            logger.warning("Email service not configured. Skipping admin notification.")
            return False
        
        admin_email = os.getenv('ADMIN_EMAIL', self.smtp_user)
        
        if not admin_email:
            logger.warning("ADMIN_EMAIL not set. Skipping admin notification.")
            return False
        
        context = {
            'lead_email': lead_email,
            'lead_data': lead_data,
            'timestamp': datetime.now().isoformat()
        }
        
        # Simple text email for admin
        subject = f"New Lead: {lead_email}"
        body = f"""
        New lead captured:
        
        Email: {lead_email}
        Source: {lead_data.get('source', 'Unknown')}
        Timestamp: {context['timestamp']}
        IP: {lead_data.get('ip_address', 'Unknown')}
        User Agent: {lead_data.get('user_agent', 'Unknown')}
        
        Total leads today: {lead_data.get('daily_count', 'Unknown')}
        """
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.from_email
        msg['To'] = admin_email
        
        try:
            logger.info(f"Sending admin notification to {admin_email}...")
            if self.smtp_port == 465:
                # Use SMTP_SSL for port 465
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30) as server:
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
            else:
                # Use SMTP with STARTTLS for port 587
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
            logger.info(f"✅ Admin notification sent to {admin_email}")
            return True
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ SMTP Authentication failed for admin notification: {e}")
            return False
        except (TimeoutError, socket.timeout, OSError) as e:
            logger.error(f"❌ Admin notification timeout/network error: {type(e).__name__}: {e}")
            logger.warning("   Skipping admin notification (non-critical)")
            return False
        except Exception as e:
            logger.error(f"❌ Admin notification error: {type(e).__name__}: {e}")
            return False