import { chromium } from 'playwright';

async function detailedTest() {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  try {
    console.log('Navigating to http://localhost:5173...');
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
    
    // Check page title
    const title = await page.title();
    console.log(`Page title: ${title}`);
    
    // Check for any visible text
    const bodyText = await page.locator('body').innerText();
    console.log('\nPage content preview:');
    console.log(bodyText.substring(0, 500) + '...');
    
    // Look for all clickable elements
    console.log('\nLooking for all clickable elements...');
    const clickableElements = await page.locator('a, button, [role="button"], [onclick]').all();
    console.log(`Found ${clickableElements.length} clickable elements`);
    
    for (const element of clickableElements) {
      const tagName = await element.evaluate(el => el.tagName);
      const text = await element.innerText().catch(() => '');
      const href = await element.getAttribute('href').catch(() => '');
      console.log(`  - ${tagName}: "${text}" ${href ? `(href: ${href})` : ''}`);
    }
    
    // Look for routing elements more broadly
    console.log('\nLooking for Vue Router links...');
    const routerLinks = await page.locator('[class*="router"], [href*="/"], nav *, aside *, header *').all();
    for (const link of routerLinks.slice(0, 10)) { // Limit to first 10
      const tagName = await link.evaluate(el => el.tagName);
      const text = await link.innerText().catch(() => '');
      const className = await link.getAttribute('class').catch(() => '');
      console.log(`  - ${tagName}: "${text}" (class: ${className})`);
    }
    
    // Try to find Upload link with different selectors
    console.log('\nSearching for Upload functionality...');
    const uploadSelectors = [
      'text=Upload',
      'text=upload',
      '[href*="upload"]',
      'button:has-text("Upload")',
      'a:has-text("Upload")',
      '*:has-text("Upload")'
    ];
    
    for (const selector of uploadSelectors) {
      const element = await page.locator(selector).first();
      if (await element.count() > 0) {
        console.log(`✓ Found element matching: ${selector}`);
        const text = await element.innerText().catch(() => '');
        console.log(`  Text: "${text}"`);
        
        // Try to click it
        try {
          await element.click();
          await page.waitForLoadState('networkidle');
          const newUrl = page.url();
          console.log(`  Navigated to: ${newUrl}`);
          
          // Take screenshot of upload page
          await page.screenshot({ path: 'screenshot-upload-found.png', fullPage: true });
          console.log('  Screenshot saved as screenshot-upload-found.png');
          break;
        } catch (e) {
          console.log(`  Could not click: ${e.message}`);
        }
      }
    }
    
  } catch (error) {
    console.error('Error:', error);
  } finally {
    await browser.close();
  }
}

detailedTest().catch(console.error);