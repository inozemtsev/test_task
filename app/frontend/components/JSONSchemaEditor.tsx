"use client";

import { useState, useEffect } from "react";
import Editor from "@monaco-editor/react";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, XCircle } from "lucide-react";

interface JSONSchemaEditorProps {
  value: string;
  onChange: (value: string) => void;
  height?: string;
}

export default function JSONSchemaEditor({
  value,
  onChange,
  height = "400px",
}: JSONSchemaEditorProps) {
  const [isValid, setIsValid] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const validateJSON = (jsonString: string) => {
    try {
      JSON.parse(jsonString);
      setIsValid(true);
      setError(null);
    } catch (e) {
      setIsValid(false);
      setError((e as Error).message);
    }
  };

  useEffect(() => {
    validateJSON(value);
  }, [value]);

  const handleEditorChange = (newValue: string | undefined) => {
    const val = newValue || "";
    onChange(val);
    validateJSON(val);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isValid ? (
            <>
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              <Badge variant="outline" className="text-green-600 border-green-600">
                Valid JSON
              </Badge>
            </>
          ) : (
            <>
              <XCircle className="h-4 w-4 text-destructive" />
              <Badge variant="outline" className="text-destructive border-destructive">
                Invalid JSON
              </Badge>
            </>
          )}
        </div>
      </div>

      <div className="border rounded-lg overflow-hidden">
        <Editor
          height={height}
          defaultLanguage="json"
          value={value}
          onChange={handleEditorChange}
          theme="vs-dark"
          onMount={(editor) => {
            // Format the document when editor mounts
            setTimeout(() => {
              editor.getAction('editor.action.formatDocument')?.run();
            }, 100);
          }}
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            automaticLayout: true,
            formatOnPaste: true,
            formatOnType: true,
            tabSize: 2,
          }}
        />
      </div>

      {error && (
        <div className="text-sm text-destructive p-2 bg-destructive/10 rounded">
          <span className="font-medium">JSON Error:</span> {error}
        </div>
      )}
    </div>
  );
}
