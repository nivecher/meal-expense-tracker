// Application configuration
const AppConfig = {
  // Base URL for static files
  staticBaseUrl: '',

  // Application settings
  app: {
    debug: false,
    env: 'production',
    version: '1.0.0',
  },

  // Initialize configuration
  init() {
    // Configuration will be set from the base template
    if (window.APP_CONFIG) {
      Object.assign(this, window.APP_CONFIG);
    }
    return this;
  },
};

// Initialize and export the configuration
export default AppConfig.init();
