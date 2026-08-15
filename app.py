from fastapi import FastAPI, File, UploadFile, Request, Form, BackgroundTasks, Response, Depends, HTTPException, Cookie, Header, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd
import io
import json
import logging
from datetime import datetime
from analyzer_v2 import OpenAIWasteAnalyzer  # Using production-grade v2 with all fixes
from database_supabase import SupabaseDatabase
from email_service import EmailService
from auth import verify_password, create_access_token, verify_token, get_password_hash
from security import SecurityConfig, InputValidator, FileValidator, CSRFProtection, SecurityHeaders
from websocket_manager import ws_manager, EventType, broadcast_cost_update, broadcast_analysis_complete, broadcast_anomaly
import uvicorn
from typing import Optional, Generator
import os
import hashlib
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Set up logging
logger = logging.getLogger(__name__)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/sample_data", StaticFiles(directory="sample_data"), name="sample_data")
templates = Jinja2Templates(directory="templates")

# Initialize services
db = SupabaseDatabase()
db.init_admin_table()  # Initialize admin table
db.init_api_keys_table()  # Initialize API keys table
db.init_usage_logs_table()  # Initialize usage logs table
email_service = EmailService()
analyzer = OpenAIWasteAnalyzer()

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda request, exc: JSONResponse(
    status_code=429,
    content={"detail": "Rate limit exceeded. Maximum requests per minute exceeded."}
))

# Request timing middleware for monitoring
import time

@app.middleware("http")
async def log_request_timing(request: Request, call_next):
    """Log request processing time for performance monitoring"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log slow requests (> 1 second)
    if process_time > 1.0:
        logger.warning(f"Slow request: {request.method} {request.url.path} - {process_time:.3f}s")
    
    return response

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Add all security headers
    headers = SecurityHeaders.get_headers()
    for key, value in headers.items():
        response.headers[key] = value
    
    return response

# Helper function to verify admin token
async def verify_admin(authorization: Optional[str] = None, admin_token: Optional[str] = Cookie(None)):
    """Verify admin authentication"""
    token = authorization.replace("Bearer ", "") if authorization else admin_token
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    email = verify_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    admin = db.get_admin_by_email(email)
    if not admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return email

# Health check endpoint for monitoring
@app.get("/health")
async def health_check():
    """Health check endpoint for Railway monitoring"""
    try:
        stats = db.get_lead_stats()
        return {
            "status": "healthy",
            "database": "connected",
            "leads": stats.get("total_leads", 0),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }, 500

# Helper function to verify API key for SDK endpoints
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key for SDK authentication"""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required. Include X-API-Key header.")
    
    # Hash the provided API key
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
    
    # Verify against database
    user_email = db.verify_api_key(key_hash)
    
    if not user_email:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return user_email

@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Professional landing page"""
    stats = db.get_lead_stats()
    return templates.TemplateResponse("landing.html", {
        "request": request,
        "stats": stats,
        "current_year": datetime.now().year
    })

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Admin login/setup page"""
    return templates.TemplateResponse("admin_login.html", {
        "request": request
    })

@app.post("/capture-lead")
@limiter.limit("5/minute")
async def capture_lead(
    background_tasks: BackgroundTasks,
    request: Request,
    email: str = Form(...)
):
    """Capture email lead and send welcome email with rate limiting and validation"""
    
    try:
        # Validate email format
        if not InputValidator.validate_email(email):
            return JSONResponse(
                status_code=400,
                content={'success': False, 'error': 'Invalid email address'}
            )
        # Get metadata
        client_ip = request.client.host
        user_agent = request.headers.get('user-agent', '')
        
        # Save lead to database
        lead_id = db.add_lead(
            email=email,
            source='landing_page',
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        # Send emails in background
        background_tasks.add_task(
            email_service.send_welcome_email,
            email
        )
        
        background_tasks.add_task(
            email_service.send_admin_notification,
            email,
            {
                'source': 'landing_page',
                'ip_address': client_ip,
                'user_agent': user_agent,
                'daily_count': db.get_lead_stats()['today_leads']
            }
        )
        
        # Log event
        db.log_email_event(email, 'welcome_sent')
        
        # Return success with redirect URL
        return JSONResponse({
            'success': True,
            'message': 'Check your email for the analysis tool!',
            'redirect': f'/analyzer?email={email}'
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'success': False, 'error': str(e)}
        )

@app.get("/csv-guide", response_class=HTMLResponse)
async def csv_guide_page(request: Request):
    """CSV upload guide with examples and template download"""
    return templates.TemplateResponse("csv-guide.html", {
        "request": request
    })

@app.get("/dev-docs", response_class=HTMLResponse)
async def dev_docs(request: Request):
    """Developer documentation for API and SDK integration"""
    return templates.TemplateResponse("dev_docs.html", {
        "request": request
    })

@app.get("/user/dashboard", response_class=HTMLResponse)

@app.get("/budgets", response_class=HTMLResponse)
async def budget_management_page(request: Request, admin_email: str = Depends(verify_admin)):
    """Budget management page for setting and tracking budgets"""
    try:
        # Get user's current budgets
        budgets = []  # TODO: Load from database
        forecasts = {}  # TODO: Load from database
        
        return templates.TemplateResponse("budget_management.html", {
            "request": request,
            "admin_email": admin_email,
            "budgets": budgets,
            "forecasts": forecasts
        })
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to load budgets: {str(e)}"})

async def user_dashboard(request: Request):
    """User-facing dashboard for SDK users to track their own usage (NOT admin stuff)"""
    return templates.TemplateResponse("user_dashboard.html", {
        "request": request
    })

@app.get("/api/csv-template")
async def get_csv_template():
    """Download CSV template for analysis"""
    csv_content = """model,prompt_tokens,completion_tokens,team
gpt-4,150,250,marketing
gpt-4,120,200,marketing
gpt-3.5-turbo,50,100,engineering
gpt-3.5-turbo,75,150,engineering
claude-3-opus,200,300,data_science
claude-3-sonnet,100,150,data_science
gemini-pro,80,120,marketing
azure-gpt-4-turbo,90,180,engineering
gpt-4,200,350,marketing
gpt-3.5-turbo,40,80,engineering
claude-3-haiku,30,60,data_science"""

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=substacker-template.csv"}
    )

@app.get("/analyzer", response_class=HTMLResponse)
async def analyzer_page(request: Request, email: Optional[str] = None):
    """The actual analyzer tool (after email capture)"""
    
    if email:
        # Log that user accessed the tool
        db.log_email_event(email, 'tool_accessed')
    
    return templates.TemplateResponse("analyzer.html", {
        "request": request,
        "email": email
    })

@app.post("/analyze")
@limiter.limit("10/minute")
async def analyze_usage(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    email: Optional[str] = Form(None)
):
    """Analyze OpenAI usage with file validation and rate limiting"""
    
    try:
        # Validate file before processing
        is_valid, error_msg = FileValidator.validate_upload(
            file.filename,
            file.size,
            file.content_type
        )
        
        if not is_valid:
            return JSONResponse(
                status_code=400,
                content={"error": error_msg}
            )
        
        contents = await file.read()
        
        # Additional security: limit content size in memory
        if len(contents) > SecurityConfig.MAX_FILE_SIZE:
            return JSONResponse(
                status_code=413,
                content={"error": "File content exceeds maximum size"}
            )
        
        # Parse file with error handling
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
            elif file.filename.endswith('.json'):
                data = json.loads(contents)
                df = pd.DataFrame(data)
            else:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid file format"}
                )
        except Exception as e:
            logger.error(f"File parsing error: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={"error": f"Failed to parse file: {str(e)}"}
            )
        
        # Validate dataframe
        is_valid, error_msg = FileValidator.validate_csv_content(len(df))
        if not is_valid:
            return JSONResponse(
                status_code=400,
                content={"error": error_msg}
            )
        
        # Run analysis
        results = analyzer.analyze_usage(df)
        
        # Save results if email provided
        if email:
            # Validate email
            if not InputValidator.validate_email(email):
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid email address"}
                )
            
            db.save_analysis_results(email, results)
            db.log_email_event(email, 'analysis_completed', {
                'waste_found': results['waste_identified'],
                'savings_percentage': results['savings_potential']
            })
            
            # Send results email in background
            background_tasks.add_task(
                email_service.send_results_email,
                email,
                results
            )
        
        return JSONResponse(content=results)
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Analysis failed: {str(e)}"}
        )

@app.post("/sample-analysis")
async def sample_analysis():
    """Run analysis on sample data for demo with complex and average examples"""
    
    # Create comprehensive sample data with realistic scenarios AND TEAM DATA
    sample_data = pd.DataFrame([
        # ===== MARKETING TEAM =====
        {'prompt': 'Classify sentiment: "I love this product"', 'model': 'gpt-3.5-turbo', 'prompt_tokens': 8, 'completion_tokens': 2, 'team': 'marketing'},
        {'prompt': 'Extract email: "Contact me at john@example.com"', 'model': 'gpt-3.5-turbo', 'prompt_tokens': 7, 'completion_tokens': 3, 'team': 'marketing'},
        {'prompt': 'Translate to Spanish: "Hello world"', 'model': 'gpt-3.5-turbo', 'prompt_tokens': 6, 'completion_tokens': 5, 'team': 'marketing'},
        {'prompt': 'Analyze market trends from Q1-Q4 2024 data and provide insights', 'model': 'gpt-4', 'prompt_tokens': 45, 'completion_tokens': 250, 'team': 'marketing'},
        {'prompt': 'Generate comprehensive business strategy for SaaS company expansion', 'model': 'gpt-4', 'prompt_tokens': 32, 'completion_tokens': 180, 'team': 'marketing'},
        {'prompt': 'What is machine learning?', 'model': 'gpt-4', 'prompt_tokens': 20, 'completion_tokens': 150, 'team': 'marketing'},
        {'prompt': 'What is machine learning?', 'model': 'gpt-4', 'prompt_tokens': 20, 'completion_tokens': 150, 'team': 'marketing'},
        {'prompt': 'What is machine learning?', 'model': 'gpt-4', 'prompt_tokens': 20, 'completion_tokens': 150, 'team': 'marketing'},
        
        # ===== ENGINEERING TEAM =====
        {'prompt': 'Extract the name from: John Smith', 'model': 'gpt-4', 'prompt_tokens': 15, 'completion_tokens': 5, 'team': 'engineering'},
        {'prompt': 'Is this positive? Great product!', 'model': 'gpt-4', 'prompt_tokens': 12, 'completion_tokens': 3, 'team': 'engineering'},
        {'prompt': 'Count words in text: "Hello world test"', 'model': 'gpt-4', 'prompt_tokens': 10, 'completion_tokens': 2, 'team': 'engineering'},
        {'prompt': 'Format date: 2024-01-15 to MM/DD/YYYY', 'model': 'gpt-4', 'prompt_tokens': 9, 'completion_tokens': 2, 'team': 'engineering'},
        {'prompt': 'Summarize article about AI trends', 'model': 'gpt-4', 'prompt_tokens': 28, 'completion_tokens': 120, 'team': 'engineering'},
        {'prompt': 'Debug Python code: def func(x): return x*2', 'model': 'gpt-4', 'prompt_tokens': 18, 'completion_tokens': 95, 'team': 'engineering'},
        
        # ===== DATA SCIENCE TEAM =====
        {'prompt': 'Hello', 'system_prompt': 'You are a helpful assistant. ' * 150, 'model': 'gpt-3.5-turbo', 'prompt_tokens': 750, 'completion_tokens': 50, 'team': 'data_science'},
        {'prompt': 'Hi', 'system_prompt': 'You are a helpful assistant. ' * 150, 'model': 'gpt-3.5-turbo', 'prompt_tokens': 750, 'completion_tokens': 45, 'team': 'data_science'},
        {'prompt': 'Generate JSON schema for user database', 'model': 'gpt-3.5-turbo', 'prompt_tokens': 22, 'completion_tokens': 85, 'team': 'data_science'},
        {'prompt': 'Explain quantum computing basics', 'model': 'gpt-3.5-turbo', 'prompt_tokens': 15, 'completion_tokens': 110, 'team': 'data_science'},
        
        # ===== REPEAT FOR SCALE =====
        {'prompt': 'What is machine learning?', 'model': 'gpt-4', 'prompt_tokens': 20, 'completion_tokens': 150, 'team': 'marketing'},
        {'prompt': 'What is machine learning?', 'model': 'gpt-4', 'prompt_tokens': 20, 'completion_tokens': 150, 'team': 'marketing'},
    ] * 12)  # Multiply to show monthly impact and scale
    
    analyzer = OpenAIWasteAnalyzer()
    results = analyzer.analyze_usage(sample_data)
    
    return JSONResponse(content=results)

@app.post("/admin/login")
@limiter.limit("5/minute")
async def admin_login(request: Request, email: str = Form(...), password: str = Form(...)):
    """Admin login endpoint with rate limiting"""
    
    try:
        admin = db.get_admin_by_email(email)
        
        if not admin or not verify_password(password, admin['password_hash']):
            return JSONResponse(
                status_code=401,
                content={"success": False, "error": "Invalid credentials"}
            )
        
        # Create JWT token
        access_token = create_access_token(data={"sub": email})
        
        response = JSONResponse({
            "success": True,
            "message": "Login successful",
            "redirect": "/admin/dashboard"
        })
        response.set_cookie(key="admin_token", value=access_token, httponly=True, max_age=1800)
        return response
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Login failed: {str(e)}"}
        )

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, admin_email: str = Depends(verify_admin)):
    """Admin dashboard with authentication"""
    
    try:
        stats = db.get_lead_stats()
        recent_leads = db.get_recent_leads(limit=50)
        api_keys = db.get_api_keys(admin_email)  # Get admin's API keys
        # Compute derived metrics safely to avoid division-by-zero in templates
        avg_savings = stats.get('average_savings_percentage', 0) or 0
        total_waste = stats.get('total_waste_found', 0) or 0

        if avg_savings and avg_savings != 0:
            total_cost_analyzed = (total_waste / avg_savings) * 100
        else:
            total_cost_analyzed = 0

        # Pass safe computed values into template context
        return templates.TemplateResponse("admin_dashboard.html", {
            "request": request,
            "stats": stats,
            "leads": recent_leads,
            "admin_email": admin_email,
            "total_cost_analyzed": total_cost_analyzed,
            "keys": api_keys
        })
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Dashboard error: {str(e)}"}
        )

@app.post("/admin/setup")
async def admin_setup(email: str = Form(...), password: str = Form(...)):
    """Initial admin setup (only works if no admin exists)"""
    
    try:
        # Check if any admin exists
        existing = db.get_admin_by_email(email)
        if existing:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Admin already exists"}
            )
        
        # Create admin
        password_hash = get_password_hash(password)
        success = db.create_admin(email, password_hash)
        
        if success:
            return JSONResponse({
                "success": True,
                "message": "Admin created. Please login."
            })
        else:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Admin creation failed"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Setup error: {str(e)}"}
        )

@app.get("/api/costs/by-team")
async def get_costs_by_team(email: Optional[str] = None):
    """Get cost breakdown by team for an analysis"""
    try:
        if not email:
            return JSONResponse(
                status_code=400,
                content={"error": "Email parameter required"}
            )
        
        # Get the analysis results from database
        results = db.get_analysis_results_by_email(email)
        
        if not results:
            return JSONResponse(
                status_code=404,
                content={"error": "No analysis found for this email"}
            )
        
        # Return team breakdown with total cost and percentages
        team_breakdown = {}
        total_cost = results.get('total_cost', 0)
        
        for team, cost in results.get('team_breakdown', {}).items():
            percentage = (cost / total_cost * 100) if total_cost > 0 else 0
            team_breakdown[team] = {
                'cost': round(cost, 2),
                'percentage': round(percentage, 1)
            }
        
        return JSONResponse({
            'success': True,
            'total_cost': round(total_cost, 2),
            'team_breakdown': team_breakdown,
            'timestamp': results.get('timestamp')
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get team costs: {str(e)}"}
        )

@app.get("/export/csv")
async def export_csv(email: Optional[str] = None, admin_email: str = Depends(verify_admin)):
    """Export analysis results as CSV"""
    
    try:
        # Get results from database
        if email:
            # Get specific lead's results
            lead = db.get_admin_by_email(email) if email else None
        
        # Create CSV in memory
        output = io.StringIO()
        output.write("Lead Email,Total Cost,Waste Amount,Savings %,Patterns,Timestamp\n")
        
        # This is a simplified example - in production you'd query the analysis_results table
        # and format it properly as CSV
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=analysis_export.csv"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Export failed: {str(e)}"}
        )

@app.get("/pixel.gif")
async def tracking_pixel(email: str):
    """Email open tracking pixel"""
    
    db.log_email_event(email, 'email_opened')
    
    # Return 1x1 transparent GIF
    gif_data = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
    return Response(content=gif_data, media_type="image/gif")

# ===== SDK INTEGRATION ENDPOINTS =====

@app.post("/api/generate-key")
async def generate_api_key(email: str = Form(...)):
    """Generate new API key for SDK integration"""
    import secrets
    import hashlib
    
    try:
        # Validate email format
        if not InputValidator.validate_email(email):
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Invalid email address"}
            )
        
        # Ensure user exists in leads table (required for foreign key constraint)
        # This will create the lead if it doesn't exist, or update if it does
        db.add_lead(
            email=email,
            source='sdk_signup',
            ip_address=None,
            user_agent='SDK Integration'
        )
        
        # Generate random API key
        random_part = secrets.token_urlsafe(32)
        api_key = f"sk_substacker_{random_part}"
        
        # Hash the key for storage
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_prefix = api_key[:20]  # Store prefix for display
        
        # Save to database
        success = db.create_api_key(email, key_prefix, key_hash)
        
        if success:
            # Log the event
            db.log_email_event(email, 'api_key_generated', {
                'key_prefix': key_prefix
            })
            
            return JSONResponse({
                "success": True,
                "api_key": api_key,  # Only returned once!
                "key_prefix": key_prefix
            })
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to create API key"}
            )
    except Exception as e:
        logger.error(f"API key generation error: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Key generation failed: {str(e)}"}
        )


@app.get("/admin/sdk-keys", response_class=HTMLResponse)
async def admin_sdk_keys(request: Request, admin_email: str = Depends(verify_admin)):
    """Admin UI to manage SDK API keys"""
    try:
        # List API keys for this admin (email)
        keys = db.get_api_keys(admin_email)
        return templates.TemplateResponse("admin_sdk_keys.html", {
            "request": request,
            "admin_email": admin_email,
            "keys": keys
        })
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to load SDK keys: {str(e)}"})


@app.post("/api/revoke-key")
async def revoke_key(key_prefix: str = Form(...), admin_email: str = Depends(verify_admin)):
    """Revoke an existing API key (admin only)"""
    try:
        success = db.revoke_api_key(admin_email, key_prefix)
        if success:
            return JSONResponse({"success": True, "message": "Key revoked"})
        else:
            return JSONResponse(status_code=400, content={"success": False, "error": "Failed to revoke key"})
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Revoke failed: {str(e)}"})

@app.post("/api/track")
@limiter.limit("1000/minute")
async def track_usage(request: Request, user_email: str = Depends(verify_api_key)):
    """Track real-time API usage from SDK with proper authentication"""
    
    try:
        # Get JSON payload from SDK
        data = await request.json()
        
        # Extract fields
        team = data.get('team')
        model = data.get('model')
        prompt_tokens = data.get('prompt_tokens', 0)
        completion_tokens = data.get('completion_tokens', 0)
        response_time = data.get('response_time', 0)
        provider = data.get('provider', 'openai')  # NEW: Support multi-provider
        
        # Validate required fields
        if not all([team, model]):
            return JSONResponse(
                status_code=400,
                content={"error": "Missing required fields: team, model"}
            )
        
        # Calculate cost using analyzer pricing (multi-provider support)
        analyzer_instance = OpenAIWasteAnalyzer()
        
        # Get pricing for the model
        pricing, is_known = analyzer_instance._get_model_pricing(model)
        
        # Warn if model is unknown
        warning = None
        if not is_known:
            warning = f"Unknown model '{model}'. Cost set to $0. Please update pricing data or contact support."
            logger.warning(f"SDK tracking unknown model: {model} for user {user_email}")
        
        # Calculate cost using the new method signature
        cost = analyzer_instance._calculate_row_cost(
            prompt_tokens, 
            completion_tokens, 
            pricing
        )
        
        # Convert Decimal to float for JSON
        cost = float(cost)
        
        # Log usage to database
        db.log_usage(
            user_email=user_email,
            team=team,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=cost,
            response_time=response_time
        )
        
        # Build response with unknown model warning
        response_data = {
            "status": "tracked",
            "cost": round(cost, 4),
            "provider": analyzer_instance._detect_provider(model).value,
            "model_recognized": is_known
        }
        
        # Add warning if model is unknown
        if warning:
            response_data["warning"] = warning
        
        return JSONResponse(response_data)
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Tracking failed: {str(e)}"}
        )

@app.get("/api/dashboard/realtime")
async def realtime_dashboard(user_email: str = Depends(verify_api_key)):
    """Get real-time dashboard data with API key authentication"""
    try:
        # Get team costs
        team_breakdown = db.get_realtime_team_costs(user_email, days=30)
        
        # Get recent activity
        recent_usage = db.get_recent_usage(user_email, limit=20)
        
        # Calculate totals
        total_cost = sum(team_breakdown.values())
        today_cost = sum(log['cost'] for log in recent_usage 
                        if log['timestamp'].startswith(datetime.now().strftime('%Y-%m-%d')))
        
        return JSONResponse({
            "total_cost": round(total_cost, 2),
            "today_cost": round(today_cost, 2),
            "team_breakdown": team_breakdown,
            "recent_activity": recent_usage,
            "last_updated": datetime.now().isoformat()
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Dashboard fetch failed: {str(e)}"}
        )


# ===== PHASE 3: REAL-TIME ANALYTICS =====

@app.get("/realtime", response_class=HTMLResponse)
async def realtime_dashboard(request: Request):
    """Real-time cost tracking dashboard with WebSocket"""
    return templates.TemplateResponse("realtime.html", {"request": request})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    
    Client connects and receives:
    - Cost updates
    - New leads
    - Analysis completions
    - Anomaly alerts
    """
    await websocket.accept()
    
    # Get user email from query params (optional)
    user_email = websocket.query_params.get("email", "guest")
    
    # Register connection
    connection_id = await ws_manager.connect(websocket, user_email)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Handle client commands
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
                
                elif message.get("type") == "subscribe":
                    # Client can explicitly subscribe to events
                    logger.info(f"Client {connection_id} subscribed to events")
                
                elif message.get("type") == "unsubscribe":
                    # Client can unsubscribe
                    logger.info(f"Client {connection_id} unsubscribed")
                    
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
    
    except WebSocketDisconnect:
        await ws_manager.disconnect(connection_id)
        logger.info(f"Client {connection_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}")
        await ws_manager.disconnect(connection_id)


@app.get("/ws/stats")
async def websocket_stats():
    """Get WebSocket connection statistics"""
    return ws_manager.get_connection_stats()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
