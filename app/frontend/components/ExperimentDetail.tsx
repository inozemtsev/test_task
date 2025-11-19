"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Edit, Play } from "lucide-react";
import ExperimentEditForm from "@/components/ExperimentEditForm";
import EvaluationRunner from "@/components/EvaluationRunner";
import type { Experiment, Judge } from "@/types";

interface ExperimentDetailProps {
  experiment: Experiment;
  judges: Judge[];
  availableModels: string[];
}

export default function ExperimentDetail({
  experiment,
  judges,
  availableModels,
}: ExperimentDetailProps) {
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [showEvaluation, setShowEvaluation] = useState(false);

  const handleEditSuccess = () => {
    setIsEditing(false);
    queryClient.invalidateQueries({ queryKey: ["experiments"] });
  };

  const handleEvaluationComplete = () => {
    setShowEvaluation(false);
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <CardTitle>{experiment.name}</CardTitle>
              <div className="flex items-center gap-2 mt-2">
                <Badge variant="secondary">{experiment.model}</Badge>
                {experiment.enable_two_pass && (
                  <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/20 dark:text-blue-400 dark:border-blue-800">
                    Two-Pass Extraction
                  </Badge>
                )}
                {experiment.created_at && (
                  <span className="text-sm text-muted-foreground">
                    Created {new Date(experiment.created_at).toLocaleDateString()}
                  </span>
                )}
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsEditing(!isEditing)}
              >
                <Edit className="h-4 w-4 mr-1" />
                {isEditing ? "Cancel" : "Edit"}
              </Button>
              <Button
                size="sm"
                onClick={() => setShowEvaluation(!showEvaluation)}
                disabled={judges.length === 0}
              >
                <Play className="h-4 w-4 mr-1" />
                {showEvaluation ? "Cancel" : "Run Evaluation"}
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {isEditing ? (
        <Card>
          <CardHeader>
            <CardTitle>Edit Experiment</CardTitle>
          </CardHeader>
          <CardContent>
            <ExperimentEditForm
              experiment={experiment}
              availableModels={availableModels}
              onSuccess={handleEditSuccess}
            />
          </CardContent>
        </Card>
      ) : showEvaluation ? (
        <Card>
          <CardHeader>
            <CardTitle>Run Evaluation</CardTitle>
          </CardHeader>
          <CardContent>
            <EvaluationRunner
              experimentId={experiment.id}
              judges={judges}
              onComplete={handleEvaluationComplete}
            />
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h3 className="text-sm font-medium mb-2">Extraction Prompt</h3>
              <div className="bg-muted p-4 rounded-lg">
                <pre className="whitespace-pre-wrap text-sm">
                  {experiment.prompt}
                </pre>
              </div>
            </div>

            <div>
              <h3 className="text-sm font-medium mb-2">JSON Schema</h3>
              <div className="bg-muted p-4 rounded-lg overflow-auto">
                <pre className="whitespace-pre text-sm font-mono">
                  {JSON.stringify(
                    JSON.parse(experiment.schema_json),
                    null,
                    2
                  )}
                </pre>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
