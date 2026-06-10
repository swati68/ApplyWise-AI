"use client";

import {
  AlertCircle,
  CheckCircle2,
  Code2,
  FileCode2,
  Loader2,
  Plus,
  Save,
  Star,
  Trash2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { PageHeader } from "@/components/page-header";
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
  type ResumeTemplateValues,
  resumeTemplateApi,
} from "@/lib/resume-template-api";
import { cn } from "@/lib/utils";


type EditorMode = "create" | "edit";


type ValidationErrors = Partial<Record<keyof ResumeTemplateValues, string>>;


const emptyFormValues: ResumeTemplateValues = {
  name: "",
  latexContent: "",
  isDefault: false,
};


const sampleLatexTemplate = String.raw`\documentclass[11pt]{article}
\usepackage[margin=0.75in]{geometry}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}

\setlist[itemize]{leftmargin=*, noitemsep, topsep=2pt}
\pagenumbering{gobble}

\begin{document}

\begin{center}
  {\LARGE [Full Name]}\\
  [Email] | [Phone] | [Location] | \href{[Portfolio URL]}{[Portfolio URL]}
\end{center}

\section*{Summary}
[Brief summary based only on verified profile facts.]

\section*{Experience}
\textbf{[Role]} \hfill [Start Date] -- [End Date]\\
[Company] \hfill [Location]
\begin{itemize}
  \item [Verified responsibility or accomplishment.]
  \item [Verified impact, technology, or scope.]
\end{itemize}

\section*{Projects}
\textbf{[Project Name]} \hfill [Tech Stack]
\begin{itemize}
  \item [Verified project detail.]
\end{itemize}

\section*{Education}
\textbf{[Institution]} \hfill [Graduation Date]\\
[Degree], [Field of Study]

\section*{Skills}
[Skill category]: [Verified skills]

\end{document}`;


function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Something went wrong.";
}


function templateToFormValues(template: ResumeTemplate): ResumeTemplateValues {
  return {
    name: template.name,
    latexContent: template.latexContent,
    isDefault: template.isDefault,
  };
}


function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}


function validate(values: ResumeTemplateValues) {
  const errors: ValidationErrors = {};

  if (values.name.trim() === "") {
    errors.name = "Template name is required.";
  }
  if (values.latexContent.trim() === "") {
    errors.latexContent = "LaTeX content is required.";
  }

  return errors;
}


function TemplateListItem({
  isSelected,
  isPendingDelete,
  onCancelDelete,
  onConfirmDelete,
  onEdit,
  onRequestDelete,
  onSetDefault,
  template,
}: {
  isSelected: boolean;
  isPendingDelete: boolean;
  onCancelDelete: () => void;
  onConfirmDelete: () => void;
  onEdit: () => void;
  onRequestDelete: () => void;
  onSetDefault: () => void;
  template: ResumeTemplate;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border bg-background p-4 transition hover:border-primary/50 hover:bg-primary/5",
        isSelected && "border-primary bg-primary/5",
      )}
    >
      <button className="w-full text-left" onClick={onEdit} type="button">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="truncate font-semibold">{template.name}</h3>
              {template.isDefault ? (
                <Badge className="gap-1" variant="secondary">
                  <Star className="h-3 w-3" />
                  Default
                </Badge>
              ) : null}
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              Updated {formatDate(template.updatedAt)}
            </p>
          </div>
          {template.isDefault ? (
            <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-500" />
          ) : null}
        </div>
      </button>
      <div className="mt-4 flex items-center justify-between gap-3">
        <span className="text-xs text-muted-foreground">
          {template.latexContent.split("\n").length} lines
        </span>
        <div className="flex flex-wrap justify-end gap-2">
          {isPendingDelete ? (
            <>
              <Button onClick={onCancelDelete} size="sm" type="button" variant="outline">
                Cancel
              </Button>
              <Button onClick={onConfirmDelete} size="sm" type="button" variant="destructive">
                <Trash2 />
                Delete
              </Button>
            </>
          ) : (
            <>
              {!template.isDefault ? (
                <Button onClick={onSetDefault} size="sm" type="button" variant="outline">
                  <Star />
                  Set default
                </Button>
              ) : null}
              <Button onClick={onRequestDelete} size="sm" type="button" variant="outline">
                <Trash2 />
                Delete
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}


function EmptyTemplateList({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="rounded-lg border border-dashed p-6 text-center">
      <div className="mx-auto mb-4 flex h-11 w-11 items-center justify-center rounded-md bg-muted text-muted-foreground">
        <FileCode2 className="h-5 w-5" />
      </div>
      <h3 className="font-semibold">No templates yet</h3>
      <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-muted-foreground">
        Create a LaTeX template for resume export workflows.
      </p>
      <Button className="mt-5" onClick={onCreate} size="sm" type="button">
        <Plus />
        New template
      </Button>
    </div>
  );
}


export function ResumeTemplateManager() {
  const [editorMode, setEditorMode] = useState<EditorMode>("create");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [formValues, setFormValues] =
    useState<ResumeTemplateValues>(emptyFormValues);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [templates, setTemplates] = useState<ResumeTemplate[]>([]);
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});

  const selectedTemplate = useMemo(
    () => templates.find((template) => template.id === selectedTemplateId) ?? null,
    [selectedTemplateId, templates],
  );

  useEffect(() => {
    let isMounted = true;

    async function loadTemplates() {
      try {
        const records = await resumeTemplateApi.list();
        if (!isMounted) {
          return;
        }

        setTemplates(records);
        setErrorMessage(null);

        if (records.length > 0) {
          const defaultTemplate = records.find((template) => template.isDefault);
          const initialTemplate = defaultTemplate ?? records[0];
          selectTemplate(initialTemplate);
        }
      } catch (error) {
        if (isMounted) {
          setErrorMessage(getErrorMessage(error));
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadTemplates();

    return () => {
      isMounted = false;
    };
  }, []);

  function selectTemplate(template: ResumeTemplate) {
    setEditorMode("edit");
    setFormValues(templateToFormValues(template));
    setPendingDeleteId(null);
    setSelectedTemplateId(template.id);
    setValidationErrors({});
  }

  function startCreate() {
    setEditorMode("create");
    setFormValues(emptyFormValues);
    setPendingDeleteId(null);
    setSelectedTemplateId(null);
    setValidationErrors({});
  }

  function insertSampleTemplate() {
    setFormValues((currentValues) => ({
      ...currentValues,
      latexContent: sampleLatexTemplate,
      name: currentValues.name.trim() === "" ? "Basic Resume Template" : currentValues.name,
    }));
    setValidationErrors((currentErrors) => ({
      ...currentErrors,
      latexContent: undefined,
      name: undefined,
    }));
  }

  async function reloadTemplates(nextSelectedId?: string) {
    const records = await resumeTemplateApi.list();
    setTemplates(records);

    const nextSelectedTemplate =
      records.find((template) => template.id === nextSelectedId) ??
      records.find((template) => template.id === selectedTemplateId) ??
      records.find((template) => template.isDefault) ??
      records[0] ??
      null;

    if (nextSelectedTemplate === null) {
      startCreate();
      return;
    }

    selectTemplate(nextSelectedTemplate);
  }

  async function saveTemplate() {
    const nextErrors = validate(formValues);
    setValidationErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setIsSaving(true);
    setErrorMessage(null);
    try {
      const payload: ResumeTemplateValues = {
        name: formValues.name.trim(),
        latexContent: formValues.latexContent,
        isDefault: formValues.isDefault,
      };

      const savedTemplate =
        editorMode === "create" || selectedTemplateId === null
          ? await resumeTemplateApi.create(payload)
          : await resumeTemplateApi.update(selectedTemplateId, payload);

      await reloadTemplates(savedTemplate.id);
      setPendingDeleteId(null);
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  }

  async function setDefaultTemplate(templateId: string) {
    setErrorMessage(null);
    try {
      const updatedTemplate = await resumeTemplateApi.setDefault(templateId);
      await reloadTemplates(updatedTemplate.id);
      setPendingDeleteId(null);
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    }
  }

  async function deleteTemplate(template: ResumeTemplate) {
    setErrorMessage(null);
    try {
      await resumeTemplateApi.delete(template.id);
      setPendingDeleteId(null);
      await reloadTemplates();
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        action={
          <Button onClick={startCreate} type="button">
            <Plus />
            New Template
          </Button>
        }
        description="Create and manage LaTeX templates for resume generation."
        eyebrow="Resume Templates"
        title="Template library"
      />

      {errorMessage ? (
        <Card className="border-destructive/30 bg-destructive/5">
          <CardContent className="flex gap-3 p-5">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
            <div>
              <h2 className="font-semibold text-destructive">Template request failed</h2>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                {errorMessage}
              </p>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[380px_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <div>
                <CardTitle>Saved templates</CardTitle>
                <CardDescription className="mt-2">
                  {templates.length} template{templates.length === 1 ? "" : "s"}
                </CardDescription>
              </div>
              {isLoading ? (
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              ) : null}
            </div>
          </CardHeader>
          <CardContent>
            {templates.length === 0 && !isLoading ? (
              <EmptyTemplateList onCreate={startCreate} />
            ) : (
              <div className="space-y-3">
                {templates.map((template) => (
                  <TemplateListItem
                    isSelected={template.id === selectedTemplateId}
                    isPendingDelete={pendingDeleteId === template.id}
                    key={template.id}
                    onCancelDelete={() => setPendingDeleteId(null)}
                    onConfirmDelete={() => deleteTemplate(template)}
                    onEdit={() => selectTemplate(template)}
                    onRequestDelete={() => {
                      selectTemplate(template);
                      setPendingDeleteId(template.id);
                    }}
                    onSetDefault={() => setDefaultTemplate(template.id)}
                    template={template}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <Badge variant="secondary">
                    {editorMode === "create" ? "Create" : "Edit"}
                  </Badge>
                  {selectedTemplate?.isDefault ? (
                    <Badge className="gap-1" variant="outline">
                      <Star className="h-3 w-3" />
                      Default
                    </Badge>
                  ) : null}
                </div>
                <CardTitle>LaTeX template editor</CardTitle>
                <CardDescription className="mt-2 max-w-2xl">
                  Store reusable LaTeX source for resume generation.
                </CardDescription>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button onClick={insertSampleTemplate} type="button" variant="outline">
                  <Code2 />
                  Insert Sample
                </Button>
                {editorMode === "edit" && selectedTemplate ? (
                  <>
                    {!selectedTemplate.isDefault ? (
                      <Button
                        onClick={() => setDefaultTemplate(selectedTemplate.id)}
                        type="button"
                        variant="outline"
                      >
                        <Star />
                        Set Default
                      </Button>
                    ) : null}
                    {pendingDeleteId === selectedTemplate.id ? (
                      <>
                        <Button
                          onClick={() => setPendingDeleteId(null)}
                          type="button"
                          variant="outline"
                        >
                          Cancel Delete
                        </Button>
                        <Button
                          onClick={() => deleteTemplate(selectedTemplate)}
                          type="button"
                          variant="destructive"
                        >
                          <Trash2 />
                          Confirm Delete
                        </Button>
                      </>
                    ) : (
                      <Button
                        onClick={() => setPendingDeleteId(selectedTemplate.id)}
                        type="button"
                        variant="outline"
                      >
                        <Trash2 />
                        Delete
                      </Button>
                    )}
                  </>
                ) : null}
              </div>
            </div>
          </CardHeader>

          <CardContent className="space-y-5">
            <label className="block space-y-2">
              <span className="text-sm font-medium text-foreground">
                Template name <span className="text-destructive">*</span>
              </span>
              <input
                className={cn(
                  "h-10 w-full rounded-md border bg-background px-3 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-ring/20",
                  validationErrors.name &&
                    "border-destructive focus:border-destructive focus:ring-destructive/20",
                )}
                onChange={(event) => {
                  setFormValues((currentValues) => ({
                    ...currentValues,
                    name: event.target.value,
                  }));
                  setValidationErrors((currentErrors) => ({
                    ...currentErrors,
                    name: undefined,
                  }));
                }}
                placeholder="Example: Compact ATS Template"
                value={formValues.name}
              />
              {validationErrors.name ? (
                <p className="text-xs text-destructive">{validationErrors.name}</p>
              ) : null}
            </label>

            <label className="flex items-center gap-3 rounded-md border bg-background p-3">
              <input
                checked={formValues.isDefault}
                className="h-4 w-4"
                onChange={(event) => {
                  setFormValues((currentValues) => ({
                    ...currentValues,
                    isDefault: event.target.checked,
                  }));
                }}
                type="checkbox"
              />
              <span className="text-sm font-medium">Make this the default template</span>
            </label>

            <label className="block space-y-2">
              <span className="text-sm font-medium text-foreground">
                LaTeX content <span className="text-destructive">*</span>
              </span>
              <textarea
                className={cn(
                  "min-h-[520px] w-full resize-y rounded-md border bg-slate-950 px-4 py-3 font-mono text-sm leading-6 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-primary focus:ring-2 focus:ring-ring/20",
                  validationErrors.latexContent &&
                    "border-destructive focus:border-destructive focus:ring-destructive/20",
                )}
                onChange={(event) => {
                  setFormValues((currentValues) => ({
                    ...currentValues,
                    latexContent: event.target.value,
                  }));
                  setValidationErrors((currentErrors) => ({
                    ...currentErrors,
                    latexContent: undefined,
                  }));
                }}
                placeholder="Paste or write LaTeX template content..."
                spellCheck={false}
                value={formValues.latexContent}
              />
              {validationErrors.latexContent ? (
                <p className="text-xs text-destructive">
                  {validationErrors.latexContent}
                </p>
              ) : null}
            </label>

            <div className="flex flex-col-reverse gap-3 border-t pt-5 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs leading-5 text-muted-foreground">
                Generated content must only use verified profile data.
              </p>
              <div className="flex gap-2">
                <Button onClick={startCreate} type="button" variant="outline">
                  Clear
                </Button>
                <Button disabled={isSaving} onClick={saveTemplate} type="button">
                  {isSaving ? <Loader2 className="animate-spin" /> : <Save />}
                  {editorMode === "create" ? "Create Template" : "Save Changes"}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
