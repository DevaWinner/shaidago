import { notFound } from "next/navigation";

// Any path under a locale that no route claims is a 404 inside the locale layout, so the
// not-found page keeps the shell and the correct `lang` instead of the framework default.
export default function UnknownPath(): never {
  notFound();
}
