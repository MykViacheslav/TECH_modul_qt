"use client";

import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui";
import { ArrowLeft, Droplets } from "lucide-react";
import StationView from "@/components/production/StationView";

export default function LakierniaStationPage() {
  return (
    <AppShell>
      <PageHeader
        eyebrow="Stanowisko Produkcyjne"
        title="Lakiernia"
        subtitle="Przygotowanie powierzchni i lakierowanie frontów oraz elementów ozdobnych."
        actions={
          <Button as="link" href="/stations" variant="secondary">
            <ArrowLeft className="w-4 h-4 mr-1" /> Powrót
          </Button>
        }
      />

      <div className="max-w-7xl mx-auto pb-20">
        <StationView 
          stationType="lakiernia" 
          stationName="Lakiernia" 
          stationDescription="Zadania stają się READY po zakończeniu Oklejania (lub CNC jeśli brak oklejania)."
          icon={Droplets}
        />
      </div>
    </AppShell>
  );
}
