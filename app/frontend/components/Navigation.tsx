"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { FileText, Scale, FlaskConical } from "lucide-react";

const tabs = [
  { name: "Transcripts", href: "/transcripts", icon: FileText },
  { name: "Judges", href: "/judges", icon: Scale },
  { name: "Experiments", href: "/experiments", icon: FlaskConical },
];

export default function Navigation() {
  const pathname = usePathname();

  return (
    <nav className="border-b">
      <div className="container mx-auto">
        <div className="flex h-16 items-center space-x-4">
          <div className="flex items-center space-x-2 font-semibold">
            <FileText className="h-6 w-6" />
            <span>Transcript Analysis</span>
          </div>
          <div className="flex-1 flex space-x-1 ml-8">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = pathname.startsWith(tab.href);
              return (
                <Link
                  key={tab.href}
                  href={tab.href}
                  className={cn(
                    "flex items-center space-x-2 px-4 py-2 rounded-md text-sm font-medium transition-colors",
                    isActive
                      ? "bg-secondary text-secondary-foreground"
                      : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  <span>{tab.name}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
}
