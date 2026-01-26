/**
 * StackedWordCaption Component
 * 
 * Displays words one-by-one as they're spoken, stacking into lines.
 * Shows a maximum of 3 lines at once - when a 4th line is needed,
 * the oldest line slides out (rolling window effect).
 * 
 * Matches the modern Varun Mayya style with serif typography
 * and mixed italic/normal styling.
 */

import React, { useMemo } from 'react';
import { interpolate, useCurrentFrame, useVideoConfig } from 'remotion';
import { WordTimestamp, TextLine, COLORS, FONTS } from './types';

interface StackedWordCaptionProps {
  /** Word timestamps from audio for sync */
  wordTimestamps: WordTimestamp[];
  /** Current playback time in seconds (relative to scene start) */
  currentTime: number;
  /** Scene start time in seconds */
  sceneStartTime: number;
  /** Maximum number of lines to show (default: 3) */
  maxLines?: number;
  /** Maximum characters per line before wrapping (default: 18) */
  maxCharsPerLine?: number;
  /** Optional style configuration for italic/normal per word */
  styleConfig?: { lines: TextLine[] };
}

/** Groups consecutive words into lines based on character limit */
function groupWordsIntoLines(
  words: string[],
  maxCharsPerLine: number
): string[][] {
  const lines: string[][] = [];
  let currentLine: string[] = [];
  let currentLength = 0;

  for (const word of words) {
    const wordLength = word.length;
    const wouldBeLength = currentLength + (currentLine.length > 0 ? 1 : 0) + wordLength;

    if (wouldBeLength > maxCharsPerLine && currentLine.length > 0) {
      // Start a new line
      lines.push(currentLine);
      currentLine = [word];
      currentLength = wordLength;
    } else {
      // Add to current line
      currentLine.push(word);
      currentLength = wouldBeLength;
    }
  }

  // Don't forget the last line
  if (currentLine.length > 0) {
    lines.push(currentLine);
  }

  return lines;
}

/** Determines if a word should be italic based on style config */
function getWordStyle(
  word: string,
  wordIndex: number,
  styleConfig?: { lines: TextLine[] }
): 'normal' | 'italic' | 'bold' {
  // If no style config, use default rules
  if (!styleConfig?.lines) {
    // Default: make certain keywords italic for emphasis
    const italicWords = ['sci-fi', 'except', 'real', 'straight'];
    return italicWords.includes(word.toLowerCase()) ? 'italic' : 'normal';
  }

  // Try to match word to style config lines
  for (const line of styleConfig.lines) {
    if (line.text.toLowerCase().includes(word.toLowerCase())) {
      return line.style;
    }
  }

  return 'normal';
}

export const StackedWordCaption: React.FC<StackedWordCaptionProps> = ({
  wordTimestamps,
  currentTime,
  sceneStartTime,
  maxLines = 3,
  maxCharsPerLine = 18,
  styleConfig,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Find all words that have been spoken up to currentTime
  const spokenWords = useMemo(() => {
    return wordTimestamps
      .filter((wt) => currentTime >= wt.start)
      .map((wt, index) => ({
        word: wt.word,
        index,
        isCurrentWord: currentTime >= wt.start && currentTime < wt.end,
        style: getWordStyle(wt.word, index, styleConfig),
      }));
  }, [wordTimestamps, currentTime, styleConfig]);

  // Group spoken words into lines
  const allLines = useMemo(() => {
    const wordStrings = spokenWords.map((w) => w.word);
    const lineGroups = groupWordsIntoLines(wordStrings, maxCharsPerLine);

    // Map back to word objects with styles
    let wordIdx = 0;
    return lineGroups.map((lineWords) => {
      return lineWords.map((word) => {
        const wordData = spokenWords[wordIdx];
        wordIdx++;
        return wordData;
      });
    });
  }, [spokenWords, maxCharsPerLine]);

  // Apply sliding window - only show last N lines
  const visibleLines = allLines.slice(-maxLines);

  // Calculate fade-in for new words
  const getWordOpacity = (wordData: typeof spokenWords[0]) => {
    const wt = wordTimestamps[wordData.index];
    if (!wt) return 1;

    // Fade in over first few frames of the word
    const wordStartFrame = wt.start * fps;
    const currentFrameInScene = currentTime * fps;
    const framesIntoWord = currentFrameInScene - wordStartFrame;

    return interpolate(framesIntoWord, [0, 5], [0, 1], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    });
  };

  // Calculate scale pop for current word
  const getWordScale = (wordData: typeof spokenWords[0]) => {
    if (!wordData.isCurrentWord) return 1;

    const wt = wordTimestamps[wordData.index];
    if (!wt) return 1;

    const wordStartFrame = wt.start * fps;
    const currentFrameInScene = currentTime * fps;
    const framesIntoWord = currentFrameInScene - wordStartFrame;

    // Small pop animation on new word
    return interpolate(framesIntoWord, [0, 3, 8], [1.1, 1.05, 1], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    });
  };

  if (visibleLines.length === 0) {
    return null;
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 4,
      }}
    >
      {visibleLines.map((line, lineIndex) => (
        <div
          key={`line-${lineIndex}-${line.map((w) => w.word).join('-')}`}
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'center',
            gap: 32,
          }}
        >
          {line.map((wordData, wordIndex) => (
            <span
              key={`${wordData.word}-${wordData.index}`}
              style={{
                fontFamily: FONTS.headline,
                fontSize: 96,
                fontWeight: wordData.style === 'bold' ? 700 : 400,
                fontStyle: wordData.style === 'italic' ? 'italic' : 'normal',
                color: COLORS.text,
                opacity: getWordOpacity(wordData),
                transform: `scale(${getWordScale(wordData)})`,
                transition: 'transform 0.1s ease-out',
                textShadow: '0 2px 8px rgba(0, 0, 0, 0.5)',
              }}
            >
              {wordData.word}
            </span>
          ))}
        </div>
      ))}
    </div>
  );
};

export default StackedWordCaption;
