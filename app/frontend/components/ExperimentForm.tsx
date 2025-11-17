"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { experimentsAPI } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import JSONSchemaEditor from "@/components/JSONSchemaEditor";
import AIAssistButton from "@/components/AIAssistButton";

interface ExperimentFormProps {
  availableModels: string[];
  onSuccess: () => void;
}

const DEFAULT_SCHEMA = `{
  "name": "ExampleSchema",
  "strict": true,
  "schema": {
    "type": "object",
    "properties": {
      "field1": {
        "type": "string",
        "description": "Description of field1"
      },
      "field2": {
        "type": "number",
        "description": "Description of field2"
      }
    },
    "required": ["field1", "field2"],
    "additionalProperties": false
  }
}`;

export default function ExperimentForm({
  availableModels,
  onSuccess,
}: ExperimentFormProps) {
  const [name, setName] = useState("");
  const [prompt, setPrompt] = useState("");
  const [schemaJson, setSchemaJson] = useState(DEFAULT_SCHEMA);
  const [model, setModel] = useState("");
  const [enableTwoPass, setEnableTwoPass] = useState(false);

  const createMutation = useMutation({
    mutationFn: experimentsAPI.create,
    onSuccess: () => {
      setName("");
      setPrompt("");
      setSchemaJson(DEFAULT_SCHEMA);
      setModel("");
      setEnableTwoPass(false);
      onSuccess();
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name && prompt && schemaJson && model) {
      createMutation.mutate({
        name,
        prompt,
        schema_json: schemaJson,
        model,
        enable_two_pass: enableTwoPass
      });
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="exp-name">Experiment Name</Label>
        <Input
          id="exp-name"
          placeholder="Enter experiment name..."
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="exp-model">Model</Label>
        <Select value={model} onValueChange={setModel} required>
          <SelectTrigger id="exp-model">
            <SelectValue placeholder="Select a model" />
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

      <div className="flex items-center space-x-2 p-4 border rounded-lg bg-muted/30">
        <Checkbox
          id="enable-two-pass"
          checked={enableTwoPass}
          onCheckedChange={(checked) => setEnableTwoPass(checked as boolean)}
        />
        <div className="space-y-1">
          <Label
            htmlFor="enable-two-pass"
            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
          >
            Enable Two-Pass Extraction
          </Label>
          <p className="text-xs text-muted-foreground">
            First pass extracts data, then a review step identifies missing/hallucinated items,
            and a second pass produces refined output. Helps improve extraction quality.
          </p>
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="exp-prompt">Extraction Prompt</Label>
          <AIAssistButton
            currentContent={prompt}
            fieldType="prompt"
            onApply={setPrompt}
            context="This is an extraction prompt for getting structured data from financial advisor transcripts."
          />
        </div>
        <Textarea
          id="exp-prompt"
          placeholder="Enter the system prompt for extracting structured data from transcripts..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          required
          rows={6}
        />
        <p className="text-xs text-muted-foreground">
          This prompt instructs the LLM on what data to extract from the
          transcript.
        </p>
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
        <p className="text-xs text-muted-foreground">
          Define the structured output schema. The extracted data will conform to
          this schema.
        </p>
      </div>

      <div className="flex justify-end gap-2">
        <Button
          type="submit"
          disabled={
            createMutation.isPending || !name || !prompt || !schemaJson || !model
          }
        >
          {createMutation.isPending ? "Creating..." : "Create Experiment"}
        </Button>
      </div>

      {createMutation.isError && (
        <p className="text-sm text-destructive">
          Error: {(createMutation.error as Error).message}
        </p>
      )}
    </form>
  );
}
