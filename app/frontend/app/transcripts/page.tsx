"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { transcriptsAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Plus, FileText, Eye } from "lucide-react";
import TranscriptList from "@/components/TranscriptList";
import TranscriptViewer from "@/components/TranscriptViewer";
import TranscriptComparison from "@/components/TranscriptComparison";
import AddTranscriptForm from "@/components/AddTranscriptForm";

export default function TranscriptsPage() {
  const queryClient = useQueryClient();
  const [selectedTranscript, setSelectedTranscript] = useState<number | null>(
    null
  );
  const [comparisonMode, setComparisonMode] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);

  const { data: transcripts, isLoading } = useQuery({
    queryKey: ["transcripts"],
    queryFn: transcriptsAPI.list,
  });

  const deleteMutation = useMutation({
    mutationFn: transcriptsAPI.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transcripts"] });
      setSelectedTranscript(null);
    },
  });

  const handleTranscriptClick = (id: number) => {
    setSelectedTranscript(id);
    setComparisonMode(false);
  };

  const handleDelete = (id: number) => {
    if (confirm("Are you sure you want to delete this transcript?")) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Transcripts</h1>
        <div className="flex gap-2">
          <Button
            variant={comparisonMode ? "default" : "outline"}
            onClick={() => {
              setComparisonMode(!comparisonMode);
              if (!comparisonMode) setSelectedTranscript(null);
            }}
          >
            <Eye className="mr-2 h-4 w-4" />
            Compare
          </Button>
          <Button
            variant={showAddForm ? "secondary" : "default"}
            onClick={() => setShowAddForm(!showAddForm)}
          >
            <Plus className="mr-2 h-4 w-4" />
            {showAddForm ? "Cancel" : "Add"}
          </Button>
        </div>
      </div>

      {showAddForm && (
        <Card>
          <CardHeader>
            <CardTitle>Add New Transcript</CardTitle>
          </CardHeader>
          <CardContent>
            <AddTranscriptForm
              onSuccess={() => {
                setShowAddForm(false);
                queryClient.invalidateQueries({ queryKey: ["transcripts"] });
              }}
            />
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <FileText className="mr-2 h-5 w-5" />
                All Transcripts ({transcripts?.length || 0})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <TranscriptList
                transcripts={transcripts || []}
                selectedId={selectedTranscript}
                onSelect={handleTranscriptClick}
                onDelete={handleDelete}
                isLoading={isLoading}
              />
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-2">
          {comparisonMode ? (
            <TranscriptComparison transcripts={transcripts || []} />
          ) : selectedTranscript ? (
            <TranscriptViewer transcriptId={selectedTranscript} />
          ) : (
            <Card className="h-full flex items-center justify-center">
              <CardContent className="text-center text-muted-foreground">
                <FileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
                <p>Select a transcript to view or enable comparison mode</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
