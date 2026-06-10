"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BriefcaseBusiness,
  ChevronDown,
  FileText,
  LayoutDashboard,
  LogOut,
  Search,
  Settings,
  UserRound,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useMemo, useRef, useState } from "react";

import { ThemeToggle } from "@/components/theme-toggle";
import type { AuthUser } from "@/lib/auth-api";
import { authApi } from "@/lib/auth-api";
import { getProfileCompletion } from "@/lib/profile-completion";
import type { ProfileCompletion } from "@/lib/profile-completion";
import {
  type ProfileData,
  profileApi,
  profileUpdatedEventName,
} from "@/lib/profile-api";
import { cn } from "@/lib/utils";


type NavigationItem = {
  exact?: boolean;
  href: string;
  label: string;
  icon: LucideIcon;
};


const navigationItems: NavigationItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/profile", label: "Profile", icon: UserRound },
  { href: "/jobs", label: "Search Jobs", icon: Search, exact: true },
  { href: "/jobs/summary", label: "Job Summary", icon: BriefcaseBusiness },
  { href: "/resumes", label: "Resumes", icon: FileText },
];


type AppShellProps = Readonly<{
  children: ReactNode;
  user: AuthUser;
}>;


const emptyProfileData: ProfileData = {
  education: [],
  experience: [],
  projects: [],
  skills: [],
};


function isActiveRoute(pathname: string, item: NavigationItem) {
  const { exact = false, href } = item;

  if (href === "/") {
    return pathname === "/";
  }
  if (exact) {
    return pathname === href;
  }

  return pathname === href || pathname.startsWith(`${href}/`);
}


function BrandMark() {
  return (
    <Link className="flex items-center gap-3" href="/dashboard">
      <div className="flex h-10 w-10 items-center justify-center rounded-md bg-slate-950 text-sm font-bold text-white shadow-sm dark:bg-white dark:text-slate-950">
        AW
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-foreground">
          ApplyWise AI
        </p>
        <p className="truncate text-xs text-muted-foreground">
          Job intelligence
        </p>
      </div>
    </Link>
  );
}


function SidebarNavigation({ pathname }: { pathname: string }) {
  return (
    <nav className="space-y-1">
      {navigationItems.map((item) => {
        const active = isActiveRoute(pathname, item);
        const Icon = item.icon;

        return (
          <Link
            className={cn(
              "flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
              active && "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground",
            )}
            href={item.href}
            key={item.href}
          >
            <Icon className="h-4 w-4" />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}


function MobileNavigation({ pathname }: { pathname: string }) {
  return (
    <div className="border-b bg-background/95 px-4 py-2 backdrop-blur lg:hidden">
      <nav className="flex gap-2 overflow-x-auto">
        {navigationItems.map((item) => {
          const active = isActiveRoute(pathname, item);
          const Icon = item.icon;

          return (
            <Link
              className={cn(
                "inline-flex h-9 shrink-0 items-center gap-2 rounded-md border px-3 text-sm font-medium text-muted-foreground transition-colors",
                active
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-card hover:bg-muted hover:text-foreground",
              )}
              href={item.href}
              key={item.href}
            >
              <Icon className="h-4 w-4" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}


function getUserInitials(user: AuthUser): string {
  const displayValue = user.full_name?.trim() || user.email;
  const nameParts = displayValue
    .split(/\s+/)
    .map((part) => part.trim())
    .filter(Boolean);

  if (nameParts.length >= 2) {
    return `${nameParts[0][0]}${nameParts[1][0]}`.toUpperCase();
  }

  return displayValue.slice(0, 2).toUpperCase();
}


function ProfileCompletionRing({
  completion,
}: {
  completion: ProfileCompletion;
}) {
  const degrees = completion.percentage * 3.6;

  return (
    <div
      className="flex items-center gap-2 rounded-full border bg-card px-2 py-1"
      title={`${completion.percentage}% profile complete`}
    >
      <div
        aria-label={`${completion.percentage}% profile complete`}
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full"
        role="img"
        style={{
          background: `conic-gradient(hsl(var(--primary)) ${degrees}deg, hsl(var(--muted)) ${degrees}deg)`,
        }}
      >
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-background text-[11px] font-semibold">
          {completion.percentage}%
        </div>
      </div>
      <div className="hidden pr-1 md:block">
        <p className="text-xs font-semibold leading-4">Profile</p>
        <p className="text-[11px] leading-4 text-muted-foreground">
          {completion.completedSections}/{completion.totalSections} sections
        </p>
      </div>
    </div>
  );
}


function UserAccountMenu({
  onLogout,
  user,
}: {
  onLogout: () => Promise<void>;
  user: AuthUser;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const displayName = user.full_name?.trim() || "ApplyWise user";
  const initials = getUserInitials(user);

  useEffect(() => {
    function closeOnOutsideClick(event: MouseEvent) {
      if (
        menuRef.current !== null &&
        event.target instanceof Node &&
        !menuRef.current.contains(event.target)
      ) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", closeOnOutsideClick);

    return () => {
      document.removeEventListener("mousedown", closeOnOutsideClick);
    };
  }, []);

  return (
    <div className="relative" ref={menuRef}>
      <button
        aria-expanded={isOpen}
        aria-haspopup="menu"
        className="flex h-10 items-center gap-2 rounded-full border bg-card pl-1 pr-2 text-sm font-medium transition hover:bg-muted"
        onClick={() => setIsOpen((currentValue) => !currentValue)}
        type="button"
      >
        <span className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-full bg-slate-950 text-xs font-semibold text-white dark:bg-white dark:text-slate-950">
          {initials}
        </span>
        <ChevronDown className="hidden h-4 w-4 text-muted-foreground sm:block" />
      </button>

      {isOpen ? (
        <div
          className="absolute right-0 top-full z-50 mt-2 w-72 overflow-hidden rounded-xl border bg-popover text-popover-foreground shadow-xl"
          role="menu"
        >
          <div className="border-b p-4">
            <p className="truncate text-sm font-semibold">{displayName}</p>
            <p className="mt-1 truncate text-xs text-muted-foreground">{user.email}</p>
          </div>
          <div className="p-2">
            <Link
              className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium hover:bg-muted"
              href="/profile"
              onClick={() => setIsOpen(false)}
              role="menuitem"
            >
              <UserRound className="h-4 w-4 text-muted-foreground" />
              Profile
            </Link>
            <Link
              className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium hover:bg-muted"
              href="/settings"
              onClick={() => setIsOpen(false)}
              role="menuitem"
            >
              <Settings className="h-4 w-4 text-muted-foreground" />
              Settings
            </Link>
          </div>
          <div className="border-t p-2">
            <button
              className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm font-medium text-destructive hover:bg-destructive/10"
              onClick={() => {
                setIsOpen(false);
                void onLogout();
              }}
              role="menuitem"
              type="button"
            >
              <LogOut className="h-4 w-4" />
              Log out
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}


export function AppShell({ children, user }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [profileData, setProfileData] = useState<ProfileData>(emptyProfileData);

  useEffect(() => {
    let isMounted = true;

    async function loadProfileCompletion() {
      try {
        const nextProfileData = await profileApi.list();
        if (isMounted) {
          setProfileData(nextProfileData);
        }
      } catch {
        if (isMounted) {
          setProfileData(emptyProfileData);
        }
      }
    }

    function handleProfileUpdated(event: Event) {
      if (event instanceof CustomEvent) {
        setProfileData(event.detail as ProfileData);
      }
    }

    void loadProfileCompletion();
    window.addEventListener(profileUpdatedEventName, handleProfileUpdated);

    return () => {
      isMounted = false;
      window.removeEventListener(profileUpdatedEventName, handleProfileUpdated);
    };
  }, []);

  const profileCompletion = useMemo(
    () => getProfileCompletion(profileData),
    [profileData],
  );

  async function handleLogout() {
    try {
      await authApi.logout();
    } finally {
      router.replace("/login");
      router.refresh();
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-72 border-r bg-card lg:flex lg:flex-col">
        <div className="flex h-16 items-center border-b px-6">
          <BrandMark />
        </div>

        <div className="flex flex-1 flex-col justify-between gap-6 overflow-y-auto px-4 py-5">
          <SidebarNavigation pathname={pathname} />
        </div>
      </aside>

      <div className="min-h-screen lg:pl-72">
        <header className="sticky top-0 z-30 border-b bg-background/90 backdrop-blur">
          <div className="flex h-16 items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
            <div className="lg:hidden">
              <BrandMark />
            </div>

            <div className="hidden flex-1 lg:block" />

            <div className="ml-auto flex items-center gap-3">
              <ProfileCompletionRing completion={profileCompletion} />
              <ThemeToggle />
              <UserAccountMenu onLogout={handleLogout} user={user} />
            </div>
          </div>

          <MobileNavigation pathname={pathname} />
        </header>

        <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}
