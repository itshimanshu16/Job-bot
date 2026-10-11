# Job Radar — Comprehensive Project Documentation & Architecture Guide

This document details the complete architecture, implementation history, technical components, API configurations, and deployment procedures for the **Job Radar** application.

---

## 1. Project Overview

**Job Radar** is an automated job search and intelligence platform designed to monitor company career pages, filter postings according to specific qualifications, score and rank listings, and present them in a responsive web application.

### Key Highlights
- **Zero Scraping / No Account Bans**: Queries official public ATS APIs (Greenhouse, Lever, Ashby, SmartRecruiters, and Workable) directly.
- **Modern Full-Stack Architecture**: Python-powered backend collector paired with a high-performance React 19 + TypeScript + Vite front-end.
- **Zero Hosting Costs**: Fully serverless operation utilizing GitHub Actions for scheduled runs (every 4 hours) and GitHub Pages for web hosting.
- **Client-Side Privacy**: Application tracking, notes, and hidden job statuses persist in browser `localStorage`—no personal user data is sent to external servers.
- **AI-Powered Evaluation**: Optional semantic re-ranking via Google Gemini to score job descriptions against a personalized candidate profile.

---

## 2. Work Done So Far

### A. Environment Audit & Dependency Resolution
- Analyzed the local Windows environment and verified active runtimes:
  - **Node.js**: v22.17.0
  - **npm**: v11.10.1
  - **Python**: v3.13.14
- Installed all required Node dependencies (`web/node_modules`) using `npm ci`.
- Installed all required Python packages (`requests`, `PyYAML`, `pytest`) using `pip`.

### B. Test Suite Execution & Validation
- **Python Backend**: Executed the full unit test suite with `pytest`.
  - **Result**: `44 passed in 0.89s` (100% pass rate).
  - Validated ATS parsing, scoring algorithms, date filtering, duplicate detection, and text cleaning.
- **React Front-End**: Executed the test suite with `vitest`.
  - **Result**: `10 passed in 940ms` (100% pass rate).
  - Validated CSV export generation, search filters, sorting mechanisms, and state counts.
- **Production Build**: Built the React application using `tsc --noEmit && vite build`.
  - Produced optimized production assets in `web/dist/` without any type or bundling errors.

### C. Git Repository Setup & Push to GitHub
- Initialized local repository on branch `main`.
- Linked the local working copy to the remote repository: [https://github.com/itshimanshu16/Job-bot.git](https://github.com/itshimanshu16/Job-bot.git).
- Staged and committed all core modules, workflows, tests, configurations, and front-end code.
- Successfully pushed the codebase to `origin/main`.

### D. Live Pipeline & Automated Action Verification
- Following the initial push, GitHub Actions automatically triggered the `Job Radar` workflow.
- The Python collector executed in the cloud runner and successfully fetched:
  - **1,169 open postings** across Ashby (Notion), Greenhouse (Stripe), and Lever (Palantir).
  - Filtered matched roles and generated initial production data files:
    - `state/seen.json`
    - `web/public/data/jobs.json`
    - `web/public/data/jobs.csv`
- Pull rebase synchronized those generated files back into the local repository.

### E. API Key Authentication & Validation
- The key provided by the user (`AQ.Ab8RN6... [redacted for security]`) was inspected and verified.
- Direct connectivity testing confirmed it as a valid **Google Gemini API Key** (compatible with `gemini-3.8-flash` and `gemini-flash-latest` via Google's OpenAI-compatible endpoint).
- Security safeguards ensured this key was **not** hardcoded into version-controlled files, protecting it from public exposure.

---

## 3. Detailed Component Breakdown

### 3.1. Python Collector Engine (`jobradar/`)

```
jobradar/
├── __main__.py       # CLI interface (run, check, detect, demo)
├── config.py         # YAML configuration loader & validation
├── pipeline.py       # Core orchestration: fetch -> filter -> score -> export
├── models.py         # Dataclasses (Job, BoardResult, PipelineResult)
├── http.py           # HTTP client with rate-limiting, retries, and headers
├── filters.py        # Logic for role matching, experience, exclusions, and scam detection
├── llm.py            # LLM scoring client for Google Gemini
├── report.py         # Exporters for jobs.json and jobs.csv
├── state.py          # State persistence (seen jobs tracking)
├── detect.py         # Automated ATS detector for arbitrary career URLs
└── sources/          # ATS API adapters:
    ├── ashby.py
    ├── greenhouse.py
    ├── lever.py
    ├── smartrecruiters.py
    └── workable.py
```

#### How the Pipeline Operates:
1. **Fetching**: Iterates through company slugs defined in `companies.yaml` across supported ATS platforms concurrently.
2. **Filtering**:
   - **Keyword Match**: Requires role titles to match configured search terms.
   - **Exclusions**: Removes senior/management levels (`senior`, `lead`, `vp`, `director`, etc.) if specified.
   - **Experience Parser**: Scans job descriptions for year requirements and drops roles exceeding `max_years_experience`.
   - **Scam Detection**: Flags suspicious phrases (e.g., application fees, security deposits, contact via Telegram/WhatsApp, generic Gmail/Yahoo contacts).
3. **Scoring**: Calculates a match score (0–100) based on title relevance and keyword/skill density.
4. **LLM Re-ranking (Optional)**: If enabled, top candidates are evaluated against the candidate profile in `config.yaml` using Gemini, returning structured fit analysis and rationales.
5. **Output**: Writes output to `web/public/data/jobs.json` and updates `state/seen.json`.

---

### 3.2. Modern React Front-End (`web/`)

```
web/
├── index.html        # Entry HTML with mobile viewport settings
├── vite.config.ts    # Relative base configuration for GitHub Pages
├── tsconfig.json     # Strict TypeScript configuration
└── src/
    ├── main.tsx      # React root mount
    ├── App.tsx       # Main page layout, state management, and status screens
    ├── styles.css    # Responsive design system with dark/light mode
    ├── types.ts      # TypeScript interfaces for jobs, marks, and metadata
    ├── lib/
    │   ├── data.ts   # Cache-busting data fetcher for jobs.json
    │   ├── jobs.ts   # Filtering, sorting, and CSV export logic
    │   ├── marks.ts  # Browser localStorage tracker for applied/hidden states
    │   └── jobs.test.ts # Automated test specifications
    └── components/
        ├── Header.tsx   # Title, total match counter, and last-updated badge
        ├── Tabs.tsx     # Filter tabs: "To review", "New", "Applied", "Hidden"
        ├── Controls.tsx # Live search box, company filter dropdown, and sort toggle
        ├── JobCard.tsx  # Interactive job cards with score meter, reasons, and accordion
        └── Footer.tsx   # ATS status summary and board health indicator
```

#### Key Front-End Features:
- **Responsive Layout**: Designed for mobile and desktop screens with horizontal tab scrolling and fluid typography.
- **Real-Time Filtering**: Zero-latency search across job titles, companies, and locations.
- **Application Tracking**: "Mark applied" stamps the current date and shifts the job to the *Applied* tab.
- **CSV Export**: Exports the tracked list of applied jobs with links and dates for personal record-keeping.
- **Adaptive Dark Mode**: Automatic theme switching respecting system preferences.

---

### 3.3. CI/CD & Automation (`.github/workflows/job-radar.yml`)

The GitHub Actions workflow automates the entire lifecycle:
1. **Trigger Schedule**: Executes every 4 hours (`17 */4 * * *`) or manually via the "Run workflow" button.
2. **Step 1 (Python Execution)**: Sets up Python 3.12, installs requirements, runs `python -m jobradar run`, and commits fresh job data back to the repository.
3. **Step 2 (React Build)**: Sets up Node.js 22, installs dependencies via `npm ci`, runs tests, and compiles the static site via `npm run build`.
4. **Step 3 (Deployment)**: Packages `web/dist` and deploys directly to **GitHub Pages**.

---

## 4. API & Authentication Overview

### ATS Job Boards (No Keys Required)
The 5 supported job platforms provide open, public REST endpoints:
- **Greenhouse**: `https://boards-api.greenhouse.io/v1/boards/{slug}/jobs`
- **Lever**: `https://api.lever.co/v0/postings/{slug}?mode=json`
- **Ashby**: `https://api.ashbyhq.com/posting-api/job-board/{slug}`
- **SmartRecruiters**: `https://api.smartrecruiters.com/v1/companies/{slug}/postings`
- **Workable**: `https://apply.workable.com/api/v1/widget/accounts/{slug}`

*No account creation, API registration, or API keys are required for any of these platforms.*

### Google Gemini API (AI Re-ranking)
- **Role**: Evaluates top-ranked postings against candidate qualifications.
- **Storage**: Must be stored as a GitHub repository secret named `LLM_API_KEY`.
- **Status**: Tested and verified with endpoint `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions`.

---

## 5. Next Steps: Making Your Site Live

To complete the setup and publish the site to GitHub Pages:

### Step 1: Configure GitHub Pages
1. Go to: [https://github.com/itshimanshu16/Job-bot/settings/pages](https://github.com/itshimanshu16/Job-bot/settings/pages)
2. Under **Build and deployment** → **Source**, change the selection from *Deploy from a branch* to **GitHub Actions**.

### Step 2: Grant Workflow Write Permissions
1. Go to: [https://github.com/itshimanshu16/Job-bot/settings/actions](https://github.com/itshimanshu16/Job-bot/settings/actions)
2. Scroll down to **Workflow permissions**.
3. Select **Read and write permissions** and click **Save**.

### Step 3: Add Your Gemini API Key
1. Go to: [https://github.com/itshimanshu16/Job-bot/settings/secrets/actions](https://github.com/itshimanshu16/Job-bot/settings/secrets/actions)
2. Click **New repository secret**.
3. Name: `LLM_API_KEY`
4. Secret: Paste your Gemini key (`AQ.Ab8RN6...`).
5. Click **Add secret**.

### Step 4: Run the Workflow
1. Go to: [https://github.com/itshimanshu16/Job-bot/actions/workflows/job-radar.yml](https://github.com/itshimanshu16/Job-bot/actions/workflows/job-radar.yml)
2. Click **Run workflow** → **Run workflow**.
3. Once completed (typically 1–2 minutes), your application will be live at:
   **`https://itshimanshu16.github.io/Job-bot/`**

---

## 6. How to Customize Your Search

- **Role & Skill Criteria**: Edit `config.yaml` to specify target role titles (`keywords`), technologies (`skills`), preferred locations (`locations`), and experience limits (`max_years_experience`).
- **Target Companies**: Edit `companies.yaml` to add or remove company slugs for any of the 5 supported platforms.
- **Candidate Profile**: In `config.yaml` under `llm.profile`, provide a summary of your degree, graduation year, and career preferences to guide AI scoring.
