/**
 * Utility Functions
 * Common helper functions used across the application
 */

// =========================================
// DOM Utilities
// =========================================

function $(selector) {
    return document.querySelector(selector);
}

function $$(selector) {
    return document.querySelectorAll(selector);
}

function addClass(element, className) {
    if (element) element.classList.add(className);
}

function removeClass(element, className) {
    if (element) element.classList.remove(className);
}

function toggleClass(element, className) {
    if (element) element.classList.toggle(className);
}

function hasClass(element, className) {
    return element && element.classList.contains(className);
}

// =========================================
// String Utilities
// =========================================

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function formatCurrency(cents) {
    return '$' + (cents / 100).toFixed(2);
}

function formatNumber(num) {
    return num.toLocaleString();
}

function formatDate(date) {
    return new Date(date).toLocaleDateString();
}

function formatDateTime(date) {
    return new Date(date).toLocaleString();
}

// =========================================
// Array Utilities
// =========================================

function chunk(array, size) {
    const chunks = [];
    for (let i = 0; i < array.length; i += size) {
        chunks.push(array.slice(i, i + size));
    }
    return chunks;
}

function unique(array) {
    return [...new Set(array)];
}

function groupBy(array, key) {
    return array.reduce((result, item) => {
        const group = item[key];
        if (!result[group]) result[group] = [];
        result[group].push(item);
        return result;
    }, {});
}

// =========================================
// Object Utilities
// =========================================

function isEmpty(obj) {
    return Object.keys(obj).length === 0;
}

function deepClone(obj) {
    return JSON.parse(JSON.stringify(obj));
}

function merge(target, source) {
    return Object.assign({}, target, source);
}

// =========================================
// Storage Utilities
// =========================================

function getStorage(key, defaultValue = null) {
    try {
        const value = localStorage.getItem(key);
        return value ? JSON.parse(value) : defaultValue;
    } catch (e) {
        return defaultValue;
    }
}

function setStorage(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
    } catch (e) {
        console.error('Storage error:', e);
        return false;
    }
}

function removeStorage(key) {
    try {
        localStorage.removeItem(key);
        return true;
    } catch (e) {
        return false;
    }
}

// =========================================
// Validation Utilities
// =========================================

function isEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function isURL(url) {
    try {
        new URL(url);
        return true;
    } catch (e) {
        return false;
    }
}

function isPhoneNumber(phone) {
    return /^\+?[\d\s\-\(\)]{10,}$/.test(phone);
}

// =========================================
// Time Utilities
// =========================================

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

function throttle(func, limit) {
    let inThrottle;
    return function executedFunction(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// =========================================
// API Utilities
// =========================================

function getAPIKey() {
    return localStorage.getItem('substacker_api_key');
}

function setAPIKey(key) {
    localStorage.setItem('substacker_api_key', key);
}

function isAuthenticated() {
    return !!getAPIKey();
}

// =========================================
// Error Handling
// =========================================

function handleError(error, context = '') {
    console.error(`[${context}]`, error);
    const message = error.message || 'An error occurred';
    showNotification(message, 'error');
    return null;
}

// =========================================
// Logging
// =========================================

function log(message, data = null) {
    const timestamp = new Date().toLocaleTimeString();
    console.log(`[${timestamp}] ${message}`, data || '');
}

function logError(message, error = null) {
    const timestamp = new Date().toLocaleTimeString();
    console.error(`[${timestamp}] ERROR: ${message}`, error || '');
}

function logWarn(message, data = null) {
    const timestamp = new Date().toLocaleTimeString();
    console.warn(`[${timestamp}] WARNING: ${message}`, data || '');
}
