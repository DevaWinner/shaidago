import type en from "../../messages/en.json";

/**
 * The English recovery copy, kept as a small module for the client error boundaries. Importing the
 * whole catalogue there would put every domain's text in the first load of every page, because a
 * JSON import is never tree-shaken. `satisfies` makes a missing or renamed key a compile error, and a
 * unit test asserts every value equals the catalogue, so the two cannot drift.
 */
export const RECOVERY = {
  notFound: {
    title: "This page is not available",
    body: "Check the address or return to the main page. ShaidaGo does not confirm whether a private record exists.",
    home: "Return to ShaidaGo"
  },
  error: {
    title: "This page could not be loaded",
    body: "Try again. If the problem continues, share the support reference without sharing private report details.",
    retry: "Try again",
    reference: "Support reference: {reference}"
  },
  loading: "Preparing this page.",
  fatal: {
    title: "ShaidaGo could not be opened"
  }
} as const satisfies typeof en.recovery;
