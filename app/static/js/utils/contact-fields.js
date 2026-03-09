export function initializeIntlPhoneInput(inputId, initialCountry = 'us') {
  const input = document.getElementById(inputId);
  if (!(input instanceof HTMLInputElement)) {
    return null;
  }

  const iti =
    typeof window.intlTelInput === 'function'
      ? window.intlTelInput(input, {
        initialCountry,
        nationalMode: false,
        autoPlaceholder: 'aggressive',
        separateDialCode: false,
        utilsScript: 'https://cdn.jsdelivr.net/npm/intl-tel-input@25.3.0/build/js/utils.js',
      })
      : null;

  function getInternationalFormatConstant() {
    return (
      window.intlTelInputUtils?.numberFormat?.INTERNATIONAL ||
      window.intlTelInput?.utils?.numberFormat?.INTERNATIONAL ||
      null
    );
  }

  function buildCandidateNumber(rawValue) {
    const trimmedValue = rawValue.trim();
    if (!trimmedValue) {
      return '';
    }

    const digits = trimmedValue.replace(/\D/g, '');
    if (!digits) {
      return '';
    }

    if (trimmedValue.startsWith('+')) {
      return `+${digits}`;
    }

    const selectedCountry = iti?.getSelectedCountryData?.();
    const dialCode = String(selectedCountry?.dialCode || '').replace(/\D/g, '');
    if (!dialCode && initialCountry.toLowerCase() === 'us') {
      if (digits.length === 10) {
        return `+1${digits}`;
      }
      if (digits.length === 11 && digits.startsWith('1')) {
        return `+${digits}`;
      }
    }

    if (!dialCode) {
      return trimmedValue.startsWith('+') ? trimmedValue : `+${digits}`;
    }

    if (digits.startsWith(dialCode)) {
      return `+${digits}`;
    }

    return `+${dialCode}${digits}`;
  }

  function formatDisplayValue() {
    const e164Value = iti?.getNumber?.() || buildCandidateNumber(input.value);
    const digits = e164Value.replace(/\D/g, '');
    const selectedCountry = iti?.getSelectedCountryData?.();
    const iso2 = String(selectedCountry?.iso2 || '').toLowerCase();

    if ((iso2 === 'us' || iso2 === 'ca' || !iso2) && digits.length === 11 && digits.startsWith('1')) {
      return `+1 (${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`;
    }

    const internationalFormat = getInternationalFormatConstant();
    return internationalFormat && iti?.getNumber ? iti.getNumber(internationalFormat) : e164Value;
  }

  function isManuallyValidNumber(candidateNumber) {
    const digits = String(candidateNumber || '').replace(/\D/g, '');
    return digits.length === 10 || (digits.length === 11 && digits.startsWith('1'));
  }

  function syncValue() {
    const rawValue = input.value.trim();
    if (!rawValue) {
      input.value = '';
      input.setCustomValidity('');
      return;
    }

    const candidateNumber = buildCandidateNumber(rawValue);
    if (candidateNumber) {
      iti?.setNumber?.(candidateNumber);
    }

    if ((iti?.isValidNumber?.() ?? false) || isManuallyValidNumber(candidateNumber)) {
      input.value = formatDisplayValue();
      input.setCustomValidity('');
      return;
    }
    input.value = rawValue;
    input.setCustomValidity('Please enter a valid phone number');
  }

  input.addEventListener('blur', syncValue);
  input.addEventListener('countrychange', () => {
    input.setCustomValidity('');
  });
  input.addEventListener('input', () => {
    input.setCustomValidity('');
  });

  return { input, iti, syncValue };
}

export function attachIntlPhoneFormatting(formSelector, phoneFieldIds) {
  const phoneControls = phoneFieldIds.map((id) => initializeIntlPhoneInput(id)).filter(Boolean);
  if (!phoneControls.length) {
    return [];
  }

  const form = document.querySelector(formSelector);
  if (form instanceof HTMLFormElement) {
    form.addEventListener('submit', (event) => {
      phoneControls.forEach((control) => {
        control.syncValue();
      });
      if (!form.checkValidity()) {
        event.preventDefault();
        form.reportValidity();
      }
    });
  }

  phoneControls.forEach((control) => {
    if (control.input.value.trim()) {
      control.syncValue();
    }
  });

  return phoneControls;
}
