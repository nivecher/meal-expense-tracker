/**
 * Timezone Detection Component
 * Automatically detects user's timezone using multiple fallback methods
 * Follows TIGER Style principles: Safety, Performance, Developer Experience
 */

class TimezoneDetector {
  constructor() {
    this.detectedTimezone = null;
    this.confidence = 'unknown';
    this.methods = [];
    this.autoSaveEnabled = true; // Flag to prevent infinite loops

    this.init();
  }

  init() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.detectTimezone());
    } else {
      this.detectTimezone();
    }
  }

  async detectTimezone() {
    try {
      // Method 1: Modern Intl.DateTimeFormat API (highest confidence)
      if (typeof Intl !== 'undefined' && Intl.DateTimeFormat) {
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        if (timezone && this.isValidTimezone(timezone)) {
          this.detectedTimezone = timezone;
          this.confidence = 'high';
          this.methods.push('Intl.DateTimeFormat');
          this.updateUI();
          return;
        }
      }

      // Method 2: Try geolocation-based detection (medium confidence)
      if ('geolocation' in navigator) {
        try {
          const position = await this.getCurrentPosition();
          const timezone = await this.getTimezoneFromCoordinates(
            position.coords.latitude,
            position.coords.longitude,
          );

          if (timezone && this.isValidTimezone(timezone)) {
            this.detectedTimezone = timezone;
            this.confidence = 'medium';
            this.methods.push('Geolocation API');
            this.updateUI();
            return;
          }
        } catch (error) {
          console.info('Geolocation detection failed:', error.message);
        }
      }

      // Method 3: Fallback to Date object analysis (low confidence)
      const timezone = this.detectTimezoneFromDate();
      if (timezone) {
        this.detectedTimezone = timezone;
        this.confidence = 'low';
        this.methods.push('Date offset analysis');
        this.updateUI();
        return;
      }

      // Method 4: Last resort - use browser language hint
      const browserTimezone = this.detectFromBrowserLanguage();
      if (browserTimezone) {
        this.detectedTimezone = browserTimezone;
        this.confidence = 'very_low';
        this.methods.push('Browser language hint');
        this.updateUI();
      }

    } catch (error) {
      console.error('Timezone detection failed:', error);
      this.confidence = 'failed';
    }
  }

  getCurrentPosition() {
    return new Promise((resolve, reject) => {
      const options = {
        timeout: 10000, // 10 second timeout
        enableHighAccuracy: false, // Faster, less battery drain
        maximumAge: 300000, // Cache for 5 minutes
      };

      navigator.geolocation.getCurrentPosition(resolve, reject, options);
    });
  }

  async getTimezoneFromCoordinates(lat, lng) {
    // Use a simple timezone lookup without external APIs
    // This is a basic implementation - in production you might want to use
    // a timezone boundary database or service

    const timezoneRules = [
      // North America
      { bounds: { north: 71, south: 15, west: -180, east: -130 }, tz: 'America/Anchorage' },
      { bounds: { north: 71, south: 25, west: -130, east: -114 }, tz: 'America/Los_Angeles' },
      { bounds: { north: 71, south: 25, west: -114, east: -104 }, tz: 'America/Denver' },
      { bounds: { north: 71, south: 25, west: -104, east: -80 }, tz: 'America/Chicago' },
      { bounds: { north: 71, south: 25, west: -80, east: -60 }, tz: 'America/New_York' },

      // Europe
      { bounds: { north: 71, south: 35, west: -10, east: 15 }, tz: 'Europe/London' },
      { bounds: { north: 71, south: 35, west: 15, east: 30 }, tz: 'Europe/Berlin' },
      { bounds: { north: 71, south: 35, west: 30, east: 45 }, tz: 'Europe/Moscow' },

      // Asia
      { bounds: { north: 71, south: 10, west: 45, east: 75 }, tz: 'Asia/Kolkata' },
      { bounds: { north: 71, south: 10, west: 75, east: 105 }, tz: 'Asia/Bangkok' },
      { bounds: { north: 71, south: 10, west: 105, east: 135 }, tz: 'Asia/Shanghai' },
      { bounds: { north: 71, south: 25, west: 135, east: 180 }, tz: 'Asia/Tokyo' },

      // Australia
      { bounds: { north: -10, south: -45, west: 110, east: 155 }, tz: 'Australia/Sydney' },

      // Default fallback
      { bounds: { north: 90, south: -90, west: -180, east: 180 }, tz: 'UTC' },
    ];

    for (const rule of timezoneRules) {
      if (lat <= rule.bounds.north && lat >= rule.bounds.south &&
        lng >= rule.bounds.west && lng <= rule.bounds.east) {
        return rule.tz;
      }
    }

    return 'UTC';
  }

  detectTimezoneFromDate() {
    try {
      const january = new Date(2024, 0, 1);
      const july = new Date(2024, 6, 1);
      const janOffset = january.getTimezoneOffset();
      const julOffset = july.getTimezoneOffset();

      // Basic timezone detection based on offset patterns
      const isDST = janOffset !== julOffset;
      const maxOffset = Math.max(janOffset, julOffset);

      // Common timezone mappings (simplified)
      const offsetMap = {
        '-720': 'Pacific/Auckland',  // UTC+12
        '-660': 'Australia/Sydney',  // UTC+11
        '-600': 'Australia/Brisbane', // UTC+10
        '-540': 'Asia/Tokyo',        // UTC+9
        '-480': 'Asia/Shanghai',     // UTC+8
        '-420': 'Asia/Bangkok',      // UTC+7
        '-360': 'Asia/Dhaka',        // UTC+6
        '-300': 'Asia/Kolkata',      // UTC+5
        '-240': 'Asia/Dubai',        // UTC+4
        '-180': 'Europe/Moscow',     // UTC+3
        '-120': 'Europe/Berlin',     // UTC+2
        '-60': 'Europe/Paris',       // UTC+1
        0: isDST ? 'Europe/London' : 'UTC', // UTC
        60: 'Atlantic/Azores',     // UTC-1
        120: 'America/Sao_Paulo',  // UTC-2
        180: 'America/Argentina/Buenos_Aires', // UTC-3
        240: 'America/New_York',   // UTC-4 (or EST)
        300: 'America/Chicago',    // UTC-5 (or CST)
        360: 'America/Denver',     // UTC-6 (or MST)
        420: 'America/Los_Angeles', // UTC-7 (or PST)
        480: 'America/Anchorage',  // UTC-8
        540: 'Pacific/Honolulu',   // UTC-9
      };

      return offsetMap[maxOffset.toString()] || 'UTC';

    } catch (error) {
      console.warn('Date-based timezone detection failed:', error);
      return null;
    }
  }

  detectFromBrowserLanguage() {
    try {
      const language = navigator.language || navigator.userLanguage;
      if (!language) return null;

      // Basic language to timezone mapping
      const languageMap = {
        'en-US': 'America/New_York',
        'en-GB': 'Europe/London',
        'en-AU': 'Australia/Sydney',
        'en-CA': 'America/Toronto',
        'fr-FR': 'Europe/Paris',
        'de-DE': 'Europe/Berlin',
        'it-IT': 'Europe/Rome',
        'es-ES': 'Europe/Madrid',
        'pt-BR': 'America/Sao_Paulo',
        'ja-JP': 'Asia/Tokyo',
        'ko-KR': 'Asia/Seoul',
        'zh-CN': 'Asia/Shanghai',
        'zh-TW': 'Asia/Taipei',
        'ru-RU': 'Europe/Moscow',
        'ar-SA': 'Asia/Riyadh',
        'hi-IN': 'Asia/Kolkata',
      };

      return languageMap[language] || languageMap[language.split('-')[0]] || null;

    } catch (error) {
      console.warn('Language-based timezone detection failed:', error);
      return null;
    }
  }

  isValidTimezone(timezone) {
    try {
      // Test if the timezone is valid by trying to create a date with it
      Intl.DateTimeFormat('en', { timeZone: timezone });
      return true;
    } catch (error) {
      return false;
    }
  }

  updateUI() {
    const timezoneSelect = document.getElementById('timezone');
    const detectedMessage = document.getElementById('timezone-detected');
    const detectButton = document.getElementById('detect-timezone-btn');

    if (!this.detectedTimezone) return;

    // Update the select dropdown
    if (timezoneSelect) {
      const option = timezoneSelect.querySelector(`option[value="${this.detectedTimezone}"]`);
      if (option) {
        const currentValue = timezoneSelect.value;
        timezoneSelect.value = this.detectedTimezone;

        // Trigger change event for any listeners
        const event = new Event('change', { bubbles: true });
        timezoneSelect.dispatchEvent(event);

        // Don't auto-save to prevent infinite loops
        // User can manually save the form if they want to update their timezone
      }
    }

    // Show detection message
    if (detectedMessage) {
      const confidenceText = {
        high: 'automatically detected',
        medium: 'detected from location',
        low: 'estimated from system',
        very_low: 'guessed from browser',
        failed: 'detection failed',
      };

      detectedMessage.innerHTML = `
        <div class="alert alert-info">
          <i class="fas fa-location-dot me-1"></i>
          <span class="fw-bold">${this.detectedTimezone.replace('_', ' ')} ${confidenceText[this.confidence]}</span>
          <br>
          <small class="text-muted">Click "Save" below to update your timezone preference.</small>
        </div>
      `;
      detectedMessage.style.display = 'block';
    }

    // Update detect button
    if (detectButton) {
      detectButton.innerHTML = '<i class="fas fa-check me-1"></i>Detected';
      detectButton.disabled = true;
      detectButton.className = detectButton.className.replace('btn-outline-primary', 'btn-success');
    }
  }

  // Save timezone via AJAX
  async saveTimezone(timezone) {
    try {
      const response = await fetch('/auth/profile', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: `timezone=${encodeURIComponent(timezone)}&csrf_token=${this.getCSRFToken()}`,
      });

      if (response.ok) {
        // Show success message
        this.showSaveMessage('Timezone saved successfully!', 'success');
        // Update the current time display without reloading the page
        this.updateCurrentTimeDisplay();
      } else {
        this.showSaveMessage('Failed to save timezone. Please try again.', 'error');
      }
    } catch (error) {
      console.error('Error saving timezone:', error);
      this.showSaveMessage('Error saving timezone. Please try again.', 'error');
    }
  }

  // Show save message
  showSaveMessage(message, type) {
    const detectedMessage = document.getElementById('timezone-detected');
    if (detectedMessage) {
      const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
      detectedMessage.innerHTML = `
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
          <i class="fas fa-${type === 'success' ? 'check' : 'exclamation-triangle'} me-1"></i>
          ${message}
        </div>
      `;
      detectedMessage.style.display = 'block';
    }
  }

  // Get CSRF token
  getCSRFToken() {
    const csrfToken = document.querySelector('meta[name="csrf-token"]');
    return csrfToken ? csrfToken.getAttribute('content') : '';
  }

  // Update current time display without reloading page
  async updateCurrentTimeDisplay() {
    try {
      // Fetch updated current time from server
      const response = await fetch('/auth/profile', {
        method: 'GET',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        },
      });

      if (response.ok) {
        // The page will be updated with the new timezone on next manual refresh
        // For now, just show a message that the timezone was updated
        console.log('Timezone updated successfully');
      }
    } catch (error) {
      console.error('Error updating time display:', error);
    }
  }

  // Public method to manually trigger detection
  async detectManually() {
    const detectButton = document.getElementById('detect-timezone-btn');
    const detectedMessage = document.getElementById('timezone-detected');

    if (detectButton) {
      detectButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Detecting...';
      detectButton.disabled = true;
    }

    if (detectedMessage) {
      detectedMessage.style.display = 'none';
    }

    await this.detectTimezone();
  }

  // Get the detected timezone info
  getDetectionInfo() {
    return {
      timezone: this.detectedTimezone,
      confidence: this.confidence,
      methods: this.methods,
    };
  }
}

// Initialize the timezone detector
const timezoneDetector = new TimezoneDetector();

// Export for potential use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = TimezoneDetector;
} else if (typeof window !== 'undefined') {
  window.TimezoneDetector = TimezoneDetector;
  window.timezoneDetector = timezoneDetector;
}
