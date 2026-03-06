import { BrowserRouter, Link, NavLink, Route, Routes } from 'react-router-dom'
import { AssumptionAnalyzerPage } from './features/analysis/AssumptionAnalyzerPage'
import { CharacterArcExplorerPage } from './features/characterArcs/CharacterArcExplorerPage'
import './App.css'

function LogoMark() {
  return (
    <span className="logo-mark" aria-hidden="true">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <path
          d="M20 12c0 4.418-3.582 8-8 8a7.97 7.97 0 0 1-5.125-1.852L4 19l.852-2.875A7.97 7.97 0 0 1 4 12c0-4.418 3.582-8 8-8s8 3.582 8 8Z"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
        <path
          d="M8.2 12.3c.65-1.35 1.9-2.2 3.7-2.2 1.95 0 3.2 1.05 3.2 2.55 0 1.1-.62 1.82-1.7 2.35-.82.41-1.22.74-1.22 1.4v.4"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
        <path
          d="M12 17.9h.01"
          stroke="currentColor"
          strokeWidth="2.6"
          strokeLinecap="round"
        />
      </svg>
    </span>
  )
}

function App() {
  return (
    <BrowserRouter>
      <div className="app-root">
        <header className="app-header">
          <div className="app-brand">
            <LogoMark />
            <span className="app-title">Discourse Intelligence Engine</span>
          </div>
          <nav className="app-nav">
            <NavLink
              to="/"
              className={({ isActive }) =>
                isActive ? 'app-nav-link active' : 'app-nav-link'
              }
              end
            >
              Home
            </NavLink>
            <NavLink
              to="/character-arcs"
              className={({ isActive }) =>
                isActive ? 'app-nav-link active' : 'app-nav-link'
              }
            >
              Character Arc Explorer
            </NavLink>
            <NavLink
              to="/assumption-analysis"
              className={({ isActive }) =>
                isActive ? 'app-nav-link active' : 'app-nav-link'
              }
            >
              Discourse Assumption Analyzer
            </NavLink>
          </nav>
        </header>
        <main className="app-main">
          <Routes>
            <Route
              path="/"
              element={
                <div className="landing-hero">
                  <section className="hero-left">
                    <div className="hero-badge">Writer-grade discourse intelligence</div>
                    <h1>See the structure beneath the words.</h1>
                    <p>
                      Explore character trajectories or detect hidden assumptions,
                      agendas, and logical fallacies — with confidence-weighted highlights.
                    </p>
                    <div className="hero-cta">
                      <Link to="/assumption-analysis" className="btn primary">
                        Analyze discourse
                      </Link>
                      <Link to="/character-arcs" className="btn secondary">
                        Explore character arcs
                      </Link>
                    </div>
                    <div className="hero-micro">
                      Paste text, upload a .txt file, or analyze a YouTube transcript.
                    </div>
                  </section>

                  <section className="hero-right" aria-label="Example preview">
                    <div className="preview-card">
                      <div className="preview-title">Example</div>
                      <div className="preview-text">
                        Either you support this bill or you hate this country. Obviously, we must act now.
                      </div>
                      <div className="preview-tags">
                        <span className="tag fallacy">False dilemma</span>
                        <span className="tag assumption">Epistemic shortcut</span>
                        <span className="tag agenda">Us vs them</span>
                      </div>
                    </div>
                    <div className="preview-card subtle">
                      <div className="preview-title">What you get</div>
                      <ul className="preview-list">
                        <li>Clickable fallacy list with confidence</li>
                        <li>Highlights that scale with certainty</li>
                        <li>Export-ready JSON outputs</li>
                      </ul>
                    </div>
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
