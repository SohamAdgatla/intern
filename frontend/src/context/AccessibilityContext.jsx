import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "health-dashboard-a11y";

const AccessibilityContext = createContext(null);

function loadPrefs() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

export function AccessibilityProvider({ children }) {
  const saved = loadPrefs();
  const [darkMode, setDarkMode] = useState(saved.darkMode ?? false);
  const [largeText, setLargeText] = useState(saved.largeText ?? false);
  const [highContrast, setHighContrast] = useState(saved.highContrast ?? false);
  const [reducedMotion, setReducedMotion] = useState(saved.reducedMotion ?? false);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", darkMode);
    root.classList.toggle("text-large", largeText);
    root.classList.toggle("high-contrast", highContrast);
    root.classList.toggle("reduce-motion", reducedMotion);
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ darkMode, largeText, highContrast, reducedMotion })
    );
  }, [darkMode, largeText, highContrast, reducedMotion]);

  const speak = useCallback((text) => {
    if (!text || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.92;
    utterance.pitch = 1;
    window.speechSynthesis.speak(utterance);
  }, []);

  const value = useMemo(
    () => ({
      darkMode,
      setDarkMode,
      largeText,
      setLargeText,
      highContrast,
      setHighContrast,
      reducedMotion,
      setReducedMotion,
      speak,
    }),
    [darkMode, largeText, highContrast, reducedMotion, speak]
  );

  return (
    <AccessibilityContext.Provider value={value}>{children}</AccessibilityContext.Provider>
  );
}

export function useAccessibility() {
  const ctx = useContext(AccessibilityContext);
  if (!ctx) throw new Error("useAccessibility must be used within AccessibilityProvider");
  return ctx;
}
