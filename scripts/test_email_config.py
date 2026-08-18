#!/usr/bin/env python3
"""
Diagnostic script to test SMTP configuration
Run locally to verify all email settings are correct
"""

import os
import smtplib
import socket

from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("SUBSTACKER EMAIL CONFIGURATION DIAGNOSTIC")
print("=" * 60)
print()

# Check all SMTP variables
variables = {
    'SMTP_HOST': os.getenv('SMTP_HOST'),
    'SMTP_PORT': os.getenv('SMTP_PORT'),
    'SMTP_USER': os.getenv('SMTP_USER'),
    'SMTP_PASS': os.getenv('SMTP_PASS'),
    'FROM_EMAIL': os.getenv('FROM_EMAIL'),
    'FROM_NAME': os.getenv('FROM_NAME'),
    'ADMIN_EMAIL': os.getenv('ADMIN_EMAIL'),
    'BASE_URL': os.getenv('BASE_URL'),
}

print("📋 ENVIRONMENT VARIABLES:")
print("-" * 60)

config_valid = True
for key, value in variables.items():
    if value:
        # Mask sensitive values
        if 'PASS' in key or 'ADMIN_EMAIL' in key:
            display = f"{'*' * len(str(value))}"
        else:
            display = value
        print(f"✅ {key:20} = {display}")
    else:
        if key in ['SMTP_USER', 'SMTP_PASS', 'SMTP_HOST']:
            print(f"❌ {key:20} = NOT SET (REQUIRED)")
            config_valid = False
        else:
            print(f"⚠️  {key:20} = NOT SET (optional)")

print()
print("📋 DEFAULTS USED IF NOT SET:")
print("-" * 60)
print("SMTP_HOST defaults to:  smtp.gmail.com")
print("SMTP_PORT defaults to:  587")
print("FROM_NAME defaults to:  Substacker")
print("FROM_EMAIL defaults to: SMTP_USER value")

print()
print("🔍 VALIDATION:")
print("-" * 60)

# Check critical variables
smtp_user = os.getenv('SMTP_USER')
smtp_pass = os.getenv('SMTP_PASS')
smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
smtp_port = os.getenv('SMTP_PORT', '587')

if not smtp_user:
    print("❌ ERROR: SMTP_USER not set!")
    print("   Email sending will FAIL")
else:
    print(f"✅ SMTP_USER is set: {smtp_user[:10]}...")

if not smtp_pass:
    print("❌ ERROR: SMTP_PASS not set!")
    print("   Email sending will FAIL")
else:
    print(f"✅ SMTP_PASS is set (length: {len(smtp_pass)} chars)")

if smtp_host and smtp_port:
    print(f"✅ SMTP Server: {smtp_host}:{smtp_port}")
else:
    print("❌ SMTP Server config missing!")

print()
print("🧪 SMTP CONNECTION TEST:")
print("-" * 60)

if smtp_user and smtp_pass:
    # Test 1: DNS Resolution
    try:
        print(f"[1/4] Resolving {smtp_host}...")
        ip_address = socket.gethostbyname(smtp_host)
        print(f"✅ Resolved to: {ip_address}")
    except socket.gaierror as e:
        print(f"❌ DNS resolution failed: {e}")
        print(f"   Cannot find {smtp_host}")
        smtp_host = None
    
    # Test 2: Port connectivity
    if smtp_host:
        try:
            print(f"[2/4] Testing port {smtp_port} connectivity...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((smtp_host, int(smtp_port)))
            sock.close()
            
            if result == 0:
                print(f"✅ Port {smtp_port} is open")
            else:
                print(f"❌ Port {smtp_port} is blocked or unreachable")
                print("   This is why emails are failing!")
                print("   🔧 FIX: Switch to Gmail SMTP (smtp.gmail.com)")
        except TimeoutError:
            print(f"❌ Connection timeout to port {smtp_port}")
            print("   🚨 RAILWAY IS BLOCKING THIS PORT")
            print("   🔧 FIX: Use smtp.gmail.com instead")
        except Exception as e:
            print(f"❌ Port test failed: {e}")
    
    # Test 3: SMTP Connection
    if smtp_host:
        try:
            print("[3/4] Connecting to SMTP server...")
            with smtplib.SMTP(smtp_host, int(smtp_port), timeout=15) as server:
                print("✅ Connected!")
                
                print("[4/4] Starting TLS encryption...")
                server.starttls()
                print("✅ TLS started!")
                
                print(f"[5/5] Authenticating as {smtp_user}...")
                server.login(smtp_user, smtp_pass)
                print("✅ Login successful!")
                
            print()
            print("🎉 ALL TESTS PASSED - Email should work!")
            print()
            
        except smtplib.SMTPAuthenticationError as e:
            print(f"❌ Authentication failed: {e}")
            print("   🔧 FIX: Check SMTP_USER and SMTP_PASS credentials")
            if 'gmail' in smtp_host.lower():
                print("   📧 Gmail: Use app-specific password from myaccount.google.com/apppasswords")
        except smtplib.SMTPException as e:
            print(f"❌ SMTP error: {e}")
        except TimeoutError as e:
            print(f"❌ Connection timeout: {e}")
            print(f"   🚨 {smtp_host}:{smtp_port} is not reachable")
            print("   🔧 CRITICAL: Railway is blocking your SMTP server")
            print()
            print("   ⚡ IMMEDIATE SOLUTION:")
            print("   Update Railway variables:")
            print("   SMTP_HOST=smtp.gmail.com")
            print("   SMTP_PORT=587")
            print("   SMTP_USER=your-email@example.com")
            print("   SMTP_PASS=your-app-password")
        except Exception as e:
            print(f"❌ Connection error: {type(e).__name__}: {e}")
            print("   Check SMTP_HOST and SMTP_PORT")
else:
    print("⚠️  Skipping connection test - credentials not set")

print()
print("=" * 60)
print("💡 HOW TO FIX EMAIL ISSUES:")
print("=" * 60)
print()
print("1. For Gmail:")
print("   - Create app-specific password at: myaccount.google.com/apppasswords")
print("   - Set SMTP_USER to your Gmail address")
print("   - Set SMTP_PASS to the app-specific password")
print("   - SMTP_HOST: smtp.gmail.com (default)")
print("   - SMTP_PORT: 587 (default)")
print()
print("2. For custom SMTP:")
print("   - Get credentials from your email provider")
print("   - Set all 4 variables: HOST, PORT, USER, PASS")
print("   - Verify TLS/SSL support")
print()
print("3. In Railway:")
print("   - Go to project Settings → Variables")
print("   - Add: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS")
print("   - Redeploy after adding")
print()
print("4. Locally in .env:")
print("   SMTP_HOST=smtp.gmail.com")
print("   SMTP_PORT=587")
print("   SMTP_USER=your-email@gmail.com")
print("   SMTP_PASS=your-app-password")
print()
