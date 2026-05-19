import { useState, useEffect, useRef } from "react";

interface ButtonProps {
  label: string;
  onClick: () => void;
  variant?: "primary" | "secondary";
}

export function Button({ label, onClick, variant = "primary" }: ButtonProps) {
  const [isPressed, setIsPressed] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timeoutRef.current !== null) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setIsPressed(true);
    onClick();
    timeoutRef.current = setTimeout(() => setIsPressed(false), 200);
  };

  return (
    <button
      className={`btn btn-${variant} ${isPressed ? "pressed" : ""}`}
      onClick={handleClick}
    >
      {label}
    </button>
  );
}