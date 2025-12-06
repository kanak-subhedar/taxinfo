const express = require("express");
const cors = require("cors");
const axios = require("axios");
const cheerio = require("cheerio");

const app = express();
app.use(cors());

const PORT = process.env.PORT || 10000;

// Domains to scan
const domains = [
  "https://cleartax.in",
  "https://taxguru.in",
  "https://groww.in",
  "https://bankbazaar.com",
  "https://policybazaar.com",
  "https://paisabazaar.com",
  "https://moneycontrol.com"
];

// Fetch link status with timeout
async function checkUrl(url) {
  try {
    await axios.get(url, { timeout: 4000 });
    return null;
  } catch (e) {
    if (e.response && e.response.status === 404) {
      return 404;
    }
    return null;
  }
}

// Crawl domain
async function scanDomain(domain) {
  const results = [];

  try {
    const { data } = await axios.get(domain, { timeout: 5000 });
    const $ = cheerio.load(data);

    const links = $("a")
      .map((i, el) => $(el).attr("href"))
      .get()
      .filter(l => l && !l.startsWith("#"))
      .slice(0, 50); // limit to 50 links

    const fullLinks = links.map(l =>
      l.startsWith("http") ? l : domain + l
    );

    const checks = await Promise.all(
      fullLinks.map(link => checkUrl(link)
        .then(status => ({ link, status }))
      )
    );

    checks.forEach(c => {
      if (c.status) {
        results.push({
          domain,
          broken: c.link,
          status: c.status
        });
      }
    });

  } catch (e) {
    console.log("Error scanning:", domain);
  }

  return results;
}

app.get("/scan", async (req, res) => {

  // Perform scan in parallel
  const scans = await Promise.all(domains.map(scanDomain));
  const all = scans.flat();

  res.json({
    total_results: all.length,
    results: all.slice(0, 20), // return first 20
    sample_size: all.length
  });
});

app.get("/", (req, res) => {
  res.send("API Online");
});

app.listen(PORT, () => console.log("Server running on port", PORT));
