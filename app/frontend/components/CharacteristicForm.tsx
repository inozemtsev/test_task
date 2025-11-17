"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { judgesAPI } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import JSONSchemaEditor from "@/components/JSONSchemaEditor";
import AIAssistButton from "@/components/AIAssistButton";
import { ChevronDown, ChevronUp } from "lucide-react";

interface CharacteristicFormProps {
  judgeId: number;
  onSuccess: () => void;
}

const DEFAULT_SCHEMA = `{
  "name": "CharacteristicEvaluation",
  "strict": true,
  "schema": {
    "type": "object",
    "properties": {
      "passes": {
        "type": "boolean",
        "description": "Whether the characteristic passes"
      },
      "reasoning": {
        "type": "string",
        "description": "Detailed reasoning for the evaluation"
      }
    },
    "required": ["passes", "reasoning"],
    "additionalProperties": false
  }
}`;

export default function CharacteristicForm({
  judgeId,
  onSuccess,
}: CharacteristicFormProps) {
  const [name, setName] = useState("");
  const [prompt, setPrompt] = useState("");
  const [schemaJson, setSchemaJson] = useState("");
  const [showSchema, setShowSchema] = useState(false);

  const createMutation = useMutation({
    mutationFn: (data: { name: string; prompt: string; schema_json?: string }) =>
      judgesAPI.addCharacteristic(judgeId, data),
    onSuccess: () => {
      setName("");
      setPrompt("");
      setSchemaJson("");
      setShowSchema(false);
      onSuccess();
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name && prompt) {
      createMutation.mutate({
        name,
        prompt,
        schema_json: schemaJson || undefined,
      });
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="char-name">Characteristic Name</Label>
        <Input
          id="char-name"
          placeholder="e.g., 'Completeness', 'Accuracy', 'Consistency'"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="char-prompt">Evaluation Prompt</Label>
          <AIAssistButton
            currentContent={prompt}
            fieldType="prompt"
            onApply={setPrompt}
            context="This is an evaluation prompt for a judge characteristic. It should define criteria for evaluating whether extracted data passes this characteristic."
          />
        </div>
        <Textarea
          id="char-prompt"
          placeholder="Define the evaluation criteria for this characteristic. The LLM will receive the transcript and extracted data, and should return a boolean (pass/fail) based on this prompt."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          required
          rows={8}
        />
        <p className="text-xs text-muted-foreground">
          This prompt will be used to evaluate whether the extracted data passes this
          characteristic. Be specific about what constitutes a pass or fail.
        </p>
      </div>

      <div className="space-y-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => {
            setShowSchema(!showSchema);
            if (!showSchema && !schemaJson) {
              setSchemaJson(DEFAULT_SCHEMA);
            }
          }}
          className="w-full"
        >
          {showSchema ? (
            <>
              <ChevronUp className="h-4 w-4 mr-2" />
              Hide Structured Output Schema
            </>
          ) : (
            <>
              <ChevronDown className="h-4 w-4 mr-2" />
              Add Structured Output Schema (Optional)
            </>
          )}
        </Button>

        {showSchema && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>JSON Schema</Label>
              <AIAssistButton
                currentContent={schemaJson}
                fieldType="schema"
                onApply={setSchemaJson}
                context="This is a JSON schema for a judge characteristic evaluation result. It must include 'passes' (boolean) and 'reasoning' (string) fields."
              />
            </div>
            <JSONSchemaEditor
              value={schemaJson}
              onChange={setSchemaJson}
              height="300px"
            />
            <p className="text-xs text-muted-foreground">
              Define a structured output schema for more precise evaluation results.
              Must include "passes" (boolean) and "reasoning" (string) fields.
            </p>
          </div>
        )}
      </div>

      <div className="flex justify-end gap-2">
        <Button
          type="submit"
          disabled={createMutation.isPending || !name || !prompt}
        >
          {createMutation.isPending ? "Adding..." : "Add Characteristic"}
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
