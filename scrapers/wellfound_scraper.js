const { chromium } = require('playwright');
const fs = require('fs');

const ROLE_QUERIES = [
  "product manager startup",
  "AI product manager",
  "founding engineer",
  "GTM engineer",
  "AI engineer startup",
  "solutions engineer"
];

async function scrapeWellfound(target = 100) {
  const browser = await chromium.launch({ headless: true });
  const storagePath = 'data/auth_state.json';

  let context;
  if (fs.existsSync(storagePath)) {
    console.log("🔑 Found auth_state.json. Using stored session cookies...");
    context = await browser.newContext({ storageState: storagePath });
  } else {
    console.warn("\n⚠️ [WARN] No data/auth_state.json found. Running Wellfound in guest mode.");
    console.warn("   To bypass Cloudflare rate-limits, run 'node scrapers/auth_manager.js'.\n");
    context = await browser.newContext({
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    });
  }

  let allJobs = [];

  for (const query of ROLE_QUERIES) {
    const page = await context.newPage();
    console.log(`\n🔍 Searching Wellfound for: "${query}"...`);

    try {
      await page.goto(`https://wellfound.com/jobs?q=${encodeURIComponent(query)}`, {
        waitUntil: 'domcontentloaded',
        timeout: 30000
      });
      await page.waitForTimeout(5000);

      // Check if blocked by Cloudflare turnstile / challenge
      const pageTitle = await page.title();
      if (pageTitle.toLowerCase().includes('just a moment') || pageTitle.toLowerCase().includes('cloudflare')) {
        console.warn(`   ⚠️ Wellfound Cloudflare challenge triggered for "${query}". Skipping query gracefully.`);
        await page.close();
        continue;
      }

      let jobs = [];
      let prevCount = 0;

      for (let i = 0; i < 10; i++) {
        await page.evaluate(() => window.scrollBy(0, 1500));
        await page.waitForTimeout(2000);

        // Try extracting from __NEXT_DATA__ first (most reliable)
        const nextDataJobs = await page.evaluate(() => {
          const scriptEl = document.querySelector('#__NEXT_DATA__');
          if (scriptEl) {
            try {
              const data = JSON.parse(scriptEl.textContent);
              const listings = data?.props?.pageProps?.listings || data?.props?.pageProps?.jobs || [];
              return listings.map(job => ({
                company: job.company?.name || job.startup?.name || 'Unknown',
                title: job.title || job.name || 'Unknown',
                description: job.description || job.snippet || 'Wellfound Job Posting',
                link: job.url || '',
                source: 'wellfound',
                scraped_at: new Date().toISOString()
              }));
            } catch { return []; }
          }
          return [];
        });

        if (nextDataJobs.length > 0) {
          jobs = nextDataJobs;
          break;
        }

        // Fallback: DOM-based extraction
        const domJobs = await page.evaluate(() => {
          const cards = Array.from(document.querySelectorAll('[class*="job"], [class*="styles_result"], [data-test="StartupResult"]'));
          return cards.map(card => {
            const titleEl = card.querySelector('a[class*="title"], h4, [class*="jobTitle"]');
            const companyEl = card.querySelector('[class*="company"], h2, [class*="startupName"]');
            const linkEl = card.querySelector('a[href*="/jobs/"]') || card.querySelector('a');

            if (!titleEl) return null;
            return {
              company: companyEl ? companyEl.innerText.trim() : 'Unknown',
              title: titleEl ? titleEl.innerText.trim() : 'Unknown',
              description: 'Wellfound Job Posting',
              link: linkEl ? (linkEl.href.startsWith('http') ? linkEl.href : 'https://wellfound.com' + linkEl.getAttribute('href')) : '',
              source: 'wellfound',
              scraped_at: new Date().toISOString()
            };
          }).filter(Boolean);
        });

        jobs = [...new Map([...jobs, ...domJobs].map(j => [j.company + j.title, j])).values()];
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

    // Delay between queries
    await new Promise(r => setTimeout(r, 2000));
  }

  allJobs = [...new Map(allJobs.map(j => [j.company + j.title, j])).values()];
  console.log(`\n📊 Total unique Wellfound jobs captured: ${allJobs.length}`);

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
  console.log(`💾 Saved ${uniqueJobs.length} total jobs (${uniqueJobs.length - existingJobs.length} new from Wellfound).`);
  await browser.close();
}

scrapeWellfound(100);
