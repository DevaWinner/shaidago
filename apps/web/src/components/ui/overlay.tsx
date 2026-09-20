"use client";

import { Dialog } from "@base-ui/react/dialog";
import { Popover } from "@base-ui/react/popover";
import type { ReactNode } from "react";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Overlays are Base UI (shadcn's own headless layer) styled with theme utilities. Each renders
 * its own trigger so the library can restore focus to it on close.
 */

const backdrop = "fixed inset-0 bg-[rgb(23_35_35/45%)]";
const viewport = "fixed inset-0 grid overflow-y-auto p-[var(--layout-gutter)]";
const popup =
  "box-border grid w-full max-w-[min(100%,68ch)] max-h-full gap-3 overflow-y-auto rounded-ledger-control border border-border bg-popover p-6 text-popover-foreground shadow-ledger-overlay [overflow-wrap:anywhere]";
const secondaryButton = buttonVariants({ variant: "secondary" });

type OverlayProperties = Readonly<{
  children: ReactNode;
  closeLabel: string;
  description: string;
  onOpenChange?: (open: boolean) => void;
  open?: boolean;
  title: string;
  triggerLabel: string;
}>;

function DialogShell({
  children,
  closeLabel,
  description,
  onOpenChange,
  open,
  placement,
  title,
  triggerLabel
}: OverlayProperties & Readonly<{ placement: "modal" | "sheet" }>): ReactNode {
  return (
    <Dialog.Root
      {...(onOpenChange === undefined ? {} : { onOpenChange })}
      {...(open === undefined ? {} : { open })}
    >
      <Dialog.Trigger className={secondaryButton} data-slot="button" data-variant="secondary">
        {triggerLabel}
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Backdrop className={backdrop} />
        <Dialog.Viewport
          className={cn(
            viewport,
            placement === "sheet" ? "items-end justify-items-center" : "place-items-center"
          )}
        >
          <Dialog.Popup
            className={cn(popup, placement === "sheet" && "rounded-b-none border-b-0")}
            data-placement={placement}
            data-slot="dialog"
          >
            <Dialog.Title className="m-0 text-ledger-lg">{title}</Dialog.Title>
            <Dialog.Description>{description}</Dialog.Description>
            {children}
            <Dialog.Close className={secondaryButton} data-slot="button" data-variant="secondary">
              {closeLabel}
            </Dialog.Close>
          </Dialog.Popup>
        </Dialog.Viewport>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function Modal(properties: OverlayProperties): ReactNode {
  return <DialogShell {...properties} placement="modal" />;
}

/** The same dialog anchored to the bottom edge on small screens. */
export function Sheet(properties: OverlayProperties): ReactNode {
  return <DialogShell {...properties} placement="sheet" />;
}

/**
 * A decision that changes something needs an explicit second action. Cancel is first in focus
 * order and closing never confirms; `onConfirm` runs only from the confirm button.
 */
export function ConfirmDialog({
  cancelLabel,
  confirmLabel,
  description,
  destructive = false,
  onConfirm,
  title,
  triggerLabel
}: Readonly<{
  cancelLabel: string;
  confirmLabel: string;
  description: string;
  destructive?: boolean;
  onConfirm: () => void;
  title: string;
  triggerLabel: string;
}>): ReactNode {
  return (
    <Dialog.Root>
      <Dialog.Trigger className={secondaryButton} data-slot="button" data-variant="secondary">
        {triggerLabel}
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Backdrop className={backdrop} />
        <Dialog.Viewport className={cn(viewport, "place-items-center")}>
          <Dialog.Popup
            className={popup}
            data-placement="modal"
            data-slot="dialog"
            role="alertdialog"
          >
            <Dialog.Title className="m-0 text-ledger-lg">{title}</Dialog.Title>
            <Dialog.Description>{description}</Dialog.Description>
            <div className="flex flex-wrap gap-3">
              <Dialog.Close className={secondaryButton} data-slot="button" data-variant="secondary">
                {cancelLabel}
              </Dialog.Close>
              <Dialog.Close
                className={buttonVariants({ variant: destructive ? "danger" : "primary" })}
                onClick={onConfirm}
              >
                {confirmLabel}
              </Dialog.Close>
            </div>
          </Dialog.Popup>
        </Dialog.Viewport>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function PopoverCard({
  children,
  content,
  triggerLabel
}: Readonly<{ children?: ReactNode; content: ReactNode; triggerLabel: string }>): ReactNode {
  return (
    <Popover.Root>
      <Popover.Trigger className={secondaryButton} data-slot="button" data-variant="secondary">
        {triggerLabel}
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Positioner>
          <Popover.Popup className={cn(popup, "w-auto")} data-slot="popover">
            {content}
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
      {children}
    </Popover.Root>
  );
}
