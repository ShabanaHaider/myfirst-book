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
        {/* Main title of the book */}
        <Heading as="h1" className={styles.title}>
          PHYSICAL AI & HUMANOID ROBOTICS TEXT BOOK
        </Heading>

        {/* Subheading about the book */}
        <p className={styles.subtitle}>
          A short description or "A complete and practical learning system where you master the future:humanoid robotics, ROS 2,large action models, simulation,VLA systems,hardware,and advanced AI for next-generation intelligent machines.".
        </p>

        {/* Start Reading button */}
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
  return (
    <Layout
      title="PHYSICAL AI & HUMANOID ROBOTICS TEXT BOOK"
      description="A complete and practical learning system where you master the future:humanoid robotics, ROS 2,large action models, simulation,VLA systems,hardware,and advanced AI for next-generation intelligent machines.">
      <HomepageHeader />
      {/* Clean homepage — no extra features */}
    </Layout>
  );
}
