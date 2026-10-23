# Setup — BHAVNAJAY profile README

This folder is the full contents of your profile repository **`BHAVNAJAY/BHAVNAJAY`**
(the special repo whose `README.md` appears on github.com/BHAVNAJAY).

```
README.md                         the profile page
SETUP.md                          this file
assets/
  hero/hero-3d.gif                   animated hero (plays once, 2.1 MB)
  hero/hero-3d-static.png            static hero (reduced-motion fallback)
  source/                         your original portrait + the background-removed cut-out
  skills/  projects/  achievements/  contact/   generated SVG pills and cards
.github/
  workflows/profile-insights.yml  daily job: 3D calendar, stats, languages, streak
  profile-3d-settings.json        colours for the 3D contribution calendar
scripts/                          generators (only needed if you want to change visuals)
```

After the workflow's first run, two more folders appear: `profile/` (stats, languages and
streak cards) and `profile-3d-contrib/` (3D calendar). The workflow creates them, so don't
add them by hand.

---

## 1. Publish (web browser, no tools needed)

1. Open **https://github.com/BHAVNAJAY/BHAVNAJAY**.
2. Click **Add file → Upload files**.
3. Drag in **everything inside this folder**: `README.md`, `SETUP.md`, `assets`, `scripts`.
   Drag folders as folders so the paths stay the same (`assets/hero/hero-3d.gif`, etc.).
4. Commit to **main**. This replaces the default "Hi there 👋" README.
5. The browser uploader often skips **`.github`** because it's a hidden folder. Add the two
   files by hand:
   - **Add file → Create new file**, name it `.github/workflows/profile-insights.yml`
     (typing the `/` creates the folders), paste in that file's contents, and commit.
   - Do the same for `.github/profile-3d-settings.json`.

### …or with git

```bash
git clone https://github.com/BHAVNAJAY/BHAVNAJAY.git
cd BHAVNAJAY
# copy everything from this folder in (including .github), replacing README.md
git add -A
git commit -m "Profile README"
git push
```

## 2. Turn on the insights workflow

1. **Settings → Actions → General**
   - *Actions permissions*: allow actions (the default for personal accounts).
   - *Workflow permissions*: the workflow asks for `contents: write` itself. If the run
     fails with a 403 on `git push`, pick **Read and write permissions** here and save.
2. Committing the workflow file starts it automatically. If you want to start it yourself:
   **Actions → Profile insights → Run workflow**.
3. Wait about 1–2 minutes for a green check. The run commits `profile/*.svg` and
   `profile-3d-contrib/profile-3d-bhavna.svg`, and the insights section fills in.

**What it does**

| Step | Tool (pinned version) | Output |
|---|---|---|
| 3D contribution calendar | `yoshi389111/github-profile-3d-contrib@v0.9.3` | `profile-3d-contrib/profile-3d-bhavna.svg` |
| Stats card | `stats-organization/github-readme-stats-action@v2` | `profile/stats.svg` |
| Top languages | `stats-organization/github-readme-stats-action@v2` | `profile/top-langs.svg` |
| Streak | `DenverCoder1/github-readme-streak-stats@v1` | `profile/streak.svg` |

- **Schedule:** daily at 19:37 UTC (01:07 IST). It also runs when you edit the workflow or
  settings file, and whenever you run it manually.
- **Permissions:** only `contents: write`, so it can commit the images back to this repo.
- **Secrets:** none. It uses GitHub's automatic `GITHUB_TOKEN`, which can only see
  **public** activity. To include private-repo work:
  1. Turn on *Settings → Public profile → Contributions & activity → Include private
     contributions on my profile*. Usually that's enough for the calendar.
  2. Optionally, create a personal access token and save it as a repository secret (for
     example `PROFILE_PAT`). In the workflow, replace `secrets.GITHUB_TOKEN` with
     `secrets.PROFILE_PAT`. Never paste a token into the workflow file itself.
- **Resilience:** each step has `continue-on-error`. If one service fails, the others still
  update and the last good image stays in place. The stats/language steps use
  `fail_on_error: "true"`, so a rate limit can't overwrite a good card with an error card.
- GitHub pauses scheduled workflows in repos with no activity for 60 days. The daily commits
  count as activity. If it does get paused, re-enable it from the Actions tab.

## 3. Things to know

- **External widget:** only the *contribution activity graph* is loaded live from a
  third-party service (`github-readme-activity-graph.vercel.app`). If that service is down,
  only that one image breaks. Everything else lives in your repo.
- **Language percentages** come from code detected in your public repositories (by bytes and
  repo count). They are not a measure of skill.
- **Streak timezone** is set to `Asia/Kolkata`. To change it, edit `timezone=` in the workflow.
- **Hero animation** plays once and then rests on the full frame. Visitors with "reduce
  motion" turned on see `hero-3d-static.png` instead. To make it loop, change `"-loop", "-1"` to
  `"-loop", "0"` in `scripts/build_hero.py` and rebuild.

## 4. Editing content later

Text inside cards and pills lives in **`scripts/build_cards.py`** (the `DATA` section).
Text in the hero lives at the top of **`scripts/build_hero.py`**. To regenerate:

```bash
pip install -r scripts/requirements.txt      # Pillow, numpy, scipy, fonttools, brotli
python3 scripts/build_cards.py               # skill pills, project & achievement cards, contact
python3 scripts/build_hero.py                # hero-3d.gif + hero-3d-static.png (needs ffmpeg; gifsicle optional)
```

Experience, about, currently-exploring and contact links are plain text in `README.md`.

To add a project link later (for example a repo for Ping), set the repo URL in `PROJECTS` in
`build_cards.py`, re-run it, and update that card's `<a href>` in `README.md`.

## 5. Troubleshooting images

| Symptom | Fix |
|---|---|
| Insight images show as broken right after publishing | The workflow hasn't run yet. Run it from the Actions tab and wait for the commit. |
| Workflow fails at `git push` with 403 | Settings → Actions → General → Workflow permissions → **Read and write**. |
| `profile-3d-bhavna.svg` missing but other cards exist | Open the run log for the "3D contribution calendar" step. Check that `.github/profile-3d-settings.json` was uploaded. |
| Hero or cards broken | Check the folder structure. Paths are case-sensitive (`assets/hero/hero-3d.gif`). |
| Activity graph broken | That's the external service. Wait and refresh, or delete that `<p>` block from `README.md`. |
| Changes don't show | GitHub caches images for a few minutes. Hard-refresh the page. |
