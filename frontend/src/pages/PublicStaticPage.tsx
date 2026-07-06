import React from 'react';
import PublicHeader from '../components/PublicHeader';

type PublicStaticPageProps = {
  title: string;
  src: string;
};

const PublicStaticPage: React.FC<PublicStaticPageProps> = ({ title, src }) => {
  return (
    <main className="ow-static-page">
      <PublicHeader theme="dark" />
      <iframe className="ow-static-frame" src={src} title={title} />
    </main>
  );
};

export default PublicStaticPage;
