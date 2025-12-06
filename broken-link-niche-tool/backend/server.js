//server

const express = require("express");
const cors = require("cors");
const crawlNiche = require("./crawler");

const app = express();
app.use(cors());
app.use(express.json());

const PAGE_SIZE = 10;

app.get("/scan", async (req, res) => {
  try {
    const niche = req.query.niche;
    const page = parseInt(req.query.page) || 1;

    if (!niche) {
      return res.status(400).json({ error: "niche parameter required" });
    }

    // Perform crawl
    const results = await crawlNiche(niche);

    // Pagination logic
    const total = results.length;
    const start = (page - 1) * PAGE_SIZE;
    const end = page * PAGE_SIZE;
    const sliced = results.slice(start, end);

    return res.json({
      niche,
      current_page: page,
      total_pages: Math.ceil(total / PAGE_SIZE),
      results: sliced,
      total_results: total
    });

  } catch (error) {
    console.error(error);
    res.status(500).json({
      error: "server error",
      details: error.message
    });
  }
});

app.get("/", (req, res) => {
  res.send("API Online");
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log("Server running on port", PORT));
