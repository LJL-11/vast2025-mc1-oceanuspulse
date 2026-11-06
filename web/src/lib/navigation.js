// One navigation boundary keeps selection, camera canvases and scroll in sync.
export let moduleNavigation = null;
export function bindModuleNavigation(handler) {
  moduleNavigation = handler;
}
export function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
export function scrollToSection(target) {
  const element =
    typeof target === "string" ? document.getElementById(target) : target;
  element?.scrollIntoView({
    behavior: prefersReducedMotion() ? "instant" : "smooth",
    block: "start",
  });
}
