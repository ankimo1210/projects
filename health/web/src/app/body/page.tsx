import { DashboardPage } from "@/components/dashboard-pages";
import { HealthPlanetPanel } from "@/components/healthplanet-panel";
export const metadata = { title: "身体" };
export default function Page() {
  return (
    <div className="space-y-8">
      <section aria-label="Health Planet の観測記録">
        <HealthPlanetPanel />
      </section>
      <section aria-label="Google のその他の身体データ">
        <h2 className="mb-4 text-base font-medium">Google · その他の身体データ</h2>
        <DashboardPage page="body" />
      </section>
    </div>
  );
}
