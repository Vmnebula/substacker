/**
 * Reusable UI Components
 * Component factory functions for creating common UI elements
 */

// =========================================
// Modal Component
// =========================================

class Modal {
    constructor(id, title = '') {
        this.id = id;
        this.title = title;
        this.element = document.getElementById(id);
    }

    open() {
        if (this.element) {
            this.element.classList.add('active');
        }
    }

    close() {
        if (this.element) {
            this.element.classList.remove('active');
        }
    }

    isOpen() {
        return this.element && this.element.classList.contains('active');
    }

    toggle() {
        this.isOpen() ? this.close() : this.open();
    }
}

// =========================================
// Table Component
// =========================================

class DataTable {
    constructor(selector, options = {}) {
        this.table = document.querySelector(selector);
        this.options = options;
        this.data = [];
        this.sortColumn = null;
        this.sortDirection = 'asc';
    }

    setData(data) {
        this.data = data;
        this.render();
    }

    render() {
        const tbody = this.table.querySelector('tbody');
        if (!tbody) return;

        tbody.innerHTML = this.data.map((row, idx) => `
            <tr data-index="${idx}">
                ${Object.values(row).map(cell => `<td>${cell}</td>`).join('')}
            </tr>
        `).join('');
    }

    sort(column) {
        if (this.sortColumn === column) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = column;
            this.sortDirection = 'asc';
        }

        this.data.sort((a, b) => {
            let aVal = a[column];
            let bVal = b[column];

            if (typeof aVal === 'string') {
                aVal = aVal.toLowerCase();
                bVal = bVal.toLowerCase();
            }

            if (this.sortDirection === 'asc') {
                return aVal > bVal ? 1 : -1;
            } else {
                return aVal < bVal ? 1 : -1;
            }
        });

        this.render();
    }

    filter(predicate) {
        this.data = this.data.filter(predicate);
        this.render();
    }
}

// =========================================
// Form Component
// =========================================

class Form {
    constructor(selector) {
        this.form = document.querySelector(selector);
        this.fields = {};
        this.setupFields();
    }

    setupFields() {
        if (!this.form) return;

        this.form.querySelectorAll('input, select, textarea').forEach(field => {
            this.fields[field.id] = field;
        });
    }

    getValues() {
        const values = {};
        Object.entries(this.fields).forEach(([id, field]) => {
            if (field.type === 'checkbox') {
                values[id] = field.checked;
            } else if (field.type === 'radio') {
                if (field.checked) values[id] = field.value;
            } else {
                values[id] = field.value;
            }
        });
        return values;
    }

    setValues(values) {
        Object.entries(values).forEach(([id, value]) => {
            const field = this.fields[id];
            if (!field) return;

            if (field.type === 'checkbox') {
                field.checked = value;
            } else if (field.type === 'radio') {
                const radio = this.form.querySelector(`input[name="${field.name}"][value="${value}"]`);
                if (radio) radio.checked = true;
            } else {
                field.value = value;
            }
        });
    }

    reset() {
        if (this.form) this.form.reset();
    }

    validate() {
        return this.form ? this.form.checkValidity() : true;
    }

    getErrors() {
        const errors = {};
        Object.entries(this.fields).forEach(([id, field]) => {
            if (!field.checkValidity()) {
                errors[id] = field.validationMessage;
            }
        });
        return errors;
    }

    onSubmit(callback) {
        if (!this.form) return;
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            if (this.validate()) {
                callback(this.getValues());
            }
        });
    }
}

// =========================================
// Notification/Toast Component
// =========================================

class Toast {
    constructor(message, type = 'info', duration = 5000) {
        this.message = message;
        this.type = type;
        this.duration = duration;
        this.element = null;
    }

    show() {
        const container = this.getContainer();
        
        this.element = document.createElement('div');
        this.element.className = `toast toast-${this.type}`;
        this.element.innerHTML = `
            <div class="toast-content">
                <i class="fas fa-${this.getIcon()}"></i>
                <span>${this.message}</span>
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;

        container.appendChild(this.element);

        if (this.duration > 0) {
            setTimeout(() => this.close(), this.duration);
        }

        return this;
    }

    close() {
        if (this.element && this.element.parentElement) {
            this.element.remove();
        }
    }

    getContainer() {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        return container;
    }

    getIcon() {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[this.type] || 'info-circle';
    }

    static success(message, duration) {
        return new Toast(message, 'success', duration).show();
    }

    static error(message, duration) {
        return new Toast(message, 'error', duration).show();
    }

    static warning(message, duration) {
        return new Toast(message, 'warning', duration).show();
    }

    static info(message, duration) {
        return new Toast(message, 'info', duration).show();
    }
}

// =========================================
// Dropdown Component
// =========================================

class Dropdown {
    constructor(triggerId, menuId) {
        this.trigger = document.getElementById(triggerId);
        this.menu = document.getElementById(menuId);
        this.setupListeners();
    }

    setupListeners() {
        if (!this.trigger) return;

        this.trigger.addEventListener('click', () => this.toggle());

        document.addEventListener('click', (e) => {
            if (!this.trigger.contains(e.target) && !this.menu.contains(e.target)) {
                this.close();
            }
        });
    }

    open() {
        if (this.menu) this.menu.classList.add('active');
    }

    close() {
        if (this.menu) this.menu.classList.remove('active');
    }

    toggle() {
        this.menu.classList.contains('active') ? this.close() : this.open();
    }
}

// =========================================
// Tabs Component
// =========================================

class Tabs {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.tabs = [];
        this.setupTabs();
    }

    setupTabs() {
        if (!this.container) return;

        const buttons = this.container.querySelectorAll('[data-tab]');
        buttons.forEach(button => {
            button.addEventListener('click', () => {
                const tabName = button.getAttribute('data-tab');
                this.switchTo(tabName);
            });
        });
    }

    switchTo(tabName) {
        // Deactivate all tabs
        this.container.querySelectorAll('[data-tab]').forEach(btn => {
            btn.classList.remove('active');
        });

        this.container.querySelectorAll(`[id^="tab-"]`).forEach(content => {
            content.classList.remove('active');
        });

        // Activate selected tab
        const button = this.container.querySelector(`[data-tab="${tabName}"]`);
        const content = document.getElementById(`tab-${tabName}`);

        if (button) button.classList.add('active');
        if (content) content.classList.add('active');
    }
}

// =========================================
// Alert/Confirmation Component
// =========================================

class Alert {
    static confirm(message) {
        return confirm(message);
    }

    static alert(message) {
        alert(message);
    }

    static show(title, message, type = 'info') {
        Toast.info(`${title}: ${message}`);
    }
}
