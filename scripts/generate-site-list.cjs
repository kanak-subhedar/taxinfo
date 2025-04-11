const fs = require("fs");
const path = require("path");

// Root of the repository
const ROOT = path.join(__dirname, "../");
const OUTPUT_FILE = path.join(ROOT, "site-list.html");

// Files to skip from the list
const ignoreList = ["sitemap.xml", "index.html", "site-list.html"];

try {
  const files = fs.readdirSync(ROOT)
    .filter(file => file.endsWith(".html") && !ignoreList.includes(file));

  const links = files
    .map(file => `<li><a href="${file}">${file.replace(".html", "")}</a></li>`)
    .join("\n");

  const html = `
<!DOCTYPE html>
<html>
<head>
  <title>My HTML Pages</title>
  <meta charset="UTF-8">
</head>
<body>
  <h1>List of HTML Pages</h1>
  <ul>
    ${links}
  </ul>
</body>
</html>
  `;

  fs.writeFileSync(OUTPUT_FILE, html, "utf8");
  console.log("✅ site-list.html generated!");
} catch (err) {
  console.error("❌ Error generating site-list.html:", err);
  process.exit(1);
}
