"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { experimentsAPI, judgesAPI, modelsAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Plus, FlaskConical } from "lucide-react";
import ExperimentForm from "@/components/ExperimentForm";
import ExperimentDetail from "@/components/ExperimentDetail";

interface Experiment {
  id: number;
  name: string;
  prompt: string;
  schema_json: string;
  model: string;
  enable_two_pass?: boolean;
}

export default function ExperimentsPage() {
  const queryClient = useQueryClient();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [selectedExperiment, setSelectedExperiment] = useState<number | null>(
    null
  );

  const { data: experiments, isLoading } = useQuery({
    queryKey: ["experiments"],
    queryFn: experimentsAPI.list,
  });

  const { data: judges } = useQuery({
    queryKey: ["judges"],
    queryFn: judgesAPI.list,
  });

  const { data: modelsData } = useQuery({
    queryKey: ["models"],
    queryFn: modelsAPI.list,
  });

  const handleCreateSuccess = () => {
    setShowCreateForm(false);
    queryClient.invalidateQueries({ queryKey: ["experiments"] });
  };

  // Set first experiment as selected by default
  const activeExperiment =
    selectedExperiment ||
    (experiments && experiments.length > 0 ? experiments[0].id : null);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Experiments</h1>
        <Button
          variant={showCreateForm ? "secondary" : "default"}
          onClick={() => setShowCreateForm(!showCreateForm)}
        >
          <Plus className="mr-2 h-4 w-4" />
          {showCreateForm ? "Cancel" : "New Experiment"}
        </Button>
      </div>

      {showCreateForm && (
        <Card>
          <CardHeader>
            <CardTitle>Create New Experiment</CardTitle>
          </CardHeader>
          <CardContent>
            <ExperimentForm
              availableModels={modelsData?.models || []}
              onSuccess={handleCreateSuccess}
            />
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <Card>
          <CardContent className="p-6">
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="h-20 bg-muted rounded animate-pulse"
                />
              ))}
            </div>
          </CardContent>
        </Card>
      ) : experiments && experiments.length > 0 ? (
        <Tabs
          value={activeExperiment?.toString() || ""}
          onValueChange={(value) => setSelectedExperiment(parseInt(value))}
        >
          <TabsList className="w-full justify-start overflow-x-auto flex-wrap h-auto">
            {experiments.map((exp: Experiment) => (
              <TabsTrigger
                key={exp.id}
                value={exp.id.toString()}
                className="flex items-center gap-2"
              >
                <FlaskConical className="h-4 w-4" />
                {exp.name}
              </TabsTrigger>
            ))}
          </TabsList>

          {experiments.map((exp: Experiment) => (
            <TabsContent key={exp.id} value={exp.id.toString()}>
              <ExperimentDetail
                experiment={exp}
                judges={judges || []}
                availableModels={modelsData?.models || []}
              />
            </TabsContent>
          ))}
        </Tabs>
      ) : (
        <Card className="flex items-center justify-center h-96">
          <CardContent className="text-center text-muted-foreground">
            <FlaskConical className="mx-auto h-12 w-12 mb-4 opacity-50" />
            <p>No experiments yet</p>
            <p className="text-sm mt-1">Create an experiment to get started</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
