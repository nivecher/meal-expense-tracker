/**
 * Promisified Geolocation
 *
 * @param {object} options - Geolocation options
 * @returns {Promise<GeolocationPosition>} - A promise that resolves with the position or rejects with an error
 */
export const getCurrentPosition = (options) =>
  new Promise((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(resolve, reject, options);
  });
