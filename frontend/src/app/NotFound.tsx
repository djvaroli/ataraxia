import { Link } from 'react-router';
import ui from '../components/ui.module.css';
import { PageHeader } from '../components/PageHeader';

export function NotFound() {
  return (
    <>
      <PageHeader title="Nothing here" />
      <p>
        <Link className={ui.quiet} to="/">
          Back to Today
        </Link>
      </p>
    </>
  );
}
