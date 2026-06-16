import { useCallback, useEffect, useMemo, useState } from 'react';
import { MarketplaceItem } from '../../services/api';
import { fallbackMarketplaceItems } from '../data/marketplaceData';
import { marketplaceApi } from '../services/marketplaceApi';

type UseMarketplaceState = {
  items: MarketplaceItem[];
  loading: boolean;
  error: string | null;
  message: string | null;
  selectedCategory: string;
  searchTerm: string;
};

export const useMarketplace = () => {
  const [state, setState] = useState<UseMarketplaceState>({
    items: [],
    loading: true,
    error: null,
    message: null,
    selectedCategory: 'all',
    searchTerm: '',
  });

  useEffect(() => {
    let isCancelled = false;

    const loadItems = async () => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const category = state.selectedCategory !== 'all' ? state.selectedCategory : undefined;
        const data = await marketplaceApi.listItems(category);
        if (!isCancelled) {
          setState((prev) => ({
            ...prev,
            items: data && data.length ? data : fallbackMarketplaceItems,
            loading: false,
          }));
        }
      } catch (error) {
        if (!isCancelled) {
          setState((prev) => ({
            ...prev,
            items: fallbackMarketplaceItems,
            loading: false,
            error: 'Live marketplace is unavailable. Showing local catalog snapshot.',
          }));
        }
      }
    };

    loadItems();
    return () => {
      isCancelled = true;
    };
  }, [state.selectedCategory]);

  const filteredItems = useMemo(() => {
    const term = state.searchTerm.trim().toLowerCase();
    if (!term) {
      return state.items;
    }
    return state.items.filter((item) => {
      return (
        item.name.toLowerCase().includes(term) ||
        item.description.toLowerCase().includes(term) ||
        item.market_index_code.toLowerCase().includes(term) ||
        item.features.some((feature) => feature.toLowerCase().includes(term))
      );
    });
  }, [state.items, state.searchTerm]);

  const categories = useMemo(() => {
    const set = new Set<string>(['all']);
    fallbackMarketplaceItems.forEach((item) => set.add(item.category));
    state.items.forEach((item) => set.add(item.category));
    return Array.from(set.values());
  }, [state.items]);

  const setCategory = useCallback((selectedCategory: string) => {
    setState((prev) => ({ ...prev, selectedCategory, message: null }));
  }, []);

  const setSearchTerm = useCallback((searchTerm: string) => {
    setState((prev) => ({ ...prev, searchTerm }));
  }, []);

  const addToCart = useCallback(async (item: MarketplaceItem) => {
    const result = await marketplaceApi.addToCart(item);
    setState((prev) => ({
      ...prev,
      message: result.message,
      error: result.ok ? null : prev.error,
    }));
  }, []);

  return {
    ...state,
    items: filteredItems,
    categories,
    setCategory,
    setSearchTerm,
    addToCart,
  };
};
