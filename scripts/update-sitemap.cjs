// File: .github/scripts/update-sitemap.js

const fs = require("fs");
const path = require("path");
const xml2js = require("xml2js");

const SITEMAP_PATH = path.join(__dirname, "../sitemap.xml");
const PUBLIC_DIR = path.join(__dirname, "../");

function getLastModifiedTime(urlPath) {
  // Remove domain part, keeping only the path
  let relativePath = urlPath.replace(/^https?:\/\/[^/]+\//, "");

  // If the path ends with a known extension, use it directly
  if (/\.(html?|pdf|xls|xlsx|csv|txt|json|xml)$/i.test(relativePath)) {
    const fullPath = path.join(PUBLIC_DIR, relativePath);
    return fs.existsSync(fullPath) ? fs.statSync(fullPath).mtime : null;
  }

  // Try appending .html
  let testPath = path.join(PUBLIC_DIR, relativePath + ".html");
  if (fs.existsSync(testPath)) return fs.statSync(testPath).mtime;

  // Try index.html inside the directory
  testPath = path.join(PUBLIC_DIR, relativePath, "index.html");
  if (fs.existsSync(testPath)) return fs.statSync(testPath).mtime;

  return null;
}

fs.readFile(SITEMAP_PATH, (err, data) => {
  if (err) throw err;
  xml2js.parseString(data, (err, result) => {
    if (err) throw err;

    const urls = result.urlset.url;
    urls.forEach((entry) => {
      const loc = entry.loc[0];
      const lastModTime = getLastModifiedTime(loc);
      if (lastModTime) {
        const isoTime = new Date(lastModTime).toISOString().split("T")[0];
        entry.lastmod = [isoTime];
      }
    });

    const builder = new xml2js.Builder();
    const xml = builder.buildObject(result);

    fs.writeFile(SITEMAP_PATH, xml, (err) => {
      if (err) throw err;
      console.log("✅ sitemap.xml updated with latest lastmod timestamps.");
    });
  });
});

