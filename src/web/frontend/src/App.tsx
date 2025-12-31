import { useState } from 'react';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { ProjectDetail } from './pages/ProjectDetail';

function App() {
  const [selectedProject, setSelectedProject] = useState<string | null>(null);

  return (
    <Layout>
      {selectedProject ? (
        <ProjectDetail
          projectId={selectedProject}
          onBack={() => setSelectedProject(null)}
        />
      ) : (
        <Dashboard onSelectProject={setSelectedProject} />
      )}
    </Layout>
  );
}

export default App;
