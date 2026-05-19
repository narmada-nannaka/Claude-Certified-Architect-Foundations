import { useState } from "react";

interface ButtonProps {
  label: string;
  onClick: () => void;
  variant?: "primary" | "secondary";
}

export function Button({ label, onClick, variant = "primary" }: ButtonProps) {
  const [isPressed, setIsPressed] = useState(false);

  const handleClick = (event: any) => {
    console.log("Button clicked", event);
    setIsPressed(true);
    onClick();
    setTimeout(() => setIsPressed(false), 200);
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