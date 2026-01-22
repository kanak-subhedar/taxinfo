async function validateLicense() {
  const userKey = localStorage.getItem("T24K_LICENSE");

  if (!userKey) {
    block("License key missing");
    return;
  }

  try {
    const res = await fetch("https://YOUR-APP.onrender.com/verify-license", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        licenseKey: userKey,
        domain: location.hostname
      })
    });

    const data = await res.json();

    if (!data.valid) throw new Error();

  } catch {
    block("Invalid or expired license");
  }
}

function block(msg) {
  document.body.innerHTML = `
    <h2 style="text-align:center;color:red">
      ${msg}<br><br>
      Purchase from t24k.com
    </h2>`;
}

validateLicense();
