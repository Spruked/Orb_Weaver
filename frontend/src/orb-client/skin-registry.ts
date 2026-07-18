import type { OrbSkinSelection } from './types';

export interface OrbSkinRegistryEntry extends OrbSkinSelection {
  immutable: boolean;
  fallback: boolean;
  ownerEditable: boolean;
}

export const ORB_SKIN_REGISTRY: Readonly<Record<string, Readonly<OrbSkinRegistryEntry>>> = Object.freeze({
  orb_factory_default_v1: Object.freeze({
    skinId: 'orb_factory_default_v1',
    displayName: 'O.R.B.S. Factory Default',
    bodyAssetUrl: '/orb-skins/tuxorb.png',
    customizationState: 'FACTORY_DEFAULT',
    immutable: true,
    fallback: true,
    ownerEditable: false,
  }),
});

export const DEFAULT_ORB_SKIN = ORB_SKIN_REGISTRY.orb_factory_default_v1;
