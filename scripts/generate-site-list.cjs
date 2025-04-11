const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "../");
const INDEX_FILE = path.join(ROOT, "blog.html"); // or index.html

// Ignore these files from the list
const ignoreList = ["sitemap.xml", "index.html", "blog.html"];

const files = fs.readdirSync(ROOT)
  .filter(file => file.endsWith(".html") && !ignoreList.includes(file));

const links = files
  .map(file => `<li><a href="${file}">${file.replace(".html", "")}</a></li>`)
  .join("\n");

const html = `
<!DOCTYPE html>
<html>
<head><title>My HTML Pages</title></head>
<body>
  <h1>List of Pages</h1>
  <ul>${links}</ul>
</body>
</html>
`;

fs.writeFileSync(INDEX_FILE, html);
console.log("✅ blog.html generated!");
