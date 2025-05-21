document.addEventListener("DOMContentLoaded", () => {
  const msalInstance = new msal.PublicClientApplication({
    auth: {
      clientId: CLIENT_ID,
      authority: `https://login.microsoftonline.com/${TENANT_ID}`,
      redirectUri: window.location.origin
    }
  });

  document.getElementById("buttonSSO").addEventListener("click", async () => {
    try {
      const loginResponse = await msalInstance.loginPopup({
        scopes: ["openid", "profile", "email", "User.Read"]
      });
      msalInstance.setActiveAccount(loginResponse.account);

      const tokenResponse = await msalInstance.acquireTokenSilent({
        scopes: ["User.Read"],
        account: loginResponse.account
      });

      const accessToken = tokenResponse.accessToken;
      const idToken = loginResponse.idToken;

      const res = await fetch("/auth/token-login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_token: idToken, access_token: accessToken })
      });

      if (!res.ok) throw new Error("Errore nel login backend");

      // Dopo il login, vai alla pagina vera
      window.location.href = "/";

    } catch (err) {
      console.error("Errore autenticazione:", err);
      document.getElementById("userInfo").innerText = "Errore nel login SSO.";
    }
  });
});