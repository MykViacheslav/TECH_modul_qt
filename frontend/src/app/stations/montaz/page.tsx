"use client";

import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui";
import { ArrowLeft, Hammer } from "lucide-react";
import StationView from "@/components/production/StationView";

export default function MontazStationPage() {
  return (
    <AppShell>
      <PageHeader
        eyebrow="Stanowisko Produkcyjne"
        title="Montaż"
        subtitle="Składanie korpusów, montaż okuć i sprawdzanie kompletności zestawów."
        actions={
          <Button as="link" href="/stations" variant="secondary">
            <ArrowLeft className="w-4 h-4 mr-1" /> Powrót
          </Button>
        }
      />

      <div className="max-w-7xl mx-auto pb-20">
        <StationView 
          stationType="montaz" 
          stationName="Montaż" 
          stationDescription="Zadania stają się READY po zakończeniu wszystkich etapów obróbki (CNC, Oklejanie, Lakiernia)."
          icon={Hammer}
        />
      </div>
    </AppShell>
  );
}
