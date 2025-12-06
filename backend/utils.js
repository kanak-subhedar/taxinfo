// Utility

module.exports = {
  cleanUrl(url) {
    if (!url) return "";
    return url.trim().replace(/#.*/, "");
  }
};

