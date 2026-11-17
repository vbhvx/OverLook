// frontend/src/components/ErrorBoundary.tsx
import React from 'react';

interface Props {
  children: React.ReactNode;
}

interface State {
  error: Error | null;
}

/** Catches render errors so one broken panel shows a recoverable message instead of a blank page. */
export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('Render error:', error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div role="alert" className="h-screen w-screen flex items-center justify-center bg-background p-6">
        <div className="max-w-md bg-panel border border-panel-border rounded-xl p-6 space-y-3">
          <h1 className="text-base font-semibold text-white">The workspace stopped rendering</h1>
          <p className="text-sm text-slate-300">
            A display error occurred. Your data is unaffected; reloading usually recovers.
          </p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-sm text-white"
          >
            Reload the workspace
          </button>
        </div>
      </div>
    );
  }
}
