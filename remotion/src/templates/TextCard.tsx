/**
 * TextCard Template
 * 
 * Layout: Bold statement text on gradient background, no image
 * Use when: Dramatic pause, key statement, no visual evidence needed
 * 
 * Visual reference: Clean, impactful text-only frames
 */

import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';
import { Scene, LAYOUT, COLORS, FONTS } from './types';
import { WordByWordCaption } from './WordByWordCaption';

interface TextCardProps {
  scene: Scene;
  currentTime: number;
}

export const TextCard: React.FC<TextCardProps> = ({ scene, currentTime }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  const headline = typeof scene.text?.headline === 'string' 
    ? scene.text.headline 
    : '';
  const isDramatic = scene.text?.style === 'dramatic';
  const gradientColors = scene.background?.colors || ['#0a0a0f', '#1a1a2e'];
  
  // Animation
  const sceneStartFrame = scene.start_seconds * fps;
  const localFrame = frame - sceneStartFrame;
  
  // Spring animation for dramatic effect
  const textSpring = spring({
    frame: localFrame,
    fps,
    config: {
      damping: 15,
      stiffness: 100,
      mass: 0.5,
    },
  });
  
  const textOpacity = interpolate(localFrame, [0, 10], [0, 1], { extrapolateRight: 'clamp' });
  const textY = interpolate(textSpring, [0, 1], [30, 0]);
  
  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(180deg, ${gradientColors[0]} 0%, ${gradientColors[1]} 100%)`,
      }}
    >
      {/* Subtle radial glow */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: 600,
          height: 600,
          background: 'radial-gradient(circle, rgba(255,255,255,0.05) 0%, transparent 70%)',
          opacity: 0.5 + Math.sin(frame * 0.03) * 0.2,
        }}
      />
      
      {/* Main Headline */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 60,
          opacity: textOpacity,
          transform: `translateY(${textY}px)`,
        }}
      >
        <div
          style={{
            fontFamily: FONTS.headline,
            fontSize: isDramatic ? 64 : 52,
            fontWeight: isDramatic ? 700 : 600,
            color: COLORS.text,
            textAlign: 'center',
            lineHeight: 1.2,
            letterSpacing: isDramatic ? '0.02em' : 'normal',
          }}
        >
          {headline}
        </div>
      </div>
      
      {/* Word-by-word caption at bottom */}
      {scene.audio?.word_timestamps && (
        <div
          style={{
            position: 'absolute',
            bottom: 200,
            left: 0,
            right: 0,
            display: 'flex',
            justifyContent: 'center',
          }}
        >
          <WordByWordCaption
            wordTimestamps={scene.audio.word_timestamps}
            currentTime={currentTime}
            sceneStartTime={scene.start_seconds}
            style="standalone"
          />
        </div>
      )}
    </AbsoluteFill>
  );
};

export default TextCard;
