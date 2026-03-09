import { BrowserRouter, Link, NavLink, Route, Routes } from 'react-router-dom'
import { AssumptionAnalyzerPage } from './features/analysis/AssumptionAnalyzerPage'
import { CharacterArcExplorerPage } from './features/characterArcs/CharacterArcExplorerPage'
import './App.css'

function LogoMark() {
  return (
    <span className="logo-mark" aria-hidden="true">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <path
          d="M20 12c0 4.4-3.6 8-8 8a8 8 0 0 1-5.2-1.9L4 19l1-2.9A8 8 0 0 1 4 12c0-4.4 3.6-8 8-8s8 3.6 8 8Z"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinejoin="round"
        />
        <path
          d="M12 7.2c.9 0 1.6.4 2 .9.5.6.4 1.4-.1 2l-1.2 1v1.2"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="12" cy="15.2" r="0.9" fill="currentColor" />
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
