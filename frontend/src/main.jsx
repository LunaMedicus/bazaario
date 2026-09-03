import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("Bazaario UI error", error, info);
  }

  render() {
    if (this.state.error) {
      return <div style={{ padding: "48px", fontFamily: "sans-serif" }}><h1>Bazaario could not load.</h1><p>{this.state.error.message}</p></div>;
    }
    return this.props.children;
  }
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary><App /></ErrorBoundary>
  </React.StrictMode>,
);
