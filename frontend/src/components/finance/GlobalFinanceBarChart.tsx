"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

type ChartRow = {
  name: string;
  value: number;
  color: string;
};

type GlobalFinanceBarChartProps = {
  chartData: ChartRow[];
  loading: boolean;
};

export default function GlobalFinanceBarChart({
  chartData,
  loading,
}: GlobalFinanceBarChartProps) {
  return (
    <div className="h-[300px] w-full">
      {chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
            <XAxis dataKey="name" stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} />
            <YAxis
              stroke="#94a3b8"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              tickFormatter={(val) => `${val / 1000}k`}
            />
            <Tooltip
              contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #ffffff10", borderRadius: "12px" }}
              itemStyle={{ color: "#fff", fontSize: "12px", fontWeight: "bold" }}
            />
            <Bar dataKey="value" radius={[8, 8, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} fillOpacity={0.8} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <div className="h-full w-full flex items-center justify-center text-slate-500 text-xs">
          {loading ? "adowanie danych..." : "Brak danych do wyswietlenia"}
        </div>
      )}
    </div>
  );
}
