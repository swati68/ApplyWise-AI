import Link from "next/link";
import { FileCode2 } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { ResumeWorkspace } from "@/components/resumes/resume-workspace";
import { Button } from "@/components/ui/button";


export default function ResumesPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        action={
          <Button asChild>
            <Link href="/resumes/templates">
              <FileCode2 />
              Manage Templates
            </Link>
          </Button>
        }
        description="Upload PDF resumes for review and manage LaTeX templates for resume generation."
        eyebrow="Resumes"
        title="Resume workspace"
      />

      <ResumeWorkspace />
    </div>
  );
}
