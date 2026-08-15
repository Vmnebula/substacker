# Substacker - Complete User Flow & Feature Mapping

**Last Updated:** November 1, 2025  
**Status:** Complete User Experience Design

---

## User Journey Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      LANDING PAGE                                │
│    (Features: Team attribution, multi-provider, 4 providers)    │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   EMAIL CAPTURE & LOGIN                          │
│         (Features: Email validation, lead tracking)             │
└────────────┬────────────────────────────────────────────────────┘
             │
             ├─────────────────────────┬──────────────────────┐
             │                         │                      │
             ▼                         ▼                      ▼
    ┌──────────────────┐   ┌──────────────────┐   ┌─────────────────┐
    │  ANALYZER PAGE   │   │  SDK SETUP       │   │  DEMO MODE      │
    │  (CSV Upload)    │   │  (Real-time)     │   │  (Sample data)  │
    └────────┬─────────┘   └────────┬─────────┘   └────────┬────────┘
             │                      │                      │
             └──────────┬───────────┴──────────┬───────────┘
                        │                      │
                        ▼                      ▼
           ┌──────────────────────────────────────────────┐
           │    ANALYSIS RESULTS PAGE                     │
           │  • Team breakdown (pie chart)                │
           │  • Cost by provider                          │
           │  • Waste patterns & recommendations          │
           │  • Download results as PDF/CSV               │
           └────────┬───────────────────────────────────┘
                    │
                    ▼
           ┌──────────────────────────────────────────────┐
           │    USER DASHBOARD (SDK Users)                │
           │  • Real-time cost tracking                   │
           │  • Team breakdown visualization              │
           │  • Budget status & alerts                    │
           │  • Anomaly detection alerts                  │
           │  • Cost forecasting & trends                 │
           │  • Historical data & reports                 │
           └────────┬───────────────────────────────────┘
                    │
                    ├─────────────────┬──────────────────┐
                    │                 │                  │
                    ▼                 ▼                  ▼
           ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
           │ BUDGET PAGE  │  │ ALERTS PAGE  │  │ REPORTS PAGE │
           │ • Set limits │  │ • Real-time  │  │ • Historical │
           │ • Monitor    │  │ • Anomalies  │  │ • Trends     │
           │ • Forecast   │  │ • Cost spikes│  │ • Forecasts  │
           └──────────────┘  └──────────────┘  └──────────────┘
```

---

## PAGE-BY-PAGE FEATURE MAPPING

### 1. LANDING PAGE
**File:** `templates/landing.html`

**Current Features:**
- Hero section with value proposition
- Social proof (teams analyzed, providers, models)
- Email capture form
- How it works section
- Why it matters section
- FAQ section

**UPDATED FEATURES (NEED TO ADD):**
- Multi-provider indicator (4 providers supported)
- Budget features highlight
- Anomaly detection features
- Real-time dashboard mention
- Comparison with competitors
- Customer testimonials


---

### 2. ANALYZER PAGE
**File:** `templates/analyzer.html`

**Current Features:**
- CSV upload interface
- Sample data demo option
- SDK setup wizard
- Method selection (Upload/SDK/Demo)
- Step-by-step SDK instructions

**UPDATED FEATURES (NEED TO ADD):**
- Multi-provider model selection UI
- Budget setup during analysis
- Anomaly detection configuration
- Real-time tracking setup
- Provider comparison preview
- Cost breakdown visualization enhancements


---

### 3. RESULTS PAGE (After Analysis)
**File:** Currently in JavaScript, needs dedicated HTML template

**Current Features:**
- Team breakdown pie chart
- Cost table by team
- Waste patterns & recommendations
- Download results

**UPDATED FEATURES (NEED TO ADD):**
- Provider breakdown (multiple providers shown)
- Budget recommendations based on results
- Anomaly detection summary
- Cost forecasting for next month
- Setup budget alerts from results
- Real-time tracking activation


---

### 4. USER DASHBOARD (SDK Users)
**File:** `templates/user_dashboard.html`

**Current Features:**
- API key display
- Basic metrics (placeholder)
- Team breakdown table
- Recent activity table

**CRITICAL MISSING FEATURES:**
- **REAL-TIME COST TRACKING** - Show live updates
- **BUDGET STATUS DISPLAY** - Show budget usage %
- **BUDGET ALERTS** - Show active alerts
- **ANOMALY ALERTS** - Show detected anomalies
- **COST CHARTS** - Daily/weekly trends
- **PROVIDER BREAKDOWN** - Show costs by provider
- **FORECAST DISPLAY** - Show projected costs
- **ACTION BUTTONS** - Set budgets, manage alerts
- **WEBHOOK/INTEGRATION STATUS** - Show connection health


---

### 5. REAL-TIME DASHBOARD
**File:** `templates/realtime.html`

**Current Features:**
- WebSocket connection status
- Metric cards (cost, requests, etc.)
- Update feed
- Live refresh

**MISSING FEATURES:**
- **BUDGET METER** - Visual progress bar
- **ANOMALY ALERTS SECTION** - Real-time alerts
- **COST TRENDS CHART** - Hourly/daily trends
- **TEAM BREAKDOWN CHART** - Live pie chart
- **PROVIDER BREAKDOWN** - Multiple provider view
- **ALERT NOTIFICATIONS** - Pop-up alerts
- **FORECAST PANEL** - Projected costs
- **DRILL-DOWN ABILITY** - Click for details


---

### 6. BUDGET MANAGEMENT PAGE (NEW)
**File:** `templates/budget_management.html` - NEEDS TO BE CREATED

**REQUIRED FEATURES:**
- List all budgets (monthly/daily/hourly/project)
- Create new budget form
- Edit existing budget
- Delete budget
- Budget status visualization (progress bars)
- Forecast vs budget comparison
- Alert threshold settings
- Historical budget tracking
- Team-level budget assignment


---

### 7. ALERTS & ANOMALIES PAGE (NEW)
**File:** `templates/alerts_page.html` - NEEDS TO BE CREATED

**REQUIRED FEATURES:**
- Active alerts list
- Alert types (budget, anomaly, trend)
- Alert history
- Acknowledge/dismiss alerts
- Configure alert thresholds
- Set notification preferences (email/slack/webhook)
- Anomaly details & root cause
- Recommendations based on anomalies
- Export alert history


---

### 8. REPORTS & ANALYTICS PAGE (NEW)
**File:** `templates/reports_page.html` - NEEDS TO BE CREATED

**REQUIRED FEATURES:**
- Daily/weekly/monthly cost reports
- Team spending trends
- Provider usage trends
- Waste identification & tracking
- Cost forecast with confidence intervals
- Year-over-year comparison
- Savings achieved tracking
- Export to PDF/Excel
- Custom date range selection


---

## FEATURE CHECKLIST BY PAGE

### Landing Page
```
MESSAGING & POSITIONING
  [DONE] Team cost attribution (existing value prop)
  [TODO] Multi-provider support (new)
  [TODO] Budget enforcement (new)
  [TODO] Anomaly detection (new)
  [TODO] Real-time tracking (new)

SOCIAL PROOF
  [DONE] Teams analyzed count
  [TODO] Budget alerts sent count (new)
  [TODO] Anomalies detected count (new)
  [TODO] Cost saved by customers (new)

FEATURES SECTION
  [DONE] Team breakdown
  [TODO] Multi-provider analysis
  [TODO] Budget management
  [TODO] Anomaly alerts
  [TODO] Real-time dashboard
```

### Analyzer Page
```
ANALYSIS OPTIONS
  [DONE] CSV upload
  [DONE] Sample demo
  [DONE] SDK setup
  [TODO] Real-time SDK tracking visualization

PRE-ANALYSIS SETUP
  [TODO] Budget configuration
  [TODO] Alert threshold setup
  [TODO] Provider selection
  [TODO] Team mapping preferences

RESULTS DISPLAY
  [DONE] Team breakdown chart
  [TODO] Provider breakdown chart
  [TODO] Budget recommendations
  [TODO] Anomaly summary
  [TODO] Cost forecast
  [TODO] Quick action buttons (set budget, enable alerts)
```

### User Dashboard (Most Critical)
```
OVERVIEW SECTION
  [DONE] API key display
  [DONE] Basic metrics placeholder
  [TODO] Real-time cost ticker
  [TODO] Budget status card
  [TODO] Anomaly alerts summary

COST TRACKING
  [TODO] Current month total
  [TODO] Today's spending
  [TODO] Trend vs yesterday
  [TODO] Forecast for month end

BUDGET STATUS
  [TODO] Budget limit display
  [TODO] Current usage %
  [TODO] Progress bar visualization
  [TODO] Days remaining
  [TODO] Pace indicator (on track/behind)

ANOMALIES & ALERTS
  [TODO] Recent anomalies list
  [TODO] Active alert count
  [TODO] Anomaly severity indicators
  [TODO] Quick dismiss buttons

CHARTS & VISUALIZATION
  [TODO] Daily cost trend chart
  [TODO] Team breakdown pie chart
  [TODO] Provider breakdown chart
  [TODO] Hourly cost breakdown

TEAM BREAKDOWN
  [DONE] Team list table
  [TODO] Cost per team chart
  [TODO] Team percentages
  [TODO] Team-level drill down

ACTIONS & CONTROLS
  [TODO] Set budget button
  [TODO] Configure alerts button
  [TODO] View detailed report button
  [TODO] Export data button

CONNECTION STATUS
  [TODO] SDK connection health
  [TODO] Last update timestamp
  [TODO] Data sync status
  [TODO] Webhook delivery status
```

### Real-Time Dashboard
```
OVERVIEW METRICS
  [DONE] Total cost (partial)
  [DONE] Request count
  [TODO] Budget utilization %
  [TODO] Anomalies detected
  [TODO] Alerts active

LIVE TRACKING
  [DONE] Update feed
  [TODO] Budget breach warning
  [TODO] Anomaly spike alert
  [TODO] Cost surge notification

VISUALIZATIONS
  [TODO] Real-time cost chart
  [TODO] Team breakdown pie
  [TODO] Provider breakdown pie
  [TODO] Trend indicators
  [TODO] Budget progress bar

ALERTS PANEL
  [TODO] Active alerts section
  [TODO] Alert notification toast
  [TODO] Anomaly details modal
  [TODO] Quick action buttons

FORECAST PANEL
  [TODO] Projected month end cost
  [TODO] Trend line chart
  [TODO] Budget impact indicator
```

---

## CRITICAL GAPS (PRIORITY ORDER)

### PRIORITY 1 (Must Have - Block Production)
1. **User Dashboard - Budget Status Card**
   - Show current budget vs usage
   - Visual progress bar
   - Alert indicator

2. **User Dashboard - Anomaly Alerts**
   - Display recent anomalies
   - Show severity level
   - Link to details

3. **User Dashboard - Cost Trend Chart**
   - Daily/hourly cost visualization
   - Trend indicator
   - Forecast line

### PRIORITY 2 (Should Have - Before Beta)
4. **Budget Management Page**
   - Create/edit/delete budgets
   - Visual status indicators
   - Forecast display

5. **Alerts & Anomalies Page**
   - Alert history
   - Configure thresholds
   - Webhook integration

6. **Reports & Analytics Page**
   - Historical trends
   - Export functionality
   - Forecasting visualization

### PRIORITY 3 (Nice to Have - Future)
7. **Landing Page Updates**
   - Feature highlights refresh
   - New messaging for features

8. **Real-Time Dashboard Enhancements**
   - Anomaly notification toast
   - Budget breach warnings

---

