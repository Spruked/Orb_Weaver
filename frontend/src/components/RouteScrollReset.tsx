import { useEffect } from "react";
import { useLocation } from "react-router-dom";

const RouteScrollReset = () => {
  const { pathname, search } = useLocation();

  useEffect(() => {
    window.history.scrollRestoration = "manual";

    const reset = () => window.scrollTo(0, 0);

    reset();
    const frame = window.requestAnimationFrame(reset);
    const timer = window.setTimeout(reset, 80);

    return () => {
      window.cancelAnimationFrame(frame);
      window.clearTimeout(timer);
    };
  }, [pathname, search]);

  return null;
};

export default RouteScrollReset;
