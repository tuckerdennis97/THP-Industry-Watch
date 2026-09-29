# Setting Up Vendor Watch on GitHub — Complete Beginner's Guide

When you're done, GitHub will run Vendor Watch every weekday morning on its own
computers and publish the dashboard at a permanent web address your team can
bookmark. No office PC has to stay on, and it costs nothing.

**Time needed:** 45–60 minutes the first time, mostly waiting on emails.
**You'll need:** the `vendor-watch-github.zip` file, access to your email, and
a web browser (Chrome or Edge).

Every step ends with a **✅ Checkpoint** describing what you should see. If
you don't see it, stop and check the step's "If something's off" note before
moving on. GitHub occasionally renames buttons, so if a label is slightly
different from this guide, look for the closest match.

---

## Part 1 — A 2-minute GitHub vocabulary

You only need six words:

| Term | What it means here |
|---|---|
| **Repository** ("repo") | A project folder that lives on GitHub. Yours will hold the script, the settings, and the saved findings. |
| **Commit** | GitHub's word for "save." Every time you change a file on GitHub, you *commit* it, with a short note about what changed. GitHub keeps every past version, so nothing is ever truly lost. |
| **Workflow** | A set of instructions telling GitHub what to run and when. Yours is one file that says, "Every weekday at 7:17 AM, run the scan and publish the dashboard." |
| **Actions** | The GitHub feature that carries out workflows. It's also the name of the tab where you watch runs happen. |
| **Pages** | GitHub's free website hosting. It's what gives your dashboard a web address. |
| **Secret** | A password-like value stored encrypted. The workflow can use it, but nobody can read it on screen, and it never appears in your files. |

---

## Part 2 — Prepare on your computer (5 minutes)

### Step 1: Unzip the project

1. Find `vendor-watch-github.zip` in your Downloads folder.
2. Right-click it → **Extract All…** → **Extract**.
3. Open the new `vendor-watch` folder.

**✅ Checkpoint:** you see a folder named `.github` and these files:
`vendor_watch.py`, `config.json`, `watch_data.json`, `README.md`,
`GITHUB_SETUP.md`, `run_watch.bat`, and `.gitignore`.

> **If something's off:** if you double-clicked the zip and only see files
> "inside" it without extracting, uploading won't work correctly. Extract it
> first. On a Mac, folders starting with a dot are hidden; press
> **Cmd + Shift + .** to show them.

### Step 2: Decide public or private (ask your manager)

GitHub's free plan only publishes websites from **public** repositories, so
anyone who finds the repository or the dashboard link could see them. What
would be visible:

- **Vendor list:** already public in your catalog's Trusted Partners page.
- **News headlines, price indexes, and rules:** all from public sources.
- **Competitor list** in `config.json`: the only part that says something about
  Tarheel's thinking.

Options:
- **Public (free):** fine for most teams. If the competitor list is a concern,
  shorten it or leave it empty. You can edit it later.
- **Private + GitHub Pro ($4/month):** the files become private, but the
  dashboard itself is still viewable by anyone who has the link.

Write down the decision; you'll use it in Step 7.

---

## Part 3 — Get your BLS key (10 minutes, runs while you do other steps)

### What is a BLS key, and why do you need one?

The **Commodity Signals** strip at the top of the dashboard shows the price
direction of plastic resins, paper, paperboard, and diesel. That data comes
from the **U.S. Bureau of Labor Statistics (BLS)**, the federal agency that
publishes the Producer Price Index (the measure of what manufacturers charge)
along with other economic statistics.

BLS lets programs request this data through its public "API" (a door that
software, rather than people, uses). There are two levels:

| | Without a key | With a free key |
|---|---|---|
| Requests allowed per day | 25 | 500 |
| Limit counted per… | network location | key (just yours) |

A **BLS key** (officially a "registration key") is a free ID string, typically
32 letters and numbers, that tells BLS the request is from you. It's not a
password to an account, and there's nothing to log into. It only raises your
limit.

**Why it matters on GitHub:** without a key, the 25-per-day limit is shared by
everyone using the same network. GitHub's computers are used by thousands of
people, so that shared limit is almost always used up before your run. In
testing, the keyless request failed exactly this way. With your own key, you
get 500 per day to yourself, and the script uses one per run.

**Cost:** free. **Account needed:** no. **Expires:** yes, **once a year** (see
Step 4).

### Step 3: Register for the key

1. Go to **https://data.bls.gov/registrationEngine/**
2. Fill in:
   - **Organization name:** `Tarheel Paper & Supply`
   - **Email address:** your work email. The key goes here, and so do the
     yearly renewal notices, so use an inbox you'll keep.
3. Check the box agreeing to the terms of service.
4. Complete the CAPTCHA.
5. Click **Submit**.
6. Check your email for a message from **labstat@bls.gov**. It usually arrives
   within minutes. **Check your spam or junk folder** if it doesn't show up.
7. The email contains your key. If it also includes a link to activate or
   validate the key, **click it**; the key won't work until you do.
8. Copy the key into a safe temporary spot (a Notepad file is fine). You'll
   paste it into GitHub in Step 11, and then you can delete the note.

**✅ Checkpoint:** you have a key about 32 characters long, made of letters and
numbers.

### Step 4: Set a renewal reminder now

BLS requires registrations to be renewed **at least once a year**. If the key
lapses, nothing breaks. The dashboard keeps showing the last saved prices with
a note saying it couldn't reach BLS, but the prices stop updating.

1. Add a calendar reminder for **11 months from today**:
   *"Renew BLS key for Vendor Watch — data.bls.gov/registrationEngine"*
2. To renew, re-register at the same page with the same email. If BLS issues a
   **new** key, update the GitHub secret by following the "Updating the BLS
   key" section at the end of this guide.

---

## Part 4 — Create your GitHub account (10 minutes)

### Step 5: Sign up

1. Go to **https://github.com/signup**
2. Enter your email address (ask IT whether Tarheel prefers a work email here).
3. Create a strong password. Save it in your password manager.
4. Choose a **username**. It becomes part of the dashboard's web address:
   `https://USERNAME.github.io/vendor-watch/`. Pick something professional,
   like `tarheel-tucker`.
5. Complete the puzzle to prove you're human.
6. GitHub emails you a code. Enter it.
7. If asked about your plan or interests, choose **Free** and skip anything
   optional.

**✅ Checkpoint:** you're on the GitHub dashboard, with your profile picture
(a default pattern) in the top-right corner.

### Step 6: Turn on two-factor authentication

GitHub will prompt you to do this, if not now then soon. Doing it now avoids
an interruption later.

1. Click your profile picture (top right) → **Settings**.
2. In the left sidebar: **Password and authentication**.
3. Under **Two-factor authentication**, click **Enable two-factor
   authentication**.
4. Scan the QR code with an authenticator app (Microsoft Authenticator, Google
   Authenticator, or similar) and enter the 6-digit code it shows.
5. **Download your recovery codes** and store them somewhere safe. They're how
   you get back in if you lose your phone.

**✅ Checkpoint:** the settings page says two-factor authentication is enabled.

> **Optional, but worth considering:** so the project belongs to Tarheel rather
> than your personal account, click your profile picture → **Your
> organizations** → **New organization** → **Free**, and name it (e.g.
> `tarheel-paper`). In Step 7, choose that organization as the **Owner**. The
> address then becomes `tarheel-paper.github.io/vendor-watch`, and ownership
> can be shared or handed off later without moving anything.

---

## Part 5 — Build the repository (15 minutes)

### Step 7: Create the repository

1. Click the **+** in the top-right corner → **New repository**.
2. **Owner:** your username (or the organization, if you made one).
3. **Repository name:** `vendor-watch`, typed exactly like that (lowercase,
   with a hyphen).
4. **Description (optional):** `Tarheel vendor & industry watch dashboard`
5. **Visibility:** **Public** (or **Private**, if you chose Pro in Step 2).
6. Leave everything else as it is. **Do not** turn on "Add README." You're
   uploading your own.
7. Click **Create repository**.

**✅ Checkpoint:** a mostly empty page headed *"Quick setup — if you've done
this kind of thing before"* with some instructions you can ignore.

### Step 8: Upload the project files

1. On that page, find the sentence *"Get started by creating a new file or
   uploading an existing file"* and click **uploading an existing file**.
2. In File Explorer, open your unzipped `vendor-watch` folder and select these
   files (hold **Ctrl** and click each one):
   - `vendor_watch.py`
   - `config.json`
   - `watch_data.json`
   - `README.md`
   - `GITHUB_SETUP.md`
   - `run_watch.bat`
   - `.gitignore`
3. Drag them onto the GitHub page, into the box that says *"Drag files here."*
4. **Do not** drag the `.github` folder; you'll create that file in Step 9.
5. Wait for all seven files to appear in the list below the box.
6. Scroll down to **Commit changes**. The note box can stay as *"Add files via
   upload."*
7. Leave **Commit directly to the main branch** selected, then click the green
   **Commit changes** button.

**✅ Checkpoint:** the repository page now lists your seven files, with the
README text displayed underneath.

> **Already running it on a PC?** Upload that PC's `watch_data.json` instead
> of the one in the zip, so your saved findings and "already seen" history
> carry over.

### Step 9: Add the workflow (the schedule)

This is the file that tells GitHub what to run and when. It goes in a
specially named folder, so you'll create it directly on GitHub, which is more
reliable than uploading a folder.

1. On your repository's main page, click **Add file** → **Create new file**.
2. Click in the **Name your file…** box and type exactly:

   ```
   .github/workflows/vendor-watch.yml
   ```

   Type it character by character. Each time you type **/**, the text before
   it jumps left and becomes a folder name. That's correct. When you're done,
   the path reads `vendor-watch / .github / workflows / vendor-watch.yml`.
3. On your computer, open the `vendor-watch` folder → `.github` → `workflows`.
   Right-click `vendor-watch.yml` → **Open with** → **Notepad**.
4. In Notepad, press **Ctrl + A** (select all), then **Ctrl + C** (copy).
5. Back on GitHub, click in the large editing area and press **Ctrl + V**
   (paste).
6. Check that the first line reads
   `# Tarheel Vendor & Industry Watch - runs the scan on GitHub's computers and`
   and the last line reads `        uses: actions/deploy-pages@v4`.
7. Click **Commit changes…** (top right) → in the pop-up, click **Commit
   changes**.

**✅ Checkpoint:** you're viewing the file, and the path at the top shows
`.github/workflows/vendor-watch.yml`.

> **If something's off:** spacing matters in this file. If you typed any of it
> by hand or the paste looks misaligned, click the **trash can icon** to delete
> it and repeat this step with a fresh copy and paste.

### Step 10: Allow the workflow to save its findings

Some GitHub accounts start with workflows set to read-only. This makes sure
yours can save the daily results.

1. Click **Settings** (the gear tab across the top of the repository, not
   your profile settings).
2. In the left sidebar: **Actions** → **General**.
3. Scroll to **Workflow permissions**.
4. Select **Read and write permissions**.
5. Click **Save**.

**✅ Checkpoint:** "Read and write permissions" is selected.

### Step 11: Store the BLS key as a secret

1. Still in the repository's **Settings**, in the left sidebar under
   **Security**: **Secrets and variables** → **Actions**.
2. Click the green **New repository secret** button.
3. **Name:** `BLS_API_KEY`, exactly like that (all capitals, with
   underscores). The workflow looks for this exact name.
4. **Secret:** paste your key from Step 3. Make sure there are no extra spaces
   before or after it.
5. Click **Add secret**.

**✅ Checkpoint:** `BLS_API_KEY` appears under **Repository secrets**. You
can't view the value again; that's normal, and it's the point. You can now
delete the temporary Notepad copy of the key.

### Step 12: Turn on the website (Pages)

1. Still in **Settings**, click **Pages** in the left sidebar (under **Code
   and automation**).
2. Under **Build and deployment**, find **Source**. Click the dropdown (it
   probably says *"Deploy from a branch"*) and choose **GitHub Actions**.

That's it. There's no save button; the choice saves itself.

**✅ Checkpoint:** Source shows **GitHub Actions**.

---

## Part 6 — First run and sharing (15 minutes, mostly waiting)

### Step 13: Run it for the first time

1. Click the **Actions** tab at the top of the repository.
2. If a yellow banner says workflows aren't enabled, click **I understand my
   workflows, go ahead and enable them**.
3. In the left sidebar, click **Vendor Watch**.
4. On the right, click the **Run workflow** dropdown → leave the branch as
   **main** → click the green **Run workflow** button.
5. Wait about 5 seconds, then refresh the page. A run appears with a spinning
   yellow circle.
6. Click the run's name to watch. Click **scan** to see each step as it
   happens. **Run the scan** shows the same progress messages you'd see on a
   PC.
7. The run takes about **5–15 minutes**. The first run looks back 90 days for
   every vendor, and later runs are faster.

**✅ Checkpoint:** a **green check mark** ✅ next to the run.

> **If you get a red ✖:** click it, then click the step with the red ✖ to read
> the error, and see the troubleshooting table at the end of this guide.

### Step 14: Open your dashboard

1. Go to **Settings** → **Pages**.
2. At the top: **"Your site is live at https://USERNAME.github.io/vendor-watch/"**
3. Click **Visit site**.

**✅ Checkpoint:** your Vendor & Industry Watch dashboard loads, with today's
date under "Last updated" and prices in the Commodity Signals strip, with no
"couldn't reach BLS" note.

> The address can take a minute or two to work after the very first run. If you
> see a 404 page, wait two minutes and refresh.

### Step 15: Share it and switch over

1. **Bookmark the link and send it to your team.** The address never changes,
   and the page updates itself every weekday morning. Nobody else needs a
   GitHub account to view it.
2. **If a PC was running it through Task Scheduler,** open Task Scheduler,
   right-click the Vendor Watch task, and choose **Disable**. Two copies
   running separately would each keep their own list.

🎉 **You're done.**

---

## Part 7 — Living with it

### What happens automatically
- **Weekdays at about 7:17 AM Eastern** (6:17 AM in winter; GitHub schedules in
  UTC and ignores daylight saving time): GitHub runs the scan, saves the
  findings back to the repository (you'll see daily commits from
  `vendor-watch-bot` — that's normal), and republishes the dashboard.
- GitHub sometimes starts scheduled runs late during busy periods, occasionally
  by up to an hour.

### Changing the watchlist, competitors, or other settings
1. Open your repository and click `config.json`.
2. Click the **pencil icon** (Edit this file), top right of the file.
3. Make your change. Mind the commas and quotes: each entry except the last in
   a list ends with a comma, and all text goes in "double quotes". For example,
   adding a competitor:
   ```
   "competitors": [
       "Imperial Dade", "Veritiv", "Bunzl Distribution",
       "SouthEastern Paper Group", "New Competitor Name"
   ],
   ```
4. Click **Commit changes…** → **Commit changes**.
5. The next scheduled run uses it. To apply it now, run the workflow manually
   (Step 13). New vendors automatically get a full 90-day first scan.

If you make a typo, the next run fails with *"config.json has a formatting
error"* and you'll get an email. Open the file's **History** (clock icon) to
see exactly what changed, or just fix the typo.

### Running a scan on demand
**Actions** → **Vendor Watch** → **Run workflow** → **Run workflow**.

### Changing the time it runs
Edit `.github/workflows/vendor-watch.yml` and change the `cron:` line. The
five parts are *minute, hour (UTC), day of month, month, day of week*.
Eastern time is UTC minus 4 hours in summer and minus 5 in winter. Examples:
- `"17 11 * * 1-5"`: 7:17 AM EDT, Monday–Friday (current)
- `"17 12 * * 1-5"`: 8:17 AM EDT, Monday–Friday
- `"17 11 * * 1"`: Mondays only

### Updating the BLS key (yearly renewal)
1. Re-register at **data.bls.gov/registrationEngine** with the same email.
2. If you receive a new key: repository **Settings** → **Secrets and variables**
   → **Actions** → click the pencil icon next to `BLS_API_KEY` → paste the new
   key → **Update secret**.
3. Run the workflow manually to confirm the prices refresh.

### Notifications
GitHub emails you when a scheduled run fails. It sends failure notices to
whoever last changed the workflow file, which should be you.

### If GitHub pauses the schedule
GitHub turns off scheduled workflows in public repositories after 60 days with
no activity. The daily data saves should count as activity, but if you ever
get an email saying the workflow was disabled: **Actions** → **Vendor Watch**
→ **Enable workflow**.

### Annual checklist (put it on the same calendar reminder)
- [ ] Renew the BLS key (see above).
- [ ] Review the watchlist against the current catalog's Trusted Partners page.
- [ ] Review the competitor list against who you're actually seeing in deals.

---

## Troubleshooting

To see why a run failed: **Actions** tab → click the run with the red ✖ →
click **scan** → the step with the red ✖ expands to show the error. After
fixing the problem, click **Re-run jobs** → **Re-run all jobs**.

| What you see | Cause and fix |
|---|---|
| "Publish the dashboard" step fails, mentioning Pages or "environment" | Pages isn't set to GitHub Actions. Redo Step 12, then re-run. |
| "Save findings" step fails with **403** or "Permission denied" | Workflow permissions are read-only. Redo Step 10, then re-run. |
| "Run the scan" fails with "config.json has a formatting error" | A typo from your last edit to `config.json`. Fix the missing comma or quote, then re-run. |
| The workflow doesn't appear under Actions | The file name or folder is wrong. It must be exactly `.github/workflows/vendor-watch.yml`. Check the path at the top of the file. |
| Run fails on the very first line with a YAML or "syntax" error | The paste in Step 9 lost its spacing. Delete the file and redo Step 9. |
| Commodity strip says it couldn't reach BLS | The secret name isn't exactly `BLS_API_KEY`, the key wasn't activated from the BLS email, the key has expired (renew it), or BLS was briefly down (it recovers on the next run). |
| Dashboard link shows 404 | The first run hasn't finished or failed, or Pages is still starting up. Check Actions, then wait two minutes and refresh. |
| A run notes some news sources were skipped | Normal occasionally. They're caught up automatically next run. |
| Dashboard shows an "out of date" banner | Scheduled runs have stopped. Check the Actions tab for failed runs or a disabled workflow. |
