/**
 * VarunPlayer - Main composition for Varun Mayya style shorts
 * 
 * Renders scenes based on the JSON script definition.
 * Each scene specifies a template, and this player renders
 * the appropriate template component with the scene data.
 * 
 * Audio is rendered per-scene using Sequence components for proper timing.
 */

import React from 'react';
import { AbsoluteFill, Audio, Sequence, useCurrentFrame, useVideoConfig, staticFile } from 'remotion';
import { Script, Scene, LAYOUT, COLORS } from './types';
import { SplitVideo } from './SplitVideo';
import { VideoCard } from './VideoCard';
import { TextOverProof } from './TextOverProof';
import { TextCard } from './TextCard';

interface VarunPlayerProps {
  script: Script;
  audioPath?: string;
}

export const VarunPlayer: React.FC<VarunPlayerProps> = ({ script, audioPath }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTime = frame / fps;
  
  // Find current scene based on time
  const currentScene = script.scenes.find(
    (scene) => currentTime >= scene.start_seconds && currentTime < scene.end_seconds
  );
  
  if (!currentScene) {
    return (
      <AbsoluteFill style={{ backgroundColor: COLORS.background }}>
        <div style={{ 
          color: COLORS.text, 
          fontSize: 32, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          height: '100%',
        }}>
          No scene at {currentTime.toFixed(2)}s
        </div>
      </AbsoluteFill>
    );
  }
  
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.background }}>
      {/* Render the appropriate template */}
      <SceneRenderer scene={currentScene} currentTime={currentTime} />
      
      {/* Per-scene audio tracks - each scene can have its own audio file */}
      {script.scenes.map((scene) => {
        if (!scene.audio?.file) return null;
        const startFrame = Math.round(scene.start_seconds * fps);
        const durationFrames = Math.round((scene.end_seconds - scene.start_seconds) * fps);
        return (
          <Sequence key={scene.id} from={startFrame} durationInFrames={durationFrames}>
            <Audio src={staticFile(scene.audio.file)} />
          </Sequence>
        );
      })}
      
      {/* Legacy: single audio track for entire video (if audioPath provided) */}
      {audioPath && (
        <Audio src={staticFile(audioPath)} />
      )}
    </AbsoluteFill>
  );
};

/** Renders the correct template based on scene.template */
const SceneRenderer: React.FC<{ scene: Scene; currentTime: number }> = ({ scene, currentTime }) => {
  switch (scene.template) {
    case 'SplitVideo':
      return <SplitVideo scene={scene} currentTime={currentTime} />;
    
    case 'VideoCard':
      return <VideoCard scene={scene} currentTime={currentTime} />;
    
    case 'TextOverProof':
      return <TextOverProof scene={scene} currentTime={currentTime} />;
    
    case 'TextCard':
      return <TextCard scene={scene} currentTime={currentTime} />;
    
    // TODO: Implement other templates
    case 'SplitProof':
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
