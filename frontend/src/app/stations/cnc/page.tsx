"use client";

import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui";
import { ArrowLeft, Cpu } from "lucide-react";
import StationView from "@/components/production/StationView";

export default function CncStationPage() {
  return (
    <AppShell>
      <PageHeader
        eyebrow="Stanowisko Produkcyjne"
        title="Centrum CNC"
        subtitle="Wycinanie elementów z płyt i wiercenie otworów konstrukcyjnych."
        actions={
          <Button as="link" href="/stations" variant="secondary">
            <ArrowLeft className="w-4 h-4 mr-1" /> Powrót
          </Button>
        }
      />

      <div className="max-w-7xl mx-auto pb-20">
        <StationView 
          stationType="cnc" 
          stationName="CNC" 
          stationDescription="Zadania oznaczone jako GOTOWE trafiają do następnego etapu (Okleiniarka)."
          icon={Cpu}
        />
      </div>
    </AppShell>
  );
}
