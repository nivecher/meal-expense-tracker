// eslint.config.js
import js from '@eslint/js';
import globals from 'globals';

export default [
  // Base configuration
  {
    files: ['**/*.js'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.node,
        ...globals.es2021,
        // Global variables that are expected to be available
        bootstrap: 'readonly',
        google: 'readonly',
        $: 'readonly',
        jQuery: 'readonly',
        showToast: 'readonly',
        L: 'readonly', // Leaflet
        map: 'readonly',
        marker: 'readonly',
        getCurrentPosition: 'readonly',
        tileLayer: 'readonly',
        copyCoordinates: 'readonly',
        centerMapOnRestaurant: 'readonly',
        flatpickr: 'readonly', // Flatpickr date picker
        // Add other globals that might be used in the application
        showAlert: 'readonly',
        urlViewMode: 'readonly',
        googleMapsInitialized: 'readonly',
      },
    },
    rules: {
      // Base rules
      'no-console': 'warn',
      'no-debugger': 'warn',
      'no-unused-vars': 'warn',
      'no-var': 'error',
      'prefer-const': 'error',
      'object-shorthand': 'error',
      'quote-props': ['error', 'as-needed'],
      'prefer-arrow-callback': 'error',
      'prefer-template': 'error',
      'template-curly-spacing': 'error',
      'no-else-return': 'error',
      'no-multi-assign': 'error',
      'no-param-reassign': 'error',
      'no-underscore-dangle': ['error', { allowAfterThis: true }],
      'no-useless-return': 'error',
      'no-warning-comments': 'warn',
      'prefer-destructuring': 'warn',
      'prefer-rest-params': 'warn',
      'prefer-spread': 'warn',
      'require-await': 'warn',
      'require-atomic-updates': 'warn',
      'no-await-in-loop': 'warn',
      'no-constant-binary-expression': 'warn',
      'no-constructor-return': 'warn',
      'no-duplicate-imports': 'error',
      'no-promise-executor-return': 'error',
      'no-self-compare': 'error',
      'no-unreachable-loop': 'warn',
      'no-use-before-define': 'error',
      'block-scoped-var': 'error',
      'camelcase': 'off', // Disabled - API response properties use snake_case
      'class-methods-use-this': 'off', // Disabled - utility methods don't need 'this'
      'consistent-return': 'off', // Disabled - event handlers don't need consistent returns
      'default-case': 'off', // Disabled - switch statements may not need default
      'default-param-last': 'error',
      'dot-notation': 'error',
      'eqeqeq': 'error',
      'max-classes-per-file': ['warn', 2],
      'max-depth': ['warn', 4],
      'max-lines-per-function': 'off', // Disabled - complex functions are sometimes necessary
      'max-params': 'off', // Disabled - some functions need many parameters
      'max-statements': 'off', // Disabled - complex logic sometimes requires many statements
      'new-cap': 'warn',
      'no-array-constructor': 'error',
      'no-bitwise': 'warn',
      'no-continue': 'warn',
      'no-eval': 'error',
      'no-extra-bind': 'error',
      'no-extra-label': 'error',
      'no-floating-decimal': 'error',
      'no-implied-eval': 'error',
      'no-iterator': 'error',
      'no-labels': 'error',
      'no-lone-blocks': 'error',
      'no-loop-func': 'error',
      'no-multi-str': 'error',
      'no-new': 'warn',
      'no-new-func': 'error',
      'no-new-wrappers': 'error',
      'no-octal-escape': 'error',
      'no-proto': 'error',
      'no-return-assign': 'error',
      'no-return-await': 'error',
      'no-script-url': 'error',
      'no-sequences': 'error',
      'no-throw-literal': 'error',
      'no-unused-expressions': 'error',
      'no-useless-call': 'error',
      'no-useless-catch': 'error',
      'no-useless-concat': 'error',
      'no-useless-return': 'error',
      'no-void': 'error',
      'prefer-named-capture-group': 'off', // Disabled - simple regex groups are fine
      'prefer-object-has-own': 'warn',
      'prefer-object-spread': 'warn',
      'prefer-promise-reject-errors': 'warn',
      'prefer-regex-literals': 'warn',
      'radix': 'error',
      'require-unicode-regexp': 'off', // Disabled - not all regex needs unicode flag
      'vars-on-top': 'warn',
      'yoda': 'warn',
      'array-bracket-spacing': ['error', 'never'],
      'arrow-spacing': 'error',
      'block-spacing': 'error',
      'brace-style': 'error',
      'comma-dangle': ['error', 'always-multiline'],
      'comma-spacing': 'error',
      'comma-style': 'error',
      'computed-property-spacing': 'error',
      'eol-last': ['error', 'always'],
      'indent': ['error', 2, { SwitchCase: 1 }],
      'semi': ['error', 'always'],
      'quotes': ['error', 'single', { avoidEscape: true }],
      'object-curly-spacing': ['error', 'always'],
      'space-before-function-paren': ['error', 'never'],
      'arrow-parens': ['error', 'always'],
      'no-multiple-empty-lines': ['error', { max: 1, maxEOF: 1 }],
    },
  },
  // Environment-specific rules
  ...(process.env.NODE_ENV === 'development'
    ? [
      // Development rules - more permissive
      {
        files: ['**/*.js'],
        rules: {
          'no-console': 'warn', // Warn about console statements in development
          'no-debugger': 'warn',
          'no-unused-vars': 'warn', // Show warnings for unused variables
        },
      },
    ]
    : [
      // Production rules - more strict
      {
        files: ['**/*.js'],
        rules: {
          'no-console': ['error', { allow: ['warn', 'error'] }], // Only allow console.warn and console.error
          'no-debugger': 'error',
          'no-unused-vars': 'error',
        },
      },
    ]
  ),
  // Test files configuration
  {
    files: ['**/*.test.js'],
    env: {
      mocha: true,
    },
    rules: {
      'no-unused-expressions': 'off',
      'no-console': 'off',
    },
  },
  // Utility files configuration (more permissive)
  {
    files: ['app/static/js/utils/**/*.js'],
    rules: {
      'no-console': 'off',
      'no-unused-vars': 'off',
    },
  },
  // Debug files configuration (allow console)
  {
    files: ['app/static/js/utils/debug.js'],
    rules: {
      'no-console': 'off',
    },
  },
  // Services directory configuration
  {
    files: ['app/static/js/services/**/*.js'],
    rules: {
      'no-console': process.env.NODE_ENV === 'production' ? 'error' : 'off',
      'no-unused-vars': ['warn', {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
        caughtErrorsIgnorePattern: '^_',
        ignoreRestSiblings: true,
      }],
    },
  },
  // Utils directory configuration
  {
    files: ['app/static/js/utils/**/*.js'],
    rules: {
      'no-console': process.env.NODE_ENV === 'production' ? 'error' : 'off',
      'no-unused-vars': ['warn', {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
        caughtErrorsIgnorePattern: '^_',
        ignoreRestSiblings: true,
      }],
      // Allow case block scoped variables
      'no-case-declarations': 'off',
    },
  },
  // Google Maps related files (specific overrides)
  {
    files: [
      'app/static/js/utils/google-maps-*.js',
    ],
    rules: {
      'no-console': process.env.NODE_ENV === 'production' ? 'error' : 'off',
    },
  },
  // Components directory configuration
  {
    files: ['app/static/js/components/**/*.js'],
    rules: {
      'no-console': process.env.NODE_ENV === 'production' ? 'error' : 'off',
      'no-unused-vars': ['warn', {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
        caughtErrorsIgnorePattern: '^_',
        ignoreRestSiblings: true,
      }],
      // Allow case block scoped variables in switch statements
      'no-case-declarations': 'off',
    },
  },
  // Test files configuration
  {
    files: ['**/*-test.js', '**/*.test.js'],
    rules: {
      'no-console': 'off',
      'no-unused-vars': 'off',
      'no-dupe-class-members': 'off',
    },
  },
  // Pages directory configuration
  {
    files: ['app/static/js/pages/**/*.js'],
    rules: {
      'no-console': process.env.NODE_ENV === 'production' ? 'error' : 'off',
      'no-unused-vars': ['warn', {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
        caughtErrorsIgnorePattern: '^_',
        ignoreRestSiblings: true,
      }],
    },
  },
  // Ignore patterns
  {
    ignores: [
      '**/node_modules/**',
      '**/dist/**',
      '**/build/**',
      '**/coverage/**',
    ],
  },
];
