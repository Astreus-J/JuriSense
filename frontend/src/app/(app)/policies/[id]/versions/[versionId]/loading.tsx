import { PageSkeleton, Skeleton } from "@/components/ui/Skeleton";

export default function Loading() {
  return (
    <PageSkeleton>
      <div role="status" className="space-y-6">
        <span className="sr-only">Loading…</span>
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-32 w-full" />
      </div>
    </PageSkeleton>
  );
}
