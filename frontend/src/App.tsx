import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import { AssumptionAnalyzerPage } from './features/analysis/AssumptionAnalyzerPage'
import { CharacterArcExplorerPage } from './features/characterArcs/CharacterArcExplorerPage'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <div className="app-root">
        <header className="app-header">
          <div className="app-brand">
            <span className="app-title">Discourse Intelligence Engine</span>
          </div>
          <nav className="app-nav">
            <Link to="/" className="app-nav-link">
              Home
            </Link>
            <Link to="/character-arcs" className="app-nav-link">
              Character Arc Explorer
            </Link>
            <Link to="/assumption-analysis" className="app-nav-link">
              Discourse Assumption Analyzer
            </Link>
          </nav>
        </header>
        <main className="app-main">
          <Routes>
            <Route
              path="/"
              element={
                <div className="landing-layout">
                  <section className="landing-intro">
                    <h1>Choose your analysis mode</h1>
                    <p>
                      Start with character journeys or uncover hidden assumptions,
                      agendas, and logical fallacies in your discourse.
                    </p>
                  </section>
                  <section className="landing-cards">
                    <Link to="/character-arcs" className="landing-card">
                      <h2>Character Arc Explorer</h2>
                      <p>
                        Analyze each character&apos;s trajectory, visualize arcs, and
                        inspect the generated Mermaid diagrams and document arcs.
                      </p>
                    </Link>
                    <Link to="/assumption-analysis" className="landing-card">
                      <h2>Discourse Assumption Analyzer</h2>
                      <p>
                        Highlight hidden assumptions, agendas, and logical fallacies
                        with color-coded confidence overlays and structural diagrams.
                      </p>
                    </Link>
                  </section>
                </div>
              }
            />
            <Route path="/character-arcs" element={<CharacterArcExplorerPage />} />
            <Route path="/assumption-analysis" element={<AssumptionAnalyzerPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
