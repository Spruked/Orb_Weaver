import React, { useEffect } from 'react';
import { bootstrapOrb } from '../orb-client/bootstrap';
import type { OrbLoaderConfig } from '../orb-client/types';

export type OrbWeaverSiteAdapterProps = OrbLoaderConfig;

export const OrbWeaverSiteAdapter: React.FC<OrbWeaverSiteAdapterProps> = (config) => {
  useEffect(() => {
    const handle = bootstrapOrb(config);
    return () => handle.unmount();
  }, [config.siteId, config.runtime, config.ws, config.version, config.debug, config.factoryAssetUrl]);
  return null;
};

export default OrbWeaverSiteAdapter;
