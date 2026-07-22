# Help gather the temperature data

Thanks for helping. Your computer will download a small share of the world's
cities from a free weather service and send it back to the project. It uses your
own internet connection, and many people together finish far faster than one.

You do NOT need to understand the code. Follow the steps for your system once,
then run a single command whenever you want (once a day is plenty).

The whole thing is safe: it only downloads public weather data, keeps no
passwords, and never deletes anything.

---

## Step 1 - install two free programs (one time)

**Git** (lets your computer talk to the project):
- Windows: https://git-scm.com/download/win  - after installing you get an app
  called **Git Bash**; use that for every command below.
- macOS: open the Terminal app and run `xcode-select --install`, or download from
  https://git-scm.com/download/mac
- Linux: `sudo apt install git`

**Python 3** (runs the downloader):
- All systems: https://www.python.org/downloads/
- On Windows, during install tick the box **"Add Python to PATH"**.

That's the only setup. You won't need to do Step 1 again.

---

## Step 2 - get the project (one time)

Open your terminal (on Windows: **Git Bash**) and paste these two lines:

```
git clone --depth 1 https://github.com/YASoftwareDev/temperatury.git
cd temperatury
```

This downloads the project into a folder called `temperatury`.

---

## Step 3 - run it (any time you like)

From inside that folder, run:

```
bash tools/daily-chunk.sh
```

The first run takes a minute or two to set itself up; later runs are quicker.
It will download whatever cities are still needed, then try to send them back.
When it finishes it prints one of these:

- **"DONE: opened a Pull Request"** - perfect, you're done. The project owner
  will accept it.
- **"DONE: pushed ... straight to ..."** - perfect, your data is already in.
- **A box saying it could not send automatically** - follow the short
  instructions in that box (usually: email one file to the project owner, or run
  `gh auth login` once so it can send Pull Requests for you - see below).

Run it again tomorrow, or whenever you want. Each run only fetches what is still
missing, so nothing is ever downloaded twice.

---

## To let it send data automatically (recommended)

If the script says it could not send your data, do this once so future runs send
a "Pull Request" by themselves:

1. Make a free account at https://github.com
2. Install the GitHub CLI from https://cli.github.com
3. In your terminal run `gh auth login` and follow the prompts (choose GitHub.com,
   HTTPS, and "log in with a web browser").
4. Run `bash tools/daily-chunk.sh` again - it will now open Pull Requests for you.

You never get asked to type passwords into the script; GitHub handles the login.

---

## Make it run by itself every day (optional)

**macOS / Linux:** run `crontab -e` and add this line (fix the path to where you
put the folder):

```
30 0 * * * cd $HOME/temperatury && bash tools/daily-chunk.sh >> $HOME/temps.log 2>&1
```

**Windows:** open "Task Scheduler", create a Basic Task that runs daily, and set
the program to your Git Bash `bash.exe` with the argument
`tools/daily-chunk.sh` and "Start in" set to your `temperatury` folder.

---

## Common questions

- **Is this safe / will it use a lot of data?** Yes, safe. It downloads a few
  megabytes of public weather numbers per run and stops when the daily free
  limit is reached.
- **It said "No new cities this run".** Someone already grabbed today's share, or
  you already ran it today. That's fine - try again tomorrow.
- **Something looked like an error.** Re-running is always safe; your progress is
  saved. If it keeps failing, send the last few lines to the project owner.
