import React from "react";

import { ui } from "../ui/ui.js";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error) {
    // Keep console noise minimal but useful.
    console.error("UI crashed:", error);
  }

  handleRetry = () => {
    this.setState({ hasError: false });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: "12px 24px" }} role="alert">
          <div style={ui.card}>
            <div style={{ fontWeight: 800, marginBottom: 6 }}>
              A apărut o eroare.
            </div>
            <div style={{ opacity: 0.9, marginBottom: 10 }}>
              Te rugăm să reîncerci.
            </div>
            <button onClick={this.handleRetry} style={ui.button}>
              Reîncearcă
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
