/**
 * find_broken_outbound_links.js
 *
 * Usage:
 * 1) Install Node.js (>=14)
 * 2) npm init -y
 * 3) npm i axios cheerio p-limit pretty-bytes
 * 4) Place optional seed_domains.txt (one domain per line), or run with --query "indian finance tax"
 * 5) Optionally set BING_API_KEY env var to let script discover top domains for your query.
 * 6) node find_broken_outbound_links.js
 *
 * Output:
 * - report.json
 * - report.html  (open in browser)
 *
 * NOTE: This script looks for BROKEN OUTBOUND LINKS on the seed domains.
 * It then aggregates broken link targets and sorts by the count of referring pages/domains (highest first).
 *
 * Limitations / Assumptions:
 * - If you don't supply BING_API_KEY, provide seed_domains.txt or pass --domains param.
 * - Do not run very large crawls without respecting robots.txt and rate limits.
 * - This is not a substitute for Ahrefs/SEMrush backlink reports, but finds actionable broken external links on niche sites.
 */

const axios = require('axios');
const cheerio = require('cheerio');
const pLimit = require('p-limit');
const fs = require('fs');
const path = require('path');
const prettyBytes = require('pretty-bytes');

const CONCURRENCY = 6;        // number of concurrent HTTP checks
const CRAWL_DEPTH = 1;        // 0 = only homepage, 1 = homepage + internal links
const MAX_PAGES_PER_DOMAIN = 12; // limit pages per seed domain to avoid long runs
const USER_AGENT = 'BrokenLinkFinder/1.0 (+https://t24k.com)';

const limit = pLimit(CONCURRENCY);

function sleep(ms){ return new Promise(r=>setTimeout(r, ms)); }

function normalizeUrl(u){
  try {
    const url = new URL(u);
    url.hash = '';
    return url.toString();
  } catch(e){ return null; }
}

async function fetchHtml(url){
  try {
    const res = await axios.get(url, { headers: { 'User-Agent': USER_AGENT }, timeout: 15000 });
    return res.data;
  } catch(e){
    return null;
  }
}

async function headStatus(url){
  try {
    // try HEAD first
    let res = await axios.head(url, { headers: { 'User-Agent': USER_AGENT }, timeout: 15000, maxRedirects: 6 });
    return { status: res.status, size: res.headers['content-length'] || null };
  } catch (err) {
    // try GET as fallback (some servers block HEAD)
    try {
      let res2 = await axios.get(url, { headers: { 'User-Agent': USER_AGENT }, timeout: 15000, maxRedirects: 6 });
      return { status: res2.status, size: res2.headers['content-length'] || null };
    } catch(e2){
      if (e2.response && e2.response.status) {
        return { status: e2.response.status, size: e2.response.headers && e2.response.headers['content-length'] || null };
      }
      return { status: null, error: e2.message || 'network' };
    }
  }
}

function extractLinks(baseUrl, html){
  const $ = cheerio.load(html || '');
  const anchors = $('a[href]');
  const links = new Set();
  anchors.each((i, el) => {
    let href = $(el).attr('href');
    if (!href) return;
    // ignore mailto/tel/javascript
    if (href.startsWith('mailto:') || href.startsWith('tel:') || href.startsWith('javascript:')) return;
    // relative -> absolute
    try {
      const u = new URL(href, baseUrl).toString();
      links.add(u);
    } catch(e){}
  });
  return Array.from(links);
}

async function discoverSeedDomainsFromBing(query, bingKey, count = 15){
  if (!bingKey) {
    console.log('No BING_API_KEY provided. Skipping SERP discovery.');
    return [];
  }
  console.log('Searching Bing for top results (this requires BING_API_KEY)...');
  try {
    const url = `https://api.bing.microsoft.com/v7.0/search?q=${encodeURIComponent(query)}&count=${count}&responseFilter=Webpages`;
    const res = await axios.get(url, { headers: { 'Ocp-Apim-Subscription-Key': bingKey, 'User-Agent': USER_AGENT } , timeout: 15000});
    const pages = (res.data.webPages && res.data.webPages.value) || [];
    const domains = new Set();
    pages.forEach(p => {
      try {
        const u = new URL(p.url);
        domains.add(u.hostname.replace(/^www\./,''));
      } catch(e){}
    });
    console.log(`Discovered ${domains.size} unique domains from Bing SERP.`);
    return Array.from(domains).slice(0, count);
  } catch(e){
    console.error('Bing search failed:', e.message || e);
    return [];
  }
}

async function crawlDomain(domain){
  const domainBase = `https://${domain}`;
  const pagesToVisit = new Set([domainBase, `http://${domain}`]);
  const visited = new Set();
  const outboundLinks = {}; // pageUrl -> [outbound links array]
  while(pagesToVisit.size && visited.size < MAX_PAGES_PER_DOMAIN){
    const next = pagesToVisit.values().next().value;
    pagesToVisit.delete(next);
    if (!next || visited.has(next)) continue;
    visited.add(next);
    const html = await fetchHtml(next);
    if (!html) continue;
    const links = extractLinks(next, html);
    outboundLinks[next] = links;
    if (CRAWL_DEPTH > 0) {
      // enqueue internal links (same hostname)
      links.forEach(l => {
        try {
          const u = new URL(l);
          if (u.hostname.replace(/^www\./,'') === domain && !visited.has(u.toString()) && pagesToVisit.size < MAX_PAGES_PER_DOMAIN) {
            pagesToVisit.add(u.toString());
          }
        } catch(e){}
      });
    }
    // small delay to be polite
    await sleep(200);
  }
  return outboundLinks;
}

async function checkOutboundLinksForDomain(domain){
  console.log(`Crawling: ${domain} ...`);
  const outboundByPage = await crawlDomain(domain);
  const pageUrls = Object.keys(outboundByPage);
  const checks = [];
  for(const p of pageUrls){
    for(const link of outboundByPage[p]){
      // only external links (not same domain)
      try {
        const linkHost = (new URL(link)).hostname.replace(/^www\./,'');
        if (linkHost === domain) continue;
      } catch(e){ continue; }
      const normalized = normalizeUrl(link);
      if (!normalized) continue;
      checks.push({ fromPage: p, target: normalized });
    }
  }

  // deduplicate checks by target+fromPage
  const dedup = {};
  checks.forEach(c => {
    const k = `${c.target}|||${c.fromPage}`;
    dedup[k] = c;
  });
  const uniqChecks = Object.values(dedup);

  const results = [];
  await Promise.all(uniqChecks.map(item => limit(async () => {
    const st = await headStatus(item.target);
    results.push({ fromPage: item.fromPage, target: item.target, status: st.status, error: st.error, size: st.size });
  })));

  return results;
}

function aggregateBrokenTargets(allResults){
  // allResults: array of {domain, results[]}
  const map = {}; // target -> {target, status, referring_pages: Set, referring_domains: Set, count}
  for(const entry of allResults){
    const domain = entry.domain;
    for(const r of entry.results){
      const status = r.status;
      // consider broken if status null, >=400
      if (!status || (status >= 400)) {
        const t = r.target;
        if (!map[t]) map[t] = { target: t, status: status, error: r.error || null, referring_pages: new Set(), referring_domains: new Set(), size: r.size || null };
        map[t].referring_pages.add(r.fromPage);
        map[t].referring_domains.add(domain);
      }
    }
  }
  const arr = Object.values(map).map(v => ({
    target: v.target,
    status: v.status,
    error: v.error,
    size: v.size,
    referring_pages: Array.from(v.referring_pages),
    referring_domains: Array.from(v.referring_domains),
    referring_page_count: v.referring_pages.size,
    referring_domain_count: v.referring_domains.size
  }));
  // sort by referring_domain_count desc then referring_page_count
  arr.sort((a,b) => {
    if (b.referring_domain_count !== a.referring_domain_count) return b.referring_domain_count - a.referring_domain_count;
    return b.referring_page_count - a.referring_page_count;
  });
  return arr;
}

function writeReport(aggregated, meta){
  const outJson = { meta, generated_at: new Date().toISOString(), results: aggregated };
  fs.writeFileSync('report.json', JSON.stringify(outJson, null, 2), 'utf8');
  // create a simple interactive HTML
  const rows = aggregated.map((r, i) => {
    return `<tr>
      <td>${i+1}</td>
      <td><a href="${r.target}" target="_blank" rel="noopener">${r.target}</a></td>
      <td>${r.status || 'ERR'}</td>
      <td>${r.referring_domain_count}</td>
      <td>${r.referring_page_count}</td>
      <td>${r.referring_domains.map(d=>`<div>${d}</div>`).join('')}</td>
      <td>${r.referring_pages.map(p=>`<div><a href="${p}" target="_blank">${p}</a></div>`).join('')}</td>
    </tr>`;
  }).join('\n');

  const html = `<!doctype html>
  <html>
  <head>
    <meta charset="utf-8"/>
    <title>Broken Outbound Links Report</title>
    <style>
      body{font-family: Inter, Arial; padding:20px;}
      table{border-collapse:collapse; width:100%;}
      th,td{border:1px solid #ddd; padding:8px;}
      th{background:#f5f7fa; text-align:left;}
      tr:nth-child(even){background:#fcfcfd;}
      a{color:#0066cc;}
      .meta{margin-bottom:12px; color:#666;}
      .small{font-size:12px;color:#444}
    </style>
  </head>
  <body>
    <h1>Broken Outbound Links Report</h1>
    <div class="meta">Query: ${meta.query || ''} | Seed domains: ${meta.seed_domains.join(', ')} | generated: ${new Date().toLocaleString()}</div>
    <table>
      <thead>
        <tr><th>#</th><th>Broken Target URL</th><th>HTTP</th><th>Referring Domains</th><th>Referring Pages</th><th>Domains</th><th>Referring Pages (links)</th></tr>
      </thead>
      <tbody>
        ${rows}
      </tbody>
    </table>
    <p class="small">Note: This report finds broken outbound links present on the seed domains (niche sites). For full backlink analysis (incoming links to a domain), use a backlink provider (Ahrefs/SEMrush).</p>
  </body>
  </html>`;
  fs.writeFileSync('report.html', html, 'utf8');
  console.log('Wrote report.json and report.html');
}

async function main(){
  const argv = require('minimist')(process.argv.slice(2));
  const query = argv.query || argv.q || null;
  const domainsArg = argv.domains || argv.d || null;

  let seedDomains = [];

  // load from seed_domains.txt if present
  if (fs.existsSync('seed_domains.txt')) {
    const content = fs.readFileSync('seed_domains.txt','utf8').split(/\r?\n/).map(s=>s.trim()).filter(Boolean);
    seedDomains = seedDomains.concat(content);
  }

  if (domainsArg){
    const parts = domainsArg.split(',').map(s=>s.trim()).filter(Boolean);
    seedDomains = seedDomains.concat(parts);
  }

  const bingKey = process.env.BING_API_KEY || null;

  if (query && !seedDomains.length){
    const discovered = await discoverSeedDomainsFromBing(query, bingKey, 20);
    seedDomains = seedDomains.concat(discovered);
  }

  if (!seedDomains.length){
    console.error('No seed domains. Provide seed_domains.txt, or pass --domains "domain1,domain2", or use --query "your niche" with BING_API_KEY env var.');
    process.exit(1);
  }

  // normalize domains (strip https etc)
  seedDomains = Array.from(new Set(seedDomains.map(d => d.replace(/^https?:\/\//,'').replace(/\/.*$/,'').replace(/^www\./,'').trim())));

  console.log('Using seed domains:', seedDomains.join(', '));
  const allResults = [];
  for(const sd of seedDomains){
    try {
      const res = await checkOutboundLinksForDomain(sd);
      allResults.push({ domain: sd, results: res });
    } catch(e){
      console.error('Failed domain', sd, e.message || e);
    }
  }

  const aggregated = aggregateBrokenTargets(allResults);
  writeReport(aggregated, { query: query || null, seed_domains: seedDomains });
}

main().catch(e=>{ console.error(e); process.exit(1); });
