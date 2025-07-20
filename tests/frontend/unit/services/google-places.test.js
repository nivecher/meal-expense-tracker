/**
 * @jest-environment jsdom
 */

import { GooglePlacesService } from '../../../../app/static/js/services/google-places';

// Mock the Google Maps API
global.google = {
  maps: {
    importLibrary: jest.fn().mockImplementation((libName) => {
      if (libName === 'places') {
        return Promise.resolve({
          Place: {
            searchByText: jest.fn().mockResolvedValue({
              places: [
                {
                  id: 'test-place-1',
                  displayName: { text: 'Test Restaurant' },
                  formattedAddress: '123 Test St',
                  location: { lat: 40.7128, lng: -74.0060 },
                  rating: 4.5,
                  userRatingCount: 100,
                  priceLevel: 'MODERATE',
                  types: ['restaurant', 'food'],
                  businessStatus: 'OPERATIONAL',
                  websiteURI: 'https://test-restaurant.com',
                  nationalPhoneNumber: '+1234567890',
                  utcOffsetMinutes: -240
                }
              ]
            }),
            fetchPlace: jest.fn().mockResolvedValue({
              id: 'test-place-1',
              displayName: { text: 'Test Restaurant' },
              formattedAddress: '123 Test St',
              location: { lat: 40.7128, lng: -74.0060 },
              rating: 4.5,
              userRatingCount: 100,
              priceLevel: 'MODERATE',
              types: ['restaurant', 'food'],
              businessStatus: 'OPERATIONAL',
              websiteURI: 'https://test-restaurant.com',
              nationalPhoneNumber: '+1234567890',
              utcOffsetMinutes: -240,
              photos: [
                {
                  name: 'photos/test-photo-1',
                  widthPx: 800,
                  heightPx: 600
                }
              ],
              regularOpeningHours: {
                weekdayDescriptions: [
                  'Monday: 9:00 AM – 10:00 PM',
                  'Tuesday: 9:00 AM – 10:00 PM',
                  'Wednesday: 9:00 AM – 10:00 PM',
                  'Thursday: 9:00 AM – 10:00 PM',
                  'Friday: 9:00 AM – 11:00 PM',
                  'Saturday: 10:00 AM – 11:00 PM',
                  'Sunday: 10:00 AM – 9:00 PM'
                ]
              },
              addressComponents: [
                {
                  longText: '123',
                  types: ['street_number']
                },
                {
                  longText: 'Test Street',
                  types: ['route']
                },
                {
                  longText: 'New York',
                  types: ['locality']
                },
                {
                  shortText: 'NY',
                  types: ['administrative_area_level_1']
                },
                {
                  longText: 'United States',
                  types: ['country']
                },
                {
                  longText: '10001',
                  types: ['postal_code']
                }
              ],
              iconBackgroundColor: '#FF9E67',
              primaryType: 'restaurant',
              viewport: {
                low: { lat: 40.7127, lng: -74.0061 },
                high: { lat: 40.7129, lng: -74.0059 }
              }
            })
          }
        });
      }
      return Promise.resolve({});
    })
  }
};

describe('GooglePlacesService', () => {
  let googlePlacesService;
  const apiKey = 'test-api-key';

  beforeEach(() => {
    googlePlacesService = new GooglePlacesService(apiKey);
    jest.clearAllMocks();
  });

  describe('searchNearby', () => {
    it('should search for nearby restaurants', async () => {
      const location = { lat: 40.7128, lng: -74.0060 };
      const options = { keyword: 'pizza', maxResults: 5 };

      const result = await googlePlacesService.searchNearby(location, options);

      expect(google.maps.importLibrary).toHaveBeenCalledWith('places');
      expect(result.results).toHaveLength(1);
      expect(result.results[0].name).toBe('Test Restaurant');
      expect(result.status).toBe('OK');
    });

    it('should handle no results', async () => {
      google.maps.importLibrary = jest.fn().mockResolvedValueOnce({
        Place: {
          searchByText: jest.fn().mockResolvedValue({ places: [] })
        }
      });

      const location = { lat: 40.7128, lng: -74.0060 };
      const result = await googlePlacesService.searchNearby(location);

      expect(result.results).toHaveLength(0);
      expect(result.status).toBe('ZERO_RESULTS');
    });
  });

  describe('getPlaceDetails', () => {
    it('should get details for a specific place', async () => {
      const placeId = 'test-place-1';
      const result = await googlePlacesService.getPlaceDetails(placeId);

      expect(google.maps.importLibrary).toHaveBeenCalledWith('places');
      expect(result).toBeDefined();
      expect(result.id).toBe('test-place-1');
      expect(result.name).toBe('Test Restaurant');
      expect(result.formatted_address).toBe('123 Test St');
      expect(result.phone).toBe('+1234567890');
      expect(result.website).toBe('https://test-restaurant.com');
      expect(result.rating).toBe(4.5);
      expect(result.photos).toHaveLength(1);
    });
  });

  describe('formatPlaceDetails', () => {
    it('should format place details correctly', async () => {
      const placeId = 'test-place-1';
      const result = await googlePlacesService.getPlaceDetails(placeId);

      // Check the formatted result
      expect(result).toMatchObject({
        id: 'test-place-1',
        name: 'Test Restaurant',
        formatted_address: '123 Test St',
        phone: '+1234567890',
        website: 'https://test-restaurant.com',
        rating: 4.5,
        user_ratings_total: 100,
        price_level: 'MODERATE',
        types: ['restaurant', 'food'],
        business_status: 'OPERATIONAL',
        location: {
          lat: 40.7128,
          lng: -74.006
        },
        photos: expect.any(Array),
        opening_hours: expect.any(Object)
      });
    });
  });
});
