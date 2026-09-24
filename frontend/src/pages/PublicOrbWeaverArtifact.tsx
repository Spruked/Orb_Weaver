import React from 'react';

/**
 * The supplied Orb-Weaver export is a compiled React artifact. Keep it as a
 * deployable public document while the editable sections are being migrated
 * into native page components.
 */
const PublicOrbWeaverArtifact: React.FC = () => (
  <main className="min-h-screen bg-[#0E151E]">
    <iframe
      title="Orb Weaver design preview"
      src="/orb-weaver.html"
      className="block h-screen min-h-[720px] w-full border-0"
    />
  </main>
);

export default PublicOrbWeaverArtifact;
