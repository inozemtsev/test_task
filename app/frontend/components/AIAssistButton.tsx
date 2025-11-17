"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { aiAssistAPI } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Wand2, Loader2 } from "lucide-react";

interface AIAssistButtonProps {
  currentContent: string;
  fieldType: "prompt" | "schema";
  onApply: (content: string) => void;
  context?: string;
  buttonSize?: "default" | "sm" | "lg" | "icon";
}

export default function AIAssistButton({
  currentContent,
  fieldType,
  onApply,
  context = "",
  buttonSize = "sm",
}: AIAssistButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [instruction, setInstruction] = useState("");
  const [generatedContent, setGeneratedContent] = useState("");

  const generateMutation = useMutation({
    mutationFn: aiAssistAPI.generate,
    onSuccess: (data: { content: string }) => {
      setGeneratedContent(data.content);
    },
  });

  const handleGenerate = () => {
    if (instruction.trim()) {
      generateMutation.mutate({
        instruction: instruction.trim(),
        current_content: currentContent,
        field_type: fieldType,
        context,
      });
    }
  };

  const handleApply = () => {
    if (generatedContent) {
      onApply(generatedContent);
      setIsOpen(false);
      setInstruction("");
      setGeneratedContent("");
    }
  };

  const handleClose = () => {
    setIsOpen(false);
    setInstruction("");
    setGeneratedContent("");
    generateMutation.reset();
  };

  return (
    <>
      <Button
        type="button"
        variant="ghost"
        size={buttonSize}
        onClick={() => setIsOpen(true)}
        className="text-purple-600 hover:text-purple-700 hover:bg-purple-50"
        title="AI Assist"
      >
        <Wand2 className="h-4 w-4" />
        {buttonSize !== "icon" && <span className="ml-2">AI Assist</span>}
      </Button>

      <Dialog open={isOpen} onOpenChange={handleClose}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>AI Assistant</DialogTitle>
            <DialogDescription>
              Describe what you want to create or how you want to improve the{" "}
              {fieldType === "prompt" ? "prompt" : "JSON schema"}.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="instruction">Your Instruction</Label>
              <Textarea
                id="instruction"
                placeholder={
                  fieldType === "prompt"
                    ? "e.g., 'Create a prompt to extract client financial goals from a conversation'"
                    : "e.g., 'Create a schema for extracting client name, age, and financial goals'"
                }
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                rows={3}
              />
            </div>

            {generateMutation.isPending && (
              <div className="flex items-center justify-center p-8 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin mr-2" />
                <span>Generating with AI...</span>
              </div>
            )}

            {generateMutation.isError && (
              <div className="text-sm text-destructive p-3 bg-destructive/10 rounded">
                Error: {(generateMutation.error as Error).message}
              </div>
            )}

            {generatedContent && !generateMutation.isPending && (
              <div className="space-y-2">
                <Label>Generated Content</Label>
                <Textarea
                  value={generatedContent}
                  onChange={(e) => setGeneratedContent(e.target.value)}
                  rows={12}
                  className={fieldType === "schema" ? "font-mono text-xs" : ""}
                />
                <p className="text-xs text-muted-foreground">
                  You can edit the generated content before applying it.
                </p>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleClose}>
              Cancel
            </Button>
            {!generatedContent ? (
              <Button
                onClick={handleGenerate}
                disabled={!instruction.trim() || generateMutation.isPending}
              >
                {generateMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Wand2 className="h-4 w-4 mr-2" />
                    Generate
                  </>
                )}
              </Button>
            ) : (
              <Button onClick={handleApply}>
                Apply
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
