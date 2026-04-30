"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useCurrentUser } from "@/services/user-context";

export default function RootPage() {
  const router = useRouter();
  const [user, , loading] = useCurrentUser();

  useEffect(() => {
    if (!loading) {
      if (user) {
        router.push("/dashboard");
      } else {
        router.push("/login");
      }
    }
  }, [user, loading, router]);

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="animate-pulse text-slate-500 font-mono tracking-widest uppercase text-sm">
        Ładowanie systemu...
      </div>
    </div>
  );
}
