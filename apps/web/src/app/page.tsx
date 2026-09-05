import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-dvh max-w-3xl flex-col justify-center px-6 py-16">
      <p className="text-sm text-ink-2">Phase 0 build</p>
      <h1 className="reading mt-2 text-4xl leading-tight text-ink">
        Answer questions, and see what the system has and has not learned about your
        understanding.
      </h1>
      <p className="mt-6 max-w-[52ch] text-ink-2">
        Every response is recorded with the reasoning behind it. Nothing is scored yet in
        this build, and the system will tell you when it does not have enough evidence to
        say anything.
      </p>
      <div className="mt-10 flex gap-3">
        <Link
          href="/login"
          className="rounded-sm px-5 py-2.5 text-sm font-medium text-white"
          style={{ background: "var(--observed)" }}
        >
          Sign in
        </Link>
        <Link
          href="/courses"
          className="rounded-sm border px-5 py-2.5 text-sm font-medium text-ink"
          style={{ borderColor: "var(--rule)" }}
        >
          Browse courses
        </Link>
      </div>
    </main>
  );
}
