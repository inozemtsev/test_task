"use client";

import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Trash2, Scale } from "lucide-react";
import { cn } from "@/lib/utils";

interface Judge {
  id: number;
  name: string;
  model: string;
  created_at: string;
}

interface JudgeListProps {
  judges: Judge[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  onDelete: (id: number) => void;
  isLoading?: boolean;
}

export default function JudgeList({
  judges,
  selectedId,
  onSelect,
  onDelete,
  isLoading,
}: JudgeListProps) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-20 rounded-lg bg-muted animate-pulse" />
        ))}
      </div>
    );
  }

  if (judges.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Scale className="mx-auto h-8 w-8 mb-2 opacity-50" />
        <p>No judges configured</p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-[600px]">
      <div className="space-y-2 pr-4">
        {judges.map((judge) => (
          <div
            key={judge.id}
            className={cn(
              "flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-colors hover:bg-accent",
              selectedId === judge.id && "bg-accent border-primary"
            )}
            onClick={() => onSelect(judge.id)}
          >
            <div className="flex-1 min-w-0">
              <p className="font-medium truncate">{judge.name}</p>
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                <Badge variant="secondary" className="text-xs">
                  {judge.model}
                </Badge>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(judge.id);
              }}
              className="ml-2 h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        ))}
      </div>
    </ScrollArea>
  );
}
