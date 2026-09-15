import { Suspense } from "react";
import ComplianceReport from "@/components/ComplianceReport";

export const metadata = { title: "Incident reports" };

export default function ReportsPage() {
  return (
    <Suspense>
      <ComplianceReport />
    </Suspense>
  );
}
