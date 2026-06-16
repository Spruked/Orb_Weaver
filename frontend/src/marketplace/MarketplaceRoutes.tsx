import React from 'react';
import { Route, Routes } from 'react-router-dom';
import MarketplaceCategory from './pages/MarketplaceCategory';
import MarketplaceCollections from './pages/MarketplaceCollections';
import MarketplaceHome from './pages/MarketplaceHome';
import MarketplaceProduct from './pages/MarketplaceProduct';
import MarketplaceSearch from './pages/MarketplaceSearch';

const MarketplaceRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<MarketplaceHome />} />
      <Route path="/marketplace" element={<MarketplaceHome />} />
      <Route path="/marketplace/category/:id" element={<MarketplaceCategory />} />
      <Route path="/marketplace/product/:id" element={<MarketplaceProduct />} />
      <Route path="/marketplace/products/:slug" element={<MarketplaceProduct />} />
      <Route path="/marketplace/collection/:id" element={<MarketplaceCollections />} />
      <Route path="/marketplace/collections" element={<MarketplaceCollections />} />
      <Route path="/marketplace/search" element={<MarketplaceSearch />} />
    </Routes>
  );
};

export default MarketplaceRoutes;
