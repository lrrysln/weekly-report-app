import React, { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { Download } from "lucide-react";
import html2canvas from "html2canvas";
import jsPDF from "jspdf";

// Mock data (replace later with API / Azure / Google backend)
const sampleData = [
  { name: "Jan", cost: 4000, equipment: 2400 },
  { name: "Feb", cost: 3000, equipment: 1398 },
  { name: "Mar", cost: 2000, equipment: 9800 },
  { name: "Apr", cost: 2780, equipment: 3908 },
  { name: "May", cost: 1890, equipment: 4800 },
  { name: "Jun", cost: 2390, equipment: 3800 },
  { name: "Jul", cost: 3490, equipment: 4300 },
];

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042"];

export default function Dashboard() {
  const [filter, setFilter] = useState("All");

  const handleDownloadPDF = async () => {
    const element = document.getElementById("dashboard-report");
    if (!element) return;

    const canvas = await html2canvas(element, { scale: 2 });
    const imgData = canvas.toDataURL("image/png");
    const pdf = new jsPDF("p", "mm", "a4");
    const imgProps = pdf.getImageProperties(imgData);
    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = (imgProps.height * pdfWidth) / imgProps.width;

    pdf.addImage(imgData, "PNG", 0, 0, pdfWidth, pdfHeight);
    pdf.save("Construction_Report.pdf");
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Construction &amp; A&amp;D Dashboard</h1>
        <Button onClick={handleDownloadPDF} className="flex items-center gap-2">
          <Download size={16} /> Download PDF
        </Button>
      </div>

      {/* Dashboard Content */}
      <div id="dashboard-report" className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Costs Over Time */}
        <Card className="shadow-md">
          <CardContent>
            <h2 className="text-lg font-semibold mb-2">Costs Over Time</h2>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={sampleData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="cost" stroke="#8884d8" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Equipment Breakdown */}
        <Card className="shadow-md">
          <CardContent>
            <h2 className="text-lg font-semibold mb-2">Equipment Breakdown</h2>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={sampleData} dataKey="equipment" nameKey="name" cx="50%" cy="50%" outerRadius={80}>
                  {sampleData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Bar Chart */}
        <Card className="shadow-md md:col-span-2">
          <CardContent>
            <h2 className="text-lg font-semibold mb-2">Monthly Comparison</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={sampleData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="cost" fill="#82ca9d" />
                <Bar dataKey="equipment" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
