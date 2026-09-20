/**
 * The service worker's cache policy, kept apart from its event handlers so it can be unit-tested.
 * It is a plain script (loaded with importScripts in the worker and with require in tests) and does
 * no I/O. Everything not explicitly allowed here is left to the network untouched: the worker never
 * calls respondWith for it. Only public catalogue pages and immutable framework assets are ever
 * stored; nothing under /api, no report, tracking, handle, reviewer, or authentication route, no
 * request with a body, no response that says no-store or private, and no cross-origin response.
 */
(function (root) {
  var LOCALES = ["en", "ha", "ig", "yo"];
  var VERSION = "v1";
  var CACHES = {
    shell: "sg-shell-" + VERSION,
    pages: "sg-pages-" + VERSION,
    assets: "sg-assets-" + VERSION,
    prefs: "sg-prefs-" + VERSION
  };
  var LIMITS = {
    pageEntries: 40,
    assetEntries: 150,
    // A saved page is served without waiting for the network only while it is this fresh.
    freshMs: 5 * 60 * 1000,
    // A saved page is never used after this, even offline.
    maxAgeMs: 7 * 24 * 60 * 60 * 1000,
    maxBytes: 3 * 1024 * 1024,
    networkTimeoutMs: 5000
  };
  var SAVED_AT = "x-sg-saved-at";
  var PAGE_QUERY_NAMES = ["locality", "category", "status", "verification", "cursor"];
  var SLUG = "[a-z0-9][a-z0-9-]{0,119}";
  var UUID = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";
  var LOCALE = "(?:" + LOCALES.join("|") + ")";
  var PAGE_PATHS = [
    new RegExp("^/" + LOCALE + "$"),
    new RegExp("^/" + LOCALE + "/projects$"),
    new RegExp("^/" + LOCALE + "/projects/" + SLUG + "$"),
    new RegExp("^/" + LOCALE + "/projects/" + SLUG + "/sources/" + UUID + "$", "i"),
    new RegExp("^/" + LOCALE + "/trust$"),
    new RegExp("^/" + LOCALE + "/offline$")
  ];

  function searchAllowed(url) {
    var names = [];
    url.searchParams.forEach(function (value, name) {
      names.push(name);
      if (PAGE_QUERY_NAMES.indexOf(name) < 0 || value.length > 512) {
        names.push("!");
      }
    });
    return names.indexOf("!") < 0;
  }

  /**
   * "page": a public catalogue page navigation; "asset": an immutable framework file; "none":
   * anything else, including every API call, private route, framework data request, and mutation.
   */
  function classify(url, request, origin) {
    if (url.origin !== origin || request.method !== "GET" || url.username || url.password) {
      return "none";
    }
    var headers = request.headers;
    var isFrameworkData =
      (headers &&
        typeof headers.get === "function" &&
        (headers.get("rsc") || headers.get("next-router-prefetch"))) ||
      url.searchParams.has("_rsc");
    if (isFrameworkData) {
      return "none";
    }
    if (url.pathname.indexOf("/_next/static/") === 0) {
      return url.search === "" ? "asset" : "none";
    }
    if (request.mode !== "navigate") {
      return "none";
    }
    for (var index = 0; index < PAGE_PATHS.length; index += 1) {
      if (PAGE_PATHS[index].test(url.pathname)) {
        return searchAllowed(url) ? "page" : "none";
      }
    }
    return "none";
  }

  function directives(response) {
    var value = response.headers.get("cache-control") || "";
    return value.toLowerCase();
  }

  /** A response may be stored only when it is a plain, successful, same-origin, non-private one. */
  function storable(response, kind) {
    if (
      !response ||
      response.status !== 200 ||
      response.type === "opaque" ||
      response.type === "opaqueredirect"
    ) {
      return false;
    }
    if (response.redirected) {
      return false;
    }
    if (response.headers.get("set-cookie") || response.headers.get("authorization")) {
      return false;
    }
    var control = directives(response);
    if (/(^|[\s,])(no-store|private)([\s,=]|$)/.test(control)) {
      return false;
    }
    var length = Number(response.headers.get("content-length") || 0);
    if (length > LIMITS.maxBytes) {
      return false;
    }
    var type = (response.headers.get("content-type") || "").toLowerCase();
    return kind === "page" ? type.indexOf("text/html") === 0 : true;
  }

  function savedAt(response) {
    var value = response && response.headers ? response.headers.get(SAVED_AT) : null;
    var time = value ? Number(value) : NaN;
    return Number.isFinite(time) ? time : undefined;
  }

  function ageMs(response, now) {
    var stored = savedAt(response);
    return stored === undefined ? Infinity : Math.max(0, now - stored);
  }

  function localeOf(pathname) {
    var match = /^\/(en|ha|ig|yo)(?:\/|$)/.exec(pathname);
    return match ? match[1] : "en";
  }

  function offlinePath(pathname) {
    return "/" + localeOf(pathname) + "/offline";
  }

  /** Which of our own caches a name belongs to; anything else named sg- but older is deleted. */
  function isCurrentCache(name) {
    return Object.keys(CACHES).some(function (key) {
      return CACHES[key] === name;
    });
  }

  var api = {
    CACHES: CACHES,
    LIMITS: LIMITS,
    LOCALES: LOCALES,
    SAVED_AT: SAVED_AT,
    ageMs: ageMs,
    classify: classify,
    isCurrentCache: isCurrentCache,
    localeOf: localeOf,
    offlinePath: offlinePath,
    savedAt: savedAt,
    storable: storable
  };

  root.SG_POLICY = api;
})(typeof self !== "undefined" ? self : typeof globalThis !== "undefined" ? globalThis : {});
