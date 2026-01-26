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
import { StackedWordCaption } from './StackedWordCaption';

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
  const baseHeight = videoWidth * (9 / 16); // Base 16:9 aspect ratio
  const heightMultiplier = videoInset?.height_multiplier ?? 1;
  const videoHeight = baseHeight * heightMultiplier;
  const borderRadius = videoInset?.border_radius ?? 16;
  const borderWidth = videoInset?.border_width ?? 2;
  
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
  
  // Check if we should use word-by-word animated captions
  const useAnimatedCaptions = scene.text?.animate === 'word_by_word' && scene.audio?.word_timestamps;
  
  // Get style config for word styling (italic/normal based on headline lines)
  const styleConfig = typeof headline === 'object' && headline?.lines
    ? { lines: headline.lines }
    : undefined;
  
  return (
    <AbsoluteFill style={{ backgroundColor: scene.background?.color || COLORS.background }}>
      {/* Text Area (Top) - Either animated word-by-word or static headline */}
      <div
        style={{
          position: 'absolute',
          top: 120,
          left: 0,
          right: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          padding: '0 40px',
        }}
      >
        {useAnimatedCaptions ? (
          /* Animated word-by-word captions with 3-line sliding window */
          <StackedWordCaption
            wordTimestamps={scene.audio!.word_timestamps!}
            currentTime={currentTime}
            sceneStartTime={scene.start_seconds}
            maxLines={3}
            maxCharsPerLine={18}
            styleConfig={styleConfig}
          />
        ) : (
          /* Static headline (original behavior) */
          <div
            style={{
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
                }}
              >
                {line.text}
              </div>
            ))}
          </div>
        )}
      </div>
      
      {/* Video Card (Center) */}
      {videoInset?.src && (
        <div
          style={{
            position: 'absolute',
            top: '45%',
            left: '50%',
            transform: 'translate(-50%, -40%)', // Above center
            width: videoWidth,
            height: videoHeight,
            borderRadius: borderRadius,
            overflow: 'hidden',
            border: videoInset.border_color ? `${borderWidth}px solid ${videoInset.border_color}` : 'none',
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
    </AbsoluteFill>
  );
};

export default VideoCard;
