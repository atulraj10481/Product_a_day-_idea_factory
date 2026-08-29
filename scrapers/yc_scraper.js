const { chromium } = require('playwright');
const fs = require('fs');

const ROLE_QUERIES = [
  "product manager",
  "AI product manager",
  "associate product manager",
  "founding product manager",
  "product specialist",
  "product lead",
  "GTM engineer",
  "solutions engineer",
  "AI engineer",
  "founding engineer",
  "full stack engineer",
  "frontend developer engineer"
];

async function scrapeYC(target = 200) {
  const browser = await chromium.launch({ headless: true });
  const storagePath = 'data/auth_state.json';
  const context = fs.existsSync(storagePath)
    ? await browser.newContext({ storageState: storagePath })
    : await browser.newContext();

  let allJobs = [];

  for (const query of ROLE_QUERIES) {
    const page = await context.newPage();
    const url = `https://www.workatastartup.com/jobs?query=${encodeURIComponent(query)}`;
    console.log(`\n🔍 Searching YC for: "${query}"...`);
    
    try {
      await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
      await page.waitForTimeout(3000);

      let jobs = [];
      let prevCount = 0;

      for (let i = 0; i < 10; i++) {
        await page.evaluate(() => window.scrollBy(0, 1500));
        await page.waitForTimeout(2000);

        const currentJobs = await page.evaluate((queryStr) => {
          const applyNodes = Array.from(document.querySelectorAll('a, button')).filter(el => el.innerText && el.innerText.trim() === 'Apply');
          return applyNodes.map(btn => {
            let card = btn.parentElement;
            while (card && !card.innerText.includes('Fulltime') && !card.innerText.includes('Intern')) {
              card = card.parentElement;
            }
            if (card) card = card.parentElement;
            if (!card) return null;

            const textLines = card.innerText.split('\n').map(l => l.trim()).filter(l => l);
            let titleIndex = textLines.findIndex(l =>
              l.includes('Product') || l.includes('Engineer') || l.includes('Manager') ||
              l.includes('Founding') || l.includes('GTM') || l.includes('AI') ||
              l.includes('Specialist') || l.includes('Lead') || l.includes('Solutions')
            );
            if (titleIndex === -1) titleIndex = 2;

            return {
              company: textLines[0] || 'Unknown',
              title: textLines[titleIndex] || textLines[1] || 'Unknown',
              description: textLines.slice(titleIndex + 1, -1).join(' '),
              link: btn.href || '',
              source: 'yc',
              scraped_at: new Date().toISOString()
            };
          }).filter(Boolean);
        }, query);

        jobs = [...new Map(currentJobs.map(j => [j.company + j.title, j])).values()];
        if (jobs.length > 0 && jobs.length === prevCount) break;
        prevCount = jobs.length;
        if (jobs.length >= target) break;
      }

      console.log(`   ✅ Captured ${jobs.length} jobs for "${query}"`);
      allJobs = [...allJobs, ...jobs];
    } catch (e) {
      console.error(`   ❌ Error scraping "${query}": ${e.message}`);
    }
    await page.close();
  }

  // Deduplicate across all queries
  allJobs = [...new Map(allJobs.map(j => [j.company + j.title, j])).values()];
  console.log(`\n📊 Total unique YC jobs: ${allJobs.length}`);

  // Merge with existing
  if (!fs.existsSync('data')) fs.mkdirSync('data');
  let existingJobs = [];
  if (fs.existsSync('data/raw_jobs.json')) {
    try {
      existingJobs = JSON.parse(fs.readFileSync('data/raw_jobs.json', 'utf8'));
    } catch (e) {
      console.error("Failed to parse existing raw_jobs.json, starting fresh.");
    }
  }

  const merged = [...existingJobs, ...allJobs];
  const uniqueJobs = [...new Map(merged.map(j => [j.company + j.title, j])).values()];

  fs.writeFileSync('data/raw_jobs.json', JSON.stringify(uniqueJobs, null, 2));
  console.log(`💾 Saved ${uniqueJobs.length} total jobs (${uniqueJobs.length - existingJobs.length} new from YC).`);
  await browser.close();
}

scrapeYC(200);
