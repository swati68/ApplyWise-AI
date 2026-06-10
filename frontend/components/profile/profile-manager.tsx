"use client";

import {
  AlertCircle,
  BriefcaseBusiness,
  Code2,
  FolderKanban,
  GraduationCap,
  Pencil,
  Plus,
  Save,
  Trash2,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
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
  type EducationProfile,
  type ExperienceProfile,
  type ProfileData,
  type ProfileRecord,
  type ProfileSectionKey,
  type ProjectProfile,
  type SkillProfile,
  profileApi,
} from "@/lib/profile-api";
import { cn } from "@/lib/utils";


type ProfileFormValues = {
  education: Omit<EducationProfile, "id">;
  experience: Omit<ExperienceProfile, "id">;
  projects: Omit<ProjectProfile, "id">;
  skills: Omit<SkillProfile, "id">;
};


type EditorState = {
  section: ProfileSectionKey;
  mode: "create" | "edit";
  record: ProfileRecord | null;
};


type SectionMeta = {
  key: ProfileSectionKey;
  title: string;
  description: string;
  emptyTitle: string;
  emptyDescription: string;
  icon: LucideIcon;
};


type ValidationErrors = Partial<Record<string, string>>;


const sectionMeta: SectionMeta[] = [
  {
    key: "education",
    title: "Education",
    description: "Schools, programs, coursework, and academic context.",
    emptyTitle: "No education added",
    emptyDescription: "Add schools, degrees, dates, and academic details.",
    icon: GraduationCap,
  },
  {
    key: "experience",
    title: "Experience",
    description: "Roles, responsibilities, tools, and impact bullets.",
    emptyTitle: "No experience added",
    emptyDescription: "Add work history to build your profile.",
    icon: BriefcaseBusiness,
  },
  {
    key: "projects",
    title: "Projects",
    description: "Portfolio work, links, technical scope, and evidence bullets.",
    emptyTitle: "No projects added",
    emptyDescription: "Capture projects with technologies, links, and concrete bullets.",
    icon: FolderKanban,
  },
  {
    key: "skills",
    title: "Skills",
    description: "Skill inventory grouped by category, proficiency, and tags.",
    emptyTitle: "No skills added",
    emptyDescription: "Add skills that can support job matching.",
    icon: Code2,
  },
];


const emptyEducation: Omit<EducationProfile, "id"> = {
  institution: "",
  degree: "",
  fieldOfStudy: "",
  startDate: "",
  endDate: "",
  gpa: "",
  location: "",
  description: "",
};


const emptyExperience: Omit<ExperienceProfile, "id"> = {
  company: "",
  role: "",
  location: "",
  startDate: "",
  endDate: "",
  isCurrent: false,
  techStack: [],
  bullets: [],
  tags: [],
};


const emptyProject: Omit<ProjectProfile, "id"> = {
  name: "",
  description: "",
  techStack: [],
  bullets: [],
  links: [],
  tags: [],
};


const emptySkill: Omit<SkillProfile, "id"> = {
  category: "",
  name: "",
  proficiency: "",
  tags: [],
};


const defaultFormValues: ProfileFormValues = {
  education: emptyEducation,
  experience: emptyExperience,
  projects: emptyProject,
  skills: emptySkill,
};


function getEmptyFormValues(section: ProfileSectionKey) {
  return structuredClone(defaultFormValues[section]);
}


function getRecordFormValues(section: ProfileSectionKey, record: ProfileRecord) {
  const { id: _id, ...values } = record;
  return structuredClone(values) as ProfileFormValues[typeof section];
}


function getSectionMeta(section: ProfileSectionKey) {
  return sectionMeta.find((item) => item.key === section) ?? sectionMeta[0];
}


function countFacts(data: ProfileData) {
  return (
    data.education.length +
    data.experience.length +
    data.projects.length +
    data.skills.length
  );
}


type SkillCategoryGroup = {
  category: string;
  skills: SkillProfile[];
};


function groupSkillsByCategory(skills: SkillProfile[]): SkillCategoryGroup[] {
  const groupedSkills = new Map<string, SkillProfile[]>();
  for (const skill of skills) {
    const category = skill.category.trim() || "Uncategorized";
    groupedSkills.set(category, [...(groupedSkills.get(category) ?? []), skill]);
  }

  return [...groupedSkills.entries()]
    .sort(([categoryA], [categoryB]) => categoryA.localeCompare(categoryB))
    .map(([category, groupedItems]) => ({
      category,
      skills: [...groupedItems].sort((skillA, skillB) =>
        skillA.name.localeCompare(skillB.name),
      ),
    }));
}


function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Something went wrong.";
}


function TextInput({
  error,
  label,
  required = false,
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  error?: string;
  label: string;
  required?: boolean;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <label className="block space-y-2">
      <span className="text-sm font-medium text-foreground">
        {label}
        {required ? <span className="text-destructive"> *</span> : null}
      </span>
      <input
        className={cn(
          "h-10 w-full rounded-md border bg-background px-3 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-ring/20",
          error && "border-destructive focus:border-destructive focus:ring-destructive/20",
        )}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        type={type}
        value={value}
      />
      {error ? <p className="text-xs text-destructive">{error}</p> : null}
    </label>
  );
}


function TextArea({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="block space-y-2">
      <span className="text-sm font-medium text-foreground">{label}</span>
      <textarea
        className="min-h-28 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-ring/20"
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        value={value}
      />
    </label>
  );
}


function ListEditor({
  addLabel,
  label,
  placeholder,
  values,
  onChange,
}: {
  addLabel: string;
  label: string;
  placeholder: string;
  values: string[];
  onChange: (values: string[]) => void;
}) {
  function updateValue(index: number, value: string) {
    const nextValues = [...values];
    nextValues[index] = value;
    onChange(nextValues);
  }

  function removeValue(index: number) {
    onChange(values.filter((_, currentIndex) => currentIndex !== index));
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-foreground">{label}</p>
        <Button
          onClick={() => onChange([...values, ""])}
          size="sm"
          type="button"
          variant="outline"
        >
          <Plus />
          {addLabel}
        </Button>
      </div>
      {values.length === 0 ? (
        <div className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
          No entries yet.
        </div>
      ) : (
        <div className="space-y-2">
          {values.map((value, index) => (
            <div className="flex gap-2" key={`${label}-${index}`}>
              <input
                className="h-10 flex-1 rounded-md border bg-background px-3 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-ring/20"
                onChange={(event) => updateValue(index, event.target.value)}
                placeholder={placeholder}
                value={value}
              />
              <Button
                aria-label={`Remove ${label} entry`}
                onClick={() => removeValue(index)}
                size="icon"
                type="button"
                variant="outline"
              >
                <X />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


function TagList({ tags }: { tags: string[] }) {
  const visibleTags = tags.filter(Boolean);
  if (visibleTags.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {visibleTags.map((tag) => (
        <Badge key={tag} variant="muted">
          {tag}
        </Badge>
      ))}
    </div>
  );
}


function BulletList({ bullets }: { bullets: string[] }) {
  const visibleBullets = bullets.filter(Boolean);
  if (visibleBullets.length === 0) {
    return null;
  }

  return (
    <ul className="space-y-2 text-sm leading-6 text-muted-foreground">
      {visibleBullets.map((bullet) => (
        <li className="flex gap-2" key={bullet}>
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
          <span>{bullet}</span>
        </li>
      ))}
    </ul>
  );
}


function EmptyState({
  description,
  icon: Icon,
  onAdd,
  title,
}: {
  description: string;
  icon: LucideIcon;
  onAdd: () => void;
  title: string;
}) {
  return (
    <div className="rounded-lg border border-dashed p-6 text-center">
      <div className="mx-auto mb-4 flex h-11 w-11 items-center justify-center rounded-md bg-muted text-muted-foreground">
        <Icon className="h-5 w-5" />
      </div>
      <h3 className="font-semibold">{title}</h3>
      <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-muted-foreground">
        {description}
      </p>
      <Button className="mt-5" onClick={onAdd} size="sm" type="button">
        <Plus />
        Add item
      </Button>
    </div>
  );
}


function EducationCard({
  education,
  onDelete,
  onEdit,
}: {
  education: EducationProfile;
  onDelete: () => void;
  onEdit: () => void;
}) {
  return (
    <div className="rounded-lg border bg-background p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-semibold">{education.institution}</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {[education.degree, education.fieldOfStudy].filter(Boolean).join(" · ") ||
              "Academic record"}
          </p>
        </div>
        <RecordActions onDelete={onDelete} onEdit={onEdit} />
      </div>
      <div className="mt-4 grid gap-2 text-sm text-muted-foreground md:grid-cols-2">
        <span>{[education.startDate, education.endDate].filter(Boolean).join(" - ")}</span>
        <span>{education.location}</span>
        <span>{education.gpa ? `GPA ${education.gpa}` : ""}</span>
      </div>
      {education.description ? (
        <p className="mt-4 text-sm leading-6 text-muted-foreground">
          {education.description}
        </p>
      ) : null}
    </div>
  );
}


function ExperienceCard({
  experience,
  onDelete,
  onEdit,
}: {
  experience: ExperienceProfile;
  onDelete: () => void;
  onEdit: () => void;
}) {
  return (
    <article className="rounded-lg border bg-background p-4">
      <div className="grid gap-4 lg:grid-cols-[minmax(0,0.75fr)_minmax(0,1.25fr)]">
        <div className="min-w-0">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="truncate font-semibold">{experience.role}</h3>
                {experience.isCurrent ? <Badge variant="secondary">Current</Badge> : null}
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                {experience.company}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {[experience.startDate, experience.endDate || "Present"]
                  .filter(Boolean)
                  .join(" - ")}
              </p>
              {experience.location ? (
                <p className="mt-1 text-xs text-muted-foreground">
                  {experience.location}
                </p>
              ) : null}
            </div>
            <RecordActions onDelete={onDelete} onEdit={onEdit} />
          </div>
          <div className="mt-4 space-y-3">
            <TagList tags={experience.techStack} />
            <TagList tags={experience.tags} />
          </div>
        </div>
        <div className="rounded-md bg-muted/35 p-4">
          <BulletList bullets={experience.bullets} />
          {experience.bullets.filter(Boolean).length === 0 ? (
            <p className="text-sm text-muted-foreground">No bullet points added.</p>
          ) : null}
        </div>
      </div>
    </article>
  );
}


function ProjectCard({
  onDelete,
  onEdit,
  project,
}: {
  onDelete: () => void;
  onEdit: () => void;
  project: ProjectProfile;
}) {
  return (
    <div className="rounded-lg border bg-background p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-semibold">{project.name}</h3>
          {project.description ? (
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {project.description}
            </p>
          ) : null}
        </div>
        <RecordActions onDelete={onDelete} onEdit={onEdit} />
      </div>
      <div className="mt-4 space-y-4">
        <TagList tags={project.techStack} />
        <BulletList bullets={project.bullets} />
        <TagList tags={project.tags} />
        <TagList tags={project.links} />
      </div>
    </div>
  );
}


function SkillCategoryPanel({
  group,
  onDelete,
  onEdit,
}: {
  group: SkillCategoryGroup;
  onDelete: (skillId: string) => void;
  onEdit: (skill: SkillProfile) => void;
}) {
  return (
    <div className="rounded-lg border bg-background">
      <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <div>
          <h3 className="font-semibold">{group.category}</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            {group.skills.length} skill{group.skills.length === 1 ? "" : "s"}
          </p>
        </div>
        <Badge variant="outline">{group.skills.length}</Badge>
      </div>
      <div className="grid gap-2 p-3 sm:grid-cols-2 xl:grid-cols-3">
        {group.skills.map((skill) => (
          <div
            className="flex min-h-16 items-start justify-between gap-3 rounded-md border bg-card p-3"
            key={skill.id}
          >
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <p className="truncate text-sm font-medium">{skill.name}</p>
                {skill.proficiency ? (
                  <Badge variant="secondary">{skill.proficiency}</Badge>
                ) : null}
              </div>
              {skill.tags.filter(Boolean).length > 0 ? (
                <p className="mt-2 line-clamp-2 text-xs leading-5 text-muted-foreground">
                  {skill.tags.filter(Boolean).join(", ")}
                </p>
              ) : null}
            </div>
            <CompactRecordActions
              onDelete={() => onDelete(skill.id)}
              onEdit={() => onEdit(skill)}
            />
          </div>
        ))}
      </div>
    </div>
  );
}


function RecordActions({
  onDelete,
  onEdit,
}: {
  onDelete: () => void;
  onEdit: () => void;
}) {
  return (
    <div className="flex gap-2">
      <Button aria-label="Edit item" onClick={onEdit} size="icon" type="button" variant="outline">
        <Pencil />
      </Button>
      <Button
        aria-label="Delete item"
        onClick={onDelete}
        size="icon"
        type="button"
        variant="outline"
      >
        <Trash2 />
      </Button>
    </div>
  );
}


function CompactRecordActions({
  onDelete,
  onEdit,
}: {
  onDelete: () => void;
  onEdit: () => void;
}) {
  return (
    <div className="flex shrink-0 gap-1">
      <Button
        aria-label="Edit item"
        className="h-8 w-8"
        onClick={onEdit}
        size="icon"
        type="button"
        variant="ghost"
      >
        <Pencil />
      </Button>
      <Button
        aria-label="Delete item"
        className="h-8 w-8"
        onClick={onDelete}
        size="icon"
        type="button"
        variant="ghost"
      >
        <Trash2 />
      </Button>
    </div>
  );
}


function SectionCard({
  data,
  meta,
  onAdd,
  onDelete,
  onEdit,
}: {
  data: ProfileData;
  meta: SectionMeta;
  onAdd: (section: ProfileSectionKey) => void;
  onDelete: (section: ProfileSectionKey, recordId: string) => void;
  onEdit: (section: ProfileSectionKey, record: ProfileRecord) => void;
}) {
  const records = data[meta.key];
  const Icon = meta.icon;
  const skillGroups = meta.key === "skills" ? groupSkillsByCategory(data.skills) : [];

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Icon className="h-5 w-5" />
            </div>
            <div>
              <CardTitle>{meta.title}</CardTitle>
              <CardDescription className="mt-2 max-w-2xl">
                {meta.description}
              </CardDescription>
            </div>
          </div>
          <Button onClick={() => onAdd(meta.key)} size="sm" type="button">
            <Plus />
            Add
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {records.length === 0 ? (
          <EmptyState
            description={meta.emptyDescription}
            icon={meta.icon}
            onAdd={() => onAdd(meta.key)}
            title={meta.emptyTitle}
          />
        ) : null}

        {meta.key === "education"
          ? data.education.map((record) => (
              <EducationCard
                education={record}
                key={record.id}
                onDelete={() => onDelete(meta.key, record.id)}
                onEdit={() => onEdit(meta.key, record)}
              />
            ))
          : null}

        {meta.key === "experience"
          ? data.experience.map((record) => (
              <ExperienceCard
                experience={record}
                key={record.id}
                onDelete={() => onDelete(meta.key, record.id)}
                onEdit={() => onEdit(meta.key, record)}
              />
            ))
          : null}

        {meta.key === "projects"
          ? data.projects.map((record) => (
              <ProjectCard
                key={record.id}
                onDelete={() => onDelete(meta.key, record.id)}
                onEdit={() => onEdit(meta.key, record)}
                project={record}
              />
            ))
          : null}

        {meta.key === "skills"
          ? skillGroups.map((group) => (
              <SkillCategoryPanel
                group={group}
                key={group.category}
                onDelete={(skillId) => onDelete(meta.key, skillId)}
                onEdit={(skill) => onEdit(meta.key, skill)}
              />
            ))
          : null}
      </CardContent>
    </Card>
  );
}


function EducationFields({
  errors,
  setValue,
  values,
}: {
  errors: ValidationErrors;
  setValue: <TField extends keyof Omit<EducationProfile, "id">>(
    field: TField,
    value: Omit<EducationProfile, "id">[TField],
  ) => void;
  values: Omit<EducationProfile, "id">;
}) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <TextInput
        error={errors.institution}
        label="Institution"
        onChange={(value) => setValue("institution", value)}
        placeholder="University or school"
        required
        value={values.institution}
      />
      <TextInput
        label="Degree"
        onChange={(value) => setValue("degree", value)}
        placeholder="MS, BS, Certificate"
        value={values.degree}
      />
      <TextInput
        label="Field of study"
        onChange={(value) => setValue("fieldOfStudy", value)}
        placeholder="Computer Science"
        value={values.fieldOfStudy}
      />
      <TextInput
        label="Location"
        onChange={(value) => setValue("location", value)}
        placeholder="City, State"
        value={values.location}
      />
      <TextInput
        label="Start date"
        onChange={(value) => setValue("startDate", value)}
        placeholder="2020-08"
        value={values.startDate}
      />
      <TextInput
        label="End date"
        onChange={(value) => setValue("endDate", value)}
        placeholder="2022-05"
        value={values.endDate}
      />
      <TextInput
        label="GPA"
        onChange={(value) => setValue("gpa", value)}
        placeholder="3.8"
        value={values.gpa}
      />
      <div className="md:col-span-2">
        <TextArea
          label="Description"
          onChange={(value) => setValue("description", value)}
          placeholder="Coursework, honors, thesis, or academic context"
          value={values.description}
        />
      </div>
    </div>
  );
}


function ExperienceFields({
  errors,
  setValue,
  values,
}: {
  errors: ValidationErrors;
  setValue: <TField extends keyof Omit<ExperienceProfile, "id">>(
    field: TField,
    value: Omit<ExperienceProfile, "id">[TField],
  ) => void;
  values: Omit<ExperienceProfile, "id">;
}) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <TextInput
        error={errors.company}
        label="Company"
        onChange={(value) => setValue("company", value)}
        placeholder="Company name"
        required
        value={values.company}
      />
      <TextInput
        error={errors.role}
        label="Role"
        onChange={(value) => setValue("role", value)}
        placeholder="Job title"
        required
        value={values.role}
      />
      <TextInput
        label="Location"
        onChange={(value) => setValue("location", value)}
        placeholder="Remote or city"
        value={values.location}
      />
      <label className="flex items-end gap-3 rounded-md border bg-background p-3">
        <input
          checked={values.isCurrent}
          className="h-4 w-4"
          onChange={(event) => setValue("isCurrent", event.target.checked)}
          type="checkbox"
        />
        <span className="text-sm font-medium">Current role</span>
      </label>
      <TextInput
        label="Start date"
        onChange={(value) => setValue("startDate", value)}
        placeholder="2023-01"
        value={values.startDate}
      />
      <TextInput
        label="End date"
        onChange={(value) => setValue("endDate", value)}
        placeholder="Leave blank if current"
        value={values.endDate}
      />
      <div className="md:col-span-2">
        <ListEditor
          addLabel="Add tech"
          label="Tech stack"
          onChange={(value) => setValue("techStack", value)}
          placeholder="Python"
          values={values.techStack}
        />
      </div>
      <div className="md:col-span-2">
        <ListEditor
          addLabel="Add bullet"
          label="Bullets"
          onChange={(value) => setValue("bullets", value)}
          placeholder="Built and maintained..."
          values={values.bullets}
        />
      </div>
      <div className="md:col-span-2">
        <ListEditor
          addLabel="Add tag"
          label="Tags"
          onChange={(value) => setValue("tags", value)}
          placeholder="Technical"
          values={values.tags}
        />
      </div>
    </div>
  );
}


function ProjectFields({
  errors,
  setValue,
  values,
}: {
  errors: ValidationErrors;
  setValue: <TField extends keyof Omit<ProjectProfile, "id">>(
    field: TField,
    value: Omit<ProjectProfile, "id">[TField],
  ) => void;
  values: Omit<ProjectProfile, "id">;
}) {
  return (
    <div className="grid gap-4">
      <TextInput
        error={errors.name}
        label="Project name"
        onChange={(value) => setValue("name", value)}
        placeholder="Project name"
        required
        value={values.name}
      />
      <TextArea
        label="Description"
        onChange={(value) => setValue("description", value)}
        placeholder="What the project does and why it matters"
        value={values.description}
      />
      <ListEditor
        addLabel="Add tech"
        label="Tech stack"
        onChange={(value) => setValue("techStack", value)}
        placeholder="Next.js"
        values={values.techStack}
      />
      <ListEditor
        addLabel="Add bullet"
        label="Bullets"
        onChange={(value) => setValue("bullets", value)}
        placeholder="Designed..."
        values={values.bullets}
      />
      <ListEditor
        addLabel="Add link"
        label="Links"
        onChange={(value) => setValue("links", value)}
        placeholder="https://example.com"
        values={values.links}
      />
      <ListEditor
        addLabel="Add tag"
        label="Tags"
        onChange={(value) => setValue("tags", value)}
        placeholder="Portfolio"
        values={values.tags}
      />
    </div>
  );
}


function SkillFields({
  errors,
  setValue,
  values,
}: {
  errors: ValidationErrors;
  setValue: <TField extends keyof Omit<SkillProfile, "id">>(
    field: TField,
    value: Omit<SkillProfile, "id">[TField],
  ) => void;
  values: Omit<SkillProfile, "id">;
}) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <TextInput
        error={errors.category}
        label="Category"
        onChange={(value) => setValue("category", value)}
        placeholder="Frontend"
        required
        value={values.category}
      />
      <TextInput
        error={errors.name}
        label="Skill name"
        onChange={(value) => setValue("name", value)}
        placeholder="Next.js"
        required
        value={values.name}
      />
      <TextInput
        label="Proficiency"
        onChange={(value) => setValue("proficiency", value)}
        placeholder="Advanced"
        value={values.proficiency}
      />
      <div className="md:col-span-2">
        <ListEditor
          addLabel="Add tag"
          label="Tags"
          onChange={(value) => setValue("tags", value)}
          placeholder="React"
          values={values.tags}
        />
      </div>
    </div>
  );
}


function sanitizeValues<TValues extends Record<string, unknown>>(values: TValues): TValues {
  const sanitized = { ...values };
  for (const [key, value] of Object.entries(sanitized)) {
    if (Array.isArray(value)) {
      sanitized[key as keyof TValues] = value
        .map((item) => (typeof item === "string" ? item.trim() : item))
        .filter(Boolean) as TValues[keyof TValues];
    }
    if (typeof value === "string") {
      sanitized[key as keyof TValues] = value.trim() as TValues[keyof TValues];
    }
  }
  return sanitized;
}


function validate(section: ProfileSectionKey, values: ProfileFormValues[ProfileSectionKey]) {
  const errors: ValidationErrors = {};

  if (section === "education" && !("institution" in values && values.institution.trim())) {
    errors.institution = "Institution is required.";
  }
  if (section === "experience") {
    if (!("company" in values && values.company.trim())) {
      errors.company = "Company is required.";
    }
    if (!("role" in values && values.role.trim())) {
      errors.role = "Role is required.";
    }
  }
  if (section === "projects" && !("name" in values && values.name.trim())) {
    errors.name = "Project name is required.";
  }
  if (section === "skills") {
    if (!("category" in values && values.category.trim())) {
      errors.category = "Category is required.";
    }
    if (!("name" in values && values.name.trim())) {
      errors.name = "Skill name is required.";
    }
  }

  return errors;
}


function ProfileEditor({
  editor,
  onCancel,
  onSave,
}: {
  editor: EditorState;
  onCancel: () => void;
  onSave: (
    section: ProfileSectionKey,
    mode: EditorState["mode"],
    recordId: string | null,
    values: ProfileFormValues[ProfileSectionKey],
  ) => Promise<void>;
}) {
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [values, setValues] = useState<ProfileFormValues[ProfileSectionKey]>(() =>
    editor.record === null
      ? getEmptyFormValues(editor.section)
      : getRecordFormValues(editor.section, editor.record),
  );

  const meta = getSectionMeta(editor.section);

  function setField(field: string, value: unknown) {
    setValues((currentValues) => ({
      ...currentValues,
      [field]: value,
    }));
    setErrors((currentErrors) => ({ ...currentErrors, [field]: undefined }));
  }

  async function handleSave() {
    const nextErrors = validate(editor.section, values);
    setErrors(nextErrors);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    await onSave(
      editor.section,
      editor.mode,
      editor.record?.id ?? null,
      sanitizeValues(values),
    );
  }

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm">
      <button
        aria-label="Close profile editor"
        className="absolute inset-0 h-full w-full cursor-default"
        onClick={onCancel}
        type="button"
      />
      <aside className="absolute right-0 top-0 flex h-full w-full max-w-3xl flex-col border-l bg-card shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b p-6">
          <div>
            <Badge className="mb-3" variant="secondary">
              {editor.mode === "create" ? "Add" : "Edit"} {meta.title}
            </Badge>
            <h2 className="text-2xl font-semibold tracking-normal">
              {meta.title} details
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Keep this information factual and based on your own profile.
            </p>
          </div>
          <Button aria-label="Close editor" onClick={onCancel} size="icon" type="button" variant="outline">
            <X />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {editor.section === "education" ? (
            <EducationFields
              errors={errors}
              setValue={(field, value) => setField(field, value)}
              values={values as Omit<EducationProfile, "id">}
            />
          ) : null}

          {editor.section === "experience" ? (
            <ExperienceFields
              errors={errors}
              setValue={(field, value) => setField(field, value)}
              values={values as Omit<ExperienceProfile, "id">}
            />
          ) : null}

          {editor.section === "projects" ? (
            <ProjectFields
              errors={errors}
              setValue={(field, value) => setField(field, value)}
              values={values as Omit<ProjectProfile, "id">}
            />
          ) : null}

          {editor.section === "skills" ? (
            <SkillFields
              errors={errors}
              setValue={(field, value) => setField(field, value)}
              values={values as Omit<SkillProfile, "id">}
            />
          ) : null}
        </div>

        <div className="flex flex-col-reverse gap-3 border-t p-6 sm:flex-row sm:justify-end">
          <Button onClick={onCancel} type="button" variant="outline">
            Cancel
          </Button>
          <Button onClick={handleSave} type="button">
            <Save />
            Save
          </Button>
        </div>
      </aside>
    </div>
  );
}


export function ProfileManager() {
  const [data, setData] = useState<ProfileData>({
    education: [],
    experience: [],
    projects: [],
    skills: [],
  });
  const [editor, setEditor] = useState<EditorState | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadProfile() {
      try {
        const nextData = await profileApi.list();
        if (isMounted) {
          setData(nextData);
          setErrorMessage(null);
        }
      } catch (error) {
        if (isMounted) {
          setErrorMessage(getErrorMessage(error));
        }
      }
    }

    void loadProfile();

    return () => {
      isMounted = false;
    };
  }, []);

  const summary = useMemo(
    () => [
      {
        label: "Completed sections",
        value: `${Object.values(data).filter((items) => items.length > 0).length}/4`,
      },
      {
        label: "Profile entries",
        value: String(countFacts(data)),
      },
      {
        label: "Bullet points",
        value: String(
          data.experience.reduce((total, item) => total + item.bullets.length, 0) +
            data.projects.reduce((total, item) => total + item.bullets.length, 0),
        ),
      },
    ],
    [data],
  );

  function openCreate(section: ProfileSectionKey) {
    setEditor({ mode: "create", record: null, section });
  }

  function openEdit(section: ProfileSectionKey, record: ProfileRecord) {
    setEditor({ mode: "edit", record, section });
  }

  async function saveRecord(
    section: ProfileSectionKey,
    mode: EditorState["mode"],
    recordId: string | null,
    values: ProfileFormValues[ProfileSectionKey],
  ) {
    try {
      setErrorMessage(null);
      const nextData =
        mode === "create" || recordId === null
          ? await profileApi.create(section, values as never)
          : await profileApi.update(section, recordId, values as never);

      setData(nextData);
      setEditor(null);
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    }
  }

  async function deleteRecord(section: ProfileSectionKey, recordId: string) {
    try {
      setErrorMessage(null);
      const nextData = await profileApi.delete(section, recordId);
      setData(nextData);
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        action={
          <Button onClick={() => openCreate("experience")} type="button">
            <Plus />
            Add Experience
          </Button>
        }
        description="Manage education, work history, projects, and skills."
        eyebrow="Profile"
        title="Profile"
      />

      <section className="grid gap-4 md:grid-cols-3">
        {summary.map((item) => (
          <Card key={item.label}>
            <CardHeader className="pb-2">
              <CardDescription>{item.label}</CardDescription>
              <CardTitle className="text-3xl">{item.value}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </section>

      {errorMessage ? (
        <Card className="border-destructive/30 bg-destructive/5">
          <CardContent className="flex gap-3 p-5">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
            <div>
              <h2 className="font-semibold text-destructive">Profile data unavailable</h2>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                {errorMessage}
              </p>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <section className="space-y-4">
        {sectionMeta.map((meta) => (
          <SectionCard
            data={data}
            key={meta.key}
            meta={meta}
            onAdd={openCreate}
            onDelete={deleteRecord}
            onEdit={openEdit}
          />
        ))}
      </section>

      {editor ? (
        <ProfileEditor
          editor={editor}
          onCancel={() => setEditor(null)}
          onSave={saveRecord}
        />
      ) : null}
    </div>
  );
}
