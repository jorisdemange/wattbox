import { chromium } from 'playwright';

async function debugTest() {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  // Capture console messages
  const consoleMessages = [];
  page.on('console', msg => {
    consoleMessages.push({
      type: msg.type(),
      text: msg.text(),
      location: msg.location()
    });
  });
  
  // Capture page errors
  const pageErrors = [];
  page.on('pageerror', error => {
    pageErrors.push(error.toString());
  });
  
  try {
    console.log('Navigating to http://localhost:5173...');
    await page.goto('http://localhost:5173', { waitUntil: 'domcontentloaded' });
    
    // Wait a bit for any async operations
    await page.waitForTimeout(2000);
    
    // Print all console messages
    console.log('\n=== Console Messages ===');
    consoleMessages.forEach(msg => {
      console.log(`[${msg.type}] ${msg.text}`);
      if (msg.location?.url) {
        console.log(`  at ${msg.location.url}:${msg.location.lineNumber}`);
      }
    });
    
    // Print any page errors
    if (pageErrors.length > 0) {
      console.log('\n=== Page Errors ===');
      pageErrors.forEach(error => console.log(error));
    }
    
    // Check if RouterView is rendering
    console.log('\n=== Checking RouterView ===');
    const routerViewContent = await page.locator('main').innerHTML();
    console.log('RouterView content:', routerViewContent ? 'Has content' : 'Empty');
    
    // Check for navigation links with more specific selectors
    console.log('\n=== Navigation Links ===');
    const navLinks = await page.locator('nav a, nav button').all();
    console.log(`Found ${navLinks.length} navigation elements`);
    
    // Try to wait for Vue to load
    await page.waitForFunction(() => {
      return window.Vue || window.__VUE__ || document.querySelector('[data-v-]');
    }, { timeout: 5000 }).catch(() => console.log('Vue not detected within 5 seconds'));
    
    // Take screenshot with annotations
    await page.screenshot({ 
      path: 'screenshot-debug.png', 
      fullPage: true 
    });
    
    // Now try to click on Upload if visible
    const uploadLink = await page.locator('text=Upload').first();
    if (await uploadLink.isVisible()) {
      console.log('\n✓ Upload link is visible, clicking...');
      await uploadLink.click();
      await page.waitForLoadState('networkidle');
      console.log('Current URL after click:', page.url());
      
      await page.screenshot({ 
        path: 'screenshot-upload-page-debug.png', 
        fullPage: true 
      });
    } else {
      console.log('\n✗ Upload link not visible');
      
      // Check what's actually rendered
      const bodyHTML = await page.locator('body').innerHTML();
      console.log('\nBody HTML preview:');
      console.log(bodyHTML.substring(0, 1000));
    }
    
  } catch (error) {
    console.error('Error:', error);
  } finally {
    // Keep browser open for manual inspection
    console.log('\nPress Ctrl+C to close browser...');
    await new Promise(() => {}); // Keep running
  }
}

debugTest().catch(console.error);