/**
 * WordByWordCaption Component
 * 
 * Displays captions that highlight word-by-word as the audio plays.
 * Matches the TikTok/Varun Mayya style of synced captions.
 */

import React from 'react';
import { interpolate } from 'remotion';
import { WordTimestamp, COLORS, FONTS } from './types';

interface WordByWordCaptionProps {
  wordTimestamps: WordTimestamp[];
  currentTime: number;
  sceneStartTime: number;
  style: 'overlay' | 'standalone';
}

export const WordByWordCaption: React.FC<WordByWordCaptionProps> = ({
  wordTimestamps,
  currentTime,
  sceneStartTime,
  style,
}) => {
  // Find current word based on time
  const currentWordIndex = wordTimestamps.findIndex(
    (wt) => currentTime >= wt.start && currentTime < wt.end
  );
  
  // Get the current word (or last spoken word if between words)
  const activeIndex = currentWordIndex >= 0 
    ? currentWordIndex 
    : wordTimestamps.findIndex((wt) => currentTime < wt.start) - 1;
  
  // Get current spoken word for display
  const currentWord = activeIndex >= 0 && activeIndex < wordTimestamps.length
    ? wordTimestamps[activeIndex].word
    : '';
  
  const isOverlay = style === 'overlay';
  
  return (
    <div
      style={{
        padding: isOverlay ? '12px 24px' : '16px 32px',
        backgroundColor: isOverlay ? 'rgba(0, 0, 0, 0.7)' : 'transparent',
        borderRadius: isOverlay ? 8 : 0,
      }}
    >
      <span
        style={{
          fontFamily: FONTS.caption,
          fontSize: isOverlay ? 28 : 36,
          fontWeight: 600,
          color: COLORS.text,
          textTransform: 'none',
          letterSpacing: '0.02em',
        }}
      >
        {currentWord}
      </span>
    </div>
  );
};

export default WordByWordCaption;
