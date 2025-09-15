/**
 * Refactoring Test Suite
 * Validates that all inline styles and embedded JavaScript have been properly refactored
 *
 * @version 1.0.0
 * @author Meal Expense Tracker Team
 */

export class RefactoringTests {
    constructor() {
        this.testResults = {
            passed: 0,
            failed: 0,
            total: 0
        };
    }

    async runAllTests() {
        console.log('🧪 Running Refactoring Test Suite...');

        await this.testInlineEventHandlers();
        await this.testInlineStyles();
        await this.testEmbeddedScripts();
        await this.testCSSClasses();
        await this.testJavaScriptModules();

        this.printResults();
    }

    async testInlineEventHandlers() {
        console.log('\n📋 Testing Inline Event Handlers...');

        const testCases = [
            {
                name: 'No onclick handlers in restaurant form',
                selector: 'app/templates/restaurants/form.html',
                check: () => !document.querySelector('[onclick]')
            },
            {
                name: 'No onclick handlers in tag helpers',
                selector: '.tag-remove',
                check: () => !document.querySelector('.tag-remove[onclick]')
            },
            {
                name: 'Data attributes present for event handling',
                selector: '[data-action]',
                check: () => document.querySelectorAll('[data-action]').length > 0
            }
        ];

        for (const testCase of testCases) {
            await this.runTest(testCase);
        }
    }

    async testInlineStyles() {
        console.log('\n🎨 Testing Inline Styles...');

        const testCases = [
            {
                name: 'No inline styles in restaurant icons',
                selector: '.restaurant-fallback-icon',
                check: () => !document.querySelector('.restaurant-fallback-icon[style]')
            },
            {
                name: 'No inline styles in amount elements',
                selector: '.amount-right',
                check: () => !document.querySelector('.amount-right[style*="min-width"]')
            },
            {
                name: 'CSS classes applied instead of inline styles',
                selector: '.amount-min-width',
                check: () => document.querySelectorAll('.amount-min-width').length > 0
            }
        ];

        for (const testCase of testCases) {
            await this.runTest(testCase);
        }
    }

    async testEmbeddedScripts() {
        console.log('\n📜 Testing Embedded Scripts...');

        const testCases = [
            {
                name: 'No large embedded script blocks',
                selector: 'script:not([src])',
                check: () => {
                    const scripts = document.querySelectorAll('script:not([src])');
                    let hasLargeScript = false;

                    scripts.forEach(script => {
                        if (script.textContent.length > 100) {
                            hasLargeScript = true;
                        }
                    });

                    return !hasLargeScript;
                }
            },
            {
                name: 'External modules loaded',
                selector: 'script[type="module"]',
                check: () => document.querySelectorAll('script[type="module"]').length > 0
            }
        ];

        for (const testCase of testCases) {
            await this.runTest(testCase);
        }
    }

    async testCSSClasses() {
        console.log('\n🎯 Testing CSS Classes...');

        const testCases = [
            {
                name: 'Utility classes available',
                selector: '.amount-min-width',
                check: () => {
                    const element = document.createElement('div');
                    element.className = 'amount-min-width';
                    const styles = window.getComputedStyle(element);
                    return styles.minWidth === '80px';
                }
            },
            {
                name: 'Restaurant icon classes available',
                selector: '.restaurant-fallback-icon',
                check: () => {
                    const element = document.createElement('div');
                    element.className = 'restaurant-fallback-icon';
                    const styles = window.getComputedStyle(element);
                    return styles.display === 'none' && styles.fontSize === '24px';
                }
            },
            {
                name: 'Scrollable container classes available',
                selector: '.scrollable-container-sm',
                check: () => {
                    const element = document.createElement('div');
                    element.className = 'scrollable-container-sm';
                    const styles = window.getComputedStyle(element);
                    return styles.maxHeight === '200px' && styles.overflowY === 'auto';
                }
            }
        ];

        for (const testCase of testCases) {
            await this.runTest(testCase);
        }
    }

    async testJavaScriptModules() {
        console.log('\n🔧 Testing JavaScript Modules...');

        const testCases = [
            {
                name: 'EventHandlers class available',
                selector: 'window.EventHandlers',
                check: () => typeof window.EventHandlers === 'function'
            },
            {
                name: 'StyleReplacer class available',
                selector: 'window.StyleReplacer',
                check: () => typeof window.StyleReplacer === 'function'
            },
            {
                name: 'TagifyConfig class available',
                selector: 'window.TagifyConfig',
                check: () => typeof window.TagifyConfig === 'function'
            }
        ];

        for (const testCase of testCases) {
            await this.runTest(testCase);
        }
    }

    async runTest(testCase) {
        this.testResults.total++;

        try {
            const result = await testCase.check();

            if (result) {
                console.log(`✅ ${testCase.name}`);
                this.testResults.passed++;
            } else {
                console.log(`❌ ${testCase.name}`);
                this.testResults.failed++;
            }
        } catch (error) {
            console.log(`❌ ${testCase.name} - Error: ${error.message}`);
            this.testResults.failed++;
        }
    }

    printResults() {
        console.log('\n📊 Test Results:');
        console.log(`Total Tests: ${this.testResults.total}`);
        console.log(`Passed: ${this.testResults.passed}`);
        console.log(`Failed: ${this.testResults.failed}`);
        console.log(`Success Rate: ${((this.testResults.passed / this.testResults.total) * 100).toFixed(1)}%`);

        if (this.testResults.failed === 0) {
            console.log('\n🎉 All tests passed! Refactoring completed successfully.');
        } else {
            console.log('\n⚠️  Some tests failed. Please review the issues above.');
        }
    }

    // Utility methods for manual testing
    static checkForInlineStyles() {
        const elementsWithStyles = document.querySelectorAll('[style]');
        console.log(`Found ${elementsWithStyles.length} elements with inline styles:`);

        elementsWithStyles.forEach((element, index) => {
            console.log(`${index + 1}. ${element.tagName} - ${element.getAttribute('style')}`);
        });

        return elementsWithStyles.length;
    }

    static checkForInlineHandlers() {
        const elementsWithHandlers = document.querySelectorAll('[onclick], [onload], [onchange]');
        console.log(`Found ${elementsWithHandlers.length} elements with inline handlers:`);

        elementsWithHandlers.forEach((element, index) => {
            const handlers = [];
            if (element.onclick) handlers.push('onclick');
            if (element.onload) handlers.push('onload');
            if (element.onchange) handlers.push('onchange');
            console.log(`${index + 1}. ${element.tagName} - ${handlers.join(', ')}`);
        });

        return elementsWithHandlers.length;
    }

    static checkForEmbeddedScripts() {
        const scripts = document.querySelectorAll('script:not([src])');
        console.log(`Found ${scripts.length} embedded script blocks:`);

        scripts.forEach((script, index) => {
            const lines = script.textContent.split('\n').length;
            console.log(`${index + 1}. ${lines} lines of code`);
        });

        return scripts.length;
    }
}

// Make available globally for manual testing
window.RefactoringTests = RefactoringTests;

// Auto-run tests in development
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    document.addEventListener('DOMContentLoaded', () => {
        const tests = new RefactoringTests();
        tests.runAllTests();
    });
}
