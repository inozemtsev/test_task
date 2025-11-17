"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { transcriptsAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FileText } from "lucide-react";

interface Transcript {
  id: number;
  name: string;
  content: string;
}

interface TranscriptComparisonProps {
  transcripts: Transcript[];
}

export default function TranscriptComparison({
  transcripts,
}: TranscriptComparisonProps) {
  const [leftId, setLeftId] = useState<number | null>(null);
  const [rightId, setRightId] = useState<number | null>(null);

  const { data: leftTranscript } = useQuery({
    queryKey: ["transcript", leftId],
    queryFn: () => transcriptsAPI.get(leftId!),
    enabled: !!leftId,
  });

  const { data: rightTranscript } = useQuery({
    queryKey: ["transcript", rightId],
    queryFn: () => transcriptsAPI.get(rightId!),
    enabled: !!rightId,
  });

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Side-by-Side Comparison</CardTitle>
        <div className="grid grid-cols-2 gap-4 mt-4">
          <Select
            value={leftId?.toString() || ""}
            onValueChange={(value) => setLeftId(parseInt(value))}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select first transcript" />
            </SelectTrigger>
            <SelectContent>
              {transcripts.map((t) => (
                <SelectItem key={t.id} value={t.id.toString()}>
                  {t.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={rightId?.toString() || ""}
            onValueChange={(value) => setRightId(parseInt(value))}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select second transcript" />
            </SelectTrigger>
            <SelectContent>
              {transcripts.map((t) => (
                <SelectItem key={t.id} value={t.id.toString()}>
                  {t.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          <div className="border rounded-lg p-4">
            {leftTranscript ? (
              <ScrollArea className="h-[500px]">
                <div className="mb-2 font-medium text-sm">
                  {leftTranscript.name}
                </div>
                <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
                  {leftTranscript.content}
                </pre>
              </ScrollArea>
            ) : (
              <div className="h-[500px] flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <FileText className="mx-auto h-8 w-8 mb-2 opacity-50" />
                  <p className="text-sm">Select a transcript</p>
                </div>
              </div>
            )}
          </div>

          <div className="border rounded-lg p-4">
            {rightTranscript ? (
              <ScrollArea className="h-[500px]">
                <div className="mb-2 font-medium text-sm">
                  {rightTranscript.name}
                </div>
                <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
                  {rightTranscript.content}
                </pre>
              </ScrollArea>
            ) : (
              <div className="h-[500px] flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <FileText className="mx-auto h-8 w-8 mb-2 opacity-50" />
                  <p className="text-sm">Select a transcript</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
