import type { ProfileData, ProfileSectionKey } from "@/lib/profile-api";


const profileSectionKeys: ProfileSectionKey[] = [
  "education",
  "experience",
  "projects",
  "skills",
];


export const profileSectionLabels: Record<ProfileSectionKey, string> = {
  education: "Education",
  experience: "Experience",
  projects: "Projects",
  skills: "Skills",
};


export type ProfileCompletion = {
  completedSections: number;
  missingSections: ProfileSectionKey[];
  percentage: number;
  totalSections: number;
};


export function getProfileCompletion(data: ProfileData): ProfileCompletion {
  const missingSections = profileSectionKeys.filter((section) => data[section].length === 0);
  const totalSections = profileSectionKeys.length;
  const completedSections = totalSections - missingSections.length;

  return {
    completedSections,
    missingSections,
    percentage: Math.round((completedSections / totalSections) * 100),
    totalSections,
  };
}
