import { api, MarketplaceItem } from '../../services/api';

export const marketplaceApi = {
  listItems: (category?: string) => api.listMarketplaceItems(category),
  addToCart: async (item: MarketplaceItem) => {
    if (!item.sku || !item.purchasable) {
      return { ok: false, message: `${item.name} is cataloged but not purchasable yet.` };
    }

    await api.upsertCartItem({ sku: item.sku, quantity: 1 });
    return { ok: true, message: `${item.name} added to cart.` };
  },
};
