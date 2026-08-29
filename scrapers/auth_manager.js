const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  console.log("============================================================");
  console.log("  🚀 Product-a-Day Idea Factory: Scraper Auth Manager");
  console.log("============================================================");
  console.log("We will open browser tabs for each platform so you can log in.");
  console.log("Session cookies will be saved for local and GitHub Actions cloud use.\n");

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
  console.log(`\n✅ Session cookies saved to: ${authPath}`);

  // Base64 encode for GitHub Actions Secret
  const fileBuffer = fs.readFileSync(authPath);
  const base64String = fileBuffer.toString('base64');
  const base64Path = path.join('data', 'auth_state.b64.txt');
  fs.writeFileSync(base64Path, base64String);

  console.log("\n============================================================");
  console.log("  🔑 GITHUB ACTIONS SECRET (AUTH_STATE_BASE64)");
  console.log("============================================================");
  console.log("1. Go to your GitHub Repository -> Settings -> Secrets and variables -> Actions");
  console.log("2. Click 'New repository secret'");
  console.log("3. Name: AUTH_STATE_BASE64");
  console.log("4. Value: Copy the Base64 text below (or from data/auth_state.b64.txt):\n");
  console.log(base64String.substring(0, 100) + "... [truncated in console, full content saved to data/auth_state.b64.txt]");
  console.log(`\n📁 Full string written to: ${base64Path}`);
  console.log("============================================================\n");

  await browser.close();
})();
