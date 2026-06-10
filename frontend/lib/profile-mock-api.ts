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


const STORAGE_KEY = "applywise-profile-mock-data";


const defaultProfileData: ProfileData = {
  education: [],
  experience: [
    {
      id: "experience-1",
      company: "ApplyWise Labs",
      role: "Product Engineer",
      location: "Remote",
      startDate: "2024-01",
      endDate: "",
      isCurrent: true,
      techStack: ["Next.js", "FastAPI", "PostgreSQL"],
      bullets: [
        "Designed typed profile data flows for resume intelligence workflows.",
        "Built maintainable API boundaries for user-owned career data.",
      ],
      tags: ["Full stack", "Product systems"],
    },
  ],
  projects: [
    {
      id: "project-1",
      name: "Resume Intelligence Profile",
      description:
        "A structured profile workspace for verified education, experience, projects, and skills.",
      techStack: ["TypeScript", "Tailwind", "FastAPI"],
      bullets: [
        "Modeled profile records as reusable sections for future tailoring workflows.",
        "Kept generated copy grounded in explicit user-provided facts.",
      ],
      links: ["https://example.com"],
      tags: ["Profile", "Resume data"],
    },
  ],
  skills: [
    {
      id: "skill-1",
      category: "Frontend",
      name: "Next.js",
      proficiency: "Advanced",
      tags: ["React", "App Router"],
    },
    {
      id: "skill-2",
      category: "Backend",
      name: "FastAPI",
      proficiency: "Intermediate",
      tags: ["Python", "APIs"],
    },
  ],
};


function cloneProfileData(data: ProfileData): ProfileData {
  return JSON.parse(JSON.stringify(data)) as ProfileData;
}


function getStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage;
}


function generateId(section: ProfileSectionKey) {
  return `${section}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}


function loadProfileData(): ProfileData {
  const storage = getStorage();
  if (storage === null) {
    return cloneProfileData(defaultProfileData);
  }

  const stored = storage.getItem(STORAGE_KEY);
  if (stored === null) {
    const initialData = cloneProfileData(defaultProfileData);
    storage.setItem(STORAGE_KEY, JSON.stringify(initialData));
    return initialData;
  }

  try {
    return JSON.parse(stored) as ProfileData;
  } catch {
    const initialData = cloneProfileData(defaultProfileData);
    storage.setItem(STORAGE_KEY, JSON.stringify(initialData));
    return initialData;
  }
}


function saveProfileData(data: ProfileData) {
  const storage = getStorage();
  if (storage !== null) {
    storage.setItem(STORAGE_KEY, JSON.stringify(data));
  }
}


export const profileMockApi = {
  async list(): Promise<ProfileData> {
    return loadProfileData();
  },

  async create<TRecord extends ProfileRecord>(
    section: ProfileSectionKey,
    values: Omit<TRecord, "id">,
  ): Promise<ProfileData> {
    const data = loadProfileData();
    const nextRecord = { id: generateId(section), ...values } as TRecord;
    const nextSection = [...data[section], nextRecord] as ProfileData[typeof section];
    const nextData = { ...data, [section]: nextSection };
    saveProfileData(nextData);
    return nextData;
  },

  async update<TRecord extends ProfileRecord>(
    section: ProfileSectionKey,
    recordId: string,
    values: Omit<TRecord, "id">,
  ): Promise<ProfileData> {
    const data = loadProfileData();
    const nextSection = data[section].map((record) =>
      record.id === recordId ? ({ id: recordId, ...values } as TRecord) : record,
    ) as ProfileData[typeof section];
    const nextData = { ...data, [section]: nextSection };
    saveProfileData(nextData);
    return nextData;
  },

  async delete(section: ProfileSectionKey, recordId: string): Promise<ProfileData> {
    const data = loadProfileData();
    const nextSection = data[section].filter((record) => record.id !== recordId) as
      | EducationProfile[]
      | ExperienceProfile[]
      | ProjectProfile[]
      | SkillProfile[];
    const nextData = { ...data, [section]: nextSection };
    saveProfileData(nextData);
    return nextData;
  },
};
