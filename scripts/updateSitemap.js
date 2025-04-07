const fs = require('fs');
const path = require('path');
const { XMLParser, XMLBuilder } = require('fast-xml-parser');

// Read sitemap
const sitemapPath = path.join(__dirname, '../sitemap.xml');
const xmlData = fs.readFileSync(sitemapPath, 'utf8');

const parser = new XMLParser({ ignoreAttributes: false });
const builder = new XMLBuilder({ ignoreAttributes: false, format: true });

const jsonObj = parser.parse(xmlData);

// Update <lastmod> tags to current date
const urls = jsonObj.urlset.url;
const today = new Date().toISOString().split('T')[0];

urls.forEach((u) => {
  u.lastmod = today;
});

// Rebuild and save XML
const newXml = builder.build({ urlset: jsonObj.urlset });
fs.writeFileSync(sitemapPath, newXml);

console.log('✅ Sitemap updated with new <lastmod> values.');

