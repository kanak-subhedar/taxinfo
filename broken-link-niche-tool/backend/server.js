const express = require("express");
const axios = require("axios");
const cheerio = require("cheerio");
const cors = require("cors");

const app = express();
app.use(cors());

// CONFIG
const DOMAINS_PER_PAGE = 20;
const URLS_PER_DOMAIN = 50;

// Utility: Get unique hostname
function extractHostname(url) {
  try {
    return new URL(url).hostname;
  } catch {
    return null;
  }
}

// Step 1: Get domains from DDG search
async function getDomains(niche, page) {
  const start = (page - 1) * DOMAINS_PER_PAGE;
  const end = start + DOMAINS_PER_PAGE;

  const query = `https://duckduckgo.com/html/?q=${encodeURIComponent(niche)}+india`;

  let res = await axios.get(query, { timeout: 8000 });
  let $ = cheerio.load(res.data);

  let links = [];

  $("a.result__a").each((i, el) => {
    const url = $(el).attr("href");
    const host = extractHostname(url);
    if (host) links.push(host);
  });

  // unique + sorted
  links = [...new Set(links)];

  return links.slice(start, end);
}

// Step 2: Crawl one website
async function scanDomain(domain) {
  let results = [];

  try {
    const base = `http://${domain}`;
    const res = await axios.get(base, { timeout: 5000 });
    const $ = cheerio.load(res.data);

    let urls = [];

    $("a").each((i, el) => {
      let url = $(el).attr("href");
      if (url && url.startsWith("http")) urls.push(url);
    });

    urls = [...new Set(urls)].slice(0, URLS_PER_DOMAIN);

    // Check broken
    for (let url of urls) {
      try {
        let r = await axios.head(url, { timeout: 3000 });
        if (r.status >= 400) {
          results.push({
            domain,
            broken: url,
            status: r.status,
          });
        }
      } catch {
        results.push({
          domain,
          broken: url,
          status: 404,
        });
      }
    }

  } catch {
    // skip if dead
    return [];
  }

  return results;
}


// API ENDPOINT
app.get("/scan", async (req, res) => {

  const niche = req.query.niche || "";
  const page = parseInt(req.query.page) || 1;

  let allResults = [];

  try {
    // 1. Get domains for this page
    let domains = await getDomains(niche, page);

    for (let domain of domains) {
      let r = await scanDomain(domain);
      allResults.push(...r);
    }

    return res.json({
      page,
      domains_checked: domains.length,
      results_found: allResults.length,
      results: allResults
    });

  } catch (e) {

    return res.json({
      page,
      error: e.message,
      results: []
    });
  }

});

const port = process.env.PORT || 10000;
app.listen(port, () => console.log("Server running on", port));
