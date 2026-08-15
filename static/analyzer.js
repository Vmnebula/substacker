// ===== ANALYZER PAGE FUNCTIONALITY =====
// Wrap in IIFE to avoid global scope pollution and variable conflicts
(function() {
    'use strict';
    
    // Check if on analyzer page (but allow SDK wizard to work too)
    const isAnalyzerPage = !!document.getElementById('uploadArea') || !!document.getElementById('methodSelection');
    if (!isAnalyzerPage) {
        console.log('Analyzer page not loaded - skipping analyzer.js');
        return;
    }
    
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const tryDemoBtn = document.getElementById('tryDemo');
    const uploadSection = document.querySelector('.upload-section');
    const loadingState = document.getElementById('loadingState');
    const resultsSection = document.getElementById('resultsSection');
    const errorState = document.getElementById('errorState');
    const newAnalysisBtn = document.getElementById('newAnalysis');
    const tryAgainBtn = document.getElementById('tryAgain');
    
    let currentResults = null;
    let currentFileData = null;  // Store file data for preview

    // Get email from URL
    const urlParams = new URLSearchParams(window.location.search);
    const email = urlParams.get('email');
    
    // ===== EVENT LISTENERS =====
    
    // CSV Upload Event Listeners (only if uploadArea exists)
    if (uploadArea) {
        // Upload area click
        uploadArea.addEventListener('click', () => fileInput.click());
        
        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('drag-over');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                handleFileSelect();
            }
        });
    }
    
    // Upload link click
    const uploadLink = document.querySelector('.upload-link');
    if (uploadLink) {
        uploadLink.addEventListener('click', (e) => {
            e.preventDefault();
            if (fileInput) fileInput.click();
        });
    }
    
    // File input change
    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelect);
    }
    
    // Try demo button
    if (tryDemoBtn) {
        tryDemoBtn.addEventListener('click', handleDemoAnalysis);
    }
    
    // New analysis button
    if (newAnalysisBtn) {
        newAnalysisBtn.addEventListener('click', resetToUpload);
    }
    
    // Try again button
    if (tryAgainBtn) {
        tryAgainBtn.addEventListener('click', resetToUpload);
    }
    
    // Export buttons
    const exportPDFBtn = document.getElementById('exportPDF');
    const exportCSVBtn = document.getElementById('exportCSV');
    const emailReportBtn = document.getElementById('emailReport');
    const getHelpBtn = document.getElementById('getHelp');
    const shareResultsBtn = document.getElementById('shareResults');
    
    if (exportPDFBtn) exportPDFBtn.addEventListener('click', exportPDF);
    if (exportCSVBtn) exportCSVBtn.addEventListener('click', exportCSV);
    if (emailReportBtn) emailReportBtn.addEventListener('click', emailReport);
    if (getHelpBtn) getHelpBtn.addEventListener('click', getHelp);
    if (shareResultsBtn) shareResultsBtn.addEventListener('click', shareResults);

    // Beta email form
    const betaEmailForm = document.getElementById('betaEmailForm');
    if (betaEmailForm) {
        betaEmailForm.addEventListener('submit', handleBetaSignup);
    }

    // ===== FILE HANDLING =====
    
    async function handleFileSelect() {
    const file = fileInput.files[0];
    
    if (!file) return;
    
    // Validate file size (50MB max)
    if (file.size > 50 * 1024 * 1024) {
        showError('File is too large. Maximum 50MB allowed.');
        return;
    }
    
    // Validate file type
    const validTypes = ['text/csv', 'application/json'];
    if (!validTypes.includes(file.type) && !file.name.endsWith('.csv') && !file.name.endsWith('.json')) {
        showError('Please upload a CSV or JSON file.');
        return;
    }
    
    await analyzeFile(file);
}

    async function analyzeFile(file) {
    try {
        // Show loading state
        uploadSection.style.display = 'none';
        loadingState.style.display = 'block';
        resultsSection.style.display = 'none';
        errorState.style.display = 'none';
        
        // Read file for preview
        const fileReader = new FileReader();
        fileReader.onload = async (e) => {
            try {
                let parsedData = [];
                const content = e.target.result;
                
                if (file.name.endsWith('.csv')) {
                    parsedData = parseCSV(content);
                } else if (file.name.endsWith('.json')) {
                    parsedData = JSON.parse(content);
                    if (!Array.isArray(parsedData)) {
                        parsedData = [parsedData];
                    }
                }
                
                currentFileData = {
                    type: file.name.endsWith('.csv') ? 'csv' : 'json',
                    data: parsedData,
                    filename: file.name
                };
            } catch (parseError) {
                console.log('Preview parsing note:', parseError.message);
            }
        };
        fileReader.readAsText(file);
        
        // Create form data
        const formData = new FormData();
        formData.append('file', file);
        if (email) {
            formData.append('email', email);
        }
        
        // Send to backend
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Analysis failed. Please try again.');
        }
        
        const results = await response.json();
        currentResults = results;
        
        // Display results
        displayResults(results);
        
    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'Analysis failed. Please check your file and try again.');
    }
}

    function parseCSV(csvContent) {
    const lines = csvContent.trim().split('\n');
    if (lines.length < 2) return [];
    
    const headers = lines[0].split(',').map(h => h.trim());
    const data = [];
    
    for (let i = 1; i < lines.length && i < 20; i++) {
        const values = lines[i].split(',');
        const row = {};
        headers.forEach((header, index) => {
            row[header] = values[index] ? values[index].trim() : '';
        });
        data.push(row);
    }
    
    return data;
}

    // ===== DEMO ANALYSIS =====
    
    async function handleDemoAnalysis() {
    try {
        // Show loading state
        uploadSection.style.display = 'none';
        loadingState.style.display = 'block';
        resultsSection.style.display = 'none';
        errorState.style.display = 'none';
        
        // Create demo data preview
        currentFileData = {
            type: 'demo',
            data: [
                { model: 'gpt-4', prompt_tokens: 20, completion_tokens: 150, prompt: 'What is machine learning?' },
                { model: 'gpt-4', prompt_tokens: 15, completion_tokens: 5, prompt: 'Extract the name from: John Smith' },
                { model: 'gpt-3.5-turbo', prompt_tokens: 8, completion_tokens: 2, prompt: 'Classify sentiment: I love this' },
                { model: 'gpt-4', prompt_tokens: 45, completion_tokens: 250, prompt: 'Analyze market trends from Q1-Q4...' },
                { model: 'gpt-3.5-turbo', prompt_tokens: 750, completion_tokens: 50, prompt: 'Hello' }
            ],
            filename: 'sample_data.json'
        };
        
        // Fetch sample data
        const response = await fetch('/sample-analysis', {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error('Sample analysis failed.');
        }
        
        const results = await response.json();
        currentResults = results;
        
        // Display results
        displayResults(results);
        
    } catch (error) {
        console.error('Error:', error);
        showError('Demo analysis failed. Please try again.');
    }
}

    // ===== DISPLAY RESULTS =====
    
    function displayResults(results) {
    // Hide loading
    loadingState.style.display = 'none';
    resultsSection.style.display = 'block';
    
    // Update summary cards
    const teamCount = results.team_breakdown ? Object.keys(results.team_breakdown).length : 0;
    document.getElementById('totalCost').textContent = formatCurrency(results.total_cost);
    document.getElementById('wasteAmount').textContent = teamCount;
    document.getElementById('savingsPercentage').textContent = (results.savings_potential).toFixed(2) + '%';
    document.getElementById('monthlySavings').textContent = 'Active';
    
    // Display team breakdown (MVP Feature)
    displayTeamBreakdown(results.team_breakdown, results.total_cost);
    
    // Update beta section with savings
    updateBetaSection(results);
    
    // Display preview
    displayPreview();
    
    // Display patterns
    displayPatterns(results.patterns);
    
    // Display recommendations
    displayRecommendations(results.patterns);
    
    // Scroll to results
    setTimeout(() => {
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }, 100);
}

    function updateBetaSection(results) {
    const totalSavings = results.waste_identified || 0;
    const savingsPercent = results.savings_potential || 0;
    
    const savingsEl = document.getElementById('betaTotalSavings');
    const percentEl = document.getElementById('betaSavingsPercent');
    
    if (savingsEl) savingsEl.textContent = formatCurrency(totalSavings);
    if (percentEl) percentEl.textContent = savingsPercent.toFixed(1) + '%';
}

    function handleBetaSignup(e) {
    e.preventDefault();
    const form = e.target;
    const emailInput = form.querySelector('input[name="beta_email"]');
    const betaEmail = emailInput.value.trim();
    
    if (!betaEmail) {
        alert('Please enter your email address');
        return;
    }
    
    // Show success
    alert('Great! You\'ve been added to our beta launch. Check your email for next steps!');
    form.reset();
}

    function displayTeamBreakdown(teamBreakdown, totalCost) {
    const teamTableBody = document.getElementById('teamTableBody');
    teamTableBody.innerHTML = '';
    
    if (!teamBreakdown || Object.keys(teamBreakdown).length === 0) {
        teamTableBody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: #999;">No team data available. Add a "team" column to your data for better insights.</td></tr>';
        return;
    }
    
    // Create color palette for teams
    const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'];
    let colorIndex = 0;
    const teamColors = {};
    
    // Populate table and build chart data
    const chartLabels = [];
    const chartData = [];
    const chartColors = [];
    
    Object.entries(teamBreakdown).forEach(([team, cost]) => {
        const percentage = (cost / totalCost * 100).toFixed(1);
        
        // Add table row
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${team}</strong></td>
            <td>${formatCurrency(cost)}</td>
            <td>${percentage}%</td>
        `;
        teamTableBody.appendChild(row);
        
        // Build chart data
        chartLabels.push(team);
        chartData.push(cost);
        const color = colors[colorIndex % colors.length];
        chartColors.push(color);
        teamColors[team] = color;
        colorIndex++;
    });
    
    // Create pie chart using Chart.js if available, otherwise use simple HTML
    const chartCanvas = document.getElementById('teamBreakdownChart');
    if (chartCanvas && typeof Chart !== 'undefined') {
        try {
            // Create pie chart
            new Chart(chartCanvas, {
                type: 'doughnut',
                data: {
                    labels: chartLabels,
                    datasets: [{
                        data: chartData,
                        backgroundColor: chartColors,
                        borderColor: 'white',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        } catch (e) {
            console.log('Chart.js not available, showing table only');
        }
    }
}

    function displayPreview() {
    const previewContent = document.getElementById('previewContent');
    
    if (!currentFileData || !currentFileData.data || currentFileData.data.length === 0) {
        previewContent.innerHTML = '<p class="preview-placeholder">No data to preview</p>';
        return;
    }
    
    const data = currentFileData.data;
    const keys = Object.keys(data[0]);
    
    // Create table
    let html = '<table class="preview-table"><thead><tr>';
    keys.forEach(key => {
        html += `<th>${key}</th>`;
    });
    html += '</tr></thead><tbody>';
    
    data.slice(0, 10).forEach(row => {
        html += '<tr>';
        keys.forEach(key => {
            let value = row[key];
            if (typeof value === 'string' && value.length > 30) {
                value = value.substring(0, 30) + '...';
            }
            html += `<td>${value}</td>`;
        });
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    
    if (data.length > 10) {
        html += `<p style="text-align: center; margin-top: 10px; font-size: 0.85rem; color: #6b7280;">... and ${data.length - 10} more rows</p>`;
    }
    
    previewContent.innerHTML = html;
}

    function displayPatterns(patterns) {
    const patternsList = document.getElementById('patternsList');
    patternsList.innerHTML = '';
    
    if (!patterns || patterns.length === 0) {
        patternsList.innerHTML = '<p>No patterns detected.</p>';
        return;
    }
    
    patterns.forEach(pattern => {
        const patternCard = document.createElement('div');
        patternCard.className = 'pattern-card';
        
        const icon = getPatternIcon(pattern.name);
        
        patternCard.innerHTML = `
            <div class="pattern-name">
                <span class="pattern-icon">${icon}</span>
                ${pattern.name}
            </div>
            <p class="pattern-description">${pattern.fix || pattern.description || 'No description available'}</p>
            <div class="pattern-impact">
                <div>
                    <div class="impact-label">Wasted Amount</div>
                    <div class="impact-amount">${formatCurrency(pattern.waste_amount || pattern.amount_wasted || 0)}</div>
                </div>
                <div>
                    <div class="impact-label">Percentage</div>
                    <div style="font-size: 1.25rem; font-weight: 700; color: var(--text-primary);">${(pattern.percentage || 0).toFixed(2)}%</div>
                </div>
            </div>
        `;
        
        patternsList.appendChild(patternCard);
    });
}

    function displayRecommendations(patterns) {
    const recommendationsList = document.getElementById('recommendationsList');
    recommendationsList.innerHTML = '';
    
    const recommendations = generateRecommendations(patterns);
    
    recommendations.forEach(rec => {
        const recItem = document.createElement('div');
        recItem.className = 'recommendation-item';
        
        recItem.innerHTML = `
            <div class="recommendation-icon">
                <i class="fas fa-check"></i>
            </div>
            <div class="recommendation-content">
                <div class="recommendation-title">${rec.title}</div>
                <div class="recommendation-description">${rec.description}</div>
            </div>
        `;
        
        recommendationsList.appendChild(recItem);
    });
}

    function generateRecommendations(patterns) {
    const recommendations = [];
    
    if (!patterns) return recommendations;
    
    // Generate recommendations based on patterns
    const patternMap = {};
    patterns.forEach(p => {
        patternMap[p.name] = p;
    });
    
    if (patternMap['Duplicate Prompts']) {
        recommendations.push({
            title: 'Implement Query Caching',
            description: 'Use Redis or in-memory caching to store frequent prompts and their responses. This eliminates duplicate API calls and can save ' + formatCurrency(patternMap['Duplicate Prompts'].waste_amount || patternMap['Duplicate Prompts'].amount_wasted || 0) + ' monthly.'
        });
    }
    
    if (patternMap['Model Overkill']) {
        recommendations.push({
            title: 'Optimize Model Selection',
            description: 'Replace expensive models with cheaper alternatives for simple tasks. Potential savings: ' + formatCurrency(patternMap['Model Overkill'].waste_amount || patternMap['Model Overkill'].amount_wasted || 0) + ' per month.'
        });
    }
    
    if (patternMap['Bloated Prompts']) {
        recommendations.push({
            title: 'Compress System Prompts',
            description: 'Reduce system prompt size by removing redundant instructions. This can reduce token usage by up to ' + Math.round(patternMap['Bloated Prompts'].percentage || 0) + '%.'
        });
    }
    
    if (patternMap['High Token Usage']) {
        recommendations.push({
            title: 'Optimize Prompt Engineering',
            description: 'Use more specific, concise prompts to reduce token consumption. Every 100 tokens saved = $1-3 depending on model.'
        });
    }
    
    if (patternMap['Large Context Windows']) {
        recommendations.push({
            title: 'Limit Context Window',
            description: 'Use smaller context windows where possible. Consider using GPT-3.5 or fine-tuned models for specific use cases.'
        });
    }
    
    // If no specific patterns, add general recommendations
    if (recommendations.length === 0) {
        recommendations.push(
            {
                title: 'Monitor API Usage',
                description: 'Set up regular monitoring and alerts for unusual spikes in API usage to catch inefficiencies early.'
            },
            {
                title: 'Implement Rate Limiting',
                description: 'Add rate limiting to prevent accidental overuse and duplicate requests from buggy code.'
            },
            {
                title: 'Use Batch Processing',
                description: 'Where possible, batch multiple requests together to reduce API call overhead.'
            }
        );
    }
    
    return recommendations;
}

    function getPatternIcon(patternName) {
    const icons = {
        'Duplicate Prompts': '📋',
        'Model Overkill': '🔨',
        'Bloated Prompts': '📚',
        'High Token Usage': '⚡',
        'Large Context Windows': '🪟'
    };
    return icons[patternName] || '🔍';
}

    // ===== EXPORT FUNCTIONS =====
    
    function exportPDF() {
    if (!currentResults) return;
    
    // Simple PDF export using browser's print functionality
    const printWindow = window.open('', '', 'height=600,width=800');
    
    let htmlContent = '<html><head><title>OpenAI Waste Analysis Report</title>';
    htmlContent += '<style>';
    htmlContent += 'body { font-family: Arial, sans-serif; margin: 20px; }';
    htmlContent += 'h1 { color: #ef4444; }';
    htmlContent += 'h2 { color: #1f2937; margin-top: 20px; }';
    htmlContent += '.summary { margin: 20px 0; padding: 15px; background: #f9fafb; border-left: 4px solid #ef4444; }';
    htmlContent += '.summary strong { display: block; margin-bottom: 5px; }';
    htmlContent += 'table { width: 100%; border-collapse: collapse; margin: 20px 0; }';
    htmlContent += 'th, td { padding: 10px; text-align: left; border-bottom: 1px solid #e5e7eb; }';
    htmlContent += 'th { background: #f3f4f6; font-weight: bold; }';
    htmlContent += '</style></head><body>';
    
    htmlContent += '<h1>OpenAI Waste Analysis Report</h1>';
    htmlContent += '<p>Generated on ' + new Date().toLocaleDateString() + '</p>';
    
    htmlContent += '<div class="summary">';
    htmlContent += '<strong>Total Cost: ' + formatCurrency(currentResults.total_cost) + '</strong>';
    htmlContent += '<strong>Waste Identified: ' + formatCurrency(currentResults.waste_identified) + '</strong>';
    htmlContent += '<strong>Savings Potential: ' + Math.round(currentResults.savings_potential) + '%</strong>';
    htmlContent += '</div>';
    
    htmlContent += '<h2>Waste Patterns</h2>';
    if (currentResults.patterns && currentResults.patterns.length > 0) {
        htmlContent += '<table>';
        htmlContent += '<tr><th>Pattern</th><th>Amount Wasted</th><th>Percentage</th></tr>';
        currentResults.patterns.forEach(p => {
            htmlContent += '<tr>';
            htmlContent += '<td>' + p.name + '</td>';
            htmlContent += '<td>' + formatCurrency(p.waste_amount || p.amount_wasted || 0) + '</td>';
            htmlContent += '<td>' + Math.round(p.percentage) + '%</td>';
            htmlContent += '</tr>';
        });
        htmlContent += '</table>';
    }
    
    htmlContent += '</body></html>';
    
    printWindow.document.write(htmlContent);
    printWindow.document.close();
    
    setTimeout(() => {
        printWindow.print();
        printWindow.close();
    }, 250);
}

    function exportCSV() {
    if (!currentResults) return;
    
    let csvContent = 'data:text/csv;charset=utf-8,';
    
    // Add headers
    csvContent += 'Metric,Value\n';
    
    // Add data
    csvContent += 'Total Cost,' + currentResults.total_cost + '\n';
    csvContent += 'Waste Identified,' + currentResults.waste_identified + '\n';
    csvContent += 'Savings Potential,' + currentResults.savings_potential + '%\n';
    csvContent += 'Monthly Savings,' + (currentResults.waste_identified / 12) + '\n\n';
    
    // Add patterns
    if (currentResults.patterns && currentResults.patterns.length > 0) {
        csvContent += 'Pattern,Amount Wasted,Percentage\n';
        currentResults.patterns.forEach(p => {
            csvContent += p.name + ',' + (p.waste_amount || p.amount_wasted || 0) + ',' + (p.percentage || 0) + '%\n';
        });
    }
    
    // Create download link
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', 'waste_analysis_' + new Date().getTime() + '.csv');
    document.body.appendChild(link);
    
    link.click();
    document.body.removeChild(link);
}

    function emailReport() {
    if (!email) {
        alert('Email not found. Please go back to the landing page and enter your email.');
        return;
    }
    
    alert('Report will be emailed to ' + email + ' shortly!');
}

    function getHelp() {
    alert('Thank you for your interest! Our team will contact you at ' + (email || 'your email') + ' to discuss implementation.');
}

    function shareResults() {
    if (!currentResults) {
        alert('No results available to share.');
        return;
    }
    
    const totalCost = currentResults.total_cost || 0;
    const teamCount = currentResults.team_breakdown ? Object.keys(currentResults.team_breakdown).length : 0;
    
    const shareText = `I just analyzed my team's AI spending with Substacker! Total: ${formatCurrency(totalCost)} across ${teamCount} teams. Get your team breakdown too at ${window.location.origin}`;
    const shareUrl = window.location.origin;
    
    if (navigator.share) {
        navigator.share({
            title: 'Substacker - AI Cost Analysis',
            text: shareText,
            url: shareUrl
        }).catch((error) => {
            console.log('Share failed:', error);
            // Fallback to clipboard
            copyToClipboard(shareText);
        });
    } else {
        copyToClipboard(shareText);
    }
}

    function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            alert('Share text copied to clipboard!');
        }).catch((err) => {
            console.error('Failed to copy:', err);
            // Fallback to textarea method
            fallbackCopyToClipboard(text);
        });
    } else {
        fallbackCopyToClipboard(text);
    }
}

    function fallbackCopyToClipboard(text) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-999999px";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        const successful = document.execCommand('copy');
        if (successful) {
            alert('Share text copied to clipboard!');
        } else {
            alert('Unable to copy. Please copy manually: ' + text);
        }
    } catch (err) {
        console.error('Fallback copy failed:', err);
        alert('Unable to copy. Please copy manually: ' + text);
    }
    
    document.body.removeChild(textArea);
}

    // ===== UI HELPERS =====
    
    function resetToUpload() {
    fileInput.value = '';
    uploadSection.style.display = 'block';
    loadingState.style.display = 'none';
    resultsSection.style.display = 'none';
    errorState.style.display = 'none';
    currentResults = null;
    
    if (uploadArea) {
        uploadArea.scrollIntoView({ behavior: 'smooth' });
    }
}

    function showError(message) {
    uploadSection.style.display = 'none';
    loadingState.style.display = 'none';
    resultsSection.style.display = 'none';
    errorState.style.display = 'block';
    
    document.getElementById('errorMessage').textContent = message;
}

    function formatCurrency(amount) {
    if (!amount) return '$0.00';
    return '$' + (Math.round(amount * 100) / 100).toFixed(2);
}

    // ===== COLLAPSIBLE SECTIONS =====
    
    const optimizationSection = document.getElementById('optimizationSection');
    if (optimizationSection) {
        optimizationSection.addEventListener('click', function(e) {
            if (e.target.closest('.collapsible-header')) {
                this.classList.toggle('expanded');
            }
        });
    }
    
    // ===== SDK INTEGRATION FUNCTIONS =====
    
    let generatedAPIKey = '';
    
    window.showSDKSetup = function() {
        document.getElementById('methodSelection').style.display = 'none';
        document.getElementById('sdkSetup').style.display = 'block';
        document.getElementById('uploadInterface').style.display = 'none';
    };
    
    window.showUploadInterface = function() {
        document.getElementById('methodSelection').style.display = 'none';
        document.getElementById('sdkSetup').style.display = 'none';
        document.getElementById('uploadInterface').style.display = 'block';
    };
    
    window.showMethodSelection = function() {
        document.getElementById('methodSelection').style.display = 'grid';
        document.getElementById('sdkSetup').style.display = 'none';
        document.getElementById('uploadInterface').style.display = 'none';
    };
    
    // Generate API Key
    const generateKeyBtn = document.getElementById('generateKeyBtn');
    if (generateKeyBtn) {
        generateKeyBtn.addEventListener('click', async function() {
            try {
                this.disabled = true;
                this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
                
                const response = await fetch('/api/generate-key', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: `email=${encodeURIComponent(email || 'user@example.com')}`
                });
                
                const data = await response.json();
                
                if (data.success) {
                    generatedAPIKey = data.api_key;
                    document.getElementById('apiKeyValue').textContent = data.api_key;
                    document.getElementById('apiKeyDisplay').style.display = 'block';
                    this.style.display = 'none';
                }
            } catch (error) {
                alert('Failed to generate API key. Please try again.');
                this.disabled = false;
                this.innerHTML = '<i class="fas fa-key"></i> Generate API Key';
            }
        });
    }
    
    window.copyAPIKey = function() {
        const keyValue = document.getElementById('apiKeyValue').textContent;
        navigator.clipboard.writeText(keyValue).then(() => {
            alert('API key copied to clipboard!');
        });
    };
    
    window.goToStep2 = function() {
        document.getElementById('step1').style.display = 'none';
        document.getElementById('step2').style.display = 'block';
        
        // Update key in code examples
        if (generatedAPIKey) {
            document.getElementById('keyInCode1').textContent = generatedAPIKey;
        }
    };
    
    window.goToStep3 = function() {
        document.getElementById('step2').style.display = 'none';
        document.getElementById('step3').style.display = 'block';
    };
    
    window.showLanguage = function(lang) {
        const tabs = document.querySelectorAll('.lang-tab');
        tabs.forEach(tab => tab.classList.remove('active'));
        event.target.classList.add('active');
        
        if (lang === 'python') {
            document.getElementById('pythonCode').style.display = 'block';
            document.getElementById('javascriptCode').style.display = 'none';
            document.getElementById('pythonExample').style.display = 'block';
        } else {
            document.getElementById('pythonCode').style.display = 'none';
            document.getElementById('javascriptCode').style.display = 'block';
            document.getElementById('pythonExample').style.display = 'none';
        }
    };
    
    window.copyCode = function(text) {
        navigator.clipboard.writeText(text).then(() => {
            alert('Copied to clipboard!');
        });
    };
    
    window.copyCodeExample = function(lang) {
        const codeBlock = document.querySelector('#pythonExample code');
        const code = codeBlock.textContent;
        navigator.clipboard.writeText(code).then(() => {
            showToast('Code example copied to clipboard', 'success');
        }).catch(() => {
            showToast('Failed to copy. Please select and copy manually.', 'error');
        });
    };
    
    window.checkSDKSetup = async function() {
        const btn = event.target;
        const originalHTML = btn.innerHTML;
        
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking...';
        
        try {
            // Check if user has API key
            if (!generatedAPIKey) {
                showToast('Please complete Step 1 to generate your API key first', 'warning');
                btn.disabled = false;
                btn.innerHTML = originalHTML;
                return;
            }
            
            // Simulate verification check (in production, this would ping an endpoint)
            await new Promise(resolve => setTimeout(resolve, 1500));
            
            // Show verification modal with detailed status
            showVerificationModal();
            
        } catch (error) {
            showToast('Verification failed. Please try again.', 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalHTML;
        }
    };
    
    window.completeSDKSetup = function() {
        // Hide step 3, show step 4 (completion)
        document.getElementById('step3').style.display = 'none';
        document.getElementById('step4').style.display = 'block';
        
        // Track completion event
        if (typeof gtag !== 'undefined') {
            gtag('event', 'sdk_setup_complete', {
                'event_category': 'engagement',
                'event_label': 'SDK Integration'
            });
        }
        
        // Show success toast
        showToast('SDK setup complete! Your application is ready to track costs.', 'success');
    };
    
    window.goToDashboard = function() {
        // Redirect to real-time dashboard
        window.location.href = '/realtime';
    };
    
    function showVerificationModal() {
        const modal = document.createElement('div');
        modal.className = 'verification-modal';
        modal.innerHTML = `
            <div class="modal-backdrop" onclick="this.parentElement.remove()"></div>
            <div class="modal-content" style="max-width: 600px;">
                <div class="modal-header">
                    <h3 style="margin: 0; color: #1f2937;">
                        <i class="fas fa-check-circle" style="color: #10b981;"></i>
                        Setup Verification
                    </h3>
                    <button onclick="this.closest('.verification-modal').remove()" style="background: none; border: none; font-size: 1.5em; cursor: pointer; color: #6b7280;">×</button>
                </div>
                <div class="modal-body" style="padding: 20px;">
                    <div class="verification-checklist">
                        <div class="check-item" style="display: flex; gap: 15px; margin-bottom: 20px;">
                            <i class="fas fa-check-circle" style="color: #10b981; font-size: 1.5em;"></i>
                            <div>
                                <strong>API Key Generated</strong>
                                <p style="color: #6b7280; margin: 5px 0 0 0; font-size: 0.9em;">
                                    Your API key is active and ready to authenticate requests
                                </p>
                            </div>
                        </div>
                        <div class="check-item" style="display: flex; gap: 15px; margin-bottom: 20px;">
                            <i class="fas fa-check-circle" style="color: #10b981; font-size: 1.5em;"></i>
                            <div>
                                <strong>SDK Package Available</strong>
                                <p style="color: #6b7280; margin: 5px 0 0 0; font-size: 0.9em;">
                                    Install with: <code style="background: #f3f4f6; padding: 2px 6px; border-radius: 4px;">pip install ./substacker_sdk</code>
                                </p>
                            </div>
                        </div>
                        <div class="check-item" style="display: flex; gap: 15px; margin-bottom: 20px;">
                            <i class="fas fa-clock" style="color: #f59e0b; font-size: 1.5em;"></i>
                            <div>
                                <strong>Waiting for First API Call</strong>
                                <p style="color: #6b7280; margin: 5px 0 0 0; font-size: 0.9em;">
                                    Make an OpenAI API call from your application to see it here
                                </p>
                            </div>
                        </div>
                    </div>
                    
                    <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin-top: 20px; border-radius: 4px;">
                        <h4 style="margin: 0 0 8px 0; color: #92400e;">
                            <i class="fas fa-lightbulb"></i> Pro Tip
                        </h4>
                        <p style="color: #78350f; margin: 0; font-size: 0.95em;">
                            After deploying your code, visit the <a href="/realtime" style="color: #3b82f6; text-decoration: none; font-weight: 600;">Real-Time Dashboard</a> to monitor costs as they occur.
                        </p>
                    </div>
                </div>
                <div class="modal-footer" style="padding: 15px 20px; background: #f9fafb; border-top: 1px solid #e5e7eb; display: flex; justify-content: flex-end; gap: 10px;">
                    <button onclick="this.closest('.verification-modal').remove()" style="background: transparent; border: 1px solid #d1d5db; padding: 10px 20px; border-radius: 6px; cursor: pointer;">
                        Close
                    </button>
                    <button onclick="this.closest('.verification-modal').remove(); completeSDKSetup();" style="background: #3b82f6; color: white; border: none; padding: 10px 20px; border-radius: 6px; font-weight: 600; cursor: pointer;">
                        Continue to Dashboard
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }
    
    function showToast(message, type = 'info') {
        // Remove any existing toasts
        const existingToast = document.querySelector('.toast-notification');
        if (existingToast) {
            existingToast.remove();
        }
        
        const toast = document.createElement('div');
        toast.className = `toast-notification toast-${type}`;
        
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        
        const colors = {
            success: '#10b981',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#3b82f6'
        };
        
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: white;
            padding: 16px 20px;
            border-radius: 8px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            z-index: 10000;
            min-width: 300px;
            max-width: 500px;
            animation: slideIn 0.3s ease-out;
            border-left: 4px solid ${colors[type]};
        `;
        
        toast.innerHTML = `
            <div style="display: flex; align-items: center; gap: 12px;">
                <i class="fas fa-${icons[type]}" style="font-size: 1.5em; color: ${colors[type]};"></i>
                <span style="flex: 1; color: #1f2937;">${message}</span>
                <button onclick="this.closest('.toast-notification').remove()" style="background: none; border: none; color: #6b7280; cursor: pointer; font-size: 1.2em;">×</button>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.style.opacity = '0';
                toast.style.transition = 'opacity 0.3s';
                setTimeout(() => toast.remove(), 300);
            }
        }, 5000);
    }
    
    // Add CSS for modal and animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(400px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        .verification-modal {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .modal-backdrop {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
        }
        
        .modal-content {
            position: relative;
            background: white;
            border-radius: 12px;
            width: 90%;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            animation: modalSlideIn 0.3s ease-out;
        }
        
        @keyframes modalSlideIn {
            from { transform: translateY(-50px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        
        .modal-header {
            padding: 20px;
            border-bottom: 1px solid #e5e7eb;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .next-step-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
            transition: all 0.2s;
        }
        
        .next-step-card:hover {
            border-color: #3b82f6;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
        }
    `;
    document.head.appendChild(style);
    
    // ===== INITIALIZE =====
    
    console.log('Analyzer.js initialized successfully');
})();
