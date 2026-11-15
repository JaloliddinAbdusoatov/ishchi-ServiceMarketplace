import * as React from "react";
import * as AvatarPrimitive from "@radix-ui/react-avatar";
import { cn, getInitials, resolveMediaUrl } from "@/lib/utils";

interface UserAvatarProps {
  src?: string | null;
  name?: string | null;
  className?: string;
}

export const UserAvatar: React.FC<UserAvatarProps> = ({ src, name, className }) => {
  const url = resolveMediaUrl(src);
  return (
    <AvatarPrimitive.Root
      className={cn(
        "relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full bg-primary/10 text-primary border border-border",
        className
      )}
    >
      {url && (
        <AvatarPrimitive.Image
          src={url}
          alt={name || "Avatar"}
          className="aspect-square h-full w-full object-cover"
        />
      )}
      <AvatarPrimitive.Fallback className="flex h-full w-full items-center justify-center text-xs font-semibold">
        {getInitials(name)}
      </AvatarPrimitive.Fallback>
    </AvatarPrimitive.Root>
  );
};
