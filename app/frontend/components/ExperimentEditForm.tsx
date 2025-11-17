"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { experimentsAPI } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import JSONSchemaEditor from "@/components/JSONSchemaEditor";
import AIAssistButton from "@/components/AIAssistButton";

interface ExperimentEditFormProps {
  experiment: any;
  availableModels: string[];
  onSuccess: () => void;
}

export default function ExperimentEditForm({
  experiment,
  availableModels,
  onSuccess,
}: ExperimentEditFormProps) {
  const [name, setName] = useState(experiment.name);
  const [prompt, setPrompt] = useState(experiment.prompt);
  const [schemaJson, setSchemaJson] = useState(experiment.schema_json);
  const [model, setModel] = useState(experiment.model);

  const updateMutation = useMutation({
    mutationFn: (data: any) => experimentsAPI.update(experiment.id, data),
    onSuccess,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate({
      name,
      prompt,
      schema_json: schemaJson,
      model,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="edit-name">Experiment Name</Label>
        <Input
          id="edit-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="edit-model">Model</Label>
        <Select value={model} onValueChange={setModel} required>
          <SelectTrigger id="edit-model">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {availableModels.map((m) => (
              <SelectItem key={m} value={m}>
                {m}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="edit-prompt">Extraction Prompt</Label>
          <AIAssistButton
            currentContent={prompt}
            fieldType="prompt"
            onApply={setPrompt}
            context="This is an extraction prompt for getting structured data from financial advisor transcripts."
          />
        </div>
        <Textarea
          id="edit-prompt"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          required
          rows={6}
        />
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>JSON Schema</Label>
          <AIAssistButton
            currentContent={schemaJson}
            fieldType="schema"
            onApply={setSchemaJson}
            context="This is a JSON schema for extracting structured data from financial advisor transcripts."
          />
        </div>
        <JSONSchemaEditor value={schemaJson} onChange={setSchemaJson} />
      </div>

      <div className="flex justify-end gap-2">
        <Button type="submit" disabled={updateMutation.isPending}>
          {updateMutation.isPending ? "Saving..." : "Save Changes"}
        </Button>
      </div>

      {updateMutation.isError && (
        <p className="text-sm text-destructive">
          Error: {(updateMutation.error as Error).message}
        </p>
      )}
    </form>
  );
}
