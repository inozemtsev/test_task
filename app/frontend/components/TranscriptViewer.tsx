"use client";

import { useQuery } from "@tanstack/react-query";
import { transcriptsAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { FileText, Calendar } from "lucide-react";

interface TranscriptViewerProps {
  transcriptId: number;
}

export default function TranscriptViewer({
  transcriptId,
}: TranscriptViewerProps) {
  const { data: transcript, isLoading } = useQuery({
    queryKey: ["transcript", transcriptId],
    queryFn: () => transcriptsAPI.get(transcriptId),
    enabled: !!transcriptId,
  });

  if (isLoading) {
    return (
      <Card className="h-full">
        <CardHeader className="animate-pulse">
          <div className="h-8 bg-muted rounded w-1/2" />
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-4 bg-muted rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!transcript) {
    return (
      <Card className="h-full flex items-center justify-center">
        <CardContent className="text-center text-muted-foreground">
          <FileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
          <p>Transcript not found</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              {transcript.name}
            </CardTitle>
            <div className="flex items-center gap-2 mt-2">
              <Badge variant="outline">{transcript.source}</Badge>
              <div className="flex items-center text-sm text-muted-foreground">
                <Calendar className="h-4 w-4 mr-1" />
                {new Date(transcript.created_at).toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[600px]">
          <div className="prose prose-sm max-w-none">
            <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
              {transcript.content}
            </pre>
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
