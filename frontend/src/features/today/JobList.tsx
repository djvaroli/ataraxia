/** Other lessons being prepared today, or that failed. */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { keys, useSubjectLabel } from '../../app/queries';
import { useApi } from '../../app/services';
import { InkLine } from '../../components/InkLine';
import ui from '../../components/ui.module.css';
import type { Job } from '../../lib/api';
import { formatTime } from '../../lib/format';
import {
  deferredUntil,
  describeJob,
  failureHint,
  failureReason,
} from '../../lib/jobs';
import styles from './today.module.css';

interface JobListProps {
  jobs: Job[];
  canRequest: boolean;
  timeZone: string | undefined;
  now: Date;
}

export function JobList({ jobs, canRequest, timeZone, now }: JobListProps) {
  if (jobs.length === 0) return null;
  return (
    <section className={styles.section} aria-labelledby="jobs-title">
      <h2 id="jobs-title" className={ui.sectionTitle}>
        In preparation
      </h2>
      <ul className={styles.jobs}>
        {jobs.map((job) => (
          <JobRow
            key={job.id}
            job={job}
            canRequest={canRequest}
            timeZone={timeZone}
            now={now}
          />
        ))}
      </ul>
    </section>
  );
}

function JobRow({
  job,
  canRequest,
  timeZone,
  now,
}: {
  job: Job;
  canRequest: boolean;
  timeZone: string | undefined;
  now: Date;
}) {
  const api = useApi();
  const client = useQueryClient();
  const subjectLabel = useSubjectLabel();
  const retry = useMutation({
    mutationFn: () => api.retryJob(job.id),
    onSettled: () => client.invalidateQueries({ queryKey: keys.today }),
  });
  const waitUntil = deferredUntil(job, now);
  const hint = job.status === 'failed' ? failureHint(job) : null;

  return (
    <li className={styles.job} data-subject={job.subject ?? undefined}>
      <p className={styles.jobTitle}>{describeJob(job, subjectLabel)}</p>
      {job.status === 'failed' ? (
        <>
          <p className={styles.jobStatus}>
            {failureReason(job)}
            {hint && <span className={styles.hint}>{hint}</span>}
          </p>
          {job.can_retry && (
            <button
              type="button"
              className={ui.quiet}
              disabled={retry.isPending || !canRequest}
              onClick={() => retry.mutate()}
            >
              {retry.isPending ? 'Retrying…' : 'Retry'}
            </button>
          )}
          {retry.error && (
            <p className={ui.error} role="alert">
              {retry.error.message}
            </p>
          )}
        </>
      ) : waitUntil ? (
        <p className={styles.jobStatus}>
          {`${failureReason(job)} Trying again at ${formatTime(waitUntil, timeZone)}.`}
        </p>
      ) : (
        <>
          <p className={styles.jobStatus}>
            {job.status === 'running' ? 'Being written…' : 'Waiting its turn…'}
          </p>
          <div className={styles.jobInk}>
            <InkLine />
          </div>
        </>
      )}
    </li>
  );
}
