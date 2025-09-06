import { chromium } from 'playwright';

async function testWattBox() {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  try {
    console.log('1. Navigating to http://localhost:5173...');
    
    // Try to navigate, catch if server is not running
    try {
      await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 10000 });
    } catch (error) {
      console.error('❌ Failed to connect to http://localhost:5173');
      console.error('Make sure the development server is running with: npm run dev');
      console.error('Note: There appears to be a Node.js version compatibility issue.');
      console.error('Current Node version: v18.20.6');
      console.error('Vite 7 requires Node.js ^20.19.0 || >=22.12.0');
      return;
    }
    
    // Take screenshot of main page
    await page.screenshot({ path: 'screenshot-main-page.png', fullPage: true });
    console.log('✓ Screenshot of main page saved as screenshot-main-page.png');
    
    // Look for Upload navigation link
    console.log('\n2. Looking for Upload page link...');
    const uploadLink = await page.locator('a:has-text("Upload"), button:has-text("Upload")').first();
    
    if (await uploadLink.count() > 0) {
      await uploadLink.click();
      await page.waitForLoadState('networkidle');
      
      await page.screenshot({ path: 'screenshot-upload-page.png', fullPage: true });
      console.log('✓ Screenshot of Upload page saved as screenshot-upload-page.png');
    } else {
      console.log('! Upload link not found in navigation');
    }
    
    // Test responsive design
    console.log('\n3. Testing responsive design...');
    
    // Mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.screenshot({ path: 'screenshot-mobile.png', fullPage: true });
    console.log('✓ Mobile screenshot (375x667) saved as screenshot-mobile.png');
    
    // Tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.screenshot({ path: 'screenshot-tablet.png', fullPage: true });
    console.log('✓ Tablet screenshot (768x1024) saved as screenshot-tablet.png');
    
    // Desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.screenshot({ path: 'screenshot-desktop.png', fullPage: true });
    console.log('✓ Desktop screenshot (1920x1080) saved as screenshot-desktop.png');
    
    // Check for any console errors
    console.log('\n4. Checking for console errors...');
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log(`Console error: ${msg.text()}`);
      }
    });
    
    // Navigate through available pages
    console.log('\n5. Checking available navigation links...');
    const navLinks = await page.locator('nav a, aside a, header a').all();
    console.log(`Found ${navLinks.length} navigation links`);
    
    for (const link of navLinks) {
      const text = await link.innerText().catch(() => '');
      const href = await link.getAttribute('href').catch(() => '');
      console.log(`  - ${text || 'No text'}: ${href || 'No href'}`);
    }
    
  } catch (error) {
    console.error('Error during testing:', error);
  } finally {
    await browser.close();
  }
}

// Run the test
testWattBox().catch(console.error);