//crawler
const axios = require("axios");
const cheerio = require("cheerio");

async function crawlPage(url) {
  try {
    const html = await axios.get(url, { timeout: 10000 });
    const $ = cheerio.load(html.data);

    const brokenLinks = [];

    $("a").each((i, el) => {
      const href = $(el).attr("href");

      if (!href) return;

      // Check for 404 pattern
      if (href.includes("404") || href.includes("not-found")) {
        brokenLinks.push({
          page: url,
          link: href
        });
      }
    });

    return brokenLinks;

  } catch (err) {
    return [];
  }
}

async function crawlNiche(niche) {
  // Starting sites (static, targeted niche)
  const sources = [
    "https://cleartax.in",
    "https://incometaxindia.gov.in",
    "https://blog.saginfotech.com",
    "https://taxguru.in",
    "https://vakilsearch.com/blog"
  ];

  let results = [];

  for (const url of sources) {
    const items = await crawlPage(url);
    results = results.concat(items);
  }

  return results;
}

module.exports = crawlNiche;

