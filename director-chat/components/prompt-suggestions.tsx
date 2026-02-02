"use client";

import type { UseChatHelpers } from "@ai-sdk/react";
import { motion, AnimatePresence } from "framer-motion";
import { memo } from "react";
import { Sparkles } from "lucide-react";
import type { ChatMessage, PromptSuggestion } from "@/lib/types";
import { cn } from "@/lib/utils";

type PromptSuggestionsProps = {
  chatId: string;
  suggestions: PromptSuggestion[];
  sendMessage: UseChatHelpers<ChatMessage>["sendMessage"];
  isLoading?: boolean;
};

/** Color classes for suggestion category indicator dots */
const categoryColors: Record<PromptSuggestion["category"], string> = {
  progress: "text-green-500 bg-green-500",
  refine: "text-amber-500 bg-amber-500",
  explore: "text-blue-500 bg-blue-500",
};

function PurePromptSuggestions({
  chatId,
  suggestions,
  sendMessage,
  isLoading = false,
}: PromptSuggestionsProps) {
  if (isLoading) {
    return (
      <div className="flex items-center gap-1.5 text-muted-foreground/60">
        <Sparkles className="h-3 w-3 animate-pulse" />
        <span className="text-xs">Thinking...</span>
      </div>
    );
  }

  if (!suggestions || suggestions.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <AnimatePresence mode="popLayout">
        {suggestions.slice(0, 3).map((suggestion, index) => {
          const colorClass = categoryColors[suggestion.category];

          return (
            <motion.button
              key={suggestion.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{
                delay: 0.03 * index,
                type: "spring",
                stiffness: 400,
                damping: 30,
              }}
              className={cn(
                "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs",
                "border border-border/50 bg-muted/30 text-muted-foreground",
                "hover:bg-muted/50 hover:text-foreground/80 hover:border-border",
                "transition-colors cursor-pointer"
              )}
              onClick={() => {
                window.history.pushState({}, "", `/chat/${chatId}`);
                sendMessage({
                  role: "user",
                  parts: [{ type: "text", text: suggestion.text }],
                });
              }}
            >
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  colorClass.split(" ")[1]
                )}
              />
              <span className="line-clamp-1 max-w-[200px]">
                {suggestion.text}
              </span>
            </motion.button>
          );
        })}
      </AnimatePresence>
    </div>
  );
}

export const PromptSuggestions = memo(
  PurePromptSuggestions,
  (prevProps, nextProps) => {
    if (prevProps.chatId !== nextProps.chatId) return false;
    if (prevProps.isLoading !== nextProps.isLoading) return false;
    if (prevProps.suggestions.length !== nextProps.suggestions.length)
      return false;
    // Deep compare suggestion IDs
    const prevIds = prevProps.suggestions.map((s) => s.id).join(",");
    const nextIds = nextProps.suggestions.map((s) => s.id).join(",");
    if (prevIds !== nextIds) return false;
    return true;
  }
);
