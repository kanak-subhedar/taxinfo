const express = require("express");
const cors = require("cors");
const axios = require("axios");
const cheerio = require("cheerio");

const app = express();
app.use(cors());

const PORT = process.env.PORT || 10000;

// Seed domains
const domains = [
  "https://cleartax.in",
  "https://taxguru.in",
  "https://groww.in",
  "https://bankbazaar.com",
  "https://policybazaar.com",
  "https://paisabazaar.com",
  "https://moneycontrol.com"
];

// Utility to check status code
async function checkUrl(url) {
  try {
    await axios.get(url, { timeout: 7000 });
    return null;
  } catch (e) {
    if (e.response && (e.response.status === 404 || e.response.status === 400)) {
      return e.response.status;
    }
    return null;
  }
}

// Main scanner function
async function scanDomain(domain) {
  const results = [];

  try {
    const { data } = await axios.get(domain, { timeout: 8000 });
    const $ = cheerio.load(data);

    const links = $("a");
    console.log("Links found:", links.length);

    for (let i = 0; i < links.length; i++) {
      const link = $(links[i]).attr("href");
      if (!link || link.startsWith("#")) continue;

      let full = link.startsWith("http") ? link : domain + link;

      const status = await checkUrl(full);
      if (status) {
        results.push({
          domain,
          broken: full,
          status
        });
      }
    }
  } catch (err) {
    console.log("Domain failed:", domain);
  }

  return results;
}

// API Route
app.get("/scan", async (req, res) => {
  const page = parseInt(req.query.page) || 1;
  const perPage = 20;

  let data = [];

  for (const d of domains) {
    console.log("Scanning:", d);
    const r = await scanDomain(d);
    data.push(...r);
  }

  const start = (page - 1) * perPage;
  const paged = data.slice(start, start + perPage);

  res.json({
    total_results: data.length,
    total_pages: Math.ceil(data.length / perPage),
    current_page: page,
    results: paged
  });
});

app.get("/", (req, res) => {
  res.send("API Online");
});

app.listen(PORT, () => console.log("Server running on port", PORT));
