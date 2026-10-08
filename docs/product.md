# Ataraxia product and experience

Ataraxia should make recording a habit take a few seconds and give its owner a reason to return that feels rewarding. A short daily reading ritual broadens vocabulary and understanding of art, history, the mind, and machine learning. The app is for one person's use, with durable personal history and a calm mobile interface.

## The daily loop

1. Open Today and see the habits scheduled for the current day.
2. Tap a habit's circle to record completion; undo immediately if needed.
3. See progress for the day and week without having to open an analytics screen.
4. Browse the five discoveries when convenient. Reading is optional and creates no overdue tasks.
5. Revisit the calendar or Library to notice progress and recall something learned.

The first useful release includes all five discovery categories. Implementation starts with habits so that content generation never becomes a dependency of habit tracking.

## Initial scope

| Area | Included in the first useful release | Later possibilities |
| --- | --- | --- |
| Habits | Binary completion, daily or selected weekdays, create/edit/archive, calendar, backfill, undo, weekly consistency | Flexible N-times-per-week targets, quantities, timers, reminders, pause periods |
| Motivation | Clear progress, personal milestones, optional streak display, small completion animation | Points, levels, challenges, a small growing garden |
| Discoveries | One word, artwork, historical event, mind insight, and ML paper per local day | Topic preferences, more sources, occasional extra discoveries |
| Library | Automatic history, category/date filters, text search, favorites, read/unread state | Notes, collections, active recall, spaced repetition |
| Access | One manually provisioned Firebase email/password account, sign-in only, mobile web UI, persistent session | Installable PWA, offline reading |
| Data | Persistent storage and a portable JSON export; backups before regular use | Import UI and a database migration if needs change |

Do not add social features, public profiles, competitive leaderboards, native mobile apps, a conversational coach, or push notifications to the initial release. There is no clinical assessment or personalized medical guidance in the mind category.

## Mobile screens

Use bottom navigation for **Today**, **Habits**, and **Library**. Settings is reachable from the profile control. On wider screens the same information can use two columns and a sidebar; maintain the same navigation and behavior.

### Today

Place the date and today's habit progress at the top, then the habit list, then discoveries. Each habit shows its name, a large completion control, and an optional short cue such as “After breakfast.” A completed row stays in place to avoid moving targets under the thumb.

Use a compact “2 of 3 today” indicator and a seven-day row of progress circles. Each day's fill represents completed scheduled habits. A day with no scheduled habits is neutral. Avoid adding several charts to the home screen.

Show five compact discovery previews in a vertical list: category, title, one-line hook, and reading time. Artwork gets a thumbnail. Opening a preview reveals the full card with sources and a favorite control. There is no infinite feed and no requirement to open every card.

Conceptual arrangement, not a visual specification:

```text
Ataraxia                       Profile
Thursday, 8 October

Today                         2 of 3
  ● Read for ten minutes
  ● Go for a walk
  ○ Write a short reflection
  M   T   W   T   F   S   S
  ●   ◐   ●   ◐   ·   ·   ·

Discover something
  Word       [word and short definition]
  Artwork    [thumbnail, title, artist]
  History    [event and year]
  Mind       [question and takeaway]
  ML paper   [title and short summary]

Today          Habits          Library
```

### Habits

The overview lists active habits and recent consistency. Select a habit to see its month calendar, completion total, and recent weekly trend. A selector changes habits without leaving the calendar. Archived habits remain accessible through a filter.

Calendar cells display the day number with a circle when completed. Use these states consistently:

| State | Appearance and behavior |
| --- | --- |
| Completed scheduled day | Filled circle and accessible “completed” label |
| Today, scheduled and incomplete | Outlined circle, tappable |
| Past scheduled day, incomplete | Empty ring, neutral label “not recorded” |
| Unscheduled day | Muted day number, no completion ring |
| Future day | Muted day number; completion disabled |

Highlight today with a separate outline that remains visible when completed. Do not rely on red versus green to communicate state. A day picker on small screens can show the full label and an explicit Complete/Undo control.

### Library

History is automatic: every published daily card enters the Library even if it has not been opened. A star means favorite, not save. This distinction avoids losing discoveries because a save button was missed.

Default to recent-first compact rows grouped by discovery date. Offer category chips, a favorites filter, a date range, and search over title, summary, tags, and useful metadata such as artist or paper author. Artwork rows include thumbnails; word rows include their short definitions. Opening a row shows the original full card and its sources. Keep read state separate from favorites.

### Settings and first use

The owner creates their account in the Firebase console before use. The app has an email/password sign-in screen and sign-out; it has no registration, invitation, or account-management flow. Disable end-user sign-up in Firebase settings as well. Password resets and account maintenance are handled through Firebase administration for this release.

On first sign-in, confirm the IANA time zone suggested by the browser, then invite creation of the first habit. Default to English. All five discovery categories start enabled; individual categories can be disabled later without deleting their history. Include export, sign-out, and an optional streak-display toggle. Changes to category selection affect unpublished slots and future days; ready cards stay in history.

## Habit behavior

A habit has a name, optional description/cue, optional color, a start date, and a schedule: every day or a chosen set of weekdays. Suggested names describe an achievable behavior, such as “Read for ten minutes.” The user decides whether the intended behavior was achieved; completion is binary in this release.

- One completion per habit per local date. Repeating Complete has no additional effect; repeating Undo also has no additional effect.
- Creation starts today by default, with an optional earlier start date for backfilling. Completion is allowed only on scheduled dates from the start date through today.
- Past days can be corrected. Future dates cannot be completed. A missing record on a past due date means “not recorded,” rather than a claim about what the person actually did.
- Schedule edits take effect tomorrow. Keep previous schedule versions so edits do not rewrite past statistics. A pending version for tomorrow may be replaced by another edit before it takes effect.
- Archive takes effect tomorrow; today's remaining completion can still be recorded. Keep historical data and earlier correction controls. Restoring starts a new active schedule tomorrow, leaving the archived interval unscheduled.
- A rename changes the display name across the history. A substantial change of behavior should be a new habit; renaming does not reset earned progress.

The user profile's time zone defines today. Store completion dates directly as local dates and event timestamps in UTC. A time zone change affects subsequent calculations of today; existing date labels and daily cards are not moved or regenerated. This is sufficient for personal use without a travel-history model.

### Statistics and motivation

Show today's completion count and the last seven completed local days' consistency. Consistency equals completed scheduled opportunities divided by scheduled opportunities in that window. Exclude today from this percentage while it is in progress. Show “No scheduled days” instead of zero percent when the denominator is zero.

For a habit scheduled Monday, Wednesday, and Friday, completing Monday and Wednesday out of a finished week gives 2/3. Tuesday is neither a miss nor an extra success. Aggregate progress sums opportunities across habits; it is not the average of their individual percentages.

Optional streaks count consecutive completed scheduled dates. Unscheduled dates do not break a streak; an incomplete today does not break it until the day ends. Archive intervals end a streak, while total completions remain. Backfills and undo recalculate streaks and statistics.

Use milestone thresholds of 7, 30, and 100 total completions per habit, with restrained celebration and reduced-motion support. Milestones are derived from completion history; undo can remove a threshold. Do not store a separate points balance or make corrections generate repeated rewards.

The default experience emphasizes returning after a gap and visible accumulated effort. A missed day does not erase total progress, incur a debt, or trigger reprimands. These are design preferences, not claims that a particular mechanic is proven to form habits.

## Discovery cards

| Category | Card content |
| --- | --- |
| Word | Word, part of speech, plain definition, register/use note, and 2–3 original example sentences suited to real conversation or writing |
| Artwork | Image when available with usable rights, title, artist or culture, approximate date, medium, 80–150 words of context, and a viewing prompt |
| History | Event, actual date/year, location where known, 80–150 words on what happened and why it mattered; “On this day” only when the date matches |
| Mind | Clear question or idea, 100–180 words, a concrete everyday connection, and an evidence limitation when relevant |
| ML paper | Exact title, authors/year, a 100–180 word plain-language abstract summary, why it is interesting, a limitation when the supplied source supports one, and links to the paper record and full text |

Lengths are targets rather than rigid UI constraints. An artwork card can be shorter when only factual collection metadata is available. Show paper summaries as summaries; do not label generated text as the authors' original abstract or invent a limitation to fill the layout. Detail screens can include a link to the original abstract. Learning about psychedelics, neurological disease, cognition, emotions, and mental health fits within the mind category as educational content.

Randomness means varied selection from eligible sources, with repeat suppression and a balance of subjects. It does not mean every work or event in existence has an equal selection probability. Selection, sources, and failure behavior are specified in [Daily discoveries](discoveries.md).

## Accessibility and failure states

Design for a 360-pixel-wide phone, comfortable text, visible focus, semantic buttons, at least 44-pixel touch targets, and light/dark themes. Support keyboard use and screen readers. Artwork uses contain-style images so the whole work can be inspected, with a full-image link. Keep reading layouts narrow enough for comfortable prose.

Habit completion responds optimistically, indicates a pending save, and rolls back with a concise retry message on failure. Serialize changes for the same habit/day while a save is pending and refetch authoritative state after an uncertain outcome. A network failure must not leave a false completed circle. Disable new changes while the browser reports offline; do not persist or automatically replay an offline mutation queue. Offline writes and synchronization are deferred.

Discovery generation can show “Preparing today's selection” and update independently of habits. One failed category does not block the others. If a card cannot be produced, show a retry state and access to previous cards. Never present yesterday's card as today's. Source images can fail independently: retain the text, attribution, and source link.

## How to judge the first release

The app succeeds if its owner can record today's habits without navigating, inspect a month of accurate circles, and quickly find an old discovery. Verify this on an actual phone. After two weeks of use, review whether the calendar and milestones encourage return, whether the reading load feels manageable, and which cards are worth revisiting before adding new mechanics.

The most promising follow-ups are flexible weekly targets, a weekly reflection, and one optional recall question drawn from saved discoveries. Build them only after the basic loop is useful.
