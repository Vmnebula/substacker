/**
 * Landing Page JavaScript
 * Handles hero chart, FAQ interactions, email forms, animations, and analytics
 */

// Initialize on DOM Load
document.addEventListener('DOMContentLoaded', function() {
    // Email form submissions
    const emailForm = document.getElementById('emailForm');
    const footerEmailForm = document.getElementById('footerEmailForm');
    
    if (emailForm) {
        emailForm.addEventListener('submit', handleEmailSubmit);
    }
    
    if (footerEmailForm) {
        footerEmailForm.addEventListener('submit', handleEmailSubmit);
    }
    
    // Initialize hero chart if present
    initializeHeroChart();
    
    // FAQ accordion
    initializeFAQ();
    
    // Waste counter animation
    initializeWasteCounter();
    
    // Scroll animations
    initializeScrollAnimations();
    
    // Navigation enhancements
    setupResponsiveMenu();
});

/**
 * Initialize Hero Chart with Chart.js
 */
function initializeHeroChart() {
    const ctx = document.getElementById('hero-chart');
    if (!ctx || typeof Chart === 'undefined') return;

    try {
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['OpenAI', 'Anthropic', 'Google', 'Azure'],
                datasets: [{
                    data: [45, 25, 20, 10],
                    backgroundColor: [
                        '#3b82f6',    // Blue
                        '#8b5cf6',    // Purple
                        '#10b981',    // Green
                        '#f59e0b'     // Amber
                    ],
                    borderWidth: 0,
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#64748b',
                            font: { size: 12, family: "'Inter', sans-serif" },
                            padding: 15,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleFont: { size: 14, weight: '600' },
                        bodyFont: { size: 12 },
                        padding: 12,
                        borderRadius: 8,
                        callbacks: {
                            label: function(context) {
                                return context.label + ': ' + context.parsed + '%';
                            }
                        }
                    }
                },
                animation: {
                    animateRotate: true,
                    animateScale: true,
                    duration: 750
                }
            }
        });
    } catch (error) {
        console.error('Error initializing hero chart:', error);
    }
}

// Handle email form submission
async function handleEmailSubmit(e) {
    e.preventDefault();
    
    const form = e.target;
    const email = form.querySelector('input[type="email"]').value;
    const button = form.querySelector('button');
    const originalText = button.innerHTML;
    
    // Show loading state
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Sending...</span>';
    
    try {
        const formData = new FormData();
        formData.append('email', email);
        
        const response = await fetch('/capture-lead', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Show success message
            button.innerHTML = '<i class="fas fa-check"></i> <span>Check Your Email!</span>';
            button.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
            
            // Redirect after 2 seconds
            setTimeout(() => {
                if (data.redirect) {
                    window.location.href = data.redirect;
                }
            }, 2000);
        } else {
            throw new Error(data.error || 'Failed to submit form');
        }
    } catch (error) {
        console.error('Error:', error);
        button.innerHTML = '<i class="fas fa-exclamation-circle"></i> <span>Error. Try again.</span>';
        button.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
        
        // Reset after 3 seconds
        setTimeout(() => {
            button.disabled = false;
            button.innerHTML = originalText;
            button.style.background = '';
        }, 3000);
    }
}

/**
 * Initialize scroll animations
 */
function initializeScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe cards and elements with animation
    document.querySelectorAll('[data-animate]').forEach(element => {
        observer.observe(element);
    });
}

// Initialize FAQ accordion
function initializeFAQ() {
    const faqItems = document.querySelectorAll('.faq-item');
    
    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');
        
        if (question) {
            question.addEventListener('click', function() {
                // Close other open items
                faqItems.forEach(otherItem => {
                    if (otherItem !== item && otherItem.classList.contains('active')) {
                        otherItem.classList.remove('active');
                    }
                });
                
                // Toggle current item
                item.classList.toggle('active');
            });
        }
    });
}

// Initialize waste counter
function initializeWasteCounter() {
    const counterDisplay = document.getElementById('wasteCounter');
    const counterMessage = document.getElementById('counterMessage');
    
    if (!counterDisplay) return;
    
    const wastePerSecond = 78.50 / 60; // $78.50 per minute
    let elapsedSeconds = 0;
    
    const interval = setInterval(() => {
        elapsedSeconds++;
        const wasteAmount = wastePerSecond * elapsedSeconds;
        
        counterDisplay.textContent = '$' + wasteAmount.toFixed(2);
        
        // Stop after 30 seconds to avoid excessive numbers
        if (elapsedSeconds > 30) {
            clearInterval(interval);
            if (counterMessage) {
                counterMessage.textContent = 'And counting...';
            }
        }
    }, 1000);
}

// Smooth scroll for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');
        if (href !== '#' && href !== '#!') {
            e.preventDefault();
            
            const target = document.querySelector(href);
            if (target) {
                const offsetTop = target.getBoundingClientRect().top + window.pageYOffset - 80;
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        }
    });
});

// Add animation to elements when they come into view
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -100px 0px'
};

const observer = new IntersectionObserver(function(entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
            observer.unobserve(entry.target);
        }
    });
}, observerOptions);

// Observe problem cards and testimonials
document.querySelectorAll('.problem-card, .testimonial-card').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    observer.observe(el);
});

// Handle responsive navbar menu
function setupResponsiveMenu() {
    const navbar = document.querySelector('.navbar');
    
    // Check if navbar exists before adding event listeners
    if (!navbar) {
        console.warn('Navbar element not found');
        return;
    }
    
    let lastScrollTop = 0;
    
    window.addEventListener('scroll', function() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        if (scrollTop > lastScrollTop) {
            // Scroll down - hide navbar
            navbar.style.transform = 'translateY(-100%)';
        } else {
            // Scroll up - show navbar
            navbar.style.transform = 'translateY(0)';
        }
        
        lastScrollTop = scrollTop <= 0 ? 0 : scrollTop;
    });
    
    navbar.style.transition = 'transform 0.3s ease';
}

// Analytics tracking
function trackEvent(eventName, eventData = {}) {
    if (typeof gtag !== 'undefined') {
        gtag('event', eventName, eventData);
    }
}

// Track form submissions
document.addEventListener('submit', function(e) {
    if (e.target.classList.contains('capture-form')) {
        const email = e.target.querySelector('input[type="email"]').value;
        trackEvent('email_capture', {
            email_domain: email.split('@')[1]
        });
    }
}, true);

// Track FAQ interactions
document.addEventListener('click', function(e) {
    const faqQuestion = e.target.closest('.faq-question');
    if (faqQuestion) {
        const faqItem = faqQuestion.closest('.faq-item');
        const question = faqQuestion.querySelector('h3').textContent;
        trackEvent('faq_clicked', {
            question: question
        });
    }
}, true);

// Performance optimization: Lazy load images
if ('IntersectionObserver' in window) {
    const images = document.querySelectorAll('img[data-src]');
    
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
                observer.unobserve(img);
            }
        });
    });
    
    images.forEach(img => imageObserver.observe(img));
}

/**
 * Utility: Copy to Clipboard
 */
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showNotification('Copied to clipboard!', 'success');
        }).catch(() => {
            fallbackCopy(text);
        });
    } else {
        fallbackCopy(text);
    }
}

function fallbackCopy(text) {
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
 * Show notification toast
 */
function showNotification(message, type = 'info') {
    const container = document.getElementById('toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <i class="fas fa-${getNotificationIcon(type)}"></i>
            <span>${message}</span>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;

    container.appendChild(toast);

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.remove();
        }
    }, 5000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
}

function getNotificationIcon(type) {
    const icons = {
        success: 'check-circle',
        error: 'exclamation-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    };
    return icons[type] || icons.info;
}

/**
 * Global navigation functions
 */
function scrollToSection(sectionId) {
    const element = document.getElementById(sectionId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
    }
}

function goToSignup() {
    window.location.href = '/analyzer';
}

function openContactForm() {
    window.location.href = '/contact';
}

/**
 * Inject toast styles
 */
(function injectStyles() {
    if (document.getElementById('landing-toast-styles')) return;

    const styles = document.createElement('style');
    styles.id = 'landing-toast-styles';
    styles.textContent = `
        .toast-container {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-width: 400px;
        }

        .toast {
            background-color: white;
            border-radius: 8px;
            padding: 14px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            animation: slideIn 0.3s ease-out;
        }

        .toast-content {
            display: flex;
            align-items: center;
            gap: 10px;
            flex: 1;
            font-size: 14px;
        }

        .toast-success { border-left: 4px solid #10b981; }
        .toast-success .toast-content { color: #10b981; }

        .toast-error { border-left: 4px solid #ef4444; }
        .toast-error .toast-content { color: #ef4444; }

        .toast-warning { border-left: 4px solid #f59e0b; }
        .toast-warning .toast-content { color: #f59e0b; }

        .toast-info { border-left: 4px solid #3b82f6; }
        .toast-info .toast-content { color: #3b82f6; }

        .toast-close {
            background: none;
            border: none;
            cursor: pointer;
            padding: 0;
            display: flex;
            align-items: center;
            color: #9ca3af;
            transition: color 0.2s;
        }

        .toast-close:hover { color: #4b5563; }

        @keyframes slideIn {
            from { transform: translateX(400px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }

        @media (max-width: 480px) {
            .toast-container {
                left: 10px;
                right: 10px;
                max-width: none;
            }
        }

        [data-animate] {
            opacity: 0;
            transform: translateY(20px);
            transition: opacity 0.6s ease, transform 0.6s ease;
        }

        [data-animate].animate-in {
            opacity: 1;
            transform: translateY(0);
        }
    `;

    document.head.appendChild(styles);
})();

/**
 * Debounce utility
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Dark mode support
 */
function initializeDarkMode() {
    const theme = localStorage.getItem('theme') || 'light';
    applyTheme(theme);

    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
            const newTheme = e.matches ? 'dark' : 'light';
            applyTheme(newTheme);
        });
    }
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeDarkMode);
} else {
    initializeDarkMode();
}

console.log(
    '%cSubstacker',
    'font-size: 24px; font-weight: bold; color: #3b82f6;'
);
console.log(
    '%cAI Cost Intelligence Platform',
    'font-size: 14px; color: #667eea;'
);

/**
 * Reveal the demo once its first frame is available, and retire the skeleton.
 */
function handleDemoLoad() {
    const demoGif = document.getElementById('demoGif');
    const skeleton = document.getElementById('demoSkeleton');
    
    if (demoGif && skeleton) {
        // Add loaded class to trigger fade-in
        demoGif.classList.add('loaded');
        
        // Hide skeleton after a brief delay
        setTimeout(() => {
            skeleton.classList.add('hidden');
        }, 400);
    }
}

/**
 * Replace the skeleton with a retry affordance if the demo cannot be fetched.
 */
function handleDemoError() {
    const skeleton = document.getElementById('demoSkeleton');
    if (!skeleton) return;
    
    const skeletonContent = skeleton.querySelector('.skeleton-content');
    if (!skeletonContent) return;
    
    skeletonContent.innerHTML = `
        <div style="color: #e53e3e;">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin: 0 auto 12px;">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
                <line x1="15" y1="9" x2="9" y2="15" stroke="currentColor" stroke-width="2"/>
                <line x1="9" y1="9" x2="15" y2="15" stroke="currentColor" stroke-width="2"/>
            </svg>
            <p>Could not load the demo</p>
            <button onclick="location.reload()" style="margin-top: 12px; padding: 8px 16px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer;">Retry</button>
        </div>
    `;
}

/**
 * Respect the viewer's motion preference for the autoplaying demo.
 *
 * The markup carries `autoplay` so the demo starts for everyone by default, which is
 * what most visitors expect. Anyone who has asked their system to reduce motion gets a
 * still poster frame instead, and the preference is watched live so toggling it in the
 * OS takes effect without a reload.
 */
function applyDemoMotionPreference() {
    const demo = document.getElementById('demoGif');
    if (!demo || typeof demo.pause !== 'function') return;

    const query = window.matchMedia('(prefers-reduced-motion: reduce)');

    const sync = () => {
        if (query.matches) {
            demo.pause();
            demo.removeAttribute('autoplay');
            demo.currentTime = 0;
        } else if (demo.paused) {
            // play() rejects when the browser blocks autoplay; the poster remains.
            demo.play().catch(() => {});
        }
    };

    sync();
    if (typeof query.addEventListener === 'function') {
        query.addEventListener('change', sync);
    }
}

document.addEventListener('DOMContentLoaded', applyDemoMotionPreference);

// Make functions globally available
window.handleDemoLoad = handleDemoLoad;
window.handleDemoError = handleDemoError;
