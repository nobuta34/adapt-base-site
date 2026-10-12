(() => {
  "use strict";
  const script = document.currentScript;
  const id = script && script.dataset.ga4Id;
  if (!/^G-[A-Z0-9]+$/.test(id || "") || !["adapt-base.com", "www.adapt-base.com"].includes(location.hostname)) return;
  const banner = document.getElementById("analytics-consent");
  const key = "ab-analytics-consent-v1";
  let enabled = false;
  function choice() { try { return localStorage.getItem(key); } catch (_) { return null; } }
  function enable() {
    if (enabled) return;
    enabled = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("consent", "default", { analytics_storage: "granted", ad_storage: "denied", ad_user_data: "denied", ad_personalization: "denied" });
    window.gtag("js", new Date());
    window.gtag("config", id, { send_page_view: false, allow_google_signals: false, allow_ad_personalization_signals: false, page_location: location.origin + location.pathname, page_referrer: "" });
    window.gtag("event", "page_view", { page_location: location.origin + location.pathname, page_title: document.title, page_referrer: "" });
    const tag = document.createElement("script");
    tag.async = true; tag.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(id);
    document.head.appendChild(tag);
  }
  banner.hidden = !!choice();
  if (choice() === "accepted") enable();
  document.getElementById("analytics-settings").addEventListener("click", () => { banner.hidden = false; banner.querySelector("button").focus(); });
  banner.addEventListener("click", (e) => {
    const button = e.target.closest("[data-analytics-choice]");
    if (!button) return;
    const value = button.dataset.analyticsChoice;
    try { localStorage.setItem(key, value); } catch (_) {}
    banner.hidden = true;
    if (value === "accepted") enable();
    else {
      window["ga-disable-" + id] = true;
      if (window.gtag) window.gtag("consent", "update", { analytics_storage: "denied" });
      for (const cookie of document.cookie.split(";")) {
        const name = cookie.split("=")[0].trim();
        if (!/^_ga(?:_|$)/.test(name)) continue;
        for (const domain of ["", "; domain=" + location.hostname, "; domain=.adapt-base.com"]) document.cookie = name + "=; Max-Age=0; path=/" + domain;
      }
      enabled = false;
      location.reload();
    }
  });
  document.addEventListener("click", (e) => {
    if (!enabled || window["ga-disable-" + id]) return;
    const link = e.target.closest("a[href]"); if (!link) return;
    const url = new URL(link.href, location.href);
    if (url.protocol === "mailto:") window.gtag("event", "contact_email_click", { contact_channel: location.pathname.startsWith("/privacy/") ? "privacy" : "contact" });
    else if (url.origin === location.origin && ["/business/", "/technical/", "/contact/"].includes(url.pathname)) window.gtag("event", "support_navigation", { destination: url.pathname });
  });
})();
