import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  errorMessage: string;
}

export class AppErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, errorMessage: "" };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, errorMessage: error.message };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("AppErrorBoundary caught error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center p-6 text-center">
          <div className="mb-4 rounded-full bg-destructive/10 p-4 text-destructive">
            <AlertTriangle className="h-8 w-8" />
          </div>
          <h1 className="text-xl font-bold">Something went wrong</h1>
          <p className="mt-2 max-w-md text-sm text-muted-foreground">
            {this.state.errorMessage || "Unexpected application error."}
          </p>
          <Button
            className="mt-6"
            onClick={() => {
              this.setState({ hasError: false, errorMessage: "" });
              window.location.assign("/");
            }}
          >
            Reload ISHCHI
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
