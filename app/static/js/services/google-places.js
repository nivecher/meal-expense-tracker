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
    constructor(apiKey = '', options = {}) {
        this.apiKey = apiKey;
        this.radius = options.radius || 5000;
        this.types = options.types || ['restaurant'];
        this.initialized = false;
        this.placesLib = null;
        this.searchBox = null;

        // Bind methods to maintain proper 'this' context
        this.getPhotoUrl = this.getPhotoUrl.bind(this);
    }

    /**
     * Initialize the Google Places service
     * @param {string} [apiKey] - Optional API key to update
     * @returns {Promise<boolean>} - Whether initialization was successful
     */
    async init(apiKey) {
        if (this.initialized && !apiKey) return true;

        // Update API key if provided
        if (apiKey) {
            this.apiKey = apiKey;
        }

        if (!this.apiKey) {
            console.error('Google Places API key is required');
            return false;
        }

        try {
            // Import the Places library
            this.placesLib = await google.maps.importLibrary("places");
            this.initialized = true;
            return true;
        } catch (error) {
            console.error('Error initializing Google Places service:', error);
            return false;
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

        try {
            // Try v3 API method first if available
            if (typeof photo.getUrl === 'function') {
                try {
                    return photo.getUrl({ maxWidth, maxHeight });
                } catch (e) {
                    console.warn('Error using photo.getUrl():', e);
                }
            }

            // Try v2 API method if available
            if (window.google?.maps?.places?.PlacePhoto?.getUrl) {
                try {
                    return window.google.maps.places.PlacePhoto.getUrl({
                        maxWidth,
                        photoReference: photoRef
                    });
                } catch (e) {
                    console.warn('Error using PlacePhoto.getUrl():', e);
                }
            }

            // Fallback to direct URL construction if we have a reference and API key
            if (photoRef && this.apiKey) {
                try {
                    const photoUrl = `https://maps.googleapis.com/maps/api/place/photo?maxwidth=${maxWidth}&photoreference=${photoRef}&key=${this.apiKey}`;
                    // Verify the URL is valid
                    if (typeof URL !== 'undefined') {
                        new URL(photoUrl); // Will throw if invalid
                        return photoUrl;
                    }
                    return photoUrl;
                } catch (e) {
                    console.warn('Error constructing photo URL:', e);
                }
            }

            // If we have a reference but no API key, try without the key (may work for some public photos)
            if (photoRef) {
                const photoUrl = `https://maps.googleapis.com/maps/api/place/photo?maxwidth=${maxWidth}&photoreference=${photoRef}`;
                try {
                    if (typeof URL !== 'undefined') {
                        new URL(photoUrl);
                    }
                    return photoUrl;
                } catch (e) {
                    console.warn('Error with unauthenticated photo URL:', e);
                }
            }
        } catch (error) {
            console.error('Unexpected error generating photo URL:', error);
        }

        // Final fallback to placeholder
        return 'https://via.placeholder.com/400x300?text=No+Image+Available';
    }

    /**
     * Search for nearby restaurants
     * @param {Object} location - The center point for the search
     * @param {number} location.lat - Latitude
     * @param {number} location.lng - Longitude
     * @param {Object} options - Search options
     * @param {string} [options.keyword] - Optional keyword search
     * @param {number} [options.radius] - Search radius in meters
     * @param {number} [options.maxResults=20] - Maximum number of results to return
     * @returns {Promise<Array>} - Array of restaurant objects
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
                    lng: location.lng
                },
                maxResultCount: options.maxResults || 20,
                language: 'en-US',
                region: 'us',
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
                    'viewport'
                ]
            };

            // Use the new Place.searchByText API
            const { places } = await Place.searchByText(request);

            if (!places || places.length === 0) {
                return { results: [], status: 'ZERO_RESULTS' };
            }

            // Fetch additional details for each place
            const placesWithDetails = await Promise.all(
                places.map(async (place) => {
                    try {
                        // Fetch additional details for each place
                        const response = await place.fetchFields({
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
                                'viewport'
                            ]
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
                })
            );

            return {
                results: placesWithDetails.filter(Boolean),
                status: 'OK'
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
                placeId: placeId,
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
                    'viewport'
                ]
            });

            // Format the place details using our helper method
            return this.formatPlaceDetails(place);
        } catch (error) {
            console.error('Error fetching place details:', error);
            throw new Error('Failed to fetch place details');
        }
    }

    /**
     * Format place details into a consistent format
     * @param {Object} place - Place details from Google Places API
     * @returns {Object} - Formatted place details
     */
    formatPlaceDetails(place) {
        if (!place) {
            return null;
        }

        // Extract display name - handle both v2 and v3 API formats
        // For v3 API, displayName is an object with text and languageCode
        // For v2 API, name is a direct property
        const displayName = (place.displayName && typeof place.displayName === 'object')
            ? place.displayName.text
            : (place.name || place.displayName || 'Unknown');

        // Extract address - handle both v2 and v3 API formats
        let address = '';
        if (place.formattedAddress) {
            address = place.formattedAddress;
        } else if (place.formatted_address) {
            address = place.formatted_address;
        } else if (place.address_components) {
            // Try to construct address from components if available
            const components = place.address_components || [];
            const streetNumber = components.find(c => c.types?.includes('street_number'))?.longName || '';
            const route = components.find(c => c.types?.includes('route'))?.longName || '';
            const locality = components.find(c => c.types?.includes('locality'))?.longName || '';
            const adminArea = components.find(c => c.types?.includes('administrative_area_level_1'))?.longName || '';
            const postalCode = components.find(c => c.types?.includes('postal_code'))?.longName || '';
            const country = components.find(c => c.types?.includes('country'))?.longName || '';

            address = [
                [streetNumber, route].filter(Boolean).join(' '),
                locality,
                [adminArea, postalCode].filter(Boolean).join(' '),
                country
            ].filter(Boolean).join(', ');
        }

        // Extract location
        let location = null;
        if (place.location) {
            // Handle both v3 (lat/lng as properties) and v2 (lat()/lng() methods) formats
            const lat = place.location.lat || (typeof place.location.latitude === 'function'
                ? place.location.latitude()
                : place.location.latitude);
            const lng = place.location.lng || (typeof place.location.longitude === 'function'
                ? place.location.longitude()
                : place.location.longitude);

            if (lat !== undefined && lng !== undefined) {
                location = { lat, lng };
            }
        } else if (place.geometry?.location) {
            const geoLoc = place.geometry.location;
            const lat = typeof geoLoc.lat === 'function' ? geoLoc.lat() : geoLoc.lat;
            const lng = typeof geoLoc.lng === 'function' ? geoLoc.lng() : geoLoc.lng;

            if (lat !== undefined && lng !== undefined) {
                location = { lat, lng };
            }
        }

        // Extract photos with robust error handling
        const photos = [];
        try {
            if (Array.isArray(place.photos) && place.photos.length > 0) {
                place.photos.forEach(photo => {
                    try {
                        // Skip if photo is not an object or is null/undefined
                        if (!photo || typeof photo !== 'object') {
                            console.warn('Skipping invalid photo object:', photo);
                            return;
                        }

                        // Try to get photo reference from different possible locations
                        const photoRef = photo.photo_reference ||
                                      (photo.name ? photo.name.split('/').pop() : null) ||
                                      'unknown';

                        // Use the instance method for getting photo URLs
                        const getUrl = (options = {}) => this.getPhotoUrl(photo, options);

                        // Add the photo to the results
                        photos.push({
                            photo_reference: photoRef,
                            width: photo.width || 400,
                            height: photo.height || 300,
                            getUrl: getUrl
                        });

                    } catch (error) {
                        console.error('Error processing individual photo:', error);
                    }
                });
            }
        } catch (error) {
            console.error('Error processing photos:', error);
        }

        // Get phone number - handle both v3 (nationalPhoneNumber) and v2 (formatted_phone_number) formats
        const phone = place.nationalPhoneNumber || place.formatted_phone_number || '';

        // Get website - handle both v3 (websiteURI) and v2 (website) formats
        const website = place.websiteURI || place.website || '';

        // Get opening hours
        const opening_hours = place.regularOpeningHours || place.opening_hours;

        // Get rating info
        const rating = place.rating || 0;
        const user_ratings_total = place.userRatingCount || place.user_ratings_total || 0;

        // Get price level - handle both v3 (priceLevel) and v2 (price_level) formats
        const price_level = place.priceLevel || place.price_level || 0;

        // Get types - ensure it's always an array
        const types = Array.isArray(place.types) ? place.types : [];

        // Get business status - default to UNKNOWN if not provided
        const business_status = place.businessStatus || place.business_status || 'UNKNOWN';

        // Get URL - handle both v3 (googleMapsUri) and v2 (url) formats
        const url = place.googleMapsUri || place.url || '';

        // Format the result
        return {
            id: place.place_id || place.id || '',
            name: displayName,
            formatted_address: address,
            phone,
            website,
            opening_hours,
            rating,
            user_ratings_total,
            price_level,
            types,
            location,
            photos,
            business_status,
            url,
            // Include the raw place object for debugging
            _raw: place
        };
    }
}

// Export a singleton instance
// Initialize with empty API key - it should be set via init method
export const googlePlacesService = new GooglePlacesService('');
