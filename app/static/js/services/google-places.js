/**
 * Google Places Service
 *
 * Handles interactions with the Google Places API for searching and retrieving
 * restaurant information.
 */

export class GooglePlacesService {
  /**
   * Initialize the Google Places service
   * @param {string} apiKey - Google Maps API key
   * @param {Object} options - Configuration options
   * @param {number} [options.radius=5000] - Default search radius in meters
   * @param {string[]} [options.types=['restaurant']] - Place types to search for
   */
  // No instance fields needed for static methods

  constructor(apiKey = '', options = {}) {
    this.apiKey = apiKey;
    this.radius = options.radius || 5000;
    this.types = options.types || ['restaurant'];
    this.initialized = false;
    this.placesLib = null;
    this.searchBox = null;

    // Bind public methods to maintain correct 'this' context
    this.getPhotoUrl = this.getPhotoUrl.bind(this);
    this.searchNearby = this.searchNearby.bind(this);
  }

  /**
     * Initialize the Google Places service
     * @param {string} [apiKey] - Optional API key to update
     * @returns {Promise<boolean>} - Whether initialization was successful
     */
  /**
   * Load the Google Maps Places library
   * @private
   */
  async #loadPlacesLibrary() {
    try {
      this.placesLib = await google.maps.importLibrary('places');
      return true;
    } catch (error) {
      console.error('Error loading Google Places library:', error);
      return false;
    }
  }

  /**
   * Initialize the Google Places service
   * @param {string} [apiKey] - Optional API key to update
   * @returns {Promise<boolean>} Resolves with true if initialization was successful
   * @throws {Error} If API key is missing or initialization fails
   */
  async init(apiKey) {
    if (this.initialized && !apiKey) {
      return true;
    }

    // Update API key if provided
    if (apiKey) {
      this.apiKey = apiKey;
    }

    if (!this.apiKey) {
      console.error('Google Places API key is required');
      return false;
    }

    const loaded = await this.#loadPlacesLibrary();
    this.initialized = loaded;
    return loaded;
  }

  /**
   * Get photo URL using v3 API method
   * @private
   */
  static #getV3PhotoUrl(photo, maxWidth, maxHeight) {
    if (typeof photo.getUrl !== 'function') {
      return null;
    }
    try {
      return photo.getUrl({ maxWidth, maxHeight });
    } catch (e) {
      console.warn('Error using photo.getUrl():', e);
      return null;
    }
  }

  /**
   * Get photo URL using v2 API method
   * @private
   */
  static #getV2PhotoUrl(photoRef, maxWidth) {
    if (!window.google?.maps?.places?.PlacePhoto?.getUrl) {
      return null;
    }
    try {
      return window.google.maps.places.PlacePhoto.getUrl({
        maxWidth,
        photoReference: photoRef,
      });
    } catch (e) {
      console.warn('Error using PlacePhoto.getUrl():', e);
      return null;
    }
  }

  /**
   * Get photo URL using direct API call
   * @private
   */
  #getDirectPhotoUrl(photoRef, maxWidth) {
    if (!photoRef || !this.apiKey) {
      return null;
    }
    try {
      const photoUrl = `https://maps.googleapis.com/maps/api/place/photo?maxwidth=${maxWidth}&photoreference=${photoRef}&key=${this.apiKey}`;
      // Verify the URL is valid
      // Using URL constructor for validation only
      const validatedUrl = new URL(photoUrl);
      if (!validatedUrl) return null;
      return photoUrl;
    } catch (e) {
      console.warn('Error constructing photo URL:', e);
      return null;
    }
  }

  /**
   * Get a photo URL with proper error handling
   * @param {Object} photo - Photo object from Google Places API
   * @param {Object} [options] - Options for the photo
   * @param {number} [options.maxWidth=400] - Maximum width of the photo
   * @param {number} [options.maxHeight=300] - Maximum height of the photo
   * @returns {string} - Photo URL or placeholder
   */
  getPhotoUrl(photo, options = {}) {
    if (!photo) {
      return 'https://via.placeholder.com/400x300?text=No+Image+Available';
    }

    const maxWidth = options.maxWidth || 400;
    const maxHeight = options.maxHeight || 300;
    const photoRef = photo.photo_reference || (photo.name ? photo.name.split('/').pop() : null);

    // Try different methods to get the photo URL
    const url = GooglePlacesService.#getV3PhotoUrl(photo, maxWidth, maxHeight) ||
                GooglePlacesService.#getV2PhotoUrl(photoRef, maxWidth) ||
                this.#getDirectPhotoUrl(photoRef, maxWidth);

    return url || `https://via.placeholder.com/${maxWidth}x${maxHeight}?text=No+Image+Available`;
  }

  /**
   * Get the fields to request for place details
   * @private
   * @returns {string[]} - Array of field names
   */
  static #getPlaceDetailFields() {
    return [
      'id',
      'displayName',
      'formattedAddress',
      'location',
      'rating',
      'userRatingCount',
      'priceLevel',
      'types',
      'photos',
      'regularOpeningHours',
      'businessStatus',
      'websiteURI',
      'nationalPhoneNumber',
      'addressComponents',
      'iconBackgroundColor',
      'primaryType',
      'utcOffsetMinutes',
      'viewport',
    ];
  }

  /**
   * Fetch additional details for a place
   * @private
   * @param {Object} place - The place to fetch details for
   * @returns {Promise<Object>} - The formatted place details
   */
  async #fetchPlaceDetails(place) {
    try {
      const response = await place.fetchFields({
        fields: GooglePlacesService.#getPlaceDetailFields(),
      });

      // The API returns the place in a 'place' property
      const placeDetails = response.place || response;
      console.log('Place details response:', placeDetails);

      const formattedDetails = this.formatPlaceDetails(placeDetails);
      console.log('Formatted details:', formattedDetails);

      return formattedDetails;
    } catch (error) {
      console.error('Error fetching place details:', error);
      return null;
    }
  }

  /**
   * Search for nearby restaurants
   * @param {Object} location - The center point for the search
   * @param {number} location.lat - Latitude
   * @param {number} location.lng - Longitude
   * @param {Object} [options] - Search options
   * @param {string} [options.keyword] - Optional keyword search
   * @param {number} [options.radius] - Search radius in meters
   * @param {number} [options.maxResults=20] - Maximum number of results to return
   * @returns {Promise<{results: Array, status: string}>} - Search results with status
   * @throws {Error} If the service fails to initialize or search
   */
  async searchNearby(location, options = {}) {
    if (!this.initialized) {
      const initialized = await this.init();
      if (!initialized) {
        throw new Error('Failed to initialize Google Places service');
      }
    }

    try {
      const { Place } = this.placesLib;

      // Create a text search request
      const request = {
        textQuery: options.keyword ? `${options.keyword} restaurant` : 'restaurant',
        locationBias: {
          lat: location.lat,
          lng: location.lng,
        },
        maxResultCount: options.maxResults || 20,
        language: 'en-US',
        region: 'us',
        fields: GooglePlacesService.#getPlaceDetailFields(),
      };

      // Use the new Place.searchByText API
      const { places } = await Place.searchByText(request);

      if (!places || places.length === 0) {
        return { results: [], status: 'ZERO_RESULTS' };
      }

      // Fetch additional details for each place
      const placesWithDetails = await Promise.all(
        places.map((place) => this.#fetchPlaceDetails(place)),
      );

      return {
        results: placesWithDetails.filter(Boolean),
        status: 'OK',
      };
    } catch (error) {
      console.error('Error searching for nearby restaurants:', error);
      throw error;
    }
  }

  /**
     * Get details for a specific place
     * @param {string} placeId - Google Place ID
     * @returns {Promise<Object>} - Place details
     */
  /**
   * Extract display name from place object
   * @private
   * @param {Object} place - Place object from Google Places API
   * @returns {string} - Extracted display name
   */
  static #extractDisplayName(place) {
    if (!place) return 'Unknown';
    return (place.displayName && typeof place.displayName === 'object')
      ? place.displayName.text
      : (place.name || place.displayName || 'Unknown');
  }

  /**
   * Extract address from place object
   * @private
   */
  static #extractAddress(place) {
    if (place.formattedAddress) return place.formattedAddress;
    if (place.formatted_address) return place.formatted_address;
    if (!place.address_components) return '';

    const components = place.address_components || [];
    const streetNumber = components.find((c) => c.types?.includes('street_number'))?.longName || '';
    const route = components.find((c) => c.types?.includes('route'))?.longName || '';
    const locality = components.find((c) => c.types?.includes('locality'))?.longName || '';
    const adminArea = components.find((c) => c.types?.includes('administrative_area_level_1'))?.longName || '';
    const postalCode = components.find((c) => c.types?.includes('postal_code'))?.longName || '';
    const country = components.find((c) => c.types?.includes('country'))?.longName || '';

    return [
      [streetNumber, route].filter(Boolean).join(' '),
      locality,
      [adminArea, postalCode].filter(Boolean).join(' '),
      country,
    ].filter(Boolean).join(', ');
  }

  /**
   * Extract location from place object
   * @private
   */
  static #extractLocation(place) {
    if (!place) return null;

    let lat;
    let lng;

    if (place.location) {
      // Handle both v3 (lat/lng as properties) and v2 (lat()/lng() methods) formats
      lat = place.location.lat || (typeof place.location.latitude === 'function'
        ? place.location.latitude()
        : place.location.latitude);
      lng = place.location.lng || (typeof place.location.longitude === 'function'
        ? place.location.longitude()
        : place.location.longitude);
    } else if (place.geometry?.location) {
      const geoLoc = place.geometry.location;
      lat = typeof geoLoc.lat === 'function' ? geoLoc.lat() : geoLoc.lat;
      lng = typeof geoLoc.lng === 'function' ? geoLoc.lng() : geoLoc.lng;
    }

    return (lat !== undefined && lng !== undefined) ? { lat, lng } : null;
  }

  /**
   * Extract photos from place object
   * @private
   */
  #extractPhotos(place) {
    const photos = [];
    if (!Array.isArray(place?.photos)) {
      return photos;
    }

    for (const photo of place.photos) {
      try {
        if (!photo || typeof photo !== 'object') {
          continue;
        }

        const photoRef = photo.photo_reference
          || (photo.name ? photo.name.split('/').pop() : null);

        if (photoRef) {
          photos.push({
            photoReference: photoRef,
            width: photo.width || 400,
            height: photo.height || 300,
            getUrl: (options = {}) => this.getPhotoUrl(photo, options),
          });
        }
      } catch (error) {
        console.error('Error processing individual photo:', error);
      }
    }

    return photos;
  }

  /**
   * Format place details into a consistent format
   * @param {Object} place - Place details from Google Places API
   * @returns {Object|null} - Formatted place details or null if invalid
   */
  formatPlaceDetails(place) {
    if (!place) return null;

    // Extract basic information
    const displayName = GooglePlacesService.#extractDisplayName(place);
    const address = GooglePlacesService.#extractAddress(place);
    const location = GooglePlacesService.#extractLocation(place);
    const photos = this.#extractPhotos(place);

    // Extract contact and business information
    const phone = place.nationalPhoneNumber || place.formatted_phone_number || '';
    const website = place.websiteURI || place.website || '';
    const openingHours = place.regularOpeningHours || place.opening_hours;
    const rating = place.rating || 0;
    const userRatingsTotal = place.userRatingCount || place.user_ratings_total || 0;
    const priceLevel = place.priceLevel || place.price_level || 0;
    const types = Array.isArray(place.types) ? place.types : [];
    const businessStatus = place.businessStatus || place.business_status || 'UNKNOWN';

    // Format the result with camelCase property names
    return {
      id: place.place_id || place.id || '',
      name: displayName,
      formattedAddress: address,
      phone,
      website,
      openingHours,
      rating,
      userRatingsTotal,
      priceLevel,
      types,
      location,
      photos,
      businessStatus,
      // Include the raw place object for debugging
      _raw: place,
    };
  }

  /**
   * Get details for a specific place
   * @param {string} placeId - Google Place ID
   * @returns {Promise<Object>} - Resolves with place details
   * @throws {Error} If the service fails to initialize or fetch details
   */
  async getPlaceDetails(placeId) {
    if (!this.initialized) {
      const initialized = await this.init();
      if (!initialized) {
        throw new Error('Failed to initialize Google Places service');
      }
    }

    try {
      const { Place } = this.placesLib;

      // Fetch place details using the new Place API
      const place = await Place.fetchPlace({
        placeId,
        requestedLanguage: 'en',
        requestedRegion: 'US',
        fields: [
          'id',
          'displayName',
          'formattedAddress',
          'location',
          'rating',
          'userRatingCount',
          'priceLevel',
          'types',
          'photos',
          'regularOpeningHours',
          'businessStatus',
          'websiteURI',
          'nationalPhoneNumber',
          'addressComponents',
          'iconBackgroundColor',
          'primaryType',
          'utcOffsetMinutes',
          'viewport',
        ],
      });

      // Format the place details using our helper method
      return this.formatPlaceDetails(place);
    } catch (error) {
      console.error('Error fetching place details:', error);
      throw error;
    }
  }
}

// Export a singleton instance
// Initialize with empty API key - it should be set via init method
export const googlePlacesService = new GooglePlacesService('');
