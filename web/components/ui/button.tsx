import type { ComponentProps } from "react";
import { cva, type VariantProps } from "class-variance-authority";

const buttonVariants = cva("button", {
  variants: { variant: { primary: "button-primary", outline: "button-outline" } },
  defaultVariants: { variant: "outline" },
});

type ButtonProps = ComponentProps<"button"> & VariantProps<typeof buttonVariants>;

export function Button({ variant, className, type = "button", ...props }: ButtonProps) {
  return <button data-slot="button" type={type} className={buttonVariants({variant, className})} {...props}/>;
}
