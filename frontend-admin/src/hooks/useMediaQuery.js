import { useEffect, useState } from "react";

// Phones: below the 640px breakpoint used throughout index.css.
export const PHONE_QUERY = "(max-width: 639.98px)";

/** True while the CSS media query matches (updates on resize/rotation). */
export default function useMediaQuery(query) {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);

  useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = () => setMatches(mql.matches);
    onChange();
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [query]);

  return matches;
}
