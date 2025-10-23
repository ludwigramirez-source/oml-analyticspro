import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import AnalyticsDashboard from "./components/analytics/AnalyticsDashboard";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AnalyticsDashboard />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
