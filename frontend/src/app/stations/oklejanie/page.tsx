"use client";

import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui";
import { ArrowLeft, Layers } from "lucide-react";
import StationView from "@/components/production/StationView";

export default function OklejanieStationPage() {
  return (
    <AppShell>
      <PageHeader
        eyebrow="Stanowisko Produkcyjne"
        title="Okleiniarka"
        subtitle="Oklejanie krawędzi formatek obrzeżem ABS/PCV."
        actions={
          <Button as="link" href="/stations" variant="secondary">
            <ArrowLeft className="w-4 h-4 mr-1" /> Powrót
          </Button>
        }
      />

      <div className="max-w-7xl mx-auto pb-20">
        <StationView 
          stationType="oklejanie" 
          stationName="Okleiniarka" 
          stationDescription="Zadania stają się READY dopiero po zakończeniu etapu CNC."
          icon={Layers}
        />
      </div>
    </AppShell>
  );
}
