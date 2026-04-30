"use client";

import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui";
import { ArrowLeft, Box } from "lucide-react";
import StationView from "@/components/production/StationView";

export default function PakowanieStationPage() {
  return (
    <AppShell>
      <PageHeader
        eyebrow="Stanowisko Produkcyjne"
        title="Pakowanie"
        subtitle="Zabezpieczanie produktów, pakowanie do wysyłki i wydawanie na magazyn gotowy."
        actions={
          <Button as="link" href="/stations" variant="secondary">
            <ArrowLeft className="w-4 h-4 mr-1" /> Powrót
          </Button>
        }
      />

      <div className="max-w-7xl mx-auto pb-20">
        <StationView 
          stationType="pakowanie" 
          stationName="Pakowanie" 
          stationDescription="Ostatni etap produkcji. Po zakończeniu projekt uznaje się za gotowy do wydania."
          icon={Box}
        />
      </div>
    </AppShell>
  );
}
