"use client";

import Link from "next/link";
import {
  AlertCircle,
  ExternalLink,
  FileCode2,
  FileText,
  Upload,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type ResumeTemplate,
  resumeTemplateApi,
} from "@/lib/resume-template-api";


type UploadedResume = {
  id: string;
  name: string;
  sizeLabel: string;
  url: string;
  uploadedAt: string;
};


function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Something went wrong.";
}


function formatFileSize(size: number) {
  if (size < 1024 * 1024) {
    return `${Math.max(1, Math.round(size / 1024))} KB`;
  }

  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}


function createUploadId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }

  return `resume-${Date.now()}`;
}


export function ResumeWorkspace() {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedUploadId, setSelectedUploadId] = useState<string | null>(null);
  const [templates, setTemplates] = useState<ResumeTemplate[]>([]);
  const [uploads, setUploads] = useState<UploadedResume[]>([]);
  const uploadsRef = useRef<UploadedResume[]>([]);

  useEffect(() => {
    uploadsRef.current = uploads;
  }, [uploads]);

  useEffect(() => {
    async function loadTemplates() {
      try {
        setTemplates(await resumeTemplateApi.list());
      } catch (error) {
        setErrorMessage(getErrorMessage(error));
      }
    }

    void loadTemplates();

    return () => {
      for (const upload of uploadsRef.current) {
        URL.revokeObjectURL(upload.url);
      }
    };
  }, []);

  const selectedUpload = useMemo(
    () => uploads.find((upload) => upload.id === selectedUploadId) ?? null,
    [selectedUploadId, uploads],
  );
  const defaultTemplate = templates.find((template) => template.isDefault);

  function handleUpload(files: FileList | null) {
    setErrorMessage(null);
    if (files === null || files.length === 0) {
      return;
    }

    const pdfFiles = Array.from(files).filter(
      (file) => file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf"),
    );

    if (pdfFiles.length === 0) {
      setErrorMessage("Please choose a PDF resume.");
      return;
    }

    const nextUploads = pdfFiles.map((file) => ({
      id: createUploadId(),
      name: file.name,
      sizeLabel: formatFileSize(file.size),
      url: URL.createObjectURL(file),
      uploadedAt: new Intl.DateTimeFormat("en", {
        month: "short",
        day: "numeric",
        year: "numeric",
      }).format(new Date()),
    }));

    setUploads((currentUploads) => [...nextUploads, ...currentUploads]);
    setSelectedUploadId(nextUploads[0]?.id ?? null);
  }

  function removeUpload(upload: UploadedResume) {
    URL.revokeObjectURL(upload.url);
    setUploads((currentUploads) =>
      currentUploads.filter((currentUpload) => currentUpload.id !== upload.id),
    );
    if (selectedUploadId === upload.id) {
      const nextUpload = uploads.find((currentUpload) => currentUpload.id !== upload.id);
      setSelectedUploadId(nextUpload?.id ?? null);
    }
  }

  return (
    <div className="space-y-6">
      {errorMessage ? (
        <Card className="border-destructive/30 bg-destructive/5">
          <CardContent className="flex gap-3 p-5">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
            <div>
              <h2 className="font-semibold text-destructive">Resume request failed</h2>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                {errorMessage}
              </p>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-md bg-primary/10 text-primary">
                <Upload className="h-5 w-5" />
              </div>
              <CardTitle>Upload PDF resume</CardTitle>
              <CardDescription>
                Add a PDF resume to view it alongside saved LaTeX templates.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed p-6 text-center transition hover:border-primary hover:bg-primary/5">
                <Upload className="mb-3 h-6 w-6 text-muted-foreground" />
                <span className="font-medium">Choose PDF resume</span>
                <span className="mt-1 text-sm text-muted-foreground">
                  Files are shown locally for review.
                </span>
                <input
                  accept="application/pdf,.pdf"
                  className="sr-only"
                  multiple
                  onChange={(event) => handleUpload(event.target.files)}
                  type="file"
                />
              </label>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <CardTitle>LaTeX templates</CardTitle>
                  <CardDescription className="mt-2">
                    {templates.length} saved template{templates.length === 1 ? "" : "s"}
                  </CardDescription>
                </div>
                <Button asChild size="sm" variant="outline">
                  <Link href="/resumes/templates">
                    <FileCode2 />
                    Manage
                  </Link>
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {templates.length === 0 ? (
                <div className="rounded-lg border border-dashed p-5 text-center">
                  <FileCode2 className="mx-auto mb-3 h-5 w-5 text-muted-foreground" />
                  <h3 className="font-semibold">No templates saved</h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Add a LaTeX template to prepare for resume generation.
                  </p>
                </div>
              ) : (
                templates.map((template) => (
                  <div
                    className="flex items-center justify-between rounded-lg border p-4"
                    key={template.id}
                  >
                    <span className="font-medium">{template.name}</span>
                    <Badge variant={template.isDefault ? "secondary" : "outline"}>
                      {template.isDefault ? "Default" : "Saved"}
                    </Badge>
                  </div>
                ))
              )}
              {defaultTemplate ? (
                <p className="text-xs text-muted-foreground">
                  Default template: {defaultTemplate.name}
                </p>
              ) : null}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Uploaded resumes</CardTitle>
            <CardDescription>
              Select a PDF to preview it or open the original file.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {uploads.length === 0 ? (
              <div className="rounded-lg border border-dashed p-8 text-center">
                <FileText className="mx-auto mb-3 h-7 w-7 text-muted-foreground" />
                <h3 className="font-semibold">No PDF resume uploaded</h3>
                <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">
                  Upload a PDF resume to preview it here.
                </p>
              </div>
            ) : (
              <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
                <div className="space-y-2">
                  {uploads.map((upload) => (
                    <div
                      className="rounded-lg border bg-background p-3"
                      key={upload.id}
                    >
                      <button
                        className="w-full text-left"
                        onClick={() => setSelectedUploadId(upload.id)}
                        type="button"
                      >
                        <p className="truncate font-medium">{upload.name}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {upload.sizeLabel} · {upload.uploadedAt}
                        </p>
                      </button>
                      <div className="mt-3 flex items-center justify-between gap-2">
                        <Badge variant={upload.id === selectedUploadId ? "secondary" : "outline"}>
                          {upload.id === selectedUploadId ? "Viewing" : "Uploaded"}
                        </Badge>
                        <Button
                          aria-label={`Remove ${upload.name}`}
                          onClick={() => removeUpload(upload)}
                          size="icon"
                          type="button"
                          variant="outline"
                        >
                          <X />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="overflow-hidden rounded-lg border bg-muted">
                  {selectedUpload ? (
                    <>
                      <div className="flex flex-col gap-3 border-b bg-background p-3 sm:flex-row sm:items-center sm:justify-between">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold">
                            Original PDF
                          </p>
                          <p className="truncate text-xs text-muted-foreground">
                            {selectedUpload.name}
                          </p>
                        </div>
                        <Button asChild size="sm" type="button" variant="outline">
                          <a
                            href={selectedUpload.url}
                            rel="noreferrer"
                            target="_blank"
                          >
                            Open original
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        </Button>
                      </div>
                      <object
                        aria-label={`Preview of ${selectedUpload.name}`}
                        className="h-[640px] w-full"
                        data={selectedUpload.url}
                        type="application/pdf"
                      >
                        <div className="p-6 text-sm text-muted-foreground">
                          PDF preview is unavailable in this browser. Use Open original to view the uploaded file.
                        </div>
                      </object>
                    </>
                  ) : null}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
