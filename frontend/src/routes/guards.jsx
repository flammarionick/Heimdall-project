import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";

export function RequireAdmin({ children }) {
  const [state, setState] = useState({ loading: true, ok: false });

  useEffect(() => {
    fetch("/auth/api/me", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((me) => setState({ loading: false, ok: !!me?.is_admin }))
      .catch(() => setState({ loading: false, ok: false }));
  }, []);

  if (state.loading) return null;
  return state.ok ? children : <Navigate to="/login" replace />;
}

export function RequireUser({ children }) {
  const [state, setState] = useState({ loading: true, ok: false });

  useEffect(() => {
    fetch("/auth/api/me", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((me) => setState({ loading: false, ok: !!me }))
      .catch(() => setState({ loading: false, ok: false }));
  }, []);

  if (state.loading) return null;
  return state.ok ? children : <Navigate to="/login" replace />;
}