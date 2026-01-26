/**
 * SplitProof Template
 * 
 * Layout: Evidence/video on top (60%), Avatar on bottom (40%)
 * Use when: Showing proof (AI video, screenshot, evidence) while avatar explains
 * 
 * Similar to SplitVideo but:
 * - Designed for "proof" content (evidence, AI-generated visuals)
 * - Supports highlight_box for drawing attention to areas
 * - Can show prompt info for AI-generated content (debug mode)
 * 
 * Visual reference: Varun Mayya frame showing screenshot evidence
 * - Evidence fills top portion (60%)
 * - Avatar talking in bottom portion (40%)
 * - Word-by-word captions overlay on evidence
 */

import React from 'react';
import { AbsoluteFill, Video, Img, useCurrentFrame, useVideoConfig, staticFile } from 'remotion';
import { Scene, LAYOUT, COLORS } from './types';
import { WordByWordCaption } from './WordByWordCaption';

interface SplitProofProps {
  scene: Scene;
  currentTime: number;
}

/**
 * SplitProof renders evidence on top with avatar below.
 * Supports video, screenshot, and AI-generated content as proof.
 * 
 * When inside a Sequence, frame 0 = scene start, so we calculate
 * local time for captions relative to scene start.
 */
export const SplitProof: React.FC<SplitProofProps> = ({ scene, currentTime: _unused }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  // Calculate local time within this scene (frame 0 = scene start)
  const localTime = frame / fps;
  
  const proofHeight = LAYOUT.height * 0.6; // 60% for proof/evidence
  const avatarHeight = LAYOUT.height * 0.4; // 40% for avatar
  
  const backgroundSrc = scene.background?.src;
  const avatarSrc = scene.avatar?.src;
  const backgroundType = scene.background?.type;
  
  // Determine if background is video (ai_video or video type)
  const isVideo = backgroundType === 'ai_video' || backgroundType === 'video';
  
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.background }}>
      {/* Proof/Evidence Area (Top 60%) */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: LAYOUT.width,
          height: proofHeight,
          overflow: 'hidden',
        }}
      >
        {/* Background content - B-Roll or Evidence */}
        {backgroundSrc && isVideo ? (
          <Video
            src={staticFile(backgroundSrc)}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
            muted
          />
        ) : backgroundSrc ? (
          <Img
            src={staticFile(backgroundSrc)}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />
        ) : (
          // Gradient fallback for missing background
          <div 
            style={{ 
              width: '100%', 
              height: '100%', 
              background: 'linear-gradient(180deg, #1a1a2e 0%, #16213e 100%)',
            }} 
          />
        )}
        
        {/* Highlight box overlay (if specified) */}
        {scene.background?.highlight_box && (
          <HighlightBox box={scene.background.highlight_box} />
        )}
        
        {/* Caption overlay on proof */}
        {scene.text?.caption_style === 'word_by_word' && scene.audio?.word_timestamps && (
          <div
            style={{
              position: 'absolute',
              bottom: 40,
              left: 0,
              right: 0,
              display: 'flex',
              justifyContent: 'center',
            }}
          >
            <WordByWordCaption
              wordTimestamps={scene.audio.word_timestamps}
              currentTime={localTime}
              sceneStartTime={0}
              style="overlay"
            />
          </div>
        )}
        
        {/* Subtle vignette overlay for cinematic effect */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.3) 100%)',
            pointerEvents: 'none',
          }}
        />
      </div>
      
      {/* Avatar Area (Bottom 40%) - Audio comes from avatar video */}
      {scene.avatar?.visible && avatarSrc && (
        <div
          style={{
            position: 'absolute',
            top: proofHeight,
            left: 0,
            width: LAYOUT.width,
            height: avatarHeight,
            overflow: 'hidden',
          }}
        >
          <Video
            src={staticFile(avatarSrc)}
            volume={1}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />
        </div>
      )}
      
      {/* Divider line between proof and avatar */}
      <div
        style={{
          position: 'absolute',
          top: proofHeight - 2,
          left: 0,
          right: 0,
          height: 4,
          background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent)',
        }}
      />
    </AbsoluteFill>
  );
};

/**
 * HighlightBox draws attention to a specific area of the proof/evidence.
 * Useful for highlighting text in screenshots or specific areas in video.
 */
const HighlightBox: React.FC<{ 
  box: { x: number; y: number; width: number; height: number } 
}> = ({ box }) => {
  return (
    <div
      style={{
        position: 'absolute',
        left: box.x,
        top: box.y,
        width: box.width,
        height: box.height,
        border: '3px solid rgba(255, 200, 0, 0.8)',
        borderRadius: 8,
        boxShadow: '0 0 20px rgba(255, 200, 0, 0.3)',
        pointerEvents: 'none',
      }}
    />
  );
};

export default SplitProof;
