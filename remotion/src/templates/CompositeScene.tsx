/**
 * CompositeScene Template
 * 
 * A scene that contains multiple word_groups, each with its own template.
 * This enables different visual treatments within a single scene based on
 * which words are being spoken.
 * 
 * Example: "This video from China" uses SplitProof, then "looks like..." uses VideoCard
 * 
 * The component determines which word_group is active based on currentTime
 * and renders the appropriate template for that segment.
 */

import React from 'react';
import { AbsoluteFill, Audio, Sequence, useVideoConfig, staticFile } from 'remotion';
import { Scene, WordGroup, CompositeSceneAudio, LAYOUT, COLORS } from './types';
import { SplitVideo } from './SplitVideo';
import { SplitProof } from './SplitProof';
import { VideoCard } from './VideoCard';
import { TextOverProof } from './TextOverProof';
import { TextCard } from './TextCard';

interface CompositeSceneProps {
  scene: Scene;
  currentTime: number;
}

/**
 * Renders different templates based on which word_group is currently active.
 * Each word_group has its own time range and template configuration.
 */
export const CompositeScene: React.FC<CompositeSceneProps> = ({ scene, currentTime }) => {
  const { fps } = useVideoConfig();
  
  // Get word groups or fallback to treating whole scene as one group
  const wordGroups = scene.word_groups || [];
  
  if (wordGroups.length === 0) {
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
          No word_groups defined for composite scene
        </div>
      </AbsoluteFill>
    );
  }
  
  // Calculate time relative to scene start
  const sceneRelativeTime = currentTime - scene.start_seconds;
  
  // Find the active word_group based on current time
  const activeGroup = wordGroups.find(
    (group) => sceneRelativeTime >= group.start_seconds && sceneRelativeTime < group.end_seconds
  );
  
  if (!activeGroup) {
    // Between word groups or out of range
    return (
      <AbsoluteFill style={{ backgroundColor: COLORS.background }} />
    );
  }
  
  // Create a synthetic scene from the word_group for template rendering
  const groupScene = createSceneFromWordGroup(scene, activeGroup, sceneRelativeTime);
  
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.background }}>
      {/* Render the template for the active word group */}
      <WordGroupRenderer 
        wordGroup={activeGroup} 
        scene={groupScene} 
        currentTime={sceneRelativeTime} 
      />
      
      {/* Audio tracks - handle multiple audio files for composite scenes */}
      <CompositeAudio scene={scene} fps={fps} />
    </AbsoluteFill>
  );
};

/**
 * Creates a Scene object from a WordGroup for template rendering.
 * This allows reusing existing template components with word_group data.
 */
function createSceneFromWordGroup(
  parentScene: Scene, 
  wordGroup: WordGroup,
  currentTimeInScene: number
): Scene {
  // Extract word timestamps for this word group
  const parentAudio = parentScene.audio;
  let wordTimestamps = parentAudio?.word_timestamps;
  
  if (wordTimestamps && wordGroup.word_range) {
    // Filter timestamps to only include words in this group's range
    wordTimestamps = wordTimestamps.slice(
      wordGroup.word_range.start,
      wordGroup.word_range.end + 1
    );
    
    // Adjust timestamps relative to word group start
    const groupStartTime = wordGroup.start_seconds;
    wordTimestamps = wordTimestamps.map(wt => ({
      ...wt,
      // Keep original timing - template will handle offset
    }));
  }
  
  return {
    id: wordGroup.id,
    template: wordGroup.template,
    start_seconds: wordGroup.start_seconds,
    end_seconds: wordGroup.end_seconds,
    background: wordGroup.background,
    avatar: wordGroup.avatar,
    video_inset: wordGroup.video_inset,
    text: wordGroup.text,
    audio: parentAudio ? {
      ...parentAudio,
      word_timestamps: wordTimestamps,
    } : undefined,
  };
}

/**
 * Renders the appropriate template based on word_group.template
 */
const WordGroupRenderer: React.FC<{ 
  wordGroup: WordGroup; 
  scene: Scene; 
  currentTime: number;
}> = ({ wordGroup, scene, currentTime }) => {
  switch (wordGroup.template) {
    case 'SplitProof':
      return <SplitProof scene={scene} currentTime={currentTime} />;
    
    case 'SplitVideo':
      return <SplitVideo scene={scene} currentTime={currentTime} />;
    
    case 'VideoCard':
      return <VideoCard scene={scene} currentTime={currentTime} />;
    
    case 'TextOverProof':
      return <TextOverProof scene={scene} currentTime={currentTime} />;
    
    case 'TextCard':
      return <TextCard scene={scene} currentTime={currentTime} />;
    
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
            Template "{wordGroup.template}" not yet implemented
          </div>
        </AbsoluteFill>
      );
  }
};

/**
 * Handles audio playback for composite scenes.
 * Supports either a single audio file or multiple files with offsets.
 */
const CompositeAudio: React.FC<{ scene: Scene; fps: number }> = ({ scene, fps }) => {
  const audio = scene.audio as CompositeSceneAudio;
  
  if (!audio) return null;
  
  // Handle multiple audio files (composite scene)
  if (audio.files && audio.files.length > 0) {
    return (
      <>
        {audio.files.map((audioFile, index) => {
          const startFrame = Math.round(audioFile.start_offset * fps);
          const durationFrames = Math.round(audioFile.duration_seconds * fps);
          return (
            <Sequence 
              key={`audio-${index}`} 
              from={startFrame} 
              durationInFrames={durationFrames}
            >
              <Audio src={staticFile(audioFile.file)} />
            </Sequence>
          );
        })}
      </>
    );
  }
  
  // Handle single audio file (legacy)
  if (audio.file) {
    return <Audio src={staticFile(audio.file)} />;
  }
  
  return null;
};

export default CompositeScene;
