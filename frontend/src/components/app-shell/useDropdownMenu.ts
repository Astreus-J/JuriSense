import { useEffect, useRef, useState } from "react";

/**
 * Shared open/close + keyboard behavior for the small menu-button widgets in
 * the app shell (`OrgSwitcher`, `UserMenu`): click-outside to close, Escape
 * to close and return focus to the trigger, focus the first item on open,
 * and arrow-key roving focus between items — the WAI-ARIA Menu Button
 * pattern's baseline keyboard support.
 */
export function useDropdownMenu() {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const itemRefs = useRef<Array<HTMLButtonElement | null>>([]);

  useEffect(() => {
    if (!open) return;
    function handlePointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    itemRefs.current[0]?.focus();
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  function registerItem(index: number) {
    return (el: HTMLButtonElement | null) => {
      itemRefs.current[index] = el;
    };
  }

  function focusItem(delta: number) {
    const items = itemRefs.current.filter(Boolean) as HTMLButtonElement[];
    if (items.length === 0) return;
    const currentIndex = items.indexOf(document.activeElement as HTMLButtonElement);
    const nextIndex = (currentIndex + delta + items.length) % items.length;
    items[nextIndex]?.focus();
  }

  function handleItemKeyDown(event: React.KeyboardEvent) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      focusItem(1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      focusItem(-1);
    }
  }

  return { open, setOpen, containerRef, triggerRef, registerItem, handleItemKeyDown };
}
