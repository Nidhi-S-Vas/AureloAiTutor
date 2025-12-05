

import { BrowserRouter, Routes, Route } from "react-router-dom";
import Upload from "./pages/Upload";
import Dashboard from "./pages/Dashboard";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Upload />} />
        <Route path="/dashboard/:id" element={<Dashboard />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
