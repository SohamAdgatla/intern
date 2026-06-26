import { useState } from "react";
import AddHealthDataPage from "./pages/AddHealthDataPage";
import Dashboard from "./pages/Dashboard";

export default function App() {
  const [page, setPage] = useState("dashboard");

  if (page === "add-data") {
    return (
      <AddHealthDataPage
        onBack={() => setPage("dashboard")}
        onSuccess={() => {
          /* dashboard refresh happens on next visit */
        }}
      />
    );
  }

  return <Dashboard onAddData={() => setPage("add-data")} />;
}
