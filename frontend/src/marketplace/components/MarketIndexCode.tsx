import React from 'react';

type MarketIndexCodeProps = {
  value: string;
};

const MarketIndexCode: React.FC<MarketIndexCodeProps> = ({ value }) => {
  return <small className="ow-market-index">{value}</small>;
};

export default MarketIndexCode;
