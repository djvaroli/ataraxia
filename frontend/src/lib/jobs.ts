/** How lesson preparation jobs are described to the reader. */
import type { Allowance, Job, JobErrorCode, SubjectId, Today } from './api';
import { plural } from './format';

export function isActive(job: Pick<Job, 'status'>): boolean {
  return job.status === 'queued' || job.status === 'running';
}

/** True while Today has anything that will change without the reader acting. */
export function hasActiveWork(today: Today | undefined): boolean {
  if (!today) return false;
  const daily = today.daily.status;
  return (
    daily === 'queued' ||
    daily === 'running' ||
    today.jobs.some((job) => isActive(job))
  );
}

const FAILURE_TEXT: Record<JobErrorCode, string> = {
  claude_auth: 'Claude isn’t signed in on the server.',
  claude_usage_limit: 'Claude’s usage limit was reached.',
  claude_timeout: 'Claude took too long to answer.',
  invalid_output: 'The lesson came back incomplete.',
  claude_error: 'Claude reported a problem while writing.',
  daily_limit: 'Today’s lesson limit was reached.',
  interrupted: 'Preparation was interrupted.',
};

/** The plain-language reason a job failed, preferring the server's wording. */
export function failureReason(job: Job): string {
  if (job.error_message) return job.error_message;
  if (job.error_code) return FAILURE_TEXT[job.error_code];
  return 'Something went wrong while preparing it.';
}

/** What the owner can do about a failure, when there is something specific. */
export function failureHint(job: Job): string | null {
  if (job.error_code === 'claude_auth') {
    return 'Sign Claude in on the server (docker compose exec -it worker claude auth login), then retry.';
  }
  if (job.error_code === 'daily_limit') return 'More lessons tomorrow.';
  return null;
}

/** A queued job that is waiting until a later time, e.g. after a usage limit. */
export function deferredUntil(job: Job, now: Date): string | null {
  if (job.status !== 'queued' || !job.next_attempt_at) return null;
  return new Date(job.next_attempt_at).getTime() > now.getTime()
    ? job.next_attempt_at
    : null;
}

export function describeJob(
  job: Job,
  subjectLabel: (id: SubjectId) => string,
): string {
  switch (job.kind) {
    case 'daily':
      return 'Today’s lesson';
    case 'surprise':
      return job.subject ? subjectLabel(job.subject) : 'A surprise';
    case 'subject':
      return job.subject ? subjectLabel(job.subject) : 'A chosen subject';
    case 'topic':
      return job.request_text ? `“${job.request_text}”` : 'Your topic';
    case 'follow_up':
      return job.request_text
        ? `Going deeper: ${job.request_text}`
        : 'A follow-up';
  }
}

/** Why no new lesson can be requested now, or null when one can. */
export function requestBlock(allowance: Allowance): string | null {
  if (allowance.remaining <= 0) {
    return 'Today’s lessons are used up. More tomorrow.';
  }
  if (allowance.waiting >= allowance.waiting_limit) {
    return `${plural(allowance.waiting, 'lesson')} are already being prepared. Ask again when one is ready.`;
  }
  return null;
}
