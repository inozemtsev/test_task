"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { transcriptsAPI } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

interface AddTranscriptFormProps {
  onSuccess: () => void;
}

export default function AddTranscriptForm({ onSuccess }: AddTranscriptFormProps) {
  const [name, setName] = useState("");
  const [content, setContent] = useState("");

  const createMutation = useMutation({
    mutationFn: transcriptsAPI.create,
    onSuccess: () => {
      setName("");
      setContent("");
      onSuccess();
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name && content) {
      createMutation.mutate({ name, content });
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">Transcript Name</Label>
        <Input
          id="name"
          placeholder="Enter transcript name..."
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="content">Transcript Content</Label>
        <Textarea
          id="content"
          placeholder="Paste transcript content here..."
          value={content}
          onChange={(e) => setContent(e.target.value)}
          required
          rows={15}
          className="font-mono text-sm"
        />
      </div>

      <div className="flex justify-end gap-2">
        <Button
          type="submit"
          disabled={createMutation.isPending || !name || !content}
        >
          {createMutation.isPending ? "Adding..." : "Add Transcript"}
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
