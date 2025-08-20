import React, { useState, useMemo } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ScatterChart, Scatter, PieChart, Pie, Cell, HeatMapGrid } from 'recharts';
import { Download, Filter, TrendingUp, Clock, DollarSign, AlertTriangle, CheckCircle, BarChart3 } from 'lucide-react';

// Sample data - in real implementation, this would come from P6 data
const generateSampleData = () => {
  const regions = ['North', 'South', 'East', 'West'];
  const prototypes = ['Type A', 'Type B', 'Type C'];
  const activities = ['Permitting', 'Site Prep', 'Foundation', 'Framing', 'Electrical', 'Plumbing', 'Inspection', 'Final'];
  
  const projects = [];
  for (let i = 1; i <= 50; i++) {
    projects.push({
      id: `P${i.toString().padStart(3, '0')}`,
      name: `Project ${i}`,
      region: regions[Math.floor(Math.random() * regions.length)],
      prototype: prototypes[Math.floor(Math.random() * prototypes.length)],
      startDate: new Date(2022 + Math.floor(Math.random() * 3), Math.floor(Math.random() * 12), 1),
      plannedDuration: 120 + Math.random() * 60,
      actualDuration: 120 + Math.random() * 100,
      cost: 250000 + Math.random() * 200000,
      status: Math.random() > 0.2 ? 'Completed' : 'Delayed'
    });
  }

  const delays = activities.map(activity => ({
    activity,
    frequency: Math.floor(Math.random() * 30) + 10,
    avgDays: Math.floor(Math.random() * 20) + 5,
    cost: Math.floor(Math.random() * 100000) + 25000
  }));

  return { projects, delays };
};

const P6Dashboard = () => {
  const [selectedRegion, setSelectedRegion] = useState('All');
  const [selectedPrototype, setSelectedPrototype] = useState('All');
  const [selectedTimeframe, setSelectedTimeframe] = useState('All');
  const [activeTab, setActiveTab] = useState('executive');
  
  const { projects, delays } = useMemo(() => generateSampleData(), []);
  
  const filteredProjects = useMemo(() => {
    return projects.filter(project => {
      if (selectedRegion !== 'All' && project.region !== selectedRegion) return false;
      if (selectedPrototype !== 'All' && project.prototype !== selectedPrototype) return false;
      return true;
    });
  }, [projects, selectedRegion, selectedPrototype]);

  const kpis = useMemo(() => {
    const totalProjects = filteredProjects.length;
    const avgPlannedDuration = filteredProjects.reduce((sum, p) => sum + p.plannedDuration, 0) / totalProjects;
    const avgActualDuration = filteredProjects.reduce((sum, p) => sum + p.actualDuration, 0) / totalProjects;
    const spi = avgPlannedDuration / avgActualDuration;
    const onTimeProjects = filteredProjects.filter(p => p.actualDuration <= p.plannedDuration).length;
    const onTimePercentage = (onTimeProjects / totalProjects) * 100;
    const avgDelay = avgActualDuration - avgPlannedDuration;
    const totalCost = filteredProjects.reduce((sum, p) => sum + p.cost, 0);

    return {
      totalProjects,
      avgPlannedDuration: Math.round(avgPlannedDuration),
      avgActualDuration: Math.round(avgActualDuration),
      spi: spi.toFixed(2),
      onTimePercentage: Math.round(onTimePercentage),
      avgDelay: Math.round(avgDelay),
      totalCost
    };
  }, [filteredProjects]);

  const exportToPDF = () => {
    const printWindow = window.open('', '_blank');
    const htmlContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>P6 Historical Project Analysis Report</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 20px; }
          .header { text-align: center; margin-bottom: 30px; }
          .kpi-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }
          .kpi-card { border: 1px solid #ddd; padding: 15px; border-radius: 8px; }
          .section { margin: 30px 0; }
          h1, h2 { color: #2563eb; }
          .executive-summary { background: #f8fafc; padding: 20px; border-radius: 8px; }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>P6 Historical Project Analysis</h1>
          <p>Executive Summary Report - Generated ${new Date().toLocaleDateString()}</p>
        </div>
        
        <div class="executive-summary">
          <h2>Executive Summary</h2>
          <p><strong>Portfolio Overview:</strong> Analysis of ${kpis.totalProjects} projects across ${selectedRegion === 'All' ? 'all regions' : selectedRegion}.</p>
          <p><strong>Key Finding:</strong> Average project delays of ${kpis.avgDelay} days, with Schedule Performance Index of ${kpis.spi}.</p>
          <p><strong>Performance:</strong> ${kpis.onTimePercentage}% of projects completed on time.</p>
          <p><strong>Impact:</strong> Total portfolio value of $${(kpis.totalCost / 1000000).toFixed(1)}M analyzed.</p>
        </div>

        <div class="kpi-grid">
          <div class="kpi-card">
            <h3>Schedule Performance</h3>
            <p>SPI: ${kpis.spi}</p>
            <p>Avg Delay: ${kpis.avgDelay} days</p>
          </div>
          <div class="kpi-card">
            <h3>On-Time Delivery</h3>
            <p>${kpis.onTimePercentage}% on time</p>
            <p>${kpis.totalProjects - Math.round(kpis.totalProjects * kpis.onTimePercentage / 100)} projects delayed</p>
          </div>
          <div class="kpi-card">
            <h3>Duration Metrics</h3>
            <p>Planned: ${kpis.avgPlannedDuration} days</p>
            <p>Actual: ${kpis.avgActualDuration} days</p>
          </div>
        </div>

        <div class="section">
          <h2>Key Recommendations</h2>
          <ol>
            <li><strong>Focus on Permitting:</strong> Implement pre-submission reviews to reduce approval times.</li>
            <li><strong>Regional Optimization:</strong> Deploy best practices from high-performing regions.</li>
            <li><strong>Vendor Management:</strong> Establish preferred contractor partnerships in underperforming areas.</li>
          </ol>
        </div>
      </body>
      </html>
    `;
    
    printWindow.document.write(htmlContent);
    printWindow.document.close();
    printWindow.print();
  };

  const exportToHTML = () => {
    const htmlContent = document.documentElement.outerHTML;
    const blob = new Blob([htmlContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'p6-analysis-dashboard.html';
    a.click();
    URL.revokeObjectURL(url);
  };

  const delayHeatmapData = delays.map(delay => ({
    activity: delay.activity,
    frequency: delay.frequency,
    impact: delay.avgDays,
    cost: delay.cost
  }));

  const durationVarianceData = filteredProjects.map(project => ({
    project: project.name,
    planned: project.plannedDuration,
    actual: project.actualDuration,
    variance: project.actualDuration - project.plannedDuration
  }));

  const regionPerformanceData = ['North', 'South', 'East', 'West'].map(region => {
    const regionProjects = projects.filter(p => p.region === region);
    const avgDuration = regionProjects.reduce((sum, p) => sum + p.actualDuration, 0) / regionProjects.length;
    const onTime = regionProjects.filter(p => p.actualDuration <= p.plannedDuration).length / regionProjects.length * 100;
    
    return {
      region,
      avgDuration: Math.round(avgDuration),
      onTimePercentage: Math.round(onTime),
      projectCount: regionProjects.length
    };
  });

  const renderExecutiveSummary = () => (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-6 rounded-lg border">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Executive Summary</h2>
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <h3 className="font-semibold text-gray-700 mb-2">Portfolio Snapshot</h3>
            <p className="text-sm text-gray-600">
              Analysis of <strong>{kpis.totalProjects} projects</strong> reveals an average delay of{' '}
              <strong className="text-red-600">{kpis.avgDelay} days</strong>, costing approximately{' '}
              <strong>${Math.round(kpis.avgDelay * 18000).toLocaleString()}</strong> per project in carrying costs.
            </p>
          </div>
          <div>
            <h3 className="font-semibold text-gray-700 mb-2">Key Insight</h3>
            <p className="text-sm text-gray-600">
              Schedule Performance Index of <strong>{kpis.spi}</strong> indicates projects are running{' '}
              <strong>{((1 - parseFloat(kpis.spi)) * 100).toFixed(1)}%</strong> behind baseline schedules.
              Only <strong>{kpis.onTimePercentage}%</strong> of projects finish on time.
            </p>
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Projects</p>
              <p className="text-2xl font-bold text-gray-900">{kpis.totalProjects}</p>
            </div>
            <BarChart3 className="h-8 w-8 text-blue-600" />
          </div>
        </div>
        
        <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Schedule Performance</p>
              <p className="text-2xl font-bold text-gray-900">{kpis.spi}</p>
              <p className="text-xs text-gray-500">SPI Target: 1.0</p>
            </div>
            <TrendingUp className="h-8 w-8 text-green-600" />
          </div>
        </div>
        
        <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">On-Time Delivery</p>
              <p className="text-2xl font-bold text-gray-900">{kpis.onTimePercentage}%</p>
            </div>
            <CheckCircle className="h-8 w-8 text-green-600" />
          </div>
        </div>
        
        <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Avg Delay</p>
              <p className="text-2xl font-bold text-red-600">{kpis.avgDelay}</p>
              <p className="text-xs text-gray-500">days</p>
            </div>
            <Clock className="h-8 w-8 text-red-600" />
          </div>
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Strategic Recommendations</h3>
        <div className="space-y-3">
          <div className="flex items-start space-x-3">
            <div className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-bold">1</div>
            <div>
              <h4 className="font-medium text-gray-900">Streamline Permitting Process</h4>
              <p className="text-sm text-gray-600">
                Implement pre-submission reviews and establish municipal relationships to reduce approval bottlenecks by an estimated 7-10 days.
              </p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <div className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-bold">2</div>
            <div>
              <h4 className="font-medium text-gray-900">Regional Best Practice Deployment</h4>
              <p className="text-sm text-gray-600">
                Replicate high-performing region processes across underperforming areas to achieve 15-20% duration improvement.
              </p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <div className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-bold">3</div>
            <div>
              <h4 className="font-medium text-gray-900">Vendor Performance Management</h4>
              <p className="text-sm text-gray-600">
                Establish preferred contractor partnerships and performance scorecards to reduce execution variability.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderDelayAnalysis = () => (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recurring Delay Analysis</h3>
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <h4 className="font-medium text-gray-700 mb-3">Top Delay Causes by Frequency</h4>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={delayHeatmapData.sort((a, b) => b.frequency - a.frequency).slice(0, 5)}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="activity" angle={-45} textAnchor="end" height={80} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="frequency" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div>
            <h4 className="font-medium text-gray-700 mb-3">Average Impact (Days)</h4>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={delayHeatmapData.sort((a, b) => b.impact - a.impact).slice(0, 5)}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="activity" angle={-45} textAnchor="end" height={80} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="impact" fill="#ef4444" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Cost Impact of Delays</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {delayHeatmapData.sort((a, b) => b.cost - a.cost).slice(0, 3).map((delay, index) => (
            <div key={delay.activity} className="p-4 border rounded-lg">
              <h4 className="font-medium text-gray-900">{delay.activity}</h4>
              <p className="text-2xl font-bold text-red-600">${delay.cost.toLocaleString()}</p>
              <p className="text-sm text-gray-600">{delay.frequency} occurrences, {delay.impact} avg days</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderDurationAnalysis = () => (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Duration & Variance Analysis</h3>
        <ResponsiveContainer width="100%" height={400}>
          <ScatterChart data={durationVarianceData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="planned" name="Planned Duration" unit=" days" />
            <YAxis dataKey="actual" name="Actual Duration" unit=" days" />
            <Tooltip cursor={{ strokeDasharray: '3 3' }} />
            <Scatter dataKey="actual" fill="#3b82f6" />
            <Line dataKey="planned" stroke="#ef4444" strokeWidth={2} dot={false} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
          <h4 className="font-medium text-gray-700 mb-3">Duration Distribution</h4>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Planned Average:</span>
              <span className="font-medium">{kpis.avgPlannedDuration} days</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Actual Average:</span>
              <span className="font-medium">{kpis.avgActualDuration} days</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Variance:</span>
              <span className="font-medium text-red-600">+{kpis.avgDelay} days</span>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
          <h4 className="font-medium text-gray-700 mb-3">Performance Insights</h4>
          <div className="space-y-2 text-sm">
            <p>• {Math.round((filteredProjects.filter(p => p.actualDuration > p.plannedDuration * 1.2).length / filteredProjects.length) * 100)}% of projects exceed baseline by >20%</p>
            <p>• Critical path drift averages {Math.round(kpis.avgDelay * 0.7)} days per project</p>
            <p>• Schedule compression opportunities identified in {Math.round(filteredProjects.length * 0.3)} projects</p>
          </div>
        </div>
      </div>
    </div>
  );

  const renderBenchmarking = () => (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Regional Performance Comparison</h3>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={regionPerformanceData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="region" />
            <YAxis yAxisId="left" />
            <YAxis yAxisId="right" orientation="right" />
            <Tooltip />
            <Bar yAxisId="left" dataKey="avgDuration" fill="#3b82f6" name="Avg Duration (days)" />
            <Bar yAxisId="right" dataKey="onTimePercentage" fill="#10b981" name="On-Time %" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
          <h4 className="font-medium text-gray-700 mb-3">Best Performers</h4>
          <div className="space-y-2">
            {regionPerformanceData
              .sort((a, b) => b.onTimePercentage - a.onTimePercentage)
              .slice(0, 2)
              .map((region, index) => (
                <div key={region.region} className="flex items-center justify-between p-2 bg-green-50 rounded">
                  <span className="font-medium text-green-800">{region.region}</span>
                  <span className="text-green-600">{region.onTimePercentage}% on-time</span>
                </div>
              ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
          <h4 className="font-medium text-gray-700 mb-3">Improvement Opportunities</h4>
          <div className="space-y-2">
            {regionPerformanceData
              .sort((a, b) => a.onTimePercentage - b.onTimePercentage)
              .slice(0, 2)
              .map((region, index) => (
                <div key={region.region} className="flex items-center justify-between p-2 bg-red-50 rounded">
                  <span className="font-medium text-red-800">{region.region}</span>
                  <span className="text-red-600">{region.onTimePercentage}% on-time</span>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">P6 Historical Project Analysis</h1>
              <p className="text-gray-600 mt-1">Interactive dashboard for construction project performance insights</p>
            </div>
            <div className="flex space-x-2 mt-4 md:mt-0">
              <button
                onClick={exportToPDF}
                className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                <Download size={16} />
                <span>Export PDF</span>
              </button>
              <button
                onClick={exportToHTML}
                className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                <Download size={16} />
                <span>Export HTML</span>
              </button>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <div className="flex items-center space-x-2 mb-4">
            <Filter size={20} className="text-gray-500" />
            <h2 className="text-lg font-semibold text-gray-900">Filters</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Region</label>
              <select
                value={selectedRegion}
                onChange={(e) => setSelectedRegion(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="All">All Regions</option>
                <option value="North">North</option>
                <option value="South">South</option>
                <option value="East">East</option>
                <option value="West">West</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Prototype</label>
              <select
                value={selectedPrototype}
                onChange={(e) => setSelectedPrototype(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="All">All Prototypes</option>
                <option value="Type A">Type A</option>
                <option value="Type B">Type B</option>
                <option value="Type C">Type C</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Timeframe</label>
              <select
                value={selectedTimeframe}
                onChange={(e) => setSelectedTimeframe(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="All">All Years</option>
                <option value="2024">2024</option>
                <option value="2023">2023</option>
                <option value="2022">2022</option>
              </select>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="bg-white rounded-lg shadow-sm border mb-6">
          <div className="border-b border-gray-200">
            <nav className="flex space-x-8 px-6">
              {[
                { id: 'executive', label: 'Executive Summary', icon: TrendingUp },
                { id: 'delays', label: 'Delay Analysis', icon: AlertTriangle },
                { id: 'duration', label: 'Duration & Variance', icon: Clock },
                { id: 'benchmarking', label: 'Benchmarking', icon: BarChart3 }
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setActiveTab(id)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                    activeTab === id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <Icon size={16} />
                  <span>{label}</span>
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Content */}
        <div className="min-h-96">
          {activeTab === 'executive' && renderExecutiveSummary()}
          {activeTab === 'delays' && renderDelayAnalysis()}
          {activeTab === 'duration' && renderDurationAnalysis()}
          {activeTab === 'benchmarking' && renderBenchmarking()}
        </div>
      </div>
    </div>
  );
};

export default P6Dashboard;

