import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import DashboardMejorado from "./components/analytics/DashboardMejorado";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<DashboardMejorado />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
