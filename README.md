# Job Radar

Job Radar checks company career pages every few hours, keeps the jobs that match what you're looking for, ranks them, and shows them in a web app you can open on your phone. You open each job and apply yourself. Nothing is ever submitted for you.

It reads the **official public job APIs** that companies' own careers pages use: Greenhouse, Lever, Ashby, SmartRecruiters and Workable. No API keys, no logins, no scraping of LinkedIn or Naukri, and no account-ban risk.

## What's inside

```
jobradar/          Python collector: fetches, filters, scores  ->  web/public/data/jobs.json
web/               React app (Vite + TypeScript) that shows jobs.json
config.yaml        your search: role keywords, skills, places, experience limit
companies.yaml     which companies to watch
state/seen.json    jobs already seen, used to mark what's new
.github/workflows/job-radar.yml   runs everything on GitHub every 4 hours and publishes the app
tests/             Python tests (pytest);  web/src/**/*.test.ts  app tests (vitest)
```

**In the app:**
- Tabs for **To review / New / Applied / Hidden**, with counts.
- Search, company filter, and sorting by best match or newest posting.
- On each job: a match score, why it matched, posting age, and *More details* (team, type, experience asked, a snippet of the posting).
- **Mark applied** records the date, so the Applied tab doubles as a tracker. **Download applied list** exports it as a CSV.
- Warnings on postings that mention fees or deposits, WhatsApp/Telegram contact, or personal email addresses.
- Marks are saved in your browser (per device).

---

## Put it on GitHub (about 15 minutes, free)

### 1. Upload the files

**Option A, with Git (recommended).** Open a terminal (Command Prompt on Windows):

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
# copy everything from this folder into here, including the hidden .github folder
git add .
git commit -m "Add Job Radar"
git push
```

**Option B, in the browser.** On the repo page, click **Add file → Upload files**. Drag in all the files and folders, then click **Commit changes**.
Check afterwards that `.github/workflows/job-radar.yml` exists in the repo. Some computers hide folders whose names start with a dot, so they can get skipped. If it's missing, click **Add file → Create new file**, type the name `.github/workflows/job-radar.yml`, paste in the contents of that file, and commit.

### 2. Repo settings (once)

1. **Settings → Pages →** under *Build and deployment*, set **Source** to **GitHub Actions**.
2. **Settings → Actions → General → Workflow permissions →** choose **Read and write permissions**, then click **Save**.

Free GitHub accounts need the repository to be **public** for Pages. Only public job listings appear on the site.

### 3. Set your search

Edit `config.yaml` (`keywords`, `skills`, `locations`, `max_years_experience`) and `companies.yaml` on GitHub with the pencil icon, then commit. Each commit triggers a run.

### 4. Run it

Open **Actions → Job Radar → Run workflow**. When it finishes (2–3 minutes), the app is at
`https://<your-username>.github.io/<your-repo>/`

From then on it runs every 4 hours. Bookmark the address on your phone.

> GitHub may pause scheduled workflows on repos with no activity for 60 days. If updates stop, open the Actions tab and re-enable the workflow.

---

## Finding companies

Each company has a *slug* on its job board, which is the name in the URL:

| Careers page URL | In `companies.yaml` |
|---|---|
| `boards.greenhouse.io/stripe` or `job-boards.greenhouse.io/stripe` | `greenhouse: [stripe]` |
| `jobs.lever.co/palantir` | `lever: [palantir]` |
| `jobs.ashbyhq.com/notion` | `ashby: [notion]` |
| `careers.smartrecruiters.com/Visa` | `smartrecruiters: [Visa]` (capitals matter) |
| `apply.workable.com/acme` | `workable: [acme]` |

Open a company's careers page, click any job, and look at the address bar. Or let the tool find it, then confirm every board works:

```bash
python -m jobradar detect https://www.company.com/careers
python -m jobradar check
```

Companies on **Workday, SuccessFactors, Taleo** or a fully custom careers site can't be read this way. Use that company's own email job alerts instead.

## Settings (`config.yaml`)

| Setting | What it does |
|---|---|
| `keywords` | Role names. A job's **title** must contain one. |
| `search_description` | Also accept jobs whose description mentions a keyword. Finds more, but noisier. |
| `skills` | Your skills. Each one found adds points. |
| `exclude_title` | Drop titles with these words (senior, manager, ...). |
| `exclude_text` | Drop jobs whose text has these phrases (walk-in, ...). |
| `locations` / `exclude_locations` | Places to keep or always skip. Empty `locations` means anywhere. |
| `include_remote` | Keep remote jobs even if the place isn't in your list. |
| `max_years_experience` | Drop jobs asking for more years than this. |
| `unknown_experience` | `keep` or `drop` jobs that don't say how much experience they need. |
| `max_age_days` | Ignore older postings. |
| `min_score` | Hide jobs scoring below this (0–100). |

**How the score works:** a title match gives the base points. Matching your location, being posted recently, being an early-career role, fitting your experience limit and mentioning your skills each add points. Postings with scam signals lose 30 points and get a warning. Every job lists the reasons it matched.

### Optional: AI re-ranking

This is the only part that needs a key. Set `llm.enabled: true` and write a few lines about yourself in `llm.profile`. Then get a free Gemini key at https://aistudio.google.com/apikey. In the repo, go to **Settings → Secrets and variables → Actions → New repository secret**, name it `LLM_API_KEY`, and paste the key.

The top 40 jobs per run get an AI fit score and a one-line reason, blended into the ranking. Each job is scored once and remembered. Any OpenAI-compatible API works: change `base_url` and `model`.

---

## Run it on your own computer

You need **Python 3.10+** and **Node.js 20+**.

```bash
# collector
python -m venv .venv
.venv\Scripts\activate            # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m jobradar run            # real data   ->  web/public/data/jobs.json
python -m jobradar demo           # or: made-up sample data, no internet needed

# app
cd web
npm install
npm run dev                       # open the address it prints, e.g. http://localhost:5173
```

Tests: `python -m pytest` in the main folder, and `npm test` in `web/`.

## Limits

- Only companies on the five supported job boards are covered.
- Experience is read from phrases like "3+ years" or "0-2 years of experience". Unusual wording can be missed, so jobs that don't state experience are kept by default.
- Scam warnings are hints, not proof. Confirm a job on the company's own website, and never pay to apply.

## License

MIT
