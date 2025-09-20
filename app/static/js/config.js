/**
 * Simple app configuration loader
 */

// Default config
const defaults = {
  staticBaseUrl: '',
  app: {
    debug: false,
    env: 'production',
    version: '0.0.0',
  },
};

// Load config from DOM
function loadConfig() {
  try {
    const configEl = document.getElementById('app-config');
    if (configEl?.dataset.appConfig) {
      const userConfig = JSON.parse(configEl.dataset.appConfig);
      return {
        ...defaults,
        ...userConfig,
        app: { ...defaults.app, ...(userConfig.app || {}) },
      };
    }
  } catch {
    console.error('Config load error:', error);
  }
  return defaults;
}

const config = loadConfig();

// Make colors globally available for backward compatibility
if (config.colors) {
  window.MEAL_TRACKER_COLORS = config.colors;
}

export default config;
