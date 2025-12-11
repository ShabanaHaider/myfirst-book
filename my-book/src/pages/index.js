import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import styles from './index.module.css';

function HomepageHeader() {
  const { siteConfig } = useDocusaurusContext();

  return (
    <header className={clsx(styles.heroBanner)}>
      <div className={styles.overlay}>
        <Heading as="h1" className={styles.title}>
          {siteConfig.title}
        </Heading>

        {siteConfig.tagline && (
          <p className={styles.subtitle}>{siteConfig.tagline}</p>
        )}

        <div className={styles.buttons}>
          <Link className={styles.readButton} to="/docs/intro">
            Start Reading →
          </Link>
        </div>
      </div>
    </header>
  );
}

export default function Home() {
  const { siteConfig } = useDocusaurusContext();

  return (
    <Layout
      title={siteConfig.title}
      description={siteConfig.tagline}>
      <HomepageHeader />
      {/* Removed HomepageFeatures for clean book cover */}
    </Layout>
  );
}
