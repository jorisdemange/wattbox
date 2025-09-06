const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

async function runUITests() {
  // Create screenshots directory
  const screenshotsDir = path.join(__dirname, 'screenshots');
  if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir);
  }

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log('🚀 Starting WattBox UI Tests...\n');

  try {
    // 1. Navigate to Dashboard
    console.log('1. Navigating to http://localhost:5173...');
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');
    
    // 2. Take Dashboard screenshot
    await page.screenshot({ 
      path: path.join(screenshotsDir, '01-dashboard.png'),
      fullPage: true 
    });
    console.log('✅ Dashboard screenshot captured');

    // 3. Click Upload link
    console.log('\n3. Navigating to Upload page...');
    await page.click('text=Upload');
    await page.waitForLoadState('networkidle');
    
    // 4. Take Upload page screenshot
    await page.screenshot({ 
      path: path.join(screenshotsDir, '02-upload-page.png'),
      fullPage: true 
    });
    console.log('✅ Upload page screenshot captured');

    // 5. Upload image
    console.log('\n5. Testing file upload...');
    const fileInput = await page.locator('input[type="file"]');
    const imagePath = '/Users/joris/Desktop/FromClipboard/2025-07-11/17.00.34.jpeg';
    
    if (fs.existsSync(imagePath)) {
      await fileInput.setInputFiles(imagePath);
      console.log('✅ Image file selected:', imagePath);
    } else {
      console.log('⚠️  Image file not found:', imagePath);
    }

    // 6. Fill manual reading
    console.log('\n6. Entering manual reading value...');
    const numberInput = await page.locator('input[type="number"]');
    await numberInput.fill('75170.3');
    console.log('✅ Manual reading entered: 75170.3');

    // 7. Click upload button
    console.log('\n7. Clicking upload button...');
    const uploadButton = await page.locator('button:has-text("Upload")');
    await uploadButton.click();
    
    // 8. Wait and capture response
    console.log('\n8. Waiting for upload response...');
    await page.waitForTimeout(3000); // Wait for response
    await page.screenshot({ 
      path: path.join(screenshotsDir, '03-upload-response.png'),
      fullPage: true 
    });
    console.log('✅ Upload response screenshot captured');

    // 9. Navigate to History
    console.log('\n9. Navigating to History page...');
    await page.click('text=History');
    await page.waitForLoadState('networkidle');
    
    // 10. Take History screenshot
    await page.screenshot({ 
      path: path.join(screenshotsDir, '04-history-page.png'),
      fullPage: true 
    });
    console.log('✅ History page screenshot captured');

    // 11. Test responsive - Mobile
    console.log('\n11. Testing responsive design - Mobile (375x667)...');
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ 
      path: path.join(screenshotsDir, '05-mobile-dashboard.png'),
      fullPage: true 
    });
    console.log('✅ Mobile view screenshot captured');

    // Test mobile navigation
    const hamburger = await page.locator('[class*="hamburger"], [class*="mobile-menu"], button[aria-label*="menu"]').first();
    if (await hamburger.isVisible()) {
      await hamburger.click();
      await page.screenshot({ 
        path: path.join(screenshotsDir, '06-mobile-menu.png')
      });
      console.log('✅ Mobile menu tested');
    }

    // Test responsive - Tablet
    console.log('\n11. Testing responsive design - Tablet (768x1024)...');
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ 
      path: path.join(screenshotsDir, '07-tablet-dashboard.png'),
      fullPage: true 
    });
    console.log('✅ Tablet view screenshot captured');

    // UI Issues Report
    console.log('\n📊 UI Test Report:');
    console.log('=================');
    
    // Check for common UI elements
    const navLinks = await page.locator('nav a, [role="navigation"] a').count();
    console.log(`✅ Navigation links found: ${navLinks}`);
    
    const forms = await page.locator('form').count();
    console.log(`✅ Forms found: ${forms}`);
    
    const buttons = await page.locator('button').count();
    console.log(`✅ Interactive buttons found: ${buttons}`);
    
    // Check for accessibility
    const imagesWithoutAlt = await page.locator('img:not([alt])').count();
    if (imagesWithoutAlt > 0) {
      console.log(`⚠️  Images without alt text: ${imagesWithoutAlt}`);
    } else {
      console.log('✅ All images have alt text');
    }
    
    console.log('\n✅ All tests completed successfully!');
    console.log(`📸 Screenshots saved in: ${screenshotsDir}`);

  } catch (error) {
    console.error('\n❌ Test failed:', error.message);
    await page.screenshot({ 
      path: path.join(screenshotsDir, 'error-screenshot.png'),
      fullPage: true 
    });
  } finally {
    await browser.close();
  }
}

// Run the tests
runUITests().catch(console.error);