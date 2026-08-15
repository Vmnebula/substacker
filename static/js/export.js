/**
 * Data Export Utilities
 * Handles CSV, JSON, and other export formats
 */

class DataExporter {
    /**
     * Export data as CSV
     */
    static exportToCSV(data, filename = 'export.csv') {
        const headers = Object.keys(data[0] || {});
        const rows = data.map(item =>
            headers.map(header => {
                const value = item[header];
                const quoted = typeof value === 'string' && value.includes(',') 
                    ? `"${value.replace(/"/g, '""')}"` 
                    : value;
                return quoted;
            }).join(',')
        );

        const csv = [headers.join(','), ...rows].join('\n');
        this.downloadFile(csv, filename, 'text/csv');
    }

    /**
     * Export data as JSON
     */
    static exportToJSON(data, filename = 'export.json') {
        const json = JSON.stringify(data, null, 2);
        this.downloadFile(json, filename, 'application/json');
    }

    /**
     * Export data as JSONL (JSON Lines)
     */
    static exportToJSONL(data, filename = 'export.jsonl') {
        const jsonl = data.map(item => JSON.stringify(item)).join('\n');
        this.downloadFile(jsonl, filename, 'application/jsonl');
    }

    /**
     * Export costs by team as CSV
     */
    static exportTeamCosts(teamCosts, filename = 'team-costs.csv') {
        const data = Object.entries(teamCosts).map(([team, cost]) => ({
            Team: team,
            Cost: cost,
            Percentage: ((cost / Object.values(teamCosts).reduce((a, b) => a + b, 0)) * 100).toFixed(2) + '%'
        }));
        this.exportToCSV(data, filename);
    }

    /**
     * Export activity log
     */
    static exportActivityLog(activities, filename = 'activity-log.csv') {
        const data = activities.map(activity => ({
            Timestamp: new Date(activity.timestamp).toLocaleString(),
            Model: activity.model,
            Team: activity.team,
            CostCents: activity.cost_cents,
            Cost: '$' + (activity.cost_cents / 100).toFixed(4),
            PromptTokens: activity.prompt_tokens,
            CompletionTokens: activity.completion_tokens,
            TotalTokens: activity.prompt_tokens + activity.completion_tokens,
            Status: activity.status,
            ResponseTime: activity.response_time + 's'
        }));
        this.exportToCSV(data, filename);
    }

    /**
     * Export budget summary
     */
    static exportBudgetSummary(budgets, filename = 'budget-summary.json') {
        const summary = {
            exportDate: new Date().toISOString(),
            budgets: budgets.map(budget => ({
                name: budget.name,
                team: budget.team,
                limitCents: budget.limit_cents,
                limit: '$' + (budget.limit_cents / 100).toFixed(2),
                spentCents: budget.spent_cents,
                spent: '$' + (budget.spent_cents / 100).toFixed(2),
                remainingCents: budget.limit_cents - budget.spent_cents,
                remaining: '$' + ((budget.limit_cents - budget.spent_cents) / 100).toFixed(2),
                percentageUsed: ((budget.spent_cents / budget.limit_cents) * 100).toFixed(2) + '%',
                status: budget.spent_cents > budget.limit_cents ? 'EXCEEDED' : 
                        budget.spent_cents > (budget.limit_cents * 0.8) ? 'WARNING' : 'OK'
            }))
        };
        this.downloadFile(JSON.stringify(summary, null, 2), filename, 'application/json');
    }

    /**
     * Generate cost report (HTML)
     */
    static generateHTMLReport(data, teamCosts, totals) {
        const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Substacker Cost Report</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }
        .container { max-width: 1000px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; }
        h1 { margin-bottom: 10px; color: #667eea; }
        .date { color: #999; margin-bottom: 30px; }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }
        .summary-card {
            background: #f9f9f9;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .summary-label { font-size: 0.9em; color: #999; margin-bottom: 5px; }
        .summary-value { font-size: 1.8em; font-weight: bold; color: #333; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th {
            background: #f5f5f5;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #ddd;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #eee;
        }
        tr:hover { background: #f9f9f9; }
        .text-right { text-align: right; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #999; font-size: 0.9em; }
        @media print {
            body { background: white; padding: 0; }
            .container { box-shadow: none; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>💰 Substacker Cost Report</h1>
        <p class="date">Generated: ${new Date().toLocaleString()}</p>

        <div class="summary-grid">
            <div class="summary-card">
                <div class="summary-label">Total Cost (30 days)</div>
                <div class="summary-value">$${totals.total.toFixed(2)}</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Teams Tracked</div>
                <div class="summary-value">${Object.keys(teamCosts).length}</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">API Calls</div>
                <div class="summary-value">${totals.calls.toLocaleString()}</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Avg Cost/Call</div>
                <div class="summary-value">$${(totals.total / totals.calls).toFixed(4)}</div>
            </div>
        </div>

        <h2 style="margin-top: 30px; margin-bottom: 15px;">Cost by Team</h2>
        <table>
            <thead>
                <tr>
                    <th>Team</th>
                    <th class="text-right">Cost</th>
                    <th class="text-right">% of Total</th>
                </tr>
            </thead>
            <tbody>
                ${Object.entries(teamCosts)
                    .sort((a, b) => b[1] - a[1])
                    .map(([team, cost]) => `
                    <tr>
                        <td>${team}</td>
                        <td class="text-right"><strong>$${cost.toFixed(2)}</strong></td>
                        <td class="text-right">${((cost / totals.total) * 100).toFixed(1)}%</td>
                    </tr>
                    `).join('')}
            </tbody>
        </table>

        <div class="footer">
            <p>Generated by Substacker | <a href="https://substacker.nayacloud.com">substacker.nayacloud.com</a></p>
        </div>
    </div>
</body>
</html>
        `;
        this.downloadFile(html, 'cost-report.html', 'text/html');
    }

    /**
     * Download file utility
     */
    static downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    /**
     * Copy to clipboard
     */
    static copyToClipboard(text) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(() => {
                showNotification('Copied to clipboard!', 'success');
            }).catch(() => {
                this.fallbackCopy(text);
            });
        } else {
            this.fallbackCopy(text);
        }
    }

    /**
     * Fallback copy to clipboard
     */
    static fallbackCopy(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            showNotification('Copied to clipboard!', 'success');
        } catch (err) {
            showNotification('Failed to copy', 'error');
        }
        document.body.removeChild(textArea);
    }

    /**
     * Print data
     */
    static print(html) {
        const printWindow = window.open('', '', 'height=400,width=600');
        printWindow.document.write(html);
        printWindow.document.close();
        printWindow.print();
    }
}

// Export globally
window.DataExporter = DataExporter;
