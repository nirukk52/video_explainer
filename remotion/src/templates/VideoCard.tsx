/**
 * VideoCard Template
 * 
 * Layout: Styled text on top, rounded video card in center, black background
 * Use when: Dramatic reveal with video evidence, text builds anticipation
 * 
 * Visual reference: Varun Mayya frame at 0:02-0:03
 * - Black background
 * - Serif text with mixed italic/regular styling
 * - Video in rounded rectangle in center
 * - Text animates word by word
 */

import React from 'react';
import { AbsoluteFill, Video, Img, useCurrentFrame, useVideoConfig, staticFile, interpolate } from 'remotion';
import { Scene, LAYOUT, COLORS, FONTS, TextLine } from './types';
import { WordByWordCaption } from './WordByWordCaption';

interface VideoCardProps {
  scene: Scene;
  currentTime: number;
}

export const VideoCard: React.FC<VideoCardProps> = ({ scene, currentTime }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  const videoInset = scene.video_inset;
  const headline = scene.text?.headline;
  
  // Calculate video dimensions
  const videoWidth = videoInset ? LAYOUT.width * (videoInset.width_percent / 100) : LAYOUT.width * 0.85;
  const videoHeight = videoWidth * (9 / 16); // Maintain 16:9 aspect ratio for inset
  const borderRadius = videoInset?.border_radius ?? 16;
  
  // Parse headline lines if structured
  const headlineLines: TextLine[] = typeof headline === 'object' && headline?.lines 
    ? headline.lines 
    : headline 
      ? [{ text: headline as string, style: 'normal' as const }] 
      : [];
  
  // Animation: text fades/slides in
  const sceneStartFrame = scene.start_seconds * fps;
  const localFrame = frame - sceneStartFrame;
  const textOpacity = interpolate(localFrame, [0, 10], [0, 1], { extrapolateRight: 'clamp' });
  const textY = interpolate(localFrame, [0, 15], [20, 0], { extrapolateRight: 'clamp' });
  
  return (
    <AbsoluteFill style={{ backgroundColor: scene.background?.color || COLORS.background }}>
      {/* Styled Headline Text (Top area) */}
      <div
        style={{
          position: 'absolute',
          top: 120,
          left: 0,
          right: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          opacity: textOpacity,
          transform: `translateY(${textY}px)`,
        }}
      >
        {headlineLines.map((line, index) => (
          <div
            key={index}
            style={{
              fontFamily: FONTS.headline,
              fontSize: 52,
              fontWeight: line.style === 'bold' ? 700 : 400,
              fontStyle: line.style === 'italic' ? 'italic' : 'normal',
              color: COLORS.text,
              textAlign: 'center',
              lineHeight: 1.2,
              padding: '0 40px',
            }}
          >
            {line.text}
          </div>
        ))}
      </div>
      
      {/* Video Card (Center) */}
      {videoInset?.src && (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -40%)', // Slightly above center
            width: videoWidth,
            height: videoHeight,
            borderRadius: borderRadius,
            overflow: 'hidden',
            border: videoInset.border_color ? `2px solid ${videoInset.border_color}` : 'none',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
          }}
        >
          <Video
            src={staticFile(videoInset.src)}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
            muted
          />
        </div>
      )}
      
      {/* Word-by-word caption (if enabled) */}
      {scene.text?.animate === 'word_by_word' && scene.audio?.word_timestamps && (
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

export default VideoCard;
