/**
 * TextOverProof Template
 * 
 * Layout: Bold headline text overlaid on evidence screenshot
 * Use when: Key quotes or headlines that need emphasis over proof image
 * 
 * Visual reference: Varun Mayya style with bold serif text over cropped images
 */

import React from 'react';
import { AbsoluteFill, Img, useCurrentFrame, useVideoConfig, staticFile, interpolate } from 'remotion';
import { Scene, LAYOUT, COLORS, FONTS } from './types';
import { WordByWordCaption } from './WordByWordCaption';

interface TextOverProofProps {
  scene: Scene;
  currentTime: number;
}

export const TextOverProof: React.FC<TextOverProofProps> = ({ scene, currentTime }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  const backgroundSrc = scene.background?.src;
  const headline = typeof scene.text?.headline === 'string' 
    ? scene.text.headline 
    : '';
  const highlightWords = scene.text?.highlight_words || [];
  
  // Animation
  const sceneStartFrame = scene.start_seconds * fps;
  const localFrame = frame - sceneStartFrame;
  const textOpacity = interpolate(localFrame, [0, 8], [0, 1], { extrapolateRight: 'clamp' });
  const textScale = interpolate(localFrame, [0, 12], [0.95, 1], { extrapolateRight: 'clamp' });
  const imageScale = interpolate(localFrame, [0, 30], [1.05, 1], { extrapolateRight: 'clamp' });
  
  // Split headline into words and highlight specified ones
  const words = headline.split(' ');
  
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.background }}>
      {/* Evidence Screenshot (full background with slight zoom) */}
      {backgroundSrc && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            overflow: 'hidden',
          }}
        >
          <Img
            src={staticFile(backgroundSrc)}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              transform: `scale(${imageScale})`,
              filter: 'brightness(0.7)', // Darken for text readability
            }}
          />
        </div>
      )}
      
      {/* Dark gradient overlay for text readability */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '40%',
          background: 'linear-gradient(180deg, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0) 100%)',
        }}
      />
      
      {/* Bold Headline Text */}
      <div
        style={{
          position: 'absolute',
          top: 120,
          left: 40,
          right: 40,
          opacity: textOpacity,
          transform: `scale(${textScale})`,
        }}
      >
        <div
          style={{
            fontFamily: FONTS.headline,
            fontSize: 56,
            fontWeight: 700,
            color: COLORS.text,
            lineHeight: 1.1,
            textShadow: '0 4px 12px rgba(0,0,0,0.5)',
          }}
        >
          {words.map((word, index) => {
            const isHighlighted = highlightWords.includes(word.toLowerCase()) || 
                                  highlightWords.includes(word);
            return (
              <span
                key={index}
                style={{
                  fontStyle: isHighlighted ? 'italic' : 'normal',
                  marginRight: '0.3em',
                }}
              >
                {word}
              </span>
            );
          })}
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
            style="overlay"
          />
        </div>
      )}
    </AbsoluteFill>
  );
};

export default TextOverProof;
