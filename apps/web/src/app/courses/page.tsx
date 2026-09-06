"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { type Course, api, ensureSession } from "@/lib/api";

export default function CoursesPage() {
  const router = useRouter();
  const [courses, setCourses] = useState<Course[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      if (!(await ensureSession())) {
        router.push("/login");
        return;
      }
      try {
        const list = await api.courses();
        if (!cancelled) setCourses(list);
      } catch {
        if (!cancelled) setError("Your courses could not be loaded. Try again in a moment.");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [router]);

  async function begin(courseId: string) {
    try {
      const session = await api.startSession(courseId);
      router.push(`/session/${session.id}`);
    } catch {
      setError("The session could not be started. Try again in a moment.");
    }
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <h1 className="reading text-2xl">Your courses</h1>

      {courses === null && !error && <p className="mt-6 text-sm text-ink-2">Loading.</p>}

      {courses?.length === 0 && (
        <p className="mt-6 max-w-[52ch] text-ink-2">
          You are not enrolled in anything yet. Ask your instructor for an enrolment link.
        </p>
      )}

      <ul className="mt-8">
        {courses?.map((course) => (
          <li key={course.id} className="border-t py-5" style={{ borderColor: "var(--rule)" }}>
            <h2 className="text-base font-medium">{course.title}</h2>
            {course.description && (
              <p className="mt-1 max-w-[56ch] text-sm text-ink-2">{course.description}</p>
            )}
            <button
              onClick={() => begin(course.id)}
              className="mt-3 text-sm font-medium"
              style={{ color: "var(--observed)" }}
            >
              Start a session
            </button>
          </li>
        ))}
      </ul>

      {error && (
        <p role="alert" className="mt-6 text-sm" style={{ color: "var(--attention)" }}>
          {error}
        </p>
      )}
    </main>
  );
}
