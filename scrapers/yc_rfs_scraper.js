const { chromium } = require('playwright');
const fs = require('fs');

async function scrapeYCRFS() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log("🔍 Scraping Y Combinator Request for Startups...");
  await page.goto('https://www.ycombinator.com/rfs', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(3000);

  // Scroll to load all content
  for (let i = 0; i < 5; i++) {
    await page.evaluate(() => window.scrollBy(0, 2000));
    await page.waitForTimeout(1000);
  }

  const ideas = await page.evaluate(() => {
    // YC RFS page typically has sections with h2/h3 headings and paragraphs
    const sections = [];
    const headings = document.querySelectorAll('h2, h3');
    
    headings.forEach(heading => {
      const title = heading.innerText.trim();
      if (!title || title.length < 3) return;
      
      // Collect all sibling paragraphs until the next heading
      let description = '';
      let sibling = heading.nextElementSibling;
      while (sibling && !['H1', 'H2', 'H3'].includes(sibling.tagName)) {
        if (sibling.innerText) {
          description += sibling.innerText.trim() + ' ';
        }
        sibling = sibling.nextElementSibling;
      }

      if (description.length > 20) {
        sections.push({
          company: 'Y Combinator (RFS)',
          title: title,
          description: description.trim().substring(0, 1000),
          link: 'https://www.ycombinator.com/rfs',
          source: 'yc_rfs',
          scraped_at: new Date().toISOString()
        });
      }
    });

    return sections;
  });

  console.log(`✅ Captured ${ideas.length} YC RFS idea areas.`);

  if (ideas.length === 0) {
    console.log("Taking debug screenshot...");
    if (!fs.existsSync('scratch')) fs.mkdirSync('scratch');
    await page.screenshot({ path: 'scratch/yc_rfs_debug.png', fullPage: true });
  }

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

  const merged = [...existingJobs, ...ideas];
  const uniqueJobs = [...new Map(merged.map(j => [j.company + j.title, j])).values()];

  fs.writeFileSync('data/raw_jobs.json', JSON.stringify(uniqueJobs, null, 2));
  console.log(`💾 Saved ${uniqueJobs.length} total jobs (${uniqueJobs.length - existingJobs.length} new from YC RFS).`);
  await browser.close();
}

scrapeYCRFS();
