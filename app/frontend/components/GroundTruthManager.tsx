"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { judgesAPI, transcriptsAPI } from "@/lib/api";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import JSONSchemaEditor from "@/components/JSONSchemaEditor";

interface GroundTruthManagerProps {
  judgeId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function GroundTruthManager({ judgeId, open, onOpenChange }: GroundTruthManagerProps) {
  const queryClient = useQueryClient();
  const [selectedTranscriptId, setSelectedTranscriptId] = useState<number | null>(null);
  const [editorValue, setEditorValue] = useState("[]");
  const [parseError, setParseError] = useState<string | null>(null);

  const { data: transcripts = [], isLoading: transcriptsLoading } = useQuery({
    queryKey: ["transcripts"],
    queryFn: () => transcriptsAPI.list(),
    enabled: open,
  });

  const { data: groundTruthDetail, isFetching: groundTruthLoading } = useQuery({
    queryKey: ["ground-truth-detail", judgeId, selectedTranscriptId],
    queryFn: () => judgesAPI.getGroundTruth(judgeId, selectedTranscriptId!),
    enabled: open && !!selectedTranscriptId,
  });

  const updateMutation = useMutation({
    mutationFn: (groundTruth: unknown) =>
      judgesAPI.updateGroundTruth(judgeId, selectedTranscriptId!, { ground_truth: groundTruth }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ground-truth-detail", judgeId, selectedTranscriptId] });
    },
  });

  useEffect(() => {
    if (!open) {
      setSelectedTranscriptId(null);
      setEditorValue("[]");
      setParseError(null);
    }
  }, [open]);

  useEffect(() => {
    if (groundTruthDetail) {
      setEditorValue(
        groundTruthDetail.ground_truth
          ? JSON.stringify(groundTruthDetail.ground_truth, null, 2)
          : "[]",
      );
      setParseError(null);
    }
  }, [groundTruthDetail]);

  const selectedTranscript = useMemo(
    () => transcripts.find((t: { id: number }) => t.id === selectedTranscriptId),
    [transcripts, selectedTranscriptId],
  );

  const handleSave = () => {
    if (!selectedTranscriptId) {
      return;
    }

    try {
      const parsed = JSON.parse(editorValue || "[]");
      if (!Array.isArray(parsed)) {
        setParseError("Ground truth must be a JSON array of fact objects.");
        return;
      }
      setParseError(null);
      updateMutation.mutate(parsed);
    } catch (error) {
      setParseError((error as Error).message);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl">
        <DialogHeader>
          <DialogTitle>Stored Ground Truth</DialogTitle>
          <DialogDescription>
            Select a transcript to review its content alongside the stored ground truth data.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-muted-foreground">
              Transcript
            </label>
            <Select
              value={selectedTranscriptId ? String(selectedTranscriptId) : undefined}
              onValueChange={(value) => setSelectedTranscriptId(Number(value))}
              disabled={transcriptsLoading || transcripts.length === 0}
            >
              <SelectTrigger>
                <SelectValue placeholder={transcriptsLoading ? "Loading transcripts..." : "Select transcript"} />
              </SelectTrigger>
              <SelectContent>
                {transcripts.map((transcript: { id: number; name: string }) => (
                  <SelectItem key={transcript.id} value={String(transcript.id)}>
                    {transcript.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {selectedTranscriptId && (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div className="flex flex-col rounded-lg border bg-muted/40">
                <div className="flex items-center justify-between border-b px-4 py-2">
                  <div>
                    <p className="font-semibold">Transcript</p>
                    {selectedTranscript && (
                      <p className="text-sm text-muted-foreground">{selectedTranscript.name}</p>
                    )}
                  </div>
                  {groundTruthDetail?.updated_at && (
                    <Badge variant="outline">
                      Updated {new Date(groundTruthDetail.updated_at).toLocaleString()}
                    </Badge>
                  )}
                </div>
                <ScrollArea className="max-h-[500px] p-4">
                  {selectedTranscript ? (
                    <pre className="whitespace-pre-wrap text-sm text-muted-foreground">
                      {selectedTranscript.content}
                    </pre>
                  ) : (
                    <p className="text-sm text-muted-foreground">Transcript not found.</p>
                  )}
                </ScrollArea>
              </div>

              <div className="flex flex-col rounded-lg border bg-muted/40">
                <div className="flex items-center justify-between border-b px-4 py-2">
                  <div>
                    <p className="font-semibold">Ground Truth JSON</p>
                    <p className="text-sm text-muted-foreground">
                      Edit and save to keep in sync with the transcript.
                    </p>
                  </div>
                </div>
                <div className="p-4">
                  <JSONSchemaEditor value={editorValue} onChange={setEditorValue} height="420px" />
                  {parseError && (
                    <div className="mt-2 rounded border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                      {parseError}
                    </div>
                  )}
                  <div className="mt-4 flex justify-end">
                    <Button
                      onClick={handleSave}
                      disabled={groundTruthLoading || updateMutation.isPending}
                    >
                      {updateMutation.isPending ? "Saving..." : "Save Ground Truth"}
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
