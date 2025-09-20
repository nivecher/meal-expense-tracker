/**
 * jQuery Form Submission Fix
 * 
 * Fixes jQuery overriding HTMLFormElement.prototype.submit
 * This ensures native form submission works properly
 */
(function() {
  'use strict';
    
  // Store the original submit method
  const originalSubmit = HTMLFormElement.prototype.submit;

  // Override the prototype to restore native functionality
  HTMLFormElement.prototype.submit = function() {
    // Create a temporary form and submit it using native method
    const tempForm = document.createElement('form');
    tempForm.method = this.method || 'GET';
    tempForm.action = this.action;
    tempForm.style.display = 'none';

    // Copy all form data
    const inputs = this.querySelectorAll('input, select, textarea');
    inputs.forEach((input) => {
      const newInput = input.cloneNode(true);
      tempForm.appendChild(newInput);
    });

    document.body.appendChild(tempForm);

    // Use the original native submit method
    originalSubmit.call(tempForm);

    document.body.removeChild(tempForm);
  };
})();
