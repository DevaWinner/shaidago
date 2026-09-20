/**
 * ShaidaGo service worker. Native Service Worker and Cache Storage APIs only, no library.
 * It stores public catalogue pages and immutable framework files, nothing else (see sw-policy.js).
 * Every request outside that allowlist is not handled here at all, so it goes straight to the
 * network: mutations, /api, reports, tracking, handles, the reviewer area, and other origins.
 */
importScripts("/sw-policy.js");

var P = self.SG_POLICY;
var PRECACHE = P.LOCALES.map(function (locale) {
  return "/" + locale + "/offline";
});
var LOW_DATA_KEY = "/__prefs/low-data";

// The files the offline pages need to run (script and style chunks named in their own HTML), so
// an offline page works the first time it is needed, not only after it has been visited.
function assetsIn(html) {
  var found = html.match(/\/_next\/static\/[^"'\s\\<>)]+/g) || [];
  return found.filter(function (path, index) {
    return found.indexOf(path) === index;
  });
}

self.addEventListener("install", function (event) {
  // Precache only the offline pages and their own assets. The worker then waits: it activates when
  // the page asks, or when every tab has closed, so an update never swaps under an open report.
  event.waitUntil(
    Promise.all([caches.open(P.CACHES.shell), caches.open(P.CACHES.assets)]).then(
      function (opened) {
        var shell = opened[0];
        var assets = opened[1];

        return Promise.all(
          PRECACHE.map(function (path) {
            return fetch(path, { credentials: "omit" }).then(function (response) {
              if (!P.storable(response, "page")) {
                return undefined;
              }
              return response
                .clone()
                .text()
                .then(function (html) {
                  return Promise.all(
                    assetsIn(html).map(function (asset) {
                      return fetch(asset, { credentials: "omit" }).then(function (file) {
                        if (P.storable(file, "asset")) {
                          return assets.put(asset, file);
                        }
                      });
                    })
                  );
                })
                .then(function () {
                  return shell.put(path, response);
                });
            });
          })
        );
      }
    )
  );
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches
      .keys()
      .then(function (names) {
        return Promise.all(
          names
            .filter(function (name) {
              return name.indexOf("sg-") === 0 && !P.isCurrentCache(name);
            })
            .map(function (name) {
              return caches.delete(name);
            })
        );
      })
      .then(function () {
        return self.clients.claim();
      })
  );
});

self.addEventListener("message", function (event) {
  if (
    event.source &&
    event.source.url &&
    new URL(event.source.url).origin !== self.location.origin
  ) {
    return;
  }
  var data = event.data || {};
  if (data.type === "SKIP_WAITING") {
    self.skipWaiting();
  } else if (data.type === "LOW_DATA") {
    event.waitUntil(
      caches.open(P.CACHES.prefs).then(function (cache) {
        return cache.put(LOW_DATA_KEY, new Response(data.value === true ? "1" : "0"));
      })
    );
  } else if (data.type === "CLEAR_SAVED_PAGES") {
    event.waitUntil(caches.delete(P.CACHES.pages));
  }
});

function lowData() {
  return caches
    .open(P.CACHES.prefs)
    .then(function (cache) {
      return cache.match(LOW_DATA_KEY);
    })
    .then(function (response) {
      return response ? response.text() : "0";
    })
    .then(function (value) {
      return value === "1";
    })
    .catch(function () {
      return false;
    });
}

function trim(cache, max) {
  return cache.keys().then(function (keys) {
    var extra = keys.length - max;
    return extra > 0
      ? Promise.all(
          keys.slice(0, extra).map(function (key) {
            return cache.delete(key);
          })
        )
      : undefined;
  });
}

/** Stores a copy stamped with the time it was saved, so the page can say how old it is. */
function savePage(request, response) {
  var copy = response.clone();
  return copy.blob().then(function (body) {
    var headers = new Headers(copy.headers);
    headers.set(P.SAVED_AT, String(Date.now()));
    var stamped = new Response(body, {
      status: copy.status,
      statusText: copy.statusText,
      headers: headers
    });
    return caches.open(P.CACHES.pages).then(function (cache) {
      return cache.put(request.url, stamped).then(function () {
        return trim(cache, P.LIMITS.pageEntries);
      });
    });
  });
}

function fromNetwork(request) {
  var controller = new AbortController();
  var timer = setTimeout(function () {
    controller.abort();
  }, P.LIMITS.networkTimeoutMs);
  return fetch(request.url, {
    credentials: "same-origin",
    signal: controller.signal,
    headers: { accept: "text/html" }
  }).finally(function () {
    clearTimeout(timer);
  });
}

function offlineFallback(url) {
  return caches.open(P.CACHES.shell).then(function (cache) {
    return cache.match(P.offlinePath(url.pathname));
  });
}

function handlePage(event) {
  var request = event.request;
  var url = new URL(request.url);

  return caches
    .open(P.CACHES.pages)
    .then(function (cache) {
      return cache.match(request.url).then(function (saved) {
        var age = saved ? P.ageMs(saved, Date.now()) : Infinity;
        var usable = saved && age <= P.LIMITS.maxAgeMs;
        var refresh = function () {
          return fromNetwork(request).then(function (response) {
            if (P.storable(response, "page")) {
              return savePage(request, response).then(function () {
                return response;
              });
            }
            return response;
          });
        };

        // Bounded stale-while-revalidate: a copy younger than freshMs is served at once and the
        // network refreshes it in the background (unless low-data mode asks for fewer transfers).
        if (usable && age <= P.LIMITS.freshMs) {
          return lowData().then(function (saving) {
            if (!saving) {
              event.waitUntil(refresh().catch(function () {}));
            }
            return saved;
          });
        }

        // Otherwise ask the network, and fall back to the saved copy (or the offline page) if it
        // fails, times out, or answers with a server error.
        return refresh()
          .then(function (response) {
            if (response.status >= 500 && usable) {
              return saved;
            }
            return response;
          })
          .catch(function () {
            return usable ? saved : offlineFallback(url);
          });
      });
    })
    .then(function (response) {
      return response || offlineFallback(url) || Response.error();
    });
}

function handleAsset(event) {
  var request = event.request;

  return caches.open(P.CACHES.assets).then(function (cache) {
    return cache.match(request.url).then(function (saved) {
      if (saved) {
        return saved;
      }
      return fetch(request.url, { credentials: "omit" }).then(function (response) {
        if (P.storable(response, "asset")) {
          event.waitUntil(
            cache.put(request.url, response.clone()).then(function () {
              return trim(cache, P.LIMITS.assetEntries);
            })
          );
        }
        return response;
      });
    });
  });
}

self.addEventListener("fetch", function (event) {
  var kind = P.classify(new URL(event.request.url), event.request, self.location.origin);

  if (kind === "page") {
    event.respondWith(handlePage(event));
  } else if (kind === "asset") {
    event.respondWith(handleAsset(event));
  }
  // Anything else: no respondWith, so the browser handles it normally, uncached by this worker.
});
