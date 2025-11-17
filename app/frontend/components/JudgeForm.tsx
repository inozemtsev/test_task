"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { judgesAPI } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface JudgeFormProps {
  availableModels: string[];
  onSuccess: () => void;
}

export default function JudgeForm({
  availableModels,
  onSuccess,
}: JudgeFormProps) {
  const [name, setName] = useState("");
  const [model, setModel] = useState("");

  const createMutation = useMutation({
    mutationFn: judgesAPI.create,
    onSuccess: () => {
      setName("");
      setModel("");
      onSuccess();
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name && model) {
      createMutation.mutate({ name, model });
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="judge-name">Judge Name</Label>
        <Input
          id="judge-name"
          placeholder="Enter judge name..."
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="judge-model">Model</Label>
        <Select value={model} onValueChange={setModel} required>
          <SelectTrigger id="judge-model">
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

      <div className="flex justify-end gap-2">
        <Button
          type="submit"
          disabled={createMutation.isPending || !name || !model}
        >
          {createMutation.isPending ? "Creating..." : "Create Judge"}
        </Button>
      </div>

      {createMutation.isError && (
        <p className="text-sm text-destructive">
          Error: {(createMutation.error as Error).message}
        </p>
      )}

      <div className="text-sm text-muted-foreground mt-4">
        <p>After creating the judge, you can add characteristics to define evaluation criteria.</p>
      </div>
    </form>
  );
}
