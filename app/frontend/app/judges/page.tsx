"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { judgesAPI, modelsAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Plus, Scale } from "lucide-react";
import JudgeList from "@/components/JudgeList";
import JudgeForm from "@/components/JudgeForm";
import JudgeDetail from "@/components/JudgeDetail";

export default function JudgesPage() {
  const queryClient = useQueryClient();
  const [selectedJudge, setSelectedJudge] = useState<number | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);

  const { data: judges, isLoading } = useQuery({
    queryKey: ["judges"],
    queryFn: judgesAPI.list,
  });

  const { data: modelsData } = useQuery({
    queryKey: ["models"],
    queryFn: modelsAPI.list,
  });

  const deleteMutation = useMutation({
    mutationFn: judgesAPI.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["judges"] });
      setSelectedJudge(null);
    },
  });

  const handleJudgeClick = (id: number) => {
    setSelectedJudge(id);
    setShowCreateForm(false);
  };

  const handleDelete = (id: number) => {
    if (confirm("Are you sure you want to delete this judge?")) {
      deleteMutation.mutate(id);
    }
  };

  const handleCreateSuccess = () => {
    setShowCreateForm(false);
    queryClient.invalidateQueries({ queryKey: ["judges"] });
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">LLM Judges</h1>
        <Button
          variant={showCreateForm ? "secondary" : "default"}
          onClick={() => {
            setShowCreateForm(!showCreateForm);
            setSelectedJudge(null);
          }}
        >
          <Plus className="mr-2 h-4 w-4" />
          {showCreateForm ? "Cancel" : "Create Judge"}
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Scale className="mr-2 h-5 w-5" />
                All Judges ({judges?.length || 0})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <JudgeList
                judges={judges || []}
                selectedId={selectedJudge}
                onSelect={handleJudgeClick}
                onDelete={handleDelete}
                isLoading={isLoading}
              />
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-2">
          {showCreateForm ? (
            <Card>
              <CardHeader>
                <CardTitle>Create New Judge</CardTitle>
              </CardHeader>
              <CardContent>
                <JudgeForm
                  availableModels={modelsData?.models || []}
                  onSuccess={handleCreateSuccess}
                />
              </CardContent>
            </Card>
          ) : selectedJudge ? (
            <JudgeDetail
              judgeId={selectedJudge}
              availableModels={modelsData?.models || []}
            />
          ) : (
            <Card className="h-full flex items-center justify-center">
              <CardContent className="text-center text-muted-foreground">
                <Scale className="mx-auto h-12 w-12 mb-4 opacity-50" />
                <p>Select a judge to view details or create a new one</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
