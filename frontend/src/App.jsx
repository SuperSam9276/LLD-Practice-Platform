import { useEffect, useState } from "react";
import ProblemsPage from "./pages/ProblemsPage.jsx";
import PracticePage from "./pages/PracticePage.jsx";
import FeedbackPage from "./pages/FeedbackPage.jsx";
import HistoryPage from "./pages/HistoryPage.jsx";

// Hash router, ~20 lines. react-router would add a dependency and a mental model
// for four static routes with one path parameter each. Deliberate YAGNI call.
//
// Routes:
//   #/                     problems list
//   #/practice/:problemId  requirements + submission form
//   #/feedback/:evalId     polled evaluation result
//   #/history              every attempt, newest first

function useHashRoute() {
  const [hash, setHash] = useState(window.location.hash || "#/");
  useEffect(() => {
    const onChange = () => setHash(window.location.hash || "#/");
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  return { section: parts[0] ?? "", param: parts[1] ?? null };
}

export const navigate = (path) => {
  window.location.hash = path;
};

export default function App() {
  const { section, param } = useHashRoute();

  let page;
  if (section === "practice" && param) page = <PracticePage problemId={param} />;
  else if (section === "feedback" && param) page = <FeedbackPage evaluationId={param} />;
  else if (section === "history") page = <HistoryPage />;
  else page = <ProblemsPage />;

  return (
    <div className="app">
      <header className="topbar">
        <a href="#/" className="brand">
          LLD Practice
        </a>
        <nav>
          <a href="#/" className={section === "" ? "active" : ""}>
            Problems
          </a>
          <a href="#/history" className={section === "history" ? "active" : ""}>
            History
          </a>
        </nav>
      </header>
      <main>{page}</main>
    </div>
  );
}
