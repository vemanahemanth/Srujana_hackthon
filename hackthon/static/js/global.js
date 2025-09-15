/**
 * ACTMS - Global JavaScript Utilities
 * Handles animations, API calls, and common functionality
 */

class ACTMS {
  constructor() {
    this.baseURL = window.location.origin;
    this.init();
  }

  init() {
    this.setupAnimations();
    this.setupTabSystem();
    this.setupMobileNav();
    this.setupScrollEffects();
  }

  // Animation System
  setupAnimations() {
    // Intersection Observer for fade-in animations
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    }, {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    });

    // Observe all fade-in elements
    document.querySelectorAll('.fade-in').forEach(el => {
      observer.observe(el);
    });

    // Stagger animations for grids
    this.staggerAnimations();
  }

  staggerAnimations() {
    document.querySelectorAll('.grid').forEach(grid => {
      const items = grid.children;
      Array.from(items).forEach((item, index) => {
        item.style.animationDelay = `${index * 100}ms`;
      });
    });
  }

  setupScrollEffects() {
    // Parallax effect for radiant beams
    let ticking = false;
    
    const updateParallax = () => {
      const scrolled = window.pageYOffset;
      const rate = scrolled * -0.5;
      
      if (document.body.querySelector('::before')) {
        document.body.style.setProperty('--beam-offset', `${rate}px`);
      }
      
      ticking = false;
    };

    const requestParallaxTick = () => {
      if (!ticking) {
        requestAnimationFrame(updateParallax);
        ticking = true;
      }
    };

    window.addEventListener('scroll', requestParallaxTick);
  }

  // Tab System
  setupTabSystem() {
    document.addEventListener('click', (e) => {
      if (e.target.classList.contains('tab-button')) {
        this.switchTab(e.target);
      }
    });
  }

  switchTab(button) {
    const tabsContainer = button.closest('.tabs-container') || button.closest('.page-content');
    const targetId = button.dataset.tab;

    // Update button states
    tabsContainer.querySelectorAll('.tab-button').forEach(btn => {
      btn.classList.remove('active');
    });
    button.classList.add('active');

    // Update content visibility
    tabsContainer.querySelectorAll('.tab-content').forEach(content => {
      content.classList.remove('active');
    });
    
    const targetContent = tabsContainer.querySelector(`[data-content="${targetId}"]`);
    if (targetContent) {
      targetContent.classList.add('active');
    }
  }

  // Mobile Navigation
  setupMobileNav() {
    const mobileToggle = document.querySelector('.mobile-nav-toggle');
    const navLinks = document.querySelector('.nav-links');

    if (mobileToggle && navLinks) {
      mobileToggle.addEventListener('click', () => {
        navLinks.classList.toggle('active');
      });
    }
  }

  // API Helper Methods
  async apiCall(endpoint, options = {}) {
    try {
      const response = await fetch(`${this.baseURL}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        },
        ...options
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API call failed:', error);
      throw error;
    }
  }

  // Dashboard Methods
  async getDashboardData() {
    return await this.apiCall('/api/dashboard');
  }

  async getTenders() {
    return await this.apiCall('/api/tenders');
  }

  async getBids(tenderId = null) {
    const url = tenderId ? `/api/bids?tender_id=${tenderId}` : '/api/bids';
    return await this.apiCall(url);
  }

  async getSuspiciousBids() {
    return await this.apiCall('/api/bids/suspicious');
  }

  async getAlerts() {
    return await this.apiCall('/api/alerts');
  }

  async createTender(tenderData) {
    return await this.apiCall('/api/tenders', {
      method: 'POST',
      body: JSON.stringify(tenderData)
    });
  }

  async submitBid(bidData) {
    return await this.apiCall('/api/bids', {
      method: 'POST',
      body: JSON.stringify(bidData)
    });
  }

  async chatWithBot(message) {
    return await this.apiCall('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message })
    });
  }

  async trainModel() {
    return await this.apiCall('/api/model/train', {
      method: 'POST'
    });
  }

  async getModelMetrics() {
    return await this.apiCall('/api/model/metrics');
  }

  // Utility Methods
  formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR'
    }).format(amount);
  }

  formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }

  formatDateTime(dateString) {
    return new Date(dateString).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  // Indian Mobile Number Validation and Formatting
  validateIndianMobile(mobile) {
    // Remove all non-digit characters
    const cleaned = mobile.replace(/\D/g, '');
    
    // Check if it's a valid Indian mobile number
    // Should be 10 digits starting with 6-9, or 12 digits starting with 91
    if (cleaned.length === 10 && /^[6-9]\d{9}$/.test(cleaned)) {
      return true;
    }
    if (cleaned.length === 12 && /^91[6-9]\d{9}$/.test(cleaned)) {
      return true;
    }
    return false;
  }

  formatIndianMobile(mobile) {
    // Remove all non-digit characters
    const cleaned = mobile.replace(/\D/g, '');
    
    if (cleaned.length === 10 && /^[6-9]\d{9}$/.test(cleaned)) {
      // Format as +91-XXXXX-XXXXX
      return `+91-${cleaned.substring(0, 5)}-${cleaned.substring(5)}`;
    }
    if (cleaned.length === 12 && /^91[6-9]\d{9}$/.test(cleaned)) {
      // Already has country code, format as +91-XXXXX-XXXXX
      const number = cleaned.substring(2);
      return `+91-${number.substring(0, 5)}-${number.substring(5)}`;
    }
    
    // Return original if invalid
    return mobile;
  }

  sanitizeIndianMobile(mobile) {
    // Convert to standard format for storage (just digits with country code)
    const cleaned = mobile.replace(/\D/g, '');
    
    if (cleaned.length === 10 && /^[6-9]\d{9}$/.test(cleaned)) {
      return `91${cleaned}`;
    }
    if (cleaned.length === 12 && /^91[6-9]\d{9}$/.test(cleaned)) {
      return cleaned;
    }
    
    return null; // Invalid number
  }

  // Toast Notifications
  showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: var(--glass-fill);
      border: 1px solid var(--glass-border);
      backdrop-filter: var(--glass-blur);
      border-radius: var(--glass-radius);
      padding: var(--spacing-md) var(--spacing-lg);
      color: var(--color-text-primary);
      box-shadow: var(--glass-shadow);
      z-index: 1000;
      animation: slideInRight 0.3s ease;
    `;
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
      toast.style.animation = 'slideOutRight 0.3s ease forwards';
      setTimeout(() => document.body.removeChild(toast), 300);
    }, 3000);
  }

  // Loading States
  showLoading(element) {
    element.classList.add('loading');
  }

  hideLoading(element) {
    element.classList.remove('loading');
  }

  // Chart Helpers (for monochrome styling)
  getChartOptions() {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: {
            color: '#FFFFFF',
            font: {
              family: 'Inter'
            }
          }
        }
      },
      scales: {
        x: {
          ticks: {
            color: '#B3B3B3',
            font: {
              family: 'Inter'
            }
          },
          grid: {
            color: 'rgba(255,255,255,0.1)'
          }
        },
        y: {
          ticks: {
            color: '#B3B3B3',
            font: {
              family: 'Inter'
            }
          },
          grid: {
            color: 'rgba(255,255,255,0.1)'
          }
        }
      }
    };
  }

  getMonochromeColors() {
    return [
      'rgba(255,255,255,0.9)',
      'rgba(255,255,255,0.7)',
      'rgba(255,255,255,0.5)',
      'rgba(255,255,255,0.3)',
      'rgba(255,255,255,0.1)'
    ];
  }

  // Counter Animation
  animateCounter(element, start, end, duration = 2000) {
    const range = end - start;
    const increment = range / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
      current += increment;
      if (current >= end) {
        current = end;
        clearInterval(timer);
      }
      element.textContent = Math.floor(current).toLocaleString();
    }, 16);
  }

  // Form Validation
  validateForm(form) {
    const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');
    let isValid = true;

    inputs.forEach(input => {
      if (!input.value.trim()) {
        this.showFieldError(input, 'This field is required');
        isValid = false;
      } else {
        this.clearFieldError(input);
      }
    });

    return isValid;
  }

  showFieldError(input, message) {
    this.clearFieldError(input);
    
    const error = document.createElement('div');
    error.className = 'field-error';
    error.style.cssText = `
      color: #FF6B6B;
      font-size: 0.875rem;
      margin-top: var(--spacing-xs);
    `;
    error.textContent = message;
    
    input.parentNode.appendChild(error);
    input.style.borderColor = '#FF6B6B';
  }

  clearFieldError(input) {
    const error = input.parentNode.querySelector('.field-error');
    if (error) {
      error.remove();
    }
    input.style.borderColor = '';
  }
}

// Initialize ACTMS
const actms = new ACTMS();

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
  @keyframes slideInRight {
    from { transform: translateX(100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
  }
  
  @keyframes slideOutRight {
    from { transform: translateX(0); opacity: 1; }
    to { transform: translateX(100%); opacity: 0; }
  }
`;
document.head.appendChild(style);

// Export for global use
window.actms = actms;