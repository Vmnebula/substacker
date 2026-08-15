// Results display handlers - only runs on pages that have the necessary elements
(function() {
    'use strict';
    
    // Check if we're on a page that needs this functionality
    const resultsSection = document.getElementById('resultsSection');
    const shareBtn = document.getElementById('shareResults');
    const helpBtn = document.getElementById('getHelp');
    
    if (!resultsSection) {
        console.log('Results section not found - skipping results.js');
        return;
    }
    
    // Share results functionality
    if (shareBtn) {
        shareBtn.addEventListener('click', function() {
            const wasteAmount = document.getElementById('wasteAmount');
            const amount = wasteAmount ? wasteAmount.textContent : '$0.00';
            const shareText = `I just discovered I'm wasting ${amount} on OpenAI API. Check your waste too! https://openai-waste.com`;
            
            if (navigator.share) {
                navigator.share({
                    title: 'OpenAI Waste Analysis',
                    text: shareText,
                    url: window.location.origin
                }).catch(err => console.log('Share error:', err));
            } else {
                navigator.clipboard.writeText(shareText).then(() => {
                    alert('Share text copied to clipboard!');
                }).catch(() => {
                    alert('Unable to share.');
                });
            }
        });
    }
    
    // Get help functionality
    if (helpBtn) {
        helpBtn.addEventListener('click', function() {
            const urlParams = new URLSearchParams(window.location.search);
            const email = urlParams.get('email');
            const wasteEl = document.getElementById('wasteAmount');
            const savingsEl = document.getElementById('savingsPercentage');
            
            const waste = wasteEl ? wasteEl.textContent : '$0.00';
            const savings = savingsEl ? savingsEl.textContent : '0%';
            
            if (email) {
                alert(`Thank you! Our team will contact you at ${email}. Potential savings: ${savings}`);
            } else {
                alert('Thank you for your interest! Our team will contact you soon.');
            }
        });
    }
})();
