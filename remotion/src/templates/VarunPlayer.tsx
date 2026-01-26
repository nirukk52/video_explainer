/**
 * VarunPlayer - Main composition for Varun Mayya style shorts
 * 
 * Renders scenes based on the JSON script definition using Sequences.
 * Each scene is wrapped in a Sequence for proper video/audio timing.
 * 
 * Key: Uses Sequences instead of conditional rendering so that
 * videos play correctly from start to finish.
 */

import React from 'react';
import { AbsoluteFill, Sequence, Audio, useVideoConfig, useCurrentFrame, staticFile } from 'remotion';
import { Script, Scene, LAYOUT, COLORS } from './types';
import { SplitVideo } from './SplitVideo';
import { SplitProof } from './SplitProof';
import { VideoCard } from './VideoCard';
import { TextOverProof } from './TextOverProof';
import { TextCard } from './TextCard';
import { CompositeScene } from './CompositeScene';

interface VarunPlayerProps {
  script: Script;
}

export const VarunPlayer: React.FC<VarunPlayerProps> = ({ script }) => {
  const { fps } = useVideoConfig();
  
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.background }}>
      {/* Render each scene in its own Sequence for proper timing */}
      {script.scenes.map((scene, index) => {
        const startFrame = Math.round(scene.start_seconds * fps);
        const durationFrames = Math.round((scene.end_seconds - scene.start_seconds) * fps);
        
        return (
          <Sequence
            key={scene.id}
            name={`Scene ${index + 1}: ${scene.id}`}
            from={startFrame}
            durationInFrames={durationFrames}
          >
            <SceneWithAudio scene={scene} fps={fps} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

/**
 * Wrapper component that handles both scene rendering and audio.
 * Uses useCurrentFrame inside the Sequence for scene-relative timing.
 */
const SceneWithAudio: React.FC<{ scene: Scene; fps: number }> = ({ scene, fps }) => {
  const frame = useCurrentFrame();
  // currentTime is relative to the scene start (since we're inside a Sequence)
  const currentTime = frame / fps;
  
  return (
    <>
      {/* Render the scene template with correct currentTime */}
      <SceneRenderer scene={scene} currentTime={currentTime} />
      
      {/* Handle avatar audio when use_avatar_audio is true */}
      {scene.avatar?.use_avatar_audio && scene.avatar?.src && (
        <Audio src={staticFile(scene.avatar.src)} />
      )}
    </>
  );
};

/** Renders the correct template based on scene.template */
const SceneRenderer: React.FC<{ scene: Scene; currentTime: number }> = ({ scene, currentTime }) => {
  switch (scene.template) {
    case 'composite':
      return <CompositeScene scene={scene} currentTime={currentTime} />;
    
    case 'SplitVideo':
      return <SplitVideo scene={scene} currentTime={currentTime} />;
    
    case 'SplitProof':
      return <SplitProof scene={scene} currentTime={currentTime} />;
    
    case 'VideoCard':
      return <VideoCard scene={scene} currentTime={currentTime} />;
    
    case 'TextOverProof':
      return <TextOverProof scene={scene} currentTime={currentTime} />;
    
    case 'TextCard':
      return <TextCard scene={scene} currentTime={currentTime} />;
    
    // TODO: Implement other templates
    case 'FullAvatar':
    case 'ProofOnly':
    default:
      return (
        <AbsoluteFill style={{ 
          backgroundColor: '#1a1a1a',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <div style={{ color: '#fff', fontSize: 32 }}>
            Template "{scene.template}" not yet implemented
          </div>
        </AbsoluteFill>
      );
  }
};

export default VarunPlayer;
