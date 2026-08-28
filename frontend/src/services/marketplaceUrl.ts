const configuredMarketplaceUrl = process.env.REACT_APP_STUDIO_MARKETPLACE_URL;
const isLocalHost = ['127.0.0.1', 'localhost'].includes(window.location.hostname);

export const marketplaceUrl = (
  configuredMarketplaceUrl
  || (isLocalHost ? 'http://127.0.0.1:8015' : 'https://marketplace.orbweaver.spruked.com')
).replace(/\/$/, '');
