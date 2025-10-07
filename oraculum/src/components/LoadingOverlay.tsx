import React, { ReactNode } from "react";

interface LoadingOverlayProps {
  isLoading: boolean;
  children: any;
}

const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  isLoading,
  children,
}) => {
  if (!isLoading) return children;

  return (
    <div className="position-relative">
      {children}
      {/* Overlay */}
      <div className="position-absolute top-0 start-0 w-100 h-100 d-flex bg-white opacity-75 justify-content-center align-items-center">
        {/* Spinner from Bootstrap */}
        <div className="spinner-border" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    </div>
  );
};
export default LoadingOverlay;
