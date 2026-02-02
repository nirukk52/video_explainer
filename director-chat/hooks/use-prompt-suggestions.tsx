"use client";

import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";
import type { PromptSuggestion } from "@/lib/types";
import { defaultSuggestions } from "@/lib/ai/prompt-suggestions";

interface PromptSuggestionsContextType {
  suggestions: PromptSuggestion[];
  setSuggestions: (suggestions: PromptSuggestion[]) => void;
  clearSuggestions: () => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
}

const PromptSuggestionsContext = createContext<
  PromptSuggestionsContextType | undefined
>(undefined);

export function PromptSuggestionsProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [suggestions, setSuggestionsState] =
    useState<PromptSuggestion[]>(defaultSuggestions);
  const [isLoading, setIsLoading] = useState(false);

  const setSuggestions = useCallback((newSuggestions: PromptSuggestion[]) => {
    setSuggestionsState(newSuggestions);
  }, []);

  const clearSuggestions = useCallback(() => {
    setSuggestionsState([]);
  }, []);

  return (
    <PromptSuggestionsContext.Provider
      value={{
        suggestions,
        setSuggestions,
        clearSuggestions,
        isLoading,
        setIsLoading,
      }}
    >
      {children}
    </PromptSuggestionsContext.Provider>
  );
}

export function usePromptSuggestions() {
  const context = useContext(PromptSuggestionsContext);
  if (context === undefined) {
    throw new Error(
      "usePromptSuggestions must be used within a PromptSuggestionsProvider"
    );
  }
  return context;
}
