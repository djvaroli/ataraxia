# Ataraxia product and experience

Ataraxia gives its owner one good lesson a day: a 10–15 minute read on art, history,
film, words, geography and geopolitics, science, mathematics, computer science, or
another subject worth knowing. A lesson can be saved, rated, and continued into a
deeper follow-up. Everything the owner does is recorded so that the history can be
reviewed later, by the owner or by Claude, to tune the lessons, write recaps, and
eventually build quizzes.

The app is for one person on a phone. It should feel like a quiet, well-made
reading room rather than a feed. The working name comes from the repository and can
change.

Habit tracking, the earlier first priority, is deferred until the learning loop is
in daily use; see [Later](#later).

## The daily loop

1. Open Today. The day's lesson is ready, prepared early in the morning in the
   owner's time zone, or can be started on request.
2. Read it. Reading time and progress are recorded; there is no quiz or obligation.
3. At the end, mark it finished, rate it ("More like this" / "Less like this"), and
   save it if it is worth keeping.
4. To go further, choose one of the suggested follow-up directions or ask a question
   of your own. The follow-up becomes the next part of the same thread.
5. Any time: ask for another lesson ("Surprise me", a chosen subject, or a specific
   topic), browse the Library, or look at Progress to see what has been covered.

Unread lessons never pile up as overdue work. Missing a day costs nothing except a
streak count.

## Lessons

A lesson is written by Claude for this reader. It has:

| Part | Content |
| --- | --- |
| Header | Subject, title, a one- or two-sentence hook, estimated reading minutes |
| Body | About 2,300–3,200 words of Markdown at the standard length, with section headings; formulas for mathematics, short code blocks for computer science |
| Illustrations | Up to three images from Wikipedia for subjects where pictures matter (artworks, places, films, people), each with a caption and source link |
| What to remember | Three to five key ideas |
| Glossary | Terms worth keeping, with short definitions (the main content in Words lessons) |
| Go deeper | Three suggested follow-up directions |
| Further | A few books, films, works, or places to explore; links are search links, never model-invented URLs |

Length is a setting: short (about 5 minutes), standard (10–15 minutes, the default),
or long (about 20 minutes).

Subjects in the initial catalog: Art, History, Film, Words, Geography & geopolitics,
Science, Mathematics, Computer science, Philosophy, Literature, and Music. Each can
be turned off in Settings without deleting its history. Every subject has its own
writing guidance; for example, Film lessons avoid spoilers past the first act unless
the lesson says so first, and Words lessons teach a small themed set of useful words
with origins and example sentences.

### Choosing what to teach

The daily lesson and "Surprise me" pick a subject at random, weighted toward subjects
the owner has rated well and away from the subjects of the last two lessons. Claude
then picks the topic, given the titles already covered (to avoid repeats) and recent
likes and dislikes (as taste hints). A requested topic skips the choice: the owner's
words become the brief.

### Follow-ups

"Go deeper" creates a new lesson linked to the one being read. Claude receives the
earlier lesson and the chosen direction or question, and continues without repeating
the basics. A thread can keep growing; the reader shows where a lesson sits in its
thread.

### Accuracy

Lessons come from the model's knowledge, not retrieved sources. The writing guidance
asks for conservative claims, plain separation of established fact from interpretation
or dispute, and explicit uncertainty about dates and figures. Images and their links
come from Wikipedia records the worker looks up, not from the model. A lesson is
reading material, not a reference; the owner can flag one that looks wrong, which
records the concern for later review.

## Activity record

Every meaningful action is stored as a timestamped event with the owner's local date:

- app opened; lesson requested, prepared, opened, read (time and how far), finished,
  saved or unsaved, rated, flagged, expanded into a follow-up;
- settings changed; generation failures.

The record is append-only and never expires. It is available through the API, a
JSON export, and a command-line tool, so a later Claude session can pull it to tune
subject weights and prompts, write weekly or monthly recaps, or point out patterns
in what the owner reads. Events contain lesson IDs and subjects; the only free text
is the owner's own topic requests, questions, and notes on flagged lessons.

## Screens

Bottom navigation: **Today**, **Library**, **Progress**. Settings opens from Progress.
Wider screens keep the same structure with a centered reading column.

### Today

The date, set like the masthead of an almanac, then today's lesson: subject, title,
hook, reading time, and a clear way to begin. While it is being prepared the page says
so plainly and updates itself. Below it: unfinished lessons to continue, and "Another
lesson" with Surprise me, a subject list, and a box to ask for any topic. The remaining
lessons allowed today are shown only when the limit is close.

### Lesson reader

A narrow column of serif text with comfortable size and line spacing, a thin reading
progress line, and minimal chrome: back, save, and a menu (flag a problem). The end
of the lesson holds What to remember, the glossary, Further, Go deeper, the rating
control, and Mark as finished.

### Library

Every lesson ever prepared, newest first, grouped by month. Filters: Saved, subject,
and text search over titles, hooks, and tags. Rows show subject, title, reading time,
and finished/saved state. Threads are visible as "Part 2 of …".

### Progress

Current and longest streak (days with a finished lesson), lessons finished, minutes
read, a breakdown by subject, and a calendar of recent weeks. This is where "which
subjects have I learned about" is answered. Settings and sign-out are reached from
here.

### Settings

Time zone (suggested from the browser on first run), subjects on/off, lesson length,
whether to prepare a lesson each morning and at what hour, and data export.

### Sign-in

Email and password through Firebase for the one account the owner created in the
Firebase console. There is no registration, invitation, or account-management flow,
and end-user sign-up is disabled in Firebase. Local development can run without
sign-in; see [architecture](architecture.md#authentication).

## Look and feel

Pleasant, calm, and specific to reading:

- warm paper and ink colors with a matching dark theme; one muted pigment color per
  subject used sparingly for labels, rules, and progress;
- a screen-designed serif for reading and headlines, a clean sans-serif for interface
  labels; generous margins and line spacing; a reading column of about 65 characters;
- small, quiet motion (fade and slide between screens, progress line), disabled for
  reduced-motion users;
- no gradients, glass effects, emoji, or generic dashboard cards.

Design for a 360-pixel-wide phone, 44-pixel touch targets, visible focus, keyboard
use, and semantic controls. Dedicated screen-reader audits are deferred. The app can
be added to the phone's home screen; offline reading is deferred.

## Limits and failure states

- A daily cap on prepared lessons (default 8) protects the owner's Claude usage. The
  morning lesson counts toward it. Reaching it disables new requests until tomorrow.
- At most three lessons can be waiting at once.
- If Claude's usage limit is reached, the lesson waits and tries again on its own
  every half hour, and the card says so.
- If preparation fails, the lesson card says why in plain words (Claude is not signed
  in on the server, or a generation problem) and offers a retry. Other lessons and
  the Library keep working.
- A lesson, once prepared, does not change. There is no "reroll"; ask for another.

## Later

Candidates once the daily loop has been used for a few weeks, roughly in order:

1. Quizzes and spaced review drawn from finished lessons' key ideas.
2. Weekly or monthly recaps written from the activity record.
3. Habit tracking (the earlier design: binary habits, schedules, calendar, streaks),
   recovered from Git history when wanted.
4. Retrieval-backed lessons for subjects where accuracy matters most.

No social features, public profiles, conversational coach, or push notifications.
