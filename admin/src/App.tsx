import { Navigate, Outlet, Route, Routes, useNavigate } from "react-router-dom";
import { useEffect } from "react";
import { Layout } from "./components/Layout";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { PlayersPage } from "./pages/PlayersPage";
import { UserDetailPage } from "./pages/UserDetailPage";
import { MessagesPage } from "./pages/MessagesPage";
import { getToken } from "./api";

function RequireAuth() {
  const token = getToken();
  if (!token) return <Navigate to="/login" replace />;
  return (
    <Layout>
      <Outlet />
    </Layout>
  );
}

function LogoutWatcher() {
  const nav = useNavigate();
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === "asteroid_admin_jwt" && !e.newValue) nav("/login");
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [nav]);
  return null;
}

export default function App() {
  return (
    <>
      <LogoutWatcher />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<RequireAuth />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/players" element={<PlayersPage />} />
          <Route path="/players/:id" element={<UserDetailPage />} />
          <Route path="/messages" element={<MessagesPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
