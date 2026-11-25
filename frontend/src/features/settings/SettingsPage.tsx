import { useMutation, useQueryClient } from '@tanstack/react-query';
import { type ReactNode, useState } from 'react';
import { keys, useMe } from '../../app/queries';
import { useServices } from '../../app/services';
import { PageHeader } from '../../components/PageHeader';
import ui from '../../components/ui.module.css';
import type {
  LessonLength,
  Me,
  Preferences,
  PreferencesUpdate,
  SubjectId,
} from '../../lib/api';
import { formatHour } from '../../lib/format';
import styles from './settings.module.css';

const LENGTHS: { value: LessonLength; label: string; detail: string }[] = [
  { value: 'short', label: 'Short', detail: 'about 5 minutes' },
  { value: 'standard', label: 'Standard', detail: '10–15 minutes' },
  { value: 'long', label: 'Long', detail: 'about 20 minutes' },
];

const HOURS = Array.from({ length: 24 }, (_, hour) => hour);

function timeZones(current: string): string[] {
  const zones =
    typeof Intl.supportedValuesOf === 'function'
      ? Intl.supportedValuesOf('timeZone')
      : [];
  return zones.includes(current) ? zones : [current, ...zones];
}

export function SettingsPage() {
  const me = useMe();
  return (
    <>
      <PageHeader title="Settings" />
      {me.isPending ? (
        <p className={styles.loading}>Opening settings…</p>
      ) : me.isError ? (
        <div className={styles.loading}>
          <p className={ui.notice} role="alert">
            {me.error.message}
          </p>
          <button
            type="button"
            className={ui.button}
            onClick={() => void me.refetch()}
          >
            Try again
          </button>
        </div>
      ) : (
        <SettingsForm me={me.data} />
      )}
      <Account />
    </>
  );
}

function SettingsForm({ me }: { me: Me }) {
  const { api } = useServices();
  const client = useQueryClient();
  const [saved, setSaved] = useState(false);
  const save = useMutation({
    mutationFn: (update: PreferencesUpdate) => api.updateMe(update),
    onMutate: () => setSaved(false),
    onSuccess: (updated) => {
      client.setQueryData(keys.me, updated);
      void client.invalidateQueries({ queryKey: keys.today });
      setSaved(true);
    },
  });

  // Show a change at once; if saving fails the server's value comes back.
  const prefs: Preferences = {
    ...me.preferences,
    ...(save.isPending ? definedFields(save.variables) : {}),
  };
  const update = (change: PreferencesUpdate) => save.mutate(change);
  const browserZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

  function toggleSubject(id: SubjectId, on: boolean) {
    const next = me.catalog
      .map((subject) => subject.id)
      .filter((subject) =>
        subject === id ? on : prefs.subjects.includes(subject),
      );
    if (next.length > 0) update({ subjects: next });
  }

  return (
    <div className={styles.form}>
      <p className={styles.status} aria-live="polite">
        {save.isError ? (
          <span className={ui.error} role="alert">
            Not saved: {save.error.message}
          </span>
        ) : save.isPending ? (
          'Saving…'
        ) : saved ? (
          'Saved.'
        ) : (
          'Changes are saved as you make them.'
        )}
      </p>

      <Group
        title="Time zone"
        hint="Decides when your day starts and when the morning lesson arrives."
      >
        <label className={ui.field}>
          <span className="visually-hidden">Time zone</span>
          <select
            className={styles.select}
            value={prefs.time_zone}
            onChange={(event) => update({ time_zone: event.target.value })}
          >
            {timeZones(prefs.time_zone).map((zone) => (
              <option key={zone} value={zone}>
                {zone.replaceAll('_', ' ')}
              </option>
            ))}
          </select>
        </label>
        {browserZone && browserZone !== prefs.time_zone && (
          <button
            type="button"
            className={ui.quiet}
            onClick={() => update({ time_zone: browserZone })}
          >
            Use this device’s time zone ({browserZone.replaceAll('_', ' ')})
          </button>
        )}
      </Group>

      <Group
        title="Subjects"
        hint="Lessons are chosen from the subjects that are on. At least one stays on."
      >
        <ul className={styles.subjects}>
          {me.catalog.map((subject) => {
            const on = prefs.subjects.includes(subject.id);
            const last = on && prefs.subjects.length === 1;
            return (
              <li key={subject.id} data-subject={subject.id}>
                <label className={styles.check}>
                  <input
                    type="checkbox"
                    checked={on}
                    disabled={last}
                    onChange={(event) =>
                      toggleSubject(subject.id, event.target.checked)
                    }
                  />
                  <span className={styles.checkText}>
                    <span className={styles.checkLabel}>{subject.label}</span>
                    <span className={styles.checkDetail}>
                      {subject.description}
                    </span>
                  </span>
                </label>
              </li>
            );
          })}
        </ul>
      </Group>

      <Group title="Lesson length">
        <div
          className={styles.choices}
          role="radiogroup"
          aria-label="Lesson length"
        >
          {LENGTHS.map((length) => (
            <label key={length.value} className={styles.check}>
              <input
                type="radio"
                name="lesson-length"
                value={length.value}
                checked={prefs.lesson_length === length.value}
                onChange={() => update({ lesson_length: length.value })}
              />
              <span className={styles.checkText}>
                <span className={styles.checkLabel}>{length.label}</span>
                <span className={styles.checkDetail}>{length.detail}</span>
              </span>
            </label>
          ))}
        </div>
      </Group>

      <Group title="Morning lesson">
        <label className={styles.check}>
          <input
            type="checkbox"
            checked={prefs.morning_lesson}
            onChange={(event) =>
              update({ morning_lesson: event.target.checked })
            }
          />
          <span className={styles.checkText}>
            <span className={styles.checkLabel}>
              Prepare a lesson each morning
            </span>
            <span className={styles.checkDetail}>
              It counts toward the daily limit of {me.lessons_per_day}.
            </span>
          </span>
        </label>
        <label className={`${ui.field} ${styles.hour}`}>
          <span className={ui.fieldLabel}>Ready by</span>
          <select
            className={styles.select}
            value={prefs.morning_hour}
            disabled={!prefs.morning_lesson}
            onChange={(event) =>
              update({ morning_hour: Number(event.target.value) })
            }
          >
            {HOURS.map((hour) => (
              <option key={hour} value={hour}>
                {formatHour(hour)}
              </option>
            ))}
          </select>
        </label>
      </Group>

      <Export />
    </div>
  );
}

function definedFields(
  update: PreferencesUpdate | undefined,
): Partial<Preferences> {
  const fields: Partial<Preferences> = {};
  if (!update) return fields;
  if (update.time_zone != null) fields.time_zone = update.time_zone;
  if (update.subjects != null) fields.subjects = update.subjects;
  if (update.lesson_length != null) fields.lesson_length = update.lesson_length;
  if (update.morning_lesson != null)
    fields.morning_lesson = update.morning_lesson;
  if (update.morning_hour != null) fields.morning_hour = update.morning_hour;
  return fields;
}

function Group({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <fieldset className={styles.group}>
      <legend className={ui.sectionTitle}>{title}</legend>
      {hint && <p className={styles.hint}>{hint}</p>}
      {children}
    </fieldset>
  );
}

function Export() {
  const { api, now } = useServices();
  const download = useMutation({
    mutationFn: () => api.exportData(),
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `ataraxia-export-${now().toISOString().slice(0, 10)}.json`;
      document.body.append(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
  });
  return (
    <Group
      title="Your data"
      hint="Everything Ataraxia has recorded (lessons, activity, reading sessions, and settings) as one JSON file."
    >
      <div>
        <button
          type="button"
          className={ui.button}
          disabled={download.isPending}
          onClick={() => download.mutate()}
        >
          {download.isPending ? 'Preparing the file…' : 'Download export'}
        </button>
      </div>
      {download.isError && (
        <p className={ui.error} role="alert">
          {download.error.message}
        </p>
      )}
    </Group>
  );
}

function Account() {
  const { auth, user } = useServices();
  const client = useQueryClient();
  if (auth.mode === 'local') {
    return (
      <p className={styles.localMode}>
        Local mode: no sign-in on this machine. Every request is treated as the
        owner’s.
      </p>
    );
  }
  return (
    <section className={styles.account} aria-label="Account">
      {user.email && (
        <p className={styles.hint}>
          Signed in as <span className={styles.email}>{user.email}</span>
        </p>
      )}
      <button
        type="button"
        className={ui.button}
        onClick={() => {
          client.clear();
          void auth.signOut();
        }}
      >
        Sign out
      </button>
    </section>
  );
}
