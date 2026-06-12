import React, { useEffect, useState } from 'react';
import { CreditCard, ShoppingCart, Trash2 } from 'lucide-react';
import { api, CartPayload, CheckoutOrder, Product } from '../services/api';

const money = (cents: number, currency = 'usd') =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: currency.toUpperCase() }).format(cents / 100);

const Cart: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [cart, setCart] = useState<CartPayload>({ items: [], total_amount_cents: 0, currency: 'usd' });
  const [orders, setOrders] = useState<CheckoutOrder[]>([]);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isCheckingOut, setIsCheckingOut] = useState('');

  const load = async () => {
    setError('');
    try {
      const [productRows, cartPayload, orderRows] = await Promise.all([
        api.listProducts(),
        api.getCart(),
        api.listCheckoutOrders(),
      ]);
      setProducts(productRows);
      setCart(cartPayload);
      setOrders(orderRows);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Cart load failed');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const addProduct = async (sku: string) => {
    setCart(await api.upsertCartItem({ sku, quantity: 1 }));
  };

  const removeProduct = async (sku: string) => {
    setCart(await api.deleteCartItem(sku));
  };

  const checkout = async (provider: 'stripe' | 'paypal') => {
    setIsCheckingOut(provider);
    setError('');
    try {
      const order = await api.createCheckout(provider);
      setOrders([order, ...orders]);
      if (order.checkout_url) {
        window.location.href = order.checkout_url;
      } else if (order.error) {
        setError(order.error);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Checkout failed');
    } finally {
      setIsCheckingOut('');
    }
  };

  if (isLoading) {
    return <div className="text-gray-500">Loading cart...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Cart & Checkout</h1>
        <p className="text-gray-500 mt-1">Service products, persisted cart, and checkout order history</p>
      </div>

      {error && <div className="rounded border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          {products.map((product) => (
            <div key={product.sku} className="card flex items-center justify-between gap-4">
              <div>
                <h2 className="font-semibold text-gray-900">{product.name}</h2>
                <p className="text-sm text-gray-500 mt-1">{product.description}</p>
                <p className="text-sm font-semibold text-gray-900 mt-2">{money(product.unit_amount_cents, product.currency)}</p>
              </div>
              <button onClick={() => addProduct(product.sku)} className="btn-primary flex items-center gap-2">
                <ShoppingCart className="w-4 h-4" />
                Add
              </button>
            </div>
          ))}
        </div>

        <div className="card h-fit">
          <h2 className="font-semibold text-gray-900 mb-4">Current Cart</h2>
          {cart.items.length === 0 ? (
            <p className="text-sm text-gray-500">No items selected.</p>
          ) : (
            <div className="space-y-3">
              {cart.items.map((item) => (
                <div key={item.sku} className="flex items-start justify-between gap-3 border-b border-gray-100 pb-3">
                  <div>
                    <p className="font-medium text-gray-900">{item.name}</p>
                    <p className="text-sm text-gray-500">
                      Qty {item.quantity} · {money(item.line_total_cents, item.currency)}
                    </p>
                  </div>
                  <button onClick={() => removeProduct(item.sku)} className="p-2 hover:bg-gray-100 rounded-lg" title="Remove">
                    <Trash2 className="w-4 h-4 text-gray-500" />
                  </button>
                </div>
              ))}
              <div className="flex justify-between font-bold text-gray-900 pt-2">
                <span>Total</span>
                <span>{money(cart.total_amount_cents, cart.currency)}</span>
              </div>
              <button
                onClick={() => checkout('stripe')}
                disabled={Boolean(isCheckingOut)}
                className="w-full btn-primary flex items-center justify-center gap-2"
              >
                <CreditCard className="w-4 h-4" />
                {isCheckingOut === 'stripe' ? 'Starting...' : 'Stripe Checkout'}
              </button>
              <button
                onClick={() => checkout('paypal')}
                disabled={Boolean(isCheckingOut)}
                className="w-full btn-secondary"
              >
                {isCheckingOut === 'paypal' ? 'Starting...' : 'PayPal Checkout'}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4">Checkout Orders</h2>
        {orders.length === 0 ? (
          <p className="text-sm text-gray-500">No checkout orders yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="py-2">Order</th>
                  <th>Provider</th>
                  <th>Status</th>
                  <th>Total</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr key={order.id} className="border-b last:border-0">
                    <td className="py-2 font-medium">#{order.id}</td>
                    <td>{order.provider}</td>
                    <td>{order.status}</td>
                    <td>{money(order.amount_cents, order.currency)}</td>
                    <td>{order.created_at ? new Date(order.created_at).toLocaleString() : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default Cart;
