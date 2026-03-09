import { attachIntlPhoneFormatting } from '../utils/contact-fields.js';

document.addEventListener('DOMContentLoaded', () => {
  attachIntlPhoneFormatting('form', ['membership_phone']);

  const emailFields = ['membership_email']
    .map((id) => document.getElementById(id))
    .filter((field) => field instanceof HTMLInputElement);

  emailFields.forEach((field) => {
    field.addEventListener('input', () => {
      field.setCustomValidity('');
    });
    field.addEventListener('blur', () => {
      if (!field.value.trim()) {
        field.setCustomValidity('');
        return;
      }
      if (field.validity.typeMismatch) {
        field.setCustomValidity('Please enter a valid email address');
      } else {
        field.setCustomValidity('');
      }
    });
  });

  const useDefaultPhone = document.getElementById('use_default_phone');
  const membershipPhone = document.getElementById('membership_phone');
  if (useDefaultPhone instanceof HTMLInputElement && membershipPhone instanceof HTMLInputElement) {
    useDefaultPhone.addEventListener('change', () => {
      membershipPhone.readOnly = useDefaultPhone.checked;
      membershipPhone.classList.toggle('bg-light', useDefaultPhone.checked);
    });
    membershipPhone.readOnly = useDefaultPhone.checked;
    membershipPhone.classList.toggle('bg-light', useDefaultPhone.checked);
  }

  const useDefaultEmail = document.getElementById('use_default_email');
  const membershipEmail = document.getElementById('membership_email');
  if (useDefaultEmail instanceof HTMLInputElement && membershipEmail instanceof HTMLInputElement) {
    useDefaultEmail.addEventListener('change', () => {
      membershipEmail.readOnly = useDefaultEmail.checked;
      membershipEmail.classList.toggle('bg-light', useDefaultEmail.checked);
    });
    membershipEmail.readOnly = useDefaultEmail.checked;
    membershipEmail.classList.toggle('bg-light', useDefaultEmail.checked);
  }

  const form = document.querySelector('form');
  if (!(form instanceof HTMLFormElement)) {
    return;
  }

  form.addEventListener('submit', (event) => {
    emailFields.forEach((field) => {
      if (field.validity.typeMismatch) {
        field.setCustomValidity('Please enter a valid email address');
      }
    });
    if (!form.checkValidity()) {
      event.preventDefault();
      form.reportValidity();
    }
  });
});
