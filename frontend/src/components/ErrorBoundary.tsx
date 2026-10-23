import React from "react";

interface State {
  error: Error | null;
}

export default class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  State
> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error("UI error", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="page">
          <h1>Something went wrong</h1>
          <pre className="error-box">{this.state.error.message}</pre>
          <button className="btn primary" onClick={() => window.location.reload()}>
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
