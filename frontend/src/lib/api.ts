/**
 * Typed client for /api/v1, built on the generated OpenAPI types.
 *
 * `fetch` and the token source are injected so tests and the demo can run the
 * same client against an in-memory server.
 */
import type { components } from './api.generated';

type Schemas = components['schemas'];

export type ClientConfig = Schemas['ClientConfig'];
export type FirebaseWebConfig = Schemas['FirebaseWebConfig'];
export type Me = Schemas['Me'];
export type Preferences = Schemas['Preferences'];
export type PreferencesUpdate = Schemas['PreferencesUpdate'];
export type SubjectInfo = Schemas['SubjectInfo'];
export type SubjectId = SubjectInfo['id'];
export type LessonLength = Preferences['lesson_length'];
export type Today = Schemas['Today'];
export type DailySlot = Schemas['DailySlot'];
export type Allowance = Schemas['Allowance'];
export type WorkerStatus = Schemas['WorkerStatus'];
export type Job = Schemas['Job'];
export type JobErrorCode = NonNullable<Job['error_code']>;
export type Lesson = Schemas['Lesson'];
export type LessonSummary = Schemas['LessonSummary'];
export type LessonState = Schemas['LessonState'];
export type LessonPage = Schemas['LessonPage'];
export type Illustration = Schemas['Illustration'];
export type FurtherItem = Schemas['FurtherItem'];
export type Direction = Schemas['Direction'];
export type GlossaryEntry = Schemas['GlossaryEntry'];
export type ThreadEntry = Schemas['ThreadEntry'];
export type Rating = LessonState['rating'];
export type LessonRequest =
  | Schemas['SurpriseRequest']
  | Schemas['SubjectRequest']
  | Schemas['TopicRequest'];
export type FollowUpRequest = Schemas['FollowUpRequest'];
export type ReadingReport = Schemas['ReadingReport'];
export type Progress = Schemas['Progress'];
export type SubjectProgress = Schemas['SubjectProgress'];
export type DayActivity = Schemas['DayActivity'];
export type ExportDocument = Schemas['ExportDocument'];
export type ErrorBody = Schemas['ErrorBody'];
export type ErrorCode = ErrorBody['error']['code'];

export type FetchLike = (
  input: string,
  init?: RequestInit,
) => Promise<Response>;
export type TokenSource = () => Promise<string | null>;

const BASE = '/api/v1';

/** An HTTP failure with the server's error code when it sent one. Status 0 means no response. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: ErrorCode | null;

  constructor(status: number, code: ErrorCode | null, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

function isErrorBody(value: unknown): value is ErrorBody {
  if (typeof value !== 'object' || value === null || !('error' in value)) {
    return false;
  }
  const error = value.error;
  return (
    typeof error === 'object' &&
    error !== null &&
    'code' in error &&
    typeof error.code === 'string' &&
    'message' in error &&
    typeof error.message === 'string'
  );
}

function fallbackMessage(status: number): string {
  if (status === 401) return 'Your session has ended. Sign in again.';
  if (status === 403) return 'This account isn’t the owner.';
  if (status === 404) return 'That could not be found.';
  if (status === 429) return 'No more lessons can be requested right now.';
  if (status >= 500) return 'Ataraxia had a problem. Try again in a moment.';
  return 'The request was not accepted.';
}

async function toApiError(response: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // A proxy error page or an empty body; use the generic message.
  }
  if (isErrorBody(body)) {
    return new ApiError(response.status, body.error.code, body.error.message);
  }
  return new ApiError(response.status, null, fallbackMessage(response.status));
}

/** The public configuration needed before sign-in; never sends credentials. */
export async function getClientConfig(
  fetchFn: FetchLike,
  signal?: AbortSignal,
): Promise<ClientConfig> {
  let response: Response;
  try {
    response = await fetchFn(`${BASE}/client-config`, { signal });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new ApiError(0, null, 'Ataraxia could not be reached.');
  }
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as ClientConfig;
}

interface RequestOptions {
  body?: unknown;
  signal?: AbortSignal;
  keepalive?: boolean;
}

export function createApiClient(fetchFn: FetchLike, getToken: TokenSource) {
  async function send(
    method: string,
    path: string,
    options: RequestOptions = {},
  ): Promise<Response> {
    const headers: Record<string, string> = { Accept: 'application/json' };
    const token = await getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    if (options.body !== undefined) {
      headers['Content-Type'] = 'application/json';
    }
    let response: Response;
    try {
      response = await fetchFn(`${BASE}${path}`, {
        method,
        headers,
        body:
          options.body === undefined ? undefined : JSON.stringify(options.body),
        signal: options.signal,
        keepalive: options.keepalive,
      });
    } catch (error) {
      if (options.signal?.aborted) throw error;
      throw new ApiError(0, null, 'Ataraxia could not be reached.');
    }
    if (!response.ok) throw await toApiError(response);
    return response;
  }

  async function json<T>(
    method: string,
    path: string,
    options?: RequestOptions,
  ): Promise<T> {
    const response = await send(method, path, options);
    return (await response.json()) as T;
  }

  const lessonPath = (id: string) => `/lessons/${encodeURIComponent(id)}`;

  return {
    getMe: (signal?: AbortSignal) => json<Me>('GET', '/me', { signal }),
    updateMe: (update: PreferencesUpdate) =>
      json<Me>('PATCH', '/me', { body: update }),

    getToday: (signal?: AbortSignal) =>
      json<Today>('GET', '/today', { signal }),
    startDailyLesson: () => json<DailySlot>('POST', '/today/lesson'),
    requestLesson: (request: LessonRequest) =>
      json<Job>('POST', '/lessons/requests', { body: request }),

    listLessons: (filters: LessonFilters, signal?: AbortSignal) => {
      const params = new URLSearchParams();
      if (filters.saved) params.set('saved', 'true');
      if (filters.subject) params.set('subject', filters.subject);
      if (filters.q) params.set('q', filters.q);
      if (filters.cursor) params.set('cursor', filters.cursor);
      if (filters.limit) params.set('limit', String(filters.limit));
      const query = params.toString();
      return json<LessonPage>('GET', `/lessons${query ? `?${query}` : ''}`, {
        signal,
      });
    },
    getLesson: (id: string, signal?: AbortSignal) =>
      json<Lesson>('GET', lessonPath(id), { signal }),
    requestFollowUp: (id: string, request: FollowUpRequest) =>
      json<Job>('POST', `${lessonPath(id)}/follow-ups`, { body: request }),
    setSaved: (id: string, saved: boolean) =>
      json<LessonState>('PUT', `${lessonPath(id)}/saved`, { body: { saved } }),
    setRating: (id: string, rating: Rating) =>
      json<LessonState>('PUT', `${lessonPath(id)}/rating`, {
        body: { rating },
      }),
    setFinished: (id: string, finished: boolean) =>
      json<LessonState>('PUT', `${lessonPath(id)}/finished`, {
        body: { finished },
      }),
    flagLesson: (id: string, note: string) =>
      json<LessonState>('PUT', `${lessonPath(id)}/flag`, { body: { note } }),
    recordOpened: (id: string) =>
      json<LessonState>('POST', `${lessonPath(id)}/opened`),
    /** Sent with keepalive so a report made while the page hides still arrives. */
    recordReading: async (id: string, report: ReadingReport) => {
      await send('POST', `${lessonPath(id)}/reading`, {
        body: report,
        keepalive: true,
      });
    },

    getJob: (id: string, signal?: AbortSignal) =>
      json<Job>('GET', `/jobs/${encodeURIComponent(id)}`, { signal }),
    retryJob: (id: string) =>
      json<Job>('POST', `/jobs/${encodeURIComponent(id)}/retry`),

    getProgress: (signal?: AbortSignal) =>
      json<Progress>('GET', '/progress', { signal }),
    recordAppOpened: async () => {
      await send('POST', '/activity', { body: { type: 'app.opened' } });
    },
    /** The complete export as a Blob, ready to download. */
    exportData: async (): Promise<Blob> => {
      const response = await send('GET', '/export');
      return response.blob();
    },
  };
}

export interface LessonFilters {
  saved?: boolean;
  subject?: SubjectId;
  q?: string;
  cursor?: string | null;
  limit?: number;
}

export type ApiClient = ReturnType<typeof createApiClient>;
