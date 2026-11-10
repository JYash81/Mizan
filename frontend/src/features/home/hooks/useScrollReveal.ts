import { useEffect, useRef } from "react";

export function useScrollReveal(threshold = 0.12) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    // Gracefully handle environments without IntersectionObserver (e.g. jsdom / SSR)
    if (typeof window === "undefined" || !("IntersectionObserver" in window)) {
      el.classList.add("revealed");
      el.querySelectorAll(".scroll-reveal").forEach((child) => child.classList.add("revealed"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("revealed");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold, rootMargin: "0px 0px -60px 0px" }
    );

    // Observe the container and all child .scroll-reveal elements
    const children = el.querySelectorAll(".scroll-reveal");
    children.forEach((child) => observer.observe(child));
    if (el.classList.contains("scroll-reveal")) {
      observer.observe(el);
    }

    return () => observer.disconnect();
  }, [threshold]);

  return ref;
}
