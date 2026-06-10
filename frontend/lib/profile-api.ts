import { request } from "@/lib/api-client";


export type ProfileSectionKey = "education" | "experience" | "projects" | "skills";


export type EducationProfile = {
  id: string;
  institution: string;
  degree: string;
  fieldOfStudy: string;
  startDate: string;
  endDate: string;
  gpa: string;
  location: string;
  description: string;
};


export type ExperienceProfile = {
  id: string;
  company: string;
  role: string;
  location: string;
  startDate: string;
  endDate: string;
  isCurrent: boolean;
  techStack: string[];
  bullets: string[];
  tags: string[];
};


export type ProjectProfile = {
  id: string;
  name: string;
  description: string;
  techStack: string[];
  bullets: string[];
  links: string[];
  tags: string[];
};


export type SkillProfile = {
  id: string;
  category: string;
  name: string;
  proficiency: string;
  tags: string[];
};


export type ProfileData = {
  education: EducationProfile[];
  experience: ExperienceProfile[];
  projects: ProjectProfile[];
  skills: SkillProfile[];
};


export type ProfileRecord =
  | EducationProfile
  | ExperienceProfile
  | ProjectProfile
  | SkillProfile;


type ProfileRecordValues =
  | Omit<EducationProfile, "id">
  | Omit<ExperienceProfile, "id">
  | Omit<ProjectProfile, "id">
  | Omit<SkillProfile, "id">;


type EducationApiRecord = {
  id: string;
  user_id: string;
  institution: string;
  degree: string | null;
  field_of_study: string | null;
  start_date: string | null;
  end_date: string | null;
  gpa: number | null;
  location: string | null;
  description: string | null;
};


type ExperienceApiRecord = {
  id: string;
  user_id: string;
  company: string;
  role: string;
  location: string | null;
  start_date: string | null;
  end_date: string | null;
  is_current: boolean;
  tech_stack: string[];
  bullets: string[];
  tags: string[];
};


type ProjectApiRecord = {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  tech_stack: string[];
  bullets: string[];
  links: string[];
  tags: string[];
};


type SkillApiRecord = {
  id: string;
  user_id: string;
  category: string;
  name: string;
  proficiency: string | null;
  tags: string[];
};


const endpointBySection: Record<ProfileSectionKey, string> = {
  education: "/profile/education",
  experience: "/profile/experience",
  projects: "/profile/projects",
  skills: "/profile/skills",
};


export const profileUpdatedEventName = "applywise:profile-updated";


function notifyProfileUpdated(data: ProfileData) {
  if (typeof window !== "undefined") {
    window.dispatchEvent(
      new CustomEvent<ProfileData>(profileUpdatedEventName, { detail: data }),
    );
  }
}


function optionalString(value: string | null | undefined): string {
  return value ?? "";
}


function optionalApiString(value: string): string | null {
  const cleanedValue = value.trim();
  return cleanedValue === "" ? null : cleanedValue;
}


function listForApi(values: string[]): string[] {
  return values.map((value) => value.trim()).filter(Boolean);
}


function dateForProfile(value: string | null): string {
  if (value === null) {
    return "";
  }

  return /^\d{4}-\d{2}-\d{2}$/.test(value) ? value.slice(0, 7) : value;
}


function dateForApi(value: string): string | null {
  const cleanedValue = value.trim();
  if (cleanedValue === "") {
    return null;
  }
  if (/^\d{4}$/.test(cleanedValue)) {
    return `${cleanedValue}-01-01`;
  }
  if (/^\d{4}-\d{2}$/.test(cleanedValue)) {
    return `${cleanedValue}-01`;
  }

  return cleanedValue;
}


function gpaForApi(value: string): number | null {
  const cleanedValue = value.trim();
  if (cleanedValue === "") {
    return null;
  }

  const parsedValue = Number(cleanedValue);
  return Number.isFinite(parsedValue) ? parsedValue : null;
}


function toEducationProfile(record: EducationApiRecord): EducationProfile {
  return {
    id: record.id,
    institution: record.institution,
    degree: optionalString(record.degree),
    fieldOfStudy: optionalString(record.field_of_study),
    startDate: dateForProfile(record.start_date),
    endDate: dateForProfile(record.end_date),
    gpa: record.gpa === null ? "" : String(record.gpa),
    location: optionalString(record.location),
    description: optionalString(record.description),
  };
}


function toExperienceProfile(record: ExperienceApiRecord): ExperienceProfile {
  return {
    id: record.id,
    company: record.company,
    role: record.role,
    location: optionalString(record.location),
    startDate: dateForProfile(record.start_date),
    endDate: dateForProfile(record.end_date),
    isCurrent: record.is_current,
    techStack: record.tech_stack,
    bullets: record.bullets,
    tags: record.tags,
  };
}


function toProjectProfile(record: ProjectApiRecord): ProjectProfile {
  return {
    id: record.id,
    name: record.name,
    description: optionalString(record.description),
    techStack: record.tech_stack,
    bullets: record.bullets,
    links: record.links,
    tags: record.tags,
  };
}


function toSkillProfile(record: SkillApiRecord): SkillProfile {
  return {
    id: record.id,
    category: record.category,
    name: record.name,
    proficiency: optionalString(record.proficiency),
    tags: record.tags,
  };
}


type ProfileApiPayload =
  | Omit<EducationApiRecord, "id" | "user_id">
  | Omit<ExperienceApiRecord, "id" | "user_id">
  | Omit<ProjectApiRecord, "id" | "user_id">
  | Omit<SkillApiRecord, "id" | "user_id">;


function toApiPayload(
  section: ProfileSectionKey,
  values: ProfileRecordValues,
): ProfileApiPayload {
  if (section === "education") {
    const education = values as Omit<EducationProfile, "id">;
    return {
      institution: education.institution,
      degree: optionalApiString(education.degree),
      field_of_study: optionalApiString(education.fieldOfStudy),
      start_date: dateForApi(education.startDate),
      end_date: dateForApi(education.endDate),
      gpa: gpaForApi(education.gpa),
      location: optionalApiString(education.location),
      description: optionalApiString(education.description),
    };
  }

  if (section === "experience") {
    const experience = values as Omit<ExperienceProfile, "id">;
    return {
      company: experience.company,
      role: experience.role,
      location: optionalApiString(experience.location),
      start_date: dateForApi(experience.startDate),
      end_date: dateForApi(experience.endDate),
      is_current: experience.isCurrent,
      tech_stack: listForApi(experience.techStack),
      bullets: listForApi(experience.bullets),
      tags: listForApi(experience.tags),
    };
  }

  if (section === "projects") {
    const project = values as Omit<ProjectProfile, "id">;
    return {
      name: project.name,
      description: optionalApiString(project.description),
      tech_stack: listForApi(project.techStack),
      bullets: listForApi(project.bullets),
      links: listForApi(project.links),
      tags: listForApi(project.tags),
    };
  }

  const skill = values as Omit<SkillProfile, "id">;
  return {
    category: skill.category,
    name: skill.name,
    proficiency: optionalApiString(skill.proficiency),
    tags: listForApi(skill.tags),
  };
}


export const profileApi = {
  async list(): Promise<ProfileData> {
    const [education, experience, projects, skills] = await Promise.all([
      request<EducationApiRecord[]>(endpointBySection.education),
      request<ExperienceApiRecord[]>(endpointBySection.experience),
      request<ProjectApiRecord[]>(endpointBySection.projects),
      request<SkillApiRecord[]>(endpointBySection.skills),
    ]);

    return {
      education: education.map(toEducationProfile),
      experience: experience.map(toExperienceProfile),
      projects: projects.map(toProjectProfile),
      skills: skills.map(toSkillProfile),
    };
  },

  async create(
    section: ProfileSectionKey,
    values: ProfileRecordValues,
  ): Promise<ProfileData> {
    await request(endpointBySection[section], {
      body: JSON.stringify(toApiPayload(section, values)),
      method: "POST",
    });

    const nextProfileData = await this.list();
    notifyProfileUpdated(nextProfileData);
    return nextProfileData;
  },

  async update(
    section: ProfileSectionKey,
    recordId: string,
    values: ProfileRecordValues,
  ): Promise<ProfileData> {
    await request(`${endpointBySection[section]}/${recordId}`, {
      body: JSON.stringify(toApiPayload(section, values)),
      method: "PUT",
    });

    const nextProfileData = await this.list();
    notifyProfileUpdated(nextProfileData);
    return nextProfileData;
  },

  async delete(section: ProfileSectionKey, recordId: string): Promise<ProfileData> {
    await request(`${endpointBySection[section]}/${recordId}`, {
      method: "DELETE",
    });

    const nextProfileData = await this.list();
    notifyProfileUpdated(nextProfileData);
    return nextProfileData;
  },
};
