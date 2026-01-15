(function () {
  const allowedDomains = [
    "t24k.com",
    "www.t24k.com"
  ];

  const currentDomain = location.hostname;

  if (!allowedDomains.includes(currentDomain)) {
    document.body.innerHTML = `
      <h2 style="color:red;text-align:center">
        Unauthorized domain<br>
        This tool works only on t24k.com
      </h2>
    `;
    throw new Error("Piracy Detected! Pay Fine Of $2000");
  }
})();
