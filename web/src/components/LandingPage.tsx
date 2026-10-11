interface Props {
  onOpenLogin: () => void;
  totalJobs?: number;
  totalBoards?: number;
}

export function LandingPage({ onOpenLogin, totalJobs = 7300, totalBoards = 21 }: Props) {
  return (
    <div className="landing">
      {/* ── Top Navigation ── */}
      <header className="landing-nav">
        <div className="landing-nav-inner">
          <div className="brand">
            <span className="brand-dot" aria-hidden="true" />
            <span className="brand-name">Job Radar</span>
            <span className="brand-tag">v2.0</span>
          </div>

          <nav className="nav-links" aria-label="Main Navigation">
            <a href="#how-it-works">How It Works</a>
            <a href="#features">Features</a>
            <a href="#tracks">Tracks</a>
            <a href="#boards">Supported Boards</a>
          </nav>

          <button type="button" className="nav-login-btn" onClick={onOpenLogin}>
            <span className="key-icon" aria-hidden="true">🔑</span> Candidate Portal
          </button>
        </div>
      </header>

      {/* ── Hero Section ── */}
      <section className="hero">
        <div className="hero-badge">
          <span className="pulse-beacon" aria-hidden="true" />
          <span>AI-Powered Multi-Board Job Discovery Bot</span>
        </div>

        <h1 className="hero-headline">
          High-Signal Job Discovery <br className="hero-br" />
          <span className="gradient-text">Engineered for Freshers.</span>
        </h1>

        <p className="hero-subtitle">
          Job Radar monitors leading tech and consulting companies across top ATS platforms—aggregating,
          verifying graduation eligibility, and pairing each job with the ideal specialized resume.
        </p>

        <div className="hero-actions">
          <button type="button" className="hero-primary-btn" onClick={onOpenLogin}>
            Access Candidate Radar <span aria-hidden="true">→</span>
          </button>
          <a href="#how-it-works" className="hero-secondary-btn">
            Explore How It Works
          </a>
        </div>

        {/* ── Stats Ribbon ── */}
        <div className="stats-ribbon">
          <div className="stat-card">
            <span className="stat-value">{totalBoards}+</span>
            <span className="stat-label">Active Company Boards</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{totalJobs.toLocaleString()}+</span>
            <span className="stat-label">Open Postings Monitored</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">3</span>
            <span className="stat-label">Specialized Career Tracks</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">100%</span>
            <span className="stat-label">Privacy-First & Zero Spam</span>
          </div>
        </div>
      </section>

      {/* ── Features Grid ── */}
      <section id="features" className="section">
        <div className="section-head">
          <h2 className="section-title">Built to Cut Through Career Portal Noise</h2>
          <p className="section-sub">
            Traditional job boards are flooded with stale, irrelevant listings. Job Radar uses deterministic rules
            and semantic scoring to surface only legitimate fresher roles.
          </p>
        </div>

        <div className="feature-grid">
          <FeatureCard
            icon="⚡"
            title="Direct ATS Ingestion"
            desc="Directly queries vendor API endpoints for Greenhouse, Lever, Ashby, SmartRecruiters, and Workable with zero scraper brittleness."
          />
          <FeatureCard
            icon="🎯"
            title="3-Track Profile Matching"
            desc="Scores every role against Software Engineering, Analytics & Consulting, and Supply Chain & Operations candidate tracks."
          />
          <FeatureCard
            icon="🛡️"
            title="Graduation Eligibility Engine"
            desc="Identifies 2027 batch openings, flags branch restrictions, and spots CGPA requirements before you apply."
          />
          <FeatureCard
            icon="📄"
            title="Contextual Resume Routing"
            desc="Automatically recommends the exact resume PDF from candidate files (tech, banking analyst, consulting, supply chain)."
          />
          <FeatureCard
            icon="📌"
            title="Local Application Tracker"
            desc="Track what you applied to with timestamps and resume filenames, kept securely in your browser with CSV export."
          />
          <FeatureCard
            icon="🔒"
            title="Zero Auto-Apply Safety"
            desc="Never submits spam applications automatically. Provides direct verified apply links for intentional, high-quality submissions."
          />
        </div>
      </section>

      {/* ── How It Works ── */}
      <section id="how-it-works" className="section alt-bg">
        <div className="section-head">
          <h2 className="section-title">How the Bot Operates</h2>
          <p className="section-sub">Four automated stages between raw career portals and your application pipeline.</p>
        </div>

        <div className="steps-container">
          <StepItem
            step="01"
            title="Multi-Board Ingestion"
            desc="Scheduled collectors fetch all active job postings from monitored companies across 5 supported ATS vendors."
          />
          <StepItem
            step="02"
            title="Eligibility & Rule Screening"
            desc="Filters out senior/manager postings, checks experience caps (freshers), and verifies graduation year eligibility."
          />
          <StepItem
            step="03"
            title="Track Assignment & Scoring"
            desc="Scores candidate keyword and skill density, assigns the winning career track, and matches the optimal resume file."
          />
          <StepItem
            step="04"
            title="Interactive Review & Tracker"
            desc="Presents ranked matches in a sleek interface with one-click resume name copying and application status tracking."
          />
        </div>
      </section>

      {/* ── Target Tracks ── */}
      <section id="tracks" className="section">
        <div className="section-head">
          <h2 className="section-title">Configured Candidate Tracks</h2>
          <p className="section-sub">Three tailored job matching profiles driven by specialized resumes.</p>
        </div>

        <div className="tracks-showcase">
          <TrackCard
            title="Software / Full-Stack"
            tags={["React", "Node.js", "TypeScript", "Next.js", "C++", "DSA"]}
            desc="Full-stack web engineering, frontend, backend, and developer trainee roles at product companies and startups."
          />
          <TrackCard
            title="Analyst & Consulting"
            tags={["SQL", "Power BI", "Statistics", "Market Research", "GenAI"]}
            desc="Business analyst, data analyst, consulting associate, and decision analytics roles across tech and BFSI."
          />
          <TrackCard
            title="Supply Chain & Operations"
            tags={["Demand Planning", "Inventory", "S&OP", "Warehousing", "Logistics"]}
            desc="Supply chain analytics, fulfillment, demand forecasting, and operations associate opportunities."
          />
        </div>
      </section>

      {/* ── Supported ATS Boards ── */}
      <section id="boards" className="section alt-bg">
        <div className="section-head">
          <h2 className="section-title">Supported Applicant Tracking Systems</h2>
          <p className="section-sub">Integrated with the top 5 modern recruitment platforms.</p>
        </div>

        <div className="boards-pills">
          <div className="board-pill">
            <span className="board-indicator green" /> Greenhouse
          </div>
          <div className="board-pill">
            <span className="board-indicator blue" /> Lever
          </div>
          <div className="board-pill">
            <span className="board-indicator purple" /> Ashby
          </div>
          <div className="board-pill">
            <span className="board-indicator orange" /> SmartRecruiters
          </div>
          <div className="board-pill">
            <span className="board-indicator teal" /> Workable
          </div>
        </div>
      </section>

      {/* ── CTA Banner ── */}
      <section className="cta-banner">
        <div className="cta-inner">
          <h2 className="cta-title">Personal Candidate Access</h2>
          <p className="cta-text">
            Are you Himanshu? Unlock your personalized Job Radar dashboard to review ranked opportunities,
            resume routing, and application history.
          </p>
          <button type="button" className="cta-btn" onClick={onOpenLogin}>
            Unlock Candidate Radar <span aria-hidden="true">🔒</span>
          </button>
        </div>
      </section>

      {/* ── Landing Footer ── */}
      <footer className="landing-foot">
        <div className="landing-foot-inner">
          <p>© {new Date().getFullYear()} Job Radar Bot. Personal Career Discovery Platform.</p>
          <p className="foot-muted">
            Automated collector running daily. Zero automated submission policy.
          </p>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, desc }: { icon: string; title: string; desc: string }) {
  return (
    <div className="feature-card">
      <div className="feature-icon" aria-hidden="true">{icon}</div>
      <h3 className="feature-title">{title}</h3>
      <p className="feature-desc">{desc}</p>
    </div>
  );
}

function StepItem({ step, title, desc }: { step: string; title: string; desc: string }) {
  return (
    <div className="step-card">
      <div className="step-num">{step}</div>
      <h3 className="step-title">{title}</h3>
      <p className="step-desc">{desc}</p>
    </div>
  );
}

function TrackCard({ title, tags, desc }: { title: string; tags: string[]; desc: string }) {
  return (
    <div className="track-card">
      <h3 className="track-card-title">{title}</h3>
      <p className="track-card-desc">{desc}</p>
      <div className="track-tags">
        {tags.map((t) => (
          <span key={t} className="track-skill-tag">
            {t}
          </span>
        ))}
      </div>
    </div>
  );
}
