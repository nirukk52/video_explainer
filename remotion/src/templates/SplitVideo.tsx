/**
 * SplitVideo Template
 * 
 * Layout: Video on top (60%), Avatar on bottom (40%)
 * Use when: Showing video footage while avatar comments on it
 * 
 * Visual reference: Varun Mayya frame at 0:00
 * - Video fills top portion
 * - Avatar talking in bottom portion
 * - Caption overlays on video
 */

import React from 'react';
import { AbsoluteFill, Video, Img, Sequence, useCurrentFrame, useVideoConfig, staticFile } from 'remotion';
import { Scene, LAYOUT, COLORS, FONTS } from './types';
import { WordByWordCaption } from './WordByWordCaption';

interface SplitVideoProps {
  scene: Scene;
  currentTime: number;
}

export const SplitVideo: React.FC<SplitVideoProps> = ({ scene, currentTime }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  const videoHeight = LAYOUT.height * 0.6; // 60% for video
  const avatarHeight = LAYOUT.height * 0.4; // 40% for avatar
  
  const backgroundSrc = scene.background?.src;
  const avatarSrc = scene.avatar?.src;
  const isVideo = scene.background?.type === 'video';
  
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.background }}>
      {/* Video/Image Area (Top 60%) */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: LAYOUT.width,
          height: videoHeight,
          overflow: 'hidden',
        }}
      >
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
          <div style={{ width: '100%', height: '100%', backgroundColor: '#1a1a1a' }} />
        )}
        
        {/* Caption overlay on video */}
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
              currentTime={currentTime}
              sceneStartTime={scene.start_seconds}
              style="overlay"
            />
          </div>
        )}
      </div>
      
      {/* Avatar Area (Bottom 40%) */}
      {scene.avatar?.visible && avatarSrc && (
        <div
          style={{
            position: 'absolute',
            top: videoHeight,
            left: 0,
            width: LAYOUT.width,
            height: avatarHeight,
            overflow: 'hidden',
          }}
        >
          <Video
            src={staticFile(avatarSrc)}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />
        </div>
      )}
    </AbsoluteFill>
  );
};

export default SplitVideo;
