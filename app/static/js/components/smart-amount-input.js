/**
 * Smart Amount Input Component
 *
 * Automatically handles decimal placement for amount inputs:
 * - User types "789" → displays as "$7.89"
 * - User types "7.89" → displays as "$7.89"
 * - User types "7890" → displays as "$78.90"
 *
 * This simplifies data entry by assuming the last two digits are cents
 * unless the user explicitly includes a decimal point.
 */

/**
 * Initialize smart amount input behavior for an input field
 * @param {HTMLInputElement} input - The amount input element
 */
export function initSmartAmountInput(input) {
  if (!input) {
    console.warn('Smart amount input: Invalid input element');
    return;
  }

  // Force the input to be type="text" for proper smart amount handling
  input.type = 'text';

  // Store original value for comparison
  let lastValidValue = input.value || '';

  // Track if user is actively typing to avoid interfering with programmatic changes
  let isUserTyping = false;
  let typingTimeout = null;

  /**
   * Convert numeric string to proper decimal format (like Quicken)
   * @param {string} value - Raw input value
   * @returns {string} Formatted value with decimal
   */
  function formatAmount(value) {
    // Remove all non-numeric characters except decimal point
    const cleanValue = value.replace(/[^\d.]/g, '');

    // Handle empty or invalid input
    if (!cleanValue || cleanValue === '.') {
      return '';
    }

    // If already has decimal point, just validate it
    if (cleanValue.includes('.')) {
      const parts = cleanValue.split('.');
      if (parts.length > 2) {
        // Multiple decimal points - return previous valid value
        return lastValidValue;
      }

      const integerPart = parts[0] || '';
      const decimalPart = parts[1] || '';

      // Limit decimal part to 2 digits
      const limitedDecimal = decimalPart.substring(0, 2);

      return integerPart + (limitedDecimal ? '.' + limitedDecimal : '');
    }

    // No decimal point - assume it's cents (like Quicken)
    const numericValue = cleanValue;

    // Handle edge cases
    if (numericValue === '0') {
      return '0.00';
    }

    // Simple rule: always place decimal before last 2 digits
    // 5 → 0.05, 50 → 0.50, 789 → 7.89, 1234 → 12.34
    if (numericValue.length === 1) {
      return `0.0${numericValue}`;
    } else if (numericValue.length === 2) {
      return `0.${numericValue}`;
    } else {
      // 3+ digits: place decimal before last 2 digits
      const integerPart = numericValue.slice(0, -2);
      const centsPart = numericValue.slice(-2);
      return `${integerPart}.${centsPart}`;
    }
  }

  /**
   * Handle input event for real-time formatting
   */
  function handleInput(event) {
    isUserTyping = true;

    // Clear any existing timeout
    if (typingTimeout) {
      clearTimeout(typingTimeout);
    }

    // Set timeout to detect when user stops typing
    typingTimeout = setTimeout(() => {
      isUserTyping = false;
    }, 500);

    const input = event.target;
    const cursorPosition = input.selectionStart;
    const rawValue = input.value;

    // Format the amount
    const formattedValue = formatAmount(rawValue);

    // Only update if the formatted value is different
    if (formattedValue !== rawValue && formattedValue !== lastValidValue) {
      input.value = formattedValue;
      lastValidValue = formattedValue;

                // Try to maintain cursor position (only for text inputs)
                if (input.type === 'text' || input.type === 'tel') {
                    try {
                        // If cursor was at the end, keep it at the end
                        if (cursorPosition >= rawValue.length) {
                            input.setSelectionRange(formattedValue.length, formattedValue.length);
                        } else {
                            // Otherwise, try to maintain relative position
                            const relativePosition = cursorPosition / rawValue.length;
                            const newPosition = Math.round(relativePosition * formattedValue.length);
                            input.setSelectionRange(newPosition, newPosition);
                        }
                    } catch (e) {
                        // Ignore cursor positioning errors for number inputs
                        console.debug('Could not set cursor position:', e.message);
                    }
                }
    } else if (formattedValue !== lastValidValue) {
      lastValidValue = formattedValue;
    }
  }

  /**
   * Handle blur event to ensure final formatting
   */
  function handleBlur(event) {
    const input = event.target;
    const formattedValue = formatAmount(input.value);

    if (formattedValue !== input.value) {
      input.value = formattedValue;
      lastValidValue = formattedValue;
    }

    // Validate minimum amount
    const amount = parseFloat(formattedValue);
    if (amount > 0 && amount < 0.01) {
      // If amount is less than 1 cent, set to minimum
      input.value = '0.01';
      lastValidValue = '0.01';
    }
  }

  /**
   * Handle keydown to prevent invalid characters
   */
  function handleKeydown(event) {
    // Allow: backspace, delete, tab, escape, enter, home, end, left, right, up, down
    if ([8, 9, 27, 13, 46, 35, 36, 37, 38, 39, 40].includes(event.keyCode)) {
      return;
    }

    // Allow Ctrl+A, Ctrl+C, Ctrl+V, Ctrl+X
    if (event.ctrlKey && [65, 67, 86, 88].includes(event.keyCode)) {
      return;
    }

    // Allow only digits and decimal point
    const char = String.fromCharCode(event.keyCode);
    if (!/\d/.test(char) && char !== '.') {
      event.preventDefault();
      return;
    }

    // Prevent multiple decimal points
    if (char === '.' && input.value.includes('.')) {
      event.preventDefault();
      return;
    }
  }

  /**
   * Handle paste events to format pasted content
   */
  function handlePaste(event) {
    // Allow default paste behavior first
    setTimeout(() => {
      const input = event.target;
      const formattedValue = formatAmount(input.value);

      if (formattedValue !== input.value) {
        input.value = formattedValue;
        lastValidValue = formattedValue;
      }
    }, 0);
  }

  // Add event listeners
  input.addEventListener('input', handleInput);
  input.addEventListener('blur', handleBlur);
  input.addEventListener('keydown', handleKeydown);
  input.addEventListener('paste', handlePaste);

  // Store reference to cleanup function
  input._smartAmountCleanup = function() {
    input.removeEventListener('input', handleInput);
    input.removeEventListener('blur', handleBlur);
    input.removeEventListener('keydown', handleKeydown);
    input.removeEventListener('paste', handlePaste);

    if (typingTimeout) {
      clearTimeout(typingTimeout);
    }
  };

  // Initialize with current value if it exists
  if (input.value) {
    const formattedValue = formatAmount(input.value);
    if (formattedValue !== input.value) {
      input.value = formattedValue;
      lastValidValue = formattedValue;
    }
  }
}

/**
 * Initialize smart amount input for all amount fields on the page
 */
export function initSmartAmountInputs() {
  // Find all amount input fields
  const amountInputs = document.querySelectorAll('input[name="amount"], input[id*="amount"], input[data-smart-amount]');

  amountInputs.forEach(input => {
    initSmartAmountInput(input);
  });
}

/**
 * Cleanup smart amount input behavior
 * @param {HTMLInputElement} input - The input element to cleanup
 */
export function cleanupSmartAmountInput(input) {
  if (input && input._smartAmountCleanup) {
    input._smartAmountCleanup();
    delete input._smartAmountCleanup;
  }
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initSmartAmountInputs);
