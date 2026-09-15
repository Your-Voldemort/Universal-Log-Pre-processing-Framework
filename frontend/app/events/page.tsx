import { Suspense } from "react";
import SearchTable from "@/components/SearchTable";

export const metadata = { title: "Events" };

export default function EventsPage() {
  return (
    <Suspense>
      <SearchTable />
    </Suspense>
  );
}
