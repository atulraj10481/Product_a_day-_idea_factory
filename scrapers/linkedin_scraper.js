const { chromium } = require('playwright');
const fs = require('fs');

const ROLE_QUERIES = [
  "product manager",
  "AI product manager",
  "associate product manager",
  "founding product manager",
  "product specialist",
  "GTM engineer",
  "solutions engineer",
  "AI engineer",
  "founding engineer",
  "full stack engineer"
];

async function scrapeLinkedIn(target = 100) {
  const browser = await chromium.launch({ headless: true });
  const storagePath = 'data/auth_state.json';

  let context;
  if (fs.existsSync(storagePath)) {
    console.log("🔑 Found auth_state.json. Using stored session cookies...");
    context = await browser.newContext({ storageState: storagePath });
  } else {
    console.warn("\n⚠️ [WARN] No data/auth_state.json found. Running LinkedIn in guest/public search mode.");
    console.warn("   To enable authenticated high-volume scraping, run 'node scrapers/auth_manager.js'.\n");
    context = await browser.newContext({
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    });
  }

  let allJobs = [];

  for (const query of ROLE_QUERIES) {
    const page = await context.newPage();
    const url = `https://www.linkedin.com/jobs/search/?keywords=${encodeURIComponent(query)}`;
    console.log(`\n🔍 Searching LinkedIn for: "${query}"...`);

    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForTimeout(5000);

      // Check if redirected to login wall
      if (page.url().includes('login') || page.url().includes('authwall')) {
        console.warn(`   ⚠️ LinkedIn requested authentication for "${query}". Skipping query gracefully.`);
        await page.close();
        continue;
      }

      let jobs = [];
      let prevCount = 0;

      for (let i = 0; i < 15; i++) {
        await page.evaluate(() => {
          const scroller = document.querySelector('.jobs-search-results-list');
          if (scroller) scroller.scrollBy(0, 1000);
          else window.scrollBy(0, 1000);
        });
        await page.waitForTimeout(2000);

        const currentJobs = await page.evaluate(() => {
          const cards = Array.from(document.querySelectorAll('[data-job-id], .base-card'));
          return cards.map(card => {
            const titleEl = card.querySelector('.artdeco-entity-lockup__title, .base-search-card__title');
            const companyEl = card.querySelector('.artdeco-entity-lockup__subtitle, .base-search-card__subtitle');
            const linkEl = card.querySelector('a');

            return {
              company: companyEl ? companyEl.innerText.trim() : 'Unknown',
              title: titleEl ? titleEl.innerText.trim() : 'Unknown',
              description: "LinkedIn Job Posting",
              link: linkEl ? linkEl.href : '',
              source: 'linkedin',
              scraped_at: new Date().toISOString()
            };
          }).filter(j => j.title !== 'Unknown');
        });

        jobs = [...new Map([...jobs, ...currentJobs].map(j => [j.company + j.title, j])).values()];

        if (jobs.length > 0 && jobs.length === prevCount) break;
        prevCount = jobs.length;
        if (jobs.length >= target) break;
      }

      console.log(`   ✅ Captured ${jobs.length} jobs for "${query}"`);
      allJobs = [...allJobs, ...jobs];
    } catch (e) {
      console.warn(`   ⚠️ Notice for "${query}": ${e.message}`);
    }
    await page.close();

    // Delay between queries to avoid rate limits
    await new Promise(r => setTimeout(r, 2000));
  }

  // Deduplicate across all queries
  allJobs = [...new Map(allJobs.map(j => [j.company + j.title, j])).values()];
  console.log(`\n📊 Total unique LinkedIn jobs captured: ${allJobs.length}`);

  // Merge with existing
  if (!fs.existsSync('data')) fs.mkdirSync('data');
  let existingJobs = [];
  if (fs.existsSync('data/raw_jobs.json')) {
    try {
      existingJobs = JSON.parse(fs.readFileSync('data/raw_jobs.json', 'utf8'));
    } catch (e) {
      console.error("Failed to parse existing raw_jobs.json.");
    }
  }

  const merged = [...existingJobs, ...allJobs];
  const uniqueJobs = [...new Map(merged.map(j => [j.company + j.title, j])).values()];

  fs.writeFileSync('data/raw_jobs.json', JSON.stringify(uniqueJobs, null, 2));
  console.log(`💾 Saved ${uniqueJobs.length} total jobs (${uniqueJobs.length - existingJobs.length} new from LinkedIn).`);
  await browser.close();
}

scrapeLinkedIn(100);
