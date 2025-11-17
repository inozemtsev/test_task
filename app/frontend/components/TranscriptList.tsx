"use client";

import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Trash2, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

interface Transcript {
  id: number;
  name: string;
  source: string;
  created_at: string;
}

interface TranscriptListProps {
  transcripts: Transcript[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  onDelete: (id: number) => void;
  isLoading?: boolean;
}

export default function TranscriptList({
  transcripts,
  selectedId,
  onSelect,
  onDelete,
  isLoading,
}: TranscriptListProps) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-16 rounded-lg bg-muted animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (transcripts.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <FileText className="mx-auto h-8 w-8 mb-2 opacity-50" />
        <p>No transcripts available</p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-[600px]">
      <div className="space-y-2 pr-4">
        {transcripts.map((transcript) => (
          <div
            key={transcript.id}
            className={cn(
              "flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-colors hover:bg-accent",
              selectedId === transcript.id && "bg-accent border-primary"
            )}
            onClick={() => onSelect(transcript.id)}
          >
            <div className="flex-1 min-w-0">
              <p className="font-medium truncate">{transcript.name}</p>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="outline" className="text-xs">
                  {transcript.source}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {new Date(transcript.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
            {transcript.source === "manual" && (
              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(transcript.id);
                }}
                className="ml-2 h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        ))}
      </div>
    </ScrollArea>
  );
}
