import React from 'react';

function FormValidator() {
  const validateEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const validatePhone = (phone) => {
    const phoneRegex = /^\d{10,}$/;
    return phoneRegex.test(phone.replace(/\D/g, ''));
  };

  const validatePolicyId = (policyId) => {
    return policyId.trim().length >= 5;
  };

  const validateDescription = (description) => {
    return description.trim().length >= 10;
  };

  const validateDate = (date) => {
    const selectedDate = new Date(date);
    const today = new Date();
    return selectedDate <= today;
  };

  return {
    validateEmail,
    validatePhone,
    validatePolicyId,
    validateDescription,
    validateDate,
  };
}

export default FormValidator;
