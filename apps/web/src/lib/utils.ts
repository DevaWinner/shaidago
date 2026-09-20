import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

// The theme's own font sizes (`text-ledger-lg`) must be known as sizes, or the merge would treat
// them as colours and silently drop a real text colour from the same element.
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [
        {
          text: [
            "ledger-display",
            "ledger-xl",
            "ledger-lg",
            "ledger-base",
            "ledger-sm",
            "ledger-xs"
          ]
        }
      ]
    }
  }
});

/** The shadcn class helper: conditional classes merged so a later utility wins over an earlier one. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
