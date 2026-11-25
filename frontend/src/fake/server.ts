/**
 * An in-memory implementation of /api/v1 behind a `fetch`-compatible function.
 *
 * Tests and the demo build run the real API client against it, so request
 * shapes, auth headers, and error handling are exercised end to end. It models
 * the documented rules loosely: enough to show every screen state, not a
 * second backend.
 */
import type {
  ClientConfig,
  DailySlot,
  ErrorCode,
  FetchLike,
  Job,
  Lesson,
  LessonState,
  LessonSummary,
  Me,
  Progress,
  SubjectId,
  SubjectInfo,
  Today,
  WorkerStatus,
} from '../lib/api';
import {
  PREPARED_TEMPLATES,
  SAMPLE_LESSONS,
  type SampleLesson,
} from './lessons';

export const CATALOG: SubjectInfo[] = [
  {
    id: 'art',
    label: 'Art',
    description:
      'Paintings, sculpture, architecture, photography, and the people who made them',
  },
  {
    id: 'history',
    label: 'History',
    description:
      'Events, people, and turning points, and why they unfolded as they did',
  },
  {
    id: 'film',
    label: 'Film',
    description: 'Notable films and filmmakers, craft, and film history',
  },
  {
    id: 'words',
    label: 'Words',
    description: 'Useful, precise, or beautiful words and where they come from',
  },
  {
    id: 'geography',
    label: 'Geography & geopolitics',
    description:
      'Places, landscapes, borders, resources, and how they shape power',
  },
  {
    id: 'science',
    label: 'Science',
    description:
      'Physics, biology, chemistry, earth and space, the mind and body',
  },
  {
    id: 'math',
    label: 'Mathematics',
    description: 'Ideas, proofs, and the intuition behind them',
  },
  {
    id: 'computing',
    label: 'Computer science',
    description:
      'Algorithms, systems, programming ideas, and computing history',
  },
  {
    id: 'philosophy',
    label: 'Philosophy',
    description: 'Big questions, arguments, and the thinkers behind them',
  },
  {
    id: 'literature',
    label: 'Literature',
    description: 'Novels, poems, plays, and the writers who made them',
  },
  {
    id: 'music',
    label: 'Music',
    description: 'Composers, genres, instruments, and how music works',
  },
];

export type Scenario =
  | 'ready'
  | 'preparing'
  | 'failed'
  | 'waiting'
  | 'not_scheduled'
  | 'limit'
  | 'new';

export interface FakeServerOptions {
  /** Fixed "now" for deterministic tests. */
  now?: () => Date;
  authMode?: ClientConfig['auth_mode'];
  scenario?: Scenario;
  /**
   * Move active jobs one step on GET /today or GET /jobs/{id} when at least
   * this many ms have passed since the last step. Left out, jobs only move
   * when `advanceJobs` is called.
   */
  advanceEveryMs?: number;
  /** Artificial latency in ms, for the demo. */
  latency?: number;
}

export interface RecordedRequest {
  method: string;
  path: string;
  body: unknown;
  authorization: string | null;
  keepalive: boolean;
}

interface Failure {
  method?: string;
  path: RegExp;
  status: number;
  code: ErrorCode;
  message: string;
  times: number;
}

interface StoredLesson {
  lesson: Lesson;
  sample: SampleLesson | null;
}

const DAY_MS = 86_400_000;

function isoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function emptyState(): LessonState {
  return {
    saved: false,
    saved_at: null,
    rating: 0,
    first_opened_at: null,
    finished_at: null,
    read_seconds: 0,
    furthest_scroll: 0,
    flagged: false,
  };
}

class HttpError extends Error {
  readonly status: number;
  readonly code: ErrorCode;
  constructor(status: number, code: ErrorCode, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export class FakeServer {
  readonly requests: RecordedRequest[] = [];
  readonly readingReports = new Map<
    string,
    { lessonId: string; seconds: number; scroll: number }
  >();
  me: Me;
  worker: WorkerStatus;
  lessonsPerDay = 8;
  advanceEveryMs: number | undefined;
  dailyWhenNone: 'waiting' | 'not_scheduled' = 'not_scheduled';

  private readonly now: () => Date;
  private readonly authMode: ClientConfig['auth_mode'];
  private readonly latency: number;
  private readonly lessons = new Map<string, StoredLesson>();
  private readonly jobs: Job[] = [];
  private readonly failures: Failure[] = [];
  private nextId = 1;
  private usedToday = 0;
  private lastAdvance: number;

  constructor(options: FakeServerOptions = {}) {
    this.now = options.now ?? (() => new Date());
    this.authMode = options.authMode ?? 'local';
    this.latency = options.latency ?? 0;
    this.advanceEveryMs = options.advanceEveryMs;
    this.lastAdvance = this.now().getTime();
    this.me = {
      auth_mode: this.authMode,
      catalog: CATALOG,
      lessons_per_day: this.lessonsPerDay,
      preferences: {
        time_zone: 'UTC',
        time_zone_confirmed: true,
        subjects: CATALOG.map((subject) => subject.id),
        lesson_length: 'standard',
        morning_lesson: true,
        morning_hour: 6,
      },
    };
    this.worker = {
      online: true,
      heartbeat_at: this.now().toISOString(),
      login_expires_at: null,
    };
    for (const sample of SAMPLE_LESSONS) this.addSample(sample);
    this.applyScenario(options.scenario ?? 'ready');
  }

  get today(): string {
    return isoDate(this.now());
  }

  /** The `fetch` the API client should use. */
  readonly fetch: FetchLike = async (input, init = {}) => {
    const method = (init.method ?? 'GET').toUpperCase();
    const url = new URL(input, 'http://fake.local');
    const headers = new Headers(init.headers);
    const body: unknown =
      typeof init.body === 'string' ? JSON.parse(init.body) : null;
    this.requests.push({
      method,
      path: url.pathname + url.search,
      body,
      authorization: headers.get('Authorization'),
      keepalive: init.keepalive === true,
    });
    if (this.latency > 0) {
      await new Promise((resolve) => setTimeout(resolve, this.latency));
    }
    const failure = this.failures.find(
      (item) =>
        item.path.test(url.pathname) &&
        (!item.method || item.method === method),
    );
    if (failure) {
      failure.times -= 1;
      if (failure.times <= 0) {
        this.failures.splice(this.failures.indexOf(failure), 1);
      }
      return errorResponse(failure.status, failure.code, failure.message);
    }
    try {
      const result = this.route(method, url.pathname, url.searchParams, body);
      if (result === undefined) return new Response(null, { status: 204 });
      const status = method === 'POST' && isAccepted(url.pathname) ? 202 : 200;
      return new Response(JSON.stringify(result), {
        status,
        headers: { 'Content-Type': 'application/json' },
      });
    } catch (error) {
      if (error instanceof HttpError) {
        return errorResponse(error.status, error.code, error.message);
      }
      throw error;
    }
  };

  /** Add `count` older copies of a sample lesson, to fill the library past one page. */
  addOlderLessons(count: number): void {
    const template = SAMPLE_LESSONS.find((sample) => sample.id === 'l-sky');
    if (!template) return;
    for (let index = 0; index < count; index += 1) {
      this.addSample({
        ...template,
        id: `l-old-${index}`,
        title: `${template.title} (${index + 1})`,
        daysAgo: 90 + index,
      });
    }
  }

  /** Make the next `times` matching requests fail. */
  failNext(failure: Omit<Failure, 'times'> & { times?: number }): void {
    this.failures.push({ times: 1, ...failure });
  }

  requestsTo(method: string, path: RegExp): RecordedRequest[] {
    return this.requests.filter(
      (item) => item.method === method && path.test(item.path),
    );
  }

  lesson(id: string): Lesson | undefined {
    return this.lessons.get(id)?.lesson;
  }

  job(id: string): Job | undefined {
    return this.jobs.find((job) => job.id === id);
  }

  allJobs(): readonly Job[] {
    return this.jobs;
  }

  /** Move every queued job to running and every running job to done. */
  advanceJobs(): void {
    const time = this.now().toISOString();
    for (const job of this.jobs) {
      if (job.status === 'running') {
        const lesson = this.prepareLesson(job);
        job.status = 'succeeded';
        job.lesson_id = lesson.id;
        job.finished_at = time;
        job.error_code = null;
        job.error_message = null;
      } else if (job.status === 'queued' && !this.isDeferred(job)) {
        job.status = 'running';
        job.attempts += 1;
        job.started_at = time;
      }
    }
  }

  /** Fail the given job as the worker would. */
  failJob(id: string, code: NonNullable<Job['error_code']>, message: string) {
    const job = this.job(id);
    if (!job) throw new Error(`No job ${id}`);
    job.status = 'failed';
    job.error_code = code;
    job.error_message = message;
    job.can_retry = true;
    job.finished_at = this.now().toISOString();
  }

  addJob(fields: Partial<Job> & Pick<Job, 'kind'>): Job {
    const now = this.now().toISOString();
    const job: Job = {
      id: `j-${this.nextId++}`,
      status: 'queued',
      local_date: this.today,
      subject: null,
      request_text: null,
      parent_lesson_id: null,
      attempts: 0,
      error_code: null,
      error_message: null,
      lesson_id: null,
      can_retry: false,
      next_attempt_at: null,
      created_at: now,
      started_at: null,
      finished_at: null,
      ...fields,
    };
    this.jobs.unshift(job);
    this.usedToday += 1;
    return job;
  }

  private isDeferred(job: Job): boolean {
    return (
      job.next_attempt_at !== null &&
      new Date(job.next_attempt_at).getTime() > this.now().getTime()
    );
  }

  private applyScenario(scenario: Scenario): void {
    const dailySample = this.lessons.get('l-vermeer');
    switch (scenario) {
      case 'ready': {
        const daily = this.addJob({ kind: 'daily', subject: 'art' });
        daily.status = 'succeeded';
        daily.lesson_id = 'l-vermeer';
        this.addJob({
          kind: 'topic',
          request_text: 'the history of the semicolon',
          status: 'running',
          attempts: 1,
          started_at: this.now().toISOString(),
        });
        this.usedToday = 6;
        break;
      }
      case 'preparing':
        this.lessons.delete('l-vermeer');
        this.addJob({ kind: 'daily', status: 'running', attempts: 1 });
        break;
      case 'failed': {
        this.lessons.delete('l-vermeer');
        const job = this.addJob({ kind: 'daily', attempts: 1 });
        this.failJob(
          job.id,
          'claude_auth',
          'Claude is not signed in on the server.',
        );
        break;
      }
      case 'waiting':
        this.lessons.delete('l-vermeer');
        this.dailyWhenNone = 'waiting';
        this.me.preferences.morning_hour = 23;
        break;
      case 'not_scheduled':
        this.lessons.delete('l-vermeer');
        this.me.preferences.morning_lesson = false;
        break;
      case 'limit': {
        const daily = this.addJob({ kind: 'daily', subject: 'art' });
        daily.status = 'succeeded';
        daily.lesson_id = 'l-vermeer';
        this.addJob({
          kind: 'subject',
          subject: 'music',
          attempts: 1,
          error_code: 'claude_usage_limit',
          error_message: 'Claude’s usage limit was reached.',
          next_attempt_at: new Date(
            this.now().getTime() + 25 * 60_000,
          ).toISOString(),
        });
        const failed = this.addJob({ kind: 'surprise', attempts: 2 });
        this.failJob(
          failed.id,
          'invalid_output',
          'The lesson came back incomplete twice.',
        );
        this.usedToday = this.lessonsPerDay;
        this.worker.login_expires_at = new Date(
          this.now().getTime() + 3 * DAY_MS,
        ).toISOString();
        break;
      }
      case 'new':
        this.lessons.clear();
        this.me.preferences.time_zone_confirmed = false;
        this.me.preferences.morning_lesson = false;
        break;
    }
    if (dailySample && scenario !== 'ready' && scenario !== 'limit') {
      // Keep the sample out of the library when today's lesson is not ready.
      this.lessons.delete('l-vermeer');
    }
  }

  private addSample(sample: SampleLesson): void {
    const created = new Date(this.now().getTime() - sample.daysAgo * DAY_MS);
    created.setUTCHours(6, 0, 0, 0);
    const parent = sample.parentId ? this.lessons.get(sample.parentId) : null;
    const state = emptyState();
    if (sample.opened) state.first_opened_at = created.toISOString();
    if (sample.finished) {
      state.finished_at = created.toISOString();
      state.read_seconds = sample.readingMinutes * 60;
    } else if (sample.opened) {
      state.read_seconds = Math.round(
        sample.readingMinutes * 60 * (sample.scroll ?? 0),
      );
    }
    if (sample.saved) {
      state.saved = true;
      state.saved_at = created.toISOString();
    }
    state.rating = sample.rating ?? 0;
    state.furthest_scroll = sample.scroll ?? 0;
    const lesson: Lesson = {
      id: sample.id,
      created_at: created.toISOString(),
      local_date: isoDate(created),
      subject: sample.subject,
      origin: sample.origin,
      title: sample.title,
      hook: sample.hook,
      reading_minutes: sample.readingMinutes,
      tags: sample.tags,
      cover: sample.illustrations[0] ?? null,
      parent_id: sample.parentId ?? null,
      thread_root_id: parent ? parent.lesson.thread_root_id : sample.id,
      part: parent ? parent.lesson.part + 1 : 1,
      state,
      request_text: sample.requestText ?? null,
      body_markdown: sample.body,
      key_ideas: sample.keyIdeas,
      glossary: sample.glossary,
      go_deeper: sample.goDeeper,
      further: sample.further,
      illustrations: sample.illustrations,
      thread: [],
    };
    this.lessons.set(sample.id, { lesson, sample });
  }

  private prepareLesson(job: Job): Lesson {
    const parent = job.parent_lesson_id
      ? this.lessons.get(job.parent_lesson_id)?.lesson
      : undefined;
    const subject: SubjectId = parent?.subject ?? job.subject ?? 'words';
    const templateId = PREPARED_TEMPLATES[subject] ?? 'l-dusk';
    const template =
      this.lessons.get(templateId)?.lesson ??
      SAMPLE_LESSONS.map((sample) => sample.id)
        .map((id) => this.lessons.get(id)?.lesson)
        .find((lesson) => lesson !== undefined);
    if (!template) throw new Error('No template lesson');
    const id = `l-new-${this.nextId++}`;
    let title = template.title;
    if (job.kind === 'topic' && job.request_text) {
      title = `On ${job.request_text}`;
    } else if (parent && job.request_text) {
      title = job.request_text;
    } else if (parent) {
      title = `${parent.title}, continued`;
    }
    const lesson: Lesson = {
      ...structuredClone(template),
      id,
      title,
      subject,
      origin: job.kind,
      created_at: this.now().toISOString(),
      local_date: this.today,
      parent_id: parent?.id ?? null,
      thread_root_id: parent?.thread_root_id ?? id,
      part: parent ? parent.part + 1 : 1,
      request_text: job.request_text,
      state: emptyState(),
    };
    this.lessons.set(id, { lesson, sample: null });
    return lesson;
  }

  private findLesson(id: string): Lesson {
    const stored = this.lessons.get(id);
    if (!stored) throw new HttpError(404, 'not_found', 'No such lesson.');
    return stored.lesson;
  }

  private withThread(lesson: Lesson): Lesson {
    const thread = [...this.lessons.values()]
      .map((item) => item.lesson)
      .filter((item) => item.thread_root_id === lesson.thread_root_id)
      .sort((a, b) => a.part - b.part)
      .map((item) => ({
        id: item.id,
        title: item.title,
        part: item.part,
        parent_id: item.parent_id,
      }));
    return { ...lesson, thread };
  }

  private summary(lesson: Lesson): LessonSummary {
    return {
      id: lesson.id,
      created_at: lesson.created_at,
      local_date: lesson.local_date,
      subject: lesson.subject,
      origin: lesson.origin,
      title: lesson.title,
      hook: lesson.hook,
      reading_minutes: lesson.reading_minutes,
      tags: lesson.tags,
      cover: lesson.cover,
      parent_id: lesson.parent_id,
      thread_root_id: lesson.thread_root_id,
      part: lesson.part,
      state: lesson.state,
    };
  }

  private sortedLessons(): Lesson[] {
    return [...this.lessons.values()]
      .map((item) => item.lesson)
      .sort((a, b) => b.created_at.localeCompare(a.created_at));
  }

  private activeJobs(): Job[] {
    return this.jobs.filter(
      (job) => job.status === 'queued' || job.status === 'running',
    );
  }

  private checkAllowance(): void {
    if (this.usedToday >= this.lessonsPerDay) {
      throw new HttpError(
        429,
        'daily_limit',
        'Today’s lessons are used up. More tomorrow.',
      );
    }
    if (this.activeJobs().length >= 3) {
      throw new HttpError(
        429,
        'too_many_waiting',
        'Three lessons are already being prepared.',
      );
    }
  }

  private dailySlot(): DailySlot {
    const job = this.jobs.find(
      (item) => item.kind === 'daily' && item.local_date === this.today,
    );
    const hour = this.me.preferences.morning_lesson
      ? this.me.preferences.morning_hour
      : null;
    if (!job) {
      const status = this.me.preferences.morning_lesson
        ? this.dailyWhenNone === 'waiting'
          ? 'waiting'
          : 'not_scheduled'
        : 'not_scheduled';
      return { status, lesson: null, job: null, morning_hour: hour };
    }
    if (job.status === 'succeeded' && job.lesson_id) {
      const lesson = this.lessons.get(job.lesson_id)?.lesson;
      return {
        status: 'ready',
        lesson: lesson ? this.summary(lesson) : null,
        job,
        morning_hour: hour,
      };
    }
    return {
      status: job.status === 'succeeded' ? 'ready' : job.status,
      lesson: null,
      job,
      morning_hour: hour,
    };
  }

  private maybeAdvance(): void {
    if (this.advanceEveryMs === undefined) return;
    const now = this.now().getTime();
    if (now - this.lastAdvance >= this.advanceEveryMs) {
      this.lastAdvance = now;
      this.advanceJobs();
    }
  }

  private getToday(): Today {
    this.maybeAdvance();
    const unfinished = this.sortedLessons()
      .filter(
        (lesson) => lesson.state.first_opened_at && !lesson.state.finished_at,
      )
      .slice(0, 5)
      .map((lesson) => this.summary(lesson));
    const jobs = this.jobs.filter(
      (job) =>
        job.kind !== 'daily' &&
        job.local_date === this.today &&
        job.status !== 'succeeded',
    );
    return {
      local_date: this.today,
      daily: this.dailySlot(),
      jobs,
      unfinished,
      allowance: {
        used: this.usedToday,
        limit: this.lessonsPerDay,
        remaining: Math.max(0, this.lessonsPerDay - this.usedToday),
        waiting: this.activeJobs().length,
        waiting_limit: 3,
      },
      worker: this.worker,
    };
  }

  private getProgress(): Progress {
    const lessons = this.sortedLessons();
    const finished = lessons.filter((lesson) => lesson.state.finished_at);
    const today = this.now().getTime();
    const days = Array.from({ length: 84 }, (_, index) => {
      const date = isoDate(new Date(today - (83 - index) * DAY_MS));
      // A deterministic, uneven history so the calendar has texture.
      const seed = (index * 37 + 11) % 23;
      const recorded = finished.filter(
        (lesson) => lesson.state.finished_at?.slice(0, 10) === date,
      ).length;
      const synthetic = seed < 9 ? 1 + (seed % 3 === 0 ? 1 : 0) : 0;
      const count = Math.max(recorded, index > 79 ? recorded : synthetic);
      return {
        date,
        finished: count,
        read_minutes: count * (8 + (seed % 7)),
      };
    });
    return {
      current_streak: 4,
      longest_streak: 11,
      lessons_total: lessons.length,
      finished_total: finished.length,
      saved_total: lessons.filter((lesson) => lesson.state.saved).length,
      read_minutes_total: Math.round(
        lessons.reduce((sum, lesson) => sum + lesson.state.read_seconds, 0) /
          60,
      ),
      subjects: CATALOG.map(({ id }) => {
        const own = lessons.filter((lesson) => lesson.subject === id);
        return {
          subject: id,
          lessons: own.length,
          finished: own.filter((lesson) => lesson.state.finished_at).length,
          read_minutes: Math.round(
            own.reduce((sum, lesson) => sum + lesson.state.read_seconds, 0) /
              60,
          ),
          liked: own.filter((lesson) => lesson.state.rating === 1).length,
          disliked: own.filter((lesson) => lesson.state.rating === -1).length,
          last_finished_on:
            own.find((lesson) => lesson.state.finished_at)?.local_date ?? null,
        };
      }),
      days,
    };
  }

  private route(
    method: string,
    path: string,
    query: URLSearchParams,
    body: unknown,
  ): unknown {
    const p = path.replace(/^\/api\/v1/, '');
    const now = this.now().toISOString();
    if (method === 'GET' && p === '/client-config') {
      return {
        auth_mode: this.authMode,
        firebase:
          this.authMode === 'firebase'
            ? {
                api_key: 'demo-key',
                auth_domain: 'demo.firebaseapp.com',
                project_id: 'demo',
                app_id: 'demo-app',
              }
            : null,
      } satisfies ClientConfig;
    }
    if (method === 'GET' && p === '/me') return this.me;
    if (method === 'PATCH' && p === '/me') {
      const update = asRecord(body);
      const prefs = { ...this.me.preferences };
      if (Array.isArray(update.subjects)) {
        if (update.subjects.length === 0) {
          throw new HttpError(
            422,
            'validation_failed',
            'Keep at least one subject.',
          );
        }
        prefs.subjects = update.subjects as SubjectId[];
      }
      if (typeof update.time_zone === 'string') {
        prefs.time_zone = update.time_zone;
        prefs.time_zone_confirmed = true;
      }
      if (typeof update.lesson_length === 'string') {
        prefs.lesson_length =
          update.lesson_length as typeof prefs.lesson_length;
      }
      if (typeof update.morning_lesson === 'boolean') {
        prefs.morning_lesson = update.morning_lesson;
      }
      if (typeof update.morning_hour === 'number') {
        prefs.morning_hour = update.morning_hour;
      }
      this.me = { ...this.me, preferences: prefs };
      return this.me;
    }
    if (method === 'GET' && p === '/today') return this.getToday();
    if (method === 'POST' && p === '/today/lesson') {
      const slot = this.dailySlot();
      if (slot.job) return slot;
      this.checkAllowance();
      this.addJob({ kind: 'daily' });
      return this.dailySlot();
    }
    if (method === 'POST' && p === '/lessons/requests') {
      const request = asRecord(body);
      this.checkAllowance();
      if (request.kind === 'topic') {
        const topic = String(request.topic ?? '').trim();
        if (topic.length < 2 || topic.length > 300) {
          throw new HttpError(
            422,
            'validation_failed',
            'A topic needs 2 to 300 characters.',
          );
        }
        return this.addJob({ kind: 'topic', request_text: topic });
      }
      if (request.kind === 'subject') {
        return this.addJob({
          kind: 'subject',
          subject: request.subject as SubjectId,
        });
      }
      return this.addJob({ kind: 'surprise' });
    }
    if (method === 'GET' && p === '/lessons') {
      let items = this.sortedLessons();
      if (query.get('saved') === 'true') {
        items = items.filter((lesson) => lesson.state.saved);
      }
      const subject = query.get('subject');
      if (subject) items = items.filter((lesson) => lesson.subject === subject);
      const q = query.get('q')?.toLowerCase();
      if (q) {
        items = items.filter((lesson) =>
          [lesson.title, lesson.hook, ...lesson.tags].some((text) =>
            text.toLowerCase().includes(q),
          ),
        );
      }
      const start = Number(query.get('cursor') ?? 0);
      const limit = Number(query.get('limit') ?? 20);
      const page = items.slice(start, start + limit);
      return {
        items: page.map((lesson) => this.summary(lesson)),
        next_cursor:
          start + limit < items.length ? String(start + limit) : null,
      };
    }
    const lessonMatch = /^\/lessons\/([^/]+)(?:\/([a-z-]+))?$/.exec(p);
    if (lessonMatch) {
      const lesson = this.findLesson(decodeURIComponent(lessonMatch[1]));
      const action = lessonMatch[2];
      const update = asRecord(body);
      const state = lesson.state;
      if (method === 'GET' && !action) return this.withThread(lesson);
      if (method === 'POST' && action === 'follow-ups') {
        this.checkAllowance();
        const direction =
          typeof update.direction === 'number' ? update.direction : null;
        const question =
          typeof update.question === 'string' ? update.question.trim() : null;
        if ((direction === null) === (question === null)) {
          throw new HttpError(
            422,
            'validation_failed',
            'Choose a direction or ask a question.',
          );
        }
        return this.addJob({
          kind: 'follow_up',
          subject: lesson.subject,
          parent_lesson_id: lesson.id,
          request_text:
            question ?? lesson.go_deeper[direction ?? 0]?.title ?? null,
        });
      }
      if (method === 'PUT' && action === 'saved') {
        state.saved = update.saved === true;
        state.saved_at = state.saved ? now : null;
        return state;
      }
      if (method === 'PUT' && action === 'rating') {
        state.rating = update.rating as LessonState['rating'];
        return state;
      }
      if (method === 'PUT' && action === 'finished') {
        state.finished_at = update.finished === true ? now : null;
        return state;
      }
      if (method === 'PUT' && action === 'flag') {
        state.flagged = true;
        return state;
      }
      if (method === 'POST' && action === 'opened') {
        state.first_opened_at ??= now;
        return state;
      }
      if (method === 'POST' && action === 'reading') {
        const sessionId = String(update.session_id);
        const previous = this.readingReports.get(sessionId);
        const seconds = Math.max(
          Number(update.seconds),
          previous?.seconds ?? 0,
        );
        const scroll = Math.max(Number(update.scroll), previous?.scroll ?? 0);
        this.readingReports.set(sessionId, {
          lessonId: lesson.id,
          seconds,
          scroll,
        });
        state.furthest_scroll = Math.max(state.furthest_scroll, scroll);
        return state;
      }
    }
    const jobMatch = /^\/jobs\/([^/]+)(\/retry)?$/.exec(p);
    if (jobMatch) {
      const job = this.job(decodeURIComponent(jobMatch[1]));
      if (!job) throw new HttpError(404, 'not_found', 'No such job.');
      if (method === 'GET' && !jobMatch[2]) {
        this.maybeAdvance();
        return job;
      }
      if (method === 'POST' && jobMatch[2]) {
        if (job.status !== 'failed') {
          throw new HttpError(
            409,
            'conflict',
            'Only a failed job can be retried.',
          );
        }
        this.checkAllowance();
        job.status = 'queued';
        job.error_code = null;
        job.error_message = null;
        job.attempts = 0;
        job.can_retry = false;
        job.finished_at = null;
        this.usedToday += 1;
        return job;
      }
    }
    if (method === 'GET' && p === '/progress') return this.getProgress();
    if (method === 'POST' && p === '/activity') return undefined;
    if (method === 'GET' && p === '/export') {
      return {
        schema_version: 1,
        exported_at: now,
        preferences: this.me.preferences,
        lessons: this.sortedLessons().map((lesson) => this.withThread(lesson)),
        jobs: this.jobs,
        calls: [],
        events: [],
        reading_sessions: [],
      };
    }
    throw new HttpError(404, 'not_found', `No route for ${method} ${p}`);
  }
}

function isAccepted(path: string): boolean {
  return /\/(requests|follow-ups|retry|today\/lesson)$/.test(path);
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null
    ? (value as Record<string, unknown>)
    : {};
}

function errorResponse(
  status: number,
  code: ErrorCode,
  message: string,
): Response {
  return new Response(
    JSON.stringify({ error: { code, message, fields: [] } }),
    { status, headers: { 'Content-Type': 'application/json' } },
  );
}
