"use client";

import { useState, useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { evaluationsAPI, transcriptsAPI } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Play, CheckCircle2, XCircle, Loader2 } from "lucide-react";

interface EvaluationRunnerProps {
  experimentId: number;
  judges: any[];
  onComplete: () => void;
}

interface EvaluationProgress {
  current: number;
  total: number;
  status: string;
  error?: string;
}

export default function EvaluationRunner({
  experimentId,
  judges,
  onComplete,
}: EvaluationRunnerProps) {
  const [selectedJudge, setSelectedJudge] = useState<number | null>(null);
  const [selectedTranscripts, setSelectedTranscripts] = useState<number[]>([]);
  const [evaluationId, setEvaluationId] = useState<number | null>(null);
  const [progress, setProgress] = useState<EvaluationProgress | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const { data: transcripts } = useQuery({
    queryKey: ["transcripts"],
    queryFn: transcriptsAPI.list,
  });

  const runMutation = useMutation({
    mutationFn: evaluationsAPI.run,
    onSuccess: (data: any) => {
      setEvaluationId(data.id);
      setIsRunning(true);
    },
  });

  useEffect(() => {
    if (!evaluationId || !isRunning) return;

    const eventSource = new EventSource(
      evaluationsAPI.streamURL(evaluationId)
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setProgress(data);

      if (data.status === "completed") {
        setIsRunning(false);
        eventSource.close();
        setTimeout(() => {
          onComplete();
        }, 1000);
      } else if (data.status === "failed") {
        setIsRunning(false);
        eventSource.close();
      }
    };

    eventSource.onerror = () => {
      setIsRunning(false);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [evaluationId, isRunning, onComplete]);

  const handleStart = () => {
    if (selectedJudge) {
      runMutation.mutate({
        experiment_id: experimentId,
        judge_id: selectedJudge,
        transcript_ids: selectedTranscripts.length > 0 ? selectedTranscripts : undefined,
      });
    }
  };

  const handleTranscriptToggle = (transcriptId: number) => {
    setSelectedTranscripts((prev) =>
      prev.includes(transcriptId)
        ? prev.filter((id) => id !== transcriptId)
        : [...prev, transcriptId]
    );
  };

  const handleSelectAll = () => {
    if (transcripts) {
      setSelectedTranscripts(transcripts.map((t: any) => t.id));
    }
  };

  const handleDeselectAll = () => {
    setSelectedTranscripts([]);
  };

  const progressPercentage =
    progress && progress.total > 0
      ? (progress.current / progress.total) * 100
      : 0;

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>Select Judge</Label>
        <Select
          value={selectedJudge?.toString() || ""}
          onValueChange={(value) => setSelectedJudge(parseInt(value))}
          disabled={isRunning}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select a judge to evaluate with" />
          </SelectTrigger>
          <SelectContent>
            {judges.map((judge) => (
              <SelectItem key={judge.id} value={judge.id.toString()}>
                {judge.name} ({judge.characteristics?.length || 0}{" "}
                characteristics)
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>Select Transcripts</Label>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleSelectAll}
              disabled={isRunning}
            >
              Select All
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleDeselectAll}
              disabled={isRunning}
            >
              Clear
            </Button>
          </div>
        </div>
        <Card className="p-4">
          <ScrollArea className="h-[200px]">
            <div className="space-y-2">
              {transcripts?.map((transcript: any) => (
                <div
                  key={transcript.id}
                  className="flex items-center space-x-2"
                >
                  <Checkbox
                    id={`transcript-${transcript.id}`}
                    checked={selectedTranscripts.includes(transcript.id)}
                    onCheckedChange={() => handleTranscriptToggle(transcript.id)}
                    disabled={isRunning}
                  />
                  <label
                    htmlFor={`transcript-${transcript.id}`}
                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                  >
                    {transcript.name}
                  </label>
                </div>
              ))}
            </div>
          </ScrollArea>
          <p className="text-xs text-muted-foreground mt-2">
            {selectedTranscripts.length > 0
              ? `${selectedTranscripts.length} transcript(s) selected`
              : "All transcripts will be evaluated"}
          </p>
        </Card>
      </div>

      {!isRunning && !progress && (
        <Button
          onClick={handleStart}
          disabled={!selectedJudge || runMutation.isPending}
          className="w-full"
        >
          <Play className="h-4 w-4 mr-2" />
          {runMutation.isPending ? "Starting..." : "Start Evaluation"}
        </Button>
      )}

      {runMutation.isError && (
        <Card className="p-4 border-destructive">
          <div className="flex items-center gap-2 text-destructive">
            <XCircle className="h-4 w-4" />
            <span className="text-sm">
              Error: {(runMutation.error as Error).message}
            </span>
          </div>
        </Card>
      )}

      {isRunning && progress && (
        <Card className="p-4">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="font-medium">Evaluation in Progress</span>
              </div>
              <span className="text-sm text-muted-foreground">
                {progress.current} / {progress.total}
              </span>
            </div>

            <Progress value={progressPercentage} className="h-2" />

            <p className="text-sm text-muted-foreground">{progress.status}</p>
          </div>
        </Card>
      )}

      {!isRunning && progress?.status === "completed" && (
        <Card className="p-4 border-green-500">
          <div className="flex items-center gap-2 text-green-600">
            <CheckCircle2 className="h-4 w-4" />
            <span className="font-medium">Evaluation Completed!</span>
          </div>
        </Card>
      )}

      {!isRunning && progress?.status === "failed" && (
        <Card className="p-4 border-destructive">
          <div className="flex items-center gap-2 text-destructive">
            <XCircle className="h-4 w-4" />
            <span className="font-medium">
              Evaluation Failed: {progress.error}
            </span>
          </div>
        </Card>
      )}
    </div>
  );
}
