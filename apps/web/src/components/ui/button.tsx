import { cva, type VariantProps } from "class-variance-authority";
import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * shadcn-style variants on the Field ledger theme. Sizing is a 44px minimum target, labels wrap
 * instead of clipping, and forced-colours mode restores a visible border.
 */
export const buttonVariants = cva(
  "inline-flex min-h-11 min-w-11 max-w-full cursor-pointer items-center justify-center gap-2 rounded-ledger-control border px-3 py-2 text-center font-semibold [overflow-wrap:anywhere] no-underline forced-colors:border-2 forced-colors:border-[ButtonText]",
  {
    variants: {
      variant: {
        primary:
          "border-ledger-accent-strong bg-primary text-primary-foreground hover:bg-ledger-accent-strong",
        secondary: "border-foreground bg-card text-foreground",
        danger: "border-destructive bg-destructive text-destructive-foreground"
      },
      size: { default: "", icon: "w-11 p-2" }
    },
    defaultVariants: { variant: "primary", size: "default" }
  }
);

export type ButtonVariant = NonNullable<VariantProps<typeof buttonVariants>["variant"]>;

export function Button({
  children,
  className,
  size,
  variant = "primary",
  ...properties
}: ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants>): ReactNode {
  return (
    <button
      className={cn(buttonVariants({ variant, size }), className)}
      data-slot="button"
      data-variant={variant}
      type="button"
      {...properties}
    >
      {children}
    </button>
  );
}

export function IconButton({
  children,
  className,
  label,
  ...properties
}: Omit<ButtonHTMLAttributes<HTMLButtonElement>, "aria-label"> &
  Readonly<{ label: string }>): ReactNode {
  return (
    <Button
      aria-label={label}
      className={className}
      size="icon"
      variant="secondary"
      {...properties}
    >
      <span aria-hidden="true">{children}</span>
    </Button>
  );
}

/** An anchor that looks like a button, for navigation that must work without JavaScript. */
export function ButtonLink({
  children,
  className,
  variant = "primary",
  ...properties
}: AnchorHTMLAttributes<HTMLAnchorElement> & Readonly<{ variant?: ButtonVariant }>): ReactNode {
  return (
    <a
      className={cn(buttonVariants({ variant }), className)}
      data-slot="button"
      data-variant={variant}
      {...properties}
    >
      {children}
    </a>
  );
}

export function Link({
  children,
  className,
  ...properties
}: AnchorHTMLAttributes<HTMLAnchorElement>): ReactNode {
  return (
    <a
      className={cn(
        "font-semibold text-ledger-accent-strong underline underline-offset-[0.2em]",
        className
      )}
      data-slot="link"
      {...properties}
    >
      {children}
    </a>
  );
}
