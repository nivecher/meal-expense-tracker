/**
 * Simple cuisine service - single source of truth for cuisine data
 * Following TIGER principles: Safety, Performance, Developer Experience
 */

class CuisineService {
  constructor() {
    this.cuisineData = null;
    this.googlePlacesMapping = null;
  }

  /**
   * Load cuisine data from API
   * @returns {Promise<Object>} Cuisine data with names, colors, icons, and mapping
   */
  async loadCuisineData() {
    if (this.cuisineData) {
      return this.cuisineData;
    }

    try {
      const response = await fetch('/api/v1/cuisines');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      this.cuisineData = result.data.cuisines;
      this.googlePlacesMapping = result.data.google_places_mapping;

      return result.data;
    } catch (error) {
      console.error('Failed to load cuisine data:', error);
      // Fallback to minimal data
      this.cuisineData = [
        { name: "Other", color: "#6b7280", icon: "question" }
      ];
      this.googlePlacesMapping = {};
      return { cuisines: this.cuisineData, google_places_mapping: this.googlePlacesMapping };
    }
  }

  /**
   * Get cuisine name from Google Places types
   * @param {Array<string>} types - Google Places types array
   * @returns {string} Mapped cuisine name or 'Other'
   */
  mapGooglePlacesToCuisine(types) {
    if (!types || !Array.isArray(types)) {
      return 'Other';
    }

    // Check each type against mapping
    for (const type of types) {
      if (this.googlePlacesMapping && this.googlePlacesMapping[type]) {
        return this.googlePlacesMapping[type];
      }
    }

    return 'Other';
  }

  /**
   * Get cuisine data by name
   * @param {string} name - Cuisine name
   * @returns {Object|null} Cuisine data or null
   */
  getCuisineData(name) {
    if (!this.cuisineData || !name) {
      return null;
    }

    return this.cuisineData.find(cuisine =>
      cuisine.name.toLowerCase() === name.toLowerCase()
    ) || { name: "Other", color: "#6b7280", icon: "question" };
  }

  /**
   * Get all cuisine names for dropdowns
   * @returns {Array<string>} Array of cuisine names
   */
  getCuisineNames() {
    return this.cuisineData ? this.cuisineData.map(c => c.name) : ['Other'];
  }
}

// Export singleton instance
export const cuisineService = new CuisineService();
