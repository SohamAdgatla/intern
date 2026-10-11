import { useEffect, useState } from "react";
import { fetchCurrentUser, logout } from "./api/auth";
import AddHealthDataPage from "./pages/AddHealthDataPage";
import Dashboard from "./pages/Dashboard";
import ProfilePage from "./pages/ProfilePage";

export default function App() {
  const [page, setPage] = useState("dashboard");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);

  useEffect(() => {
    let ignore = false;

    fetchCurrentUser()
      .then((user) => {
        if (!ignore) {
          setCurrentUser(user);
          setIsAuthenticated(true);
        }
      })
      .catch(() => {
        if (!ignore) {
          setCurrentUser(null);
          setIsAuthenticated(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, []);

  const handleLogout = async () => {
    try {
      await logout();
    } catch {
      // ignore and clear the local app state anyway
    } finally {
      setCurrentUser(null);
      setIsAuthenticated(false);
      setPage("dashboard");
    }
  };

  const handleAuthenticated = (user) => {
    setCurrentUser(user || null);
    setIsAuthenticated(true);
    setPage("dashboard");
  };

  const handleProfileUpdated = (user) => {
    setCurrentUser(user || null);
  };

  if (!isAuthenticated) {
    return (
      <AddHealthDataPage
        isAuthenticated={isAuthenticated}
        onBack={() => setPage("dashboard")}
        onAuthenticated={handleAuthenticated}
        initialAuthMode="login"
        onSuccess={() => {
          /* dashboard refresh happens on next visit */
        }}
      />
    );
  }

  if (page === "add-data") {
    return (
      <AddHealthDataPage
        isAuthenticated={isAuthenticated}
        onBack={() => setPage("dashboard")}
        onAuthenticated={handleAuthenticated}
        onSuccess={() => {
          /* dashboard refresh happens on next visit */
        }}
      />
    );
  }

  if (page === "profile") {
    return (
      <ProfilePage
        userName={currentUser?.full_name || currentUser?.given_name || currentUser?.username || "Patient"}
        currentUser={currentUser}
        onBack={() => setPage("dashboard")}
        onProfileUpdated={handleProfileUpdated}
      />
    );
  }

  return (
    <Dashboard
      userName={currentUser?.full_name || currentUser?.given_name || currentUser?.username || "Patient"}
      onAddData={() => setPage("add-data")}
      onOpenProfile={() => setPage("profile")}
      onLogout={handleLogout}
    />
  );
}
