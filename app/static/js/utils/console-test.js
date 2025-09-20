/**
 * Console Test Utility
 * 
 * Tests browser console functionality and error handling
 * 
 * @version 1.0.0
 * @author Meal Expense Tracker Team
 */

class ConsoleTest {
  constructor() {
    this.testResults = [];
    this.init();
  }

  init() {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.runTests());
    } else {
      this.runTests();
    }
  }

  runTests() {
    console.log('🧪 Running console tests...');
    
    this.testConsoleMethods();
    this.testErrorHandling();
    this.testPerformance();
    this.testFiltering();
    
    this.displayResults();
  }

  testConsoleMethods() {
    try {
      console.log('✅ Console.log working');
      console.warn('⚠️ Console.warn working');
      console.error('❌ Console.error working');
      console.info('ℹ️ Console.info working');
      
      this.testResults.push({
        test: 'Console Methods',
        status: 'PASS',
        message: 'All console methods working correctly',
      });
    } catch {
      this.testResults.push({
        test: 'Console Methods',
        status: 'FAIL',
        message: `Console methods failed: ${error.message}`,
      });
    }
  }

  testErrorHandling() {
    try {
      // Test if error handler is available
      if (window.errorHandler) {
        this.testResults.push({
          test: 'Error Handler',
          status: 'PASS',
          message: 'Error handler is loaded and available',
        });
      } else {
        this.testResults.push({
          test: 'Error Handler',
          status: 'SKIP',
          message: 'Error handler not loaded (may be disabled)',
        });
      }

      // Test error stats
      if (window.getErrorStats) {
        const stats = window.getErrorStats();
        this.testResults.push({
          test: 'Error Stats',
          status: 'PASS',
          message: `Error stats available: ${stats.totalErrors} errors recorded`,
        });
      } else {
        this.testResults.push({
          test: 'Error Stats',
          status: 'SKIP',
          message: 'Error stats not available (error handler disabled)',
        });
      }
    } catch {
      this.testResults.push({
        test: 'Error Handling',
        status: 'FAIL',
        message: `Error handling test failed: ${error.message}`,
      });
    }
  }

  testPerformance() {
    try {
      // Test if performance monitoring is working
      if (performance && performance.now) {
        const start = performance.now();
        // Simulate some work
        for (let i = 0; i < 1000; i++) {
          Math.random();
        }
        const end = performance.now();
        const duration = end - start;
        
        this.testResults.push({
          test: 'Performance API',
          status: 'PASS',
          message: `Performance API working, test took ${duration.toFixed(2)}ms`,
        });
      } else {
        this.testResults.push({
          test: 'Performance API',
          status: 'FAIL',
          message: 'Performance API not available',
        });
      }
    } catch {
      this.testResults.push({
        test: 'Performance',
        status: 'FAIL',
        message: `Performance test failed: ${error.message}`,
      });
    }
  }

  testFiltering() {
    try {
      // Test console filtering
      if (window.showFilteredMessages) {
        const filteredCount = window.showFilteredMessages();
        this.testResults.push({
          test: 'Console Filtering',
          status: 'PASS',
          message: `Console filtering working, ${filteredCount} messages filtered`,
        });
      } else {
        this.testResults.push({
          test: 'Console Filtering',
          status: 'SKIP',
          message: 'Console filtering not available (error handler disabled)',
        });
      }
    } catch {
      this.testResults.push({
        test: 'Console Filtering',
        status: 'FAIL',
        message: `Console filtering test failed: ${error.message}`,
      });
    }
  }

  displayResults() {
    console.group('🧪 Console Test Results');
    
    const passed = this.testResults.filter((r) => r.status === 'PASS').length;
    const failed = this.testResults.filter((r) => r.status === 'FAIL').length;
    const skipped = this.testResults.filter((r) => r.status === 'SKIP').length;
    
    console.log(`✅ Passed: ${passed}`);
    console.log(`❌ Failed: ${failed}`);
    console.log(`⏭️ Skipped: ${skipped}`);
    console.log(`📊 Total: ${this.testResults.length}`);
    
    console.log('\n📋 Detailed Results:');
    this.testResults.forEach((result, index) => {
      const icon = result.status === 'PASS' ? '✅' : 
        result.status === 'SKIP' ? '⏭️' : '❌';
      console.log(`${index + 1}. ${icon} ${result.test}: ${result.message}`);
    });
    
    console.groupEnd();
    
    // Store results for external access
    window.consoleTestResults = {
      passed,
      failed,
      skipped,
      total: this.testResults.length,
      results: this.testResults,
      timestamp: new Date().toISOString(),
    };
  }
}

// Auto-run tests only in development mode and only when explicitly enabled
if ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && 
    window.location.search.includes('debug=console')) {
  new ConsoleTest();
}

// Export for manual testing
export default ConsoleTest;
