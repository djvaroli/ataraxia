import type { SubjectId } from '../lib/api';
import { useSubjectLabel } from '../app/queries';
import ui from './ui.module.css';

interface SubjectLabelProps {
  subject: SubjectId;
  className?: string;
}

/** The subject's name in tracked capitals, in its pigment. */
export function SubjectLabel({ subject, className }: SubjectLabelProps) {
  const label = useSubjectLabel();
  return (
    <span
      data-subject={subject}
      className={className ? `${ui.subject} ${className}` : ui.subject}
    >
      {label(subject)}
    </span>
  );
}
