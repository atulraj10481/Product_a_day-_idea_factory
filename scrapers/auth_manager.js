const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

function sanitizeAndCompressAuth(rawState) {
  const targetDomains = ['linkedin.com', 'workatastartup.com', 'ycombinator.com', 'wellfound.com'];
  
  // Filter only cookies from target platforms (strips third-party ad/analytics cookies)
  const filteredCookies = (rawState.cookies || []).filter(cookie => 
    targetDomains.some(domain => cookie.domain && cookie.domain.includes(domain))
  );

  // Keep essential auth origins, strip bloated tracking/chat storage
  const cleanOrigins = (rawState.origins || []).filter(origin => 
    targetDomains.some(domain => origin.origin && origin.origin.includes(domain))
  ).map(origin => ({
    origin: origin.origin,
    localStorage: (origin.localStorage || []).filter(item => 
      !item.name.includes('posthog') && 
      !item.name.includes('rudder') && 
      !item.name.includes('beacon') &&
      !item.name.includes('clarity')
    )
  }));

  const cleanState = {
    cookies: filteredCookies,
    origins: cleanOrigins
  };

  const jsonString = JSON.stringify(cleanState);
  
  // Gzip compress to ensure it stays well within GitHub's 48KB secret limit
  const gzippedBuffer = zlib.gzipSync(jsonString);
  return gzippedBuffer.toString('base64');
}

(async () => {
  console.log("============================================================");
  console.log("  🚀 Product-a-Day Idea Factory: Scraper Auth Manager");
  console.log("============================================================");
  console.log("We will open browser tabs for each platform so you can log in.");
  console.log("Session cookies will be saved and compressed for GitHub Actions.\n");

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();

  const readline = require('readline').createInterface({
    input: process.stdin,
    output: process.stdout
  });

  const promptUser = (question) => new Promise(resolve => {
    readline.question(`\n*** ${question} ***\n`, resolve);
  });

  // Platform 1: Work at a Startup (YC)
  console.log("[1/3] Opening Work at a Startup (YC)...");
  const page1 = await context.newPage();
  await page1.goto('https://www.workatastartup.com/login');
  await promptUser("Press ENTER when you have logged into YC...");

  // Platform 2: LinkedIn
  console.log("\n[2/3] Opening LinkedIn...");
  const page2 = await context.newPage();
  await page2.goto('https://www.linkedin.com/login');
  await promptUser("Press ENTER when you have logged into LinkedIn (and passed 2FA/verification)...");

  // Platform 3: Wellfound (AngelList Talent)
  console.log("\n[3/3] Opening Wellfound...");
  const page3 = await context.newPage();
  await page3.goto('https://wellfound.com/login');
  await promptUser("Press ENTER when you have logged into Wellfound...");

  readline.close();

  if (!fs.existsSync('data')) fs.mkdirSync('data');
  const authPath = path.join('data', 'auth_state.json');
  await context.storageState({ path: authPath });
  console.log(`\n✅ Raw session cookies saved to: ${authPath}`);

  // Sanitize and compress
  const rawState = JSON.parse(fs.readFileSync(authPath, 'utf8'));
  const compressedBase64 = sanitizeAndCompressAuth(rawState);
  const base64Path = path.join('data', 'auth_state.b64.txt');
  fs.writeFileSync(base64Path, compressedBase64);

  console.log(`✅ Optimized & compressed secret: ${compressedBase64.length} bytes (GitHub limit is 48,000 bytes)`);
  console.log("\n============================================================");
  console.log("  🔑 GITHUB ACTIONS SECRET (AUTH_STATE_BASE64)");
  console.log("============================================================");
  console.log("1. Go to your GitHub Repository -> Settings -> Secrets and variables -> Actions");
  console.log("2. Click 'New repository secret'");
  console.log("3. Name: AUTH_STATE_BASE64");
  console.log(`4. Value: Copy the entire text from '${base64Path}'`);
  console.log("============================================================\n");

  await browser.close();
})();

module.exports = { sanitizeAndCompressAuth };
