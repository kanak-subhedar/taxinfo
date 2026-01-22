async function validateLicense() {
  const key = localStorage.getItem("LICENSE_KEYS");

  if (!key) block("License required");

  try {
    const res = await fetch("https://YOUR-RENDER-APP.onrender.com/verify-license", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        licenseKey: key,
        domain: location.hostname
      })
    });

    if (!res.ok) throw new Error();
  } catch {
    block("Invalid or revoked license");
  }
}

function block(msg) {
  document.body.innerHTML = `
    <h2 style="color:red;text-align:center">
      ${msg}<br><br>
      Purchase at t24k.com
    </h2>`;
  throw new Error(msg);
}

validateLicense();

