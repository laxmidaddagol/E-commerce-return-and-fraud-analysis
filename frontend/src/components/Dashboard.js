import React, { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { format } from 'date-fns';
import toast from 'react-hot-toast';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, PieChart, Pie, Cell, AreaChart, Area, ScatterChart, Scatter
} from 'recharts';
import {
  Card, CardContent, CardHeader, CardTitle,
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
  Button, Badge, Alert, AlertDescription,
  Tabs, TabsContent, TabsList, TabsTrigger,
  Input, Label
} from './ui/index';
import { 
  TrendingUp, TrendingDown, Users, ShoppingCart, 
  AlertTriangle, Shield, Download, RefreshCw,
  DollarSign, Package, Calendar, Filter
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = () => {
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [selectedMetric, setSelectedMetric] = useState('return_rate');
  const [exportType, setExportType] = useState('csv');
  const [isGeneratingData, setIsGeneratingData] = useState(false);

  // Fetch dashboard metrics
  const { data: metrics, isLoading: metricsLoading, refetch: refetchMetrics } = useQuery({
    queryKey: ['dashboard-metrics', dateRange],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (dateRange.start) params.append('start_date', dateRange.start);
      if (dateRange.end) params.append('end_date', dateRange.end);
      
      const response = await axios.get(`${API}/analytics/dashboard?${params}`);
      return response.data;
    }
  });

  // Fetch customer risk profiles
  const { data: riskProfiles, isLoading: riskLoading } = useQuery({
    queryKey: ['risk-profiles'],
    queryFn: async () => {
      const response = await axios.get(`${API}/analytics/customer-risk-profiles?limit=50`);
      return response.data;
    }
  });

  // Fetch trend analysis
  const { data: trends, isLoading: trendsLoading } = useQuery({
    queryKey: ['trends'],
    queryFn: async () => {
      const response = await axios.get(`${API}/analytics/trends?days=30`);
      return response.data.data;
    }
  });

  // Fetch fraud patterns
  const { data: fraudPatterns, isLoading: fraudLoading } = useQuery({
    queryKey: ['fraud-patterns'],
    queryFn: async () => {
      const response = await axios.get(`${API}/fraud/patterns`);
      return response.data;
    }
  });

  // Generate sample data
  const generateSampleData = async () => {
    setIsGeneratingData(true);
    try {
      const response = await axios.post(`${API}/generate-sample-data`, {
        customers: 1000,
        sellers: 50,
        products: 500,
        orders: 5000,
        return_rate: 0.15
      });
      
      if (response.data.success) {
        toast.success('Sample data generated successfully!');
        setTimeout(() => {
          refetchMetrics();
          window.location.reload();
        }, 2000);
      }
    } catch (error) {
      toast.error('Failed to generate sample data');
      console.error(error);
    } finally {
      setIsGeneratingData(false);
    }
  };

  // Export data
  const exportData = async (dataType) => {
    try {
      const requestBody = {
        export_type: exportType,
        data_type: dataType,
        filters: dateRange.start && dateRange.end ? {
          start_date: dateRange.start,
          end_date: dateRange.end
        } : null,
        include_fraud_scores: true
      };

      const response = await axios.post(
        `${API}/export/${exportType}`,
        requestBody,
        { responseType: 'blob' }
      );

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${dataType}_export.${exportType}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success(`${dataType} data exported successfully!`);
    } catch (error) {
      toast.error('Export failed');
      console.error(error);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(value);
  };

  const formatPercentage = (value) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  // Color scheme
  const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7c7c', '#8dd1e1'];

  const getRiskColor = (level) => {
    switch (level) {
      case 'critical': return 'bg-red-100 text-red-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-green-100 text-green-800';
    }
  };

  // Prepare chart data
  const returnReasonsData = useMemo(() => {
    if (!metrics?.top_return_reasons) return [];
    
    return Object.entries(metrics.top_return_reasons).map(([reason, count]) => ({
      name: reason.replace('_', ' ').toUpperCase(),
      value: count,
      percentage: ((count / metrics.total_returns) * 100).toFixed(1)
    }));
  }, [metrics]);

  const riskDistributionData = useMemo(() => {
    if (!riskProfiles) return [];
    
    const distribution = riskProfiles.reduce((acc, profile) => {
      acc[profile.risk_level] = (acc[profile.risk_level] || 0) + 1;
      return acc;
    }, {});
    
    return Object.entries(distribution).map(([level, count]) => ({
      name: level.toUpperCase(),
      value: count
    }));
  }, [riskProfiles]);

  if (metricsLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-lg">Loading analytics dashboard...</p>
        </div>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-center py-12">
          <Package className="h-16 w-16 mx-auto mb-4 text-gray-400" />
          <h2 className="text-2xl font-bold mb-4">No Data Available</h2>
          <p className="text-gray-600 mb-6">
            Generate sample e-commerce data to start analyzing return patterns and fraud detection.
          </p>
          <Button 
            onClick={generateSampleData}
            disabled={isGeneratingData}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {isGeneratingData ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                Generating Data...
              </>
            ) : (
              'Generate Sample Data'
            )}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold">E-Commerce Return & Fraud Analysis</h1>
          <p className="text-gray-600">Comprehensive analytics pipeline for return data and fraud detection</p>
        </div>
        
        <div className="flex gap-2">
          <Select value={exportType} onValueChange={setExportType}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="csv">CSV</SelectItem>
              <SelectItem value="json">JSON</SelectItem>
            </SelectContent>
          </Select>
          
          <Button 
            variant="outline" 
            onClick={generateSampleData}
            disabled={isGeneratingData}
          >
            {isGeneratingData ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>

      {/* Date Range Filter */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Date Range Filter
          </CardTitle>
        </CardHeader>
        <CardContent className="flex gap-4 items-end">
          <div>
            <Label htmlFor="start-date">Start Date</Label>
            <Input
              id="start-date"
              type="date"
              value={dateRange.start}
              onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
            />
          </div>
          <div>
            <Label htmlFor="end-date">End Date</Label>
            <Input
              id="end-date"
              type="date"
              value={dateRange.end}
              onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
            />
          </div>
          <Button 
            onClick={() => setDateRange({ start: '', end: '' })}
            variant="outline"
          >
            Clear
          </Button>
        </CardContent>
      </Card>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Orders</CardTitle>
            <ShoppingCart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.total_orders.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              Revenue: {formatCurrency(metrics.total_revenue)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Return Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatPercentage(metrics.overall_return_rate)}</div>
            <p className="text-xs text-muted-foreground">
              {metrics.total_returns.toLocaleString()} returns
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Fraud Detection Rate</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatPercentage(metrics.fraud_detection_rate)}</div>
            <p className="text-xs text-muted-foreground">
              {metrics.high_risk_customers} high-risk customers
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Processing Time</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.avg_processing_time.toFixed(1)} days</div>
            <p className="text-xs text-muted-foreground">
              Refund amount: {formatCurrency(metrics.total_refund_amount)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Analytics */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="fraud">Fraud Analysis</TabsTrigger>
          <TabsTrigger value="trends">Trends</TabsTrigger>
          <TabsTrigger value="export">Data Export</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Return Reasons Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Top Return Reasons</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={returnReasonsData}
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      dataKey="value"
                      label={({name, percentage}) => `${name}: ${percentage}%`}
                    >
                      {returnReasonsData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Risk Distribution */}
            <Card>
              <CardHeader>
                <CardTitle>Customer Risk Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={riskDistributionData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="value" fill="#8884d8" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Daily Trends */}
          {trends?.daily_trends && (
            <Card>
              <CardHeader>
                <CardTitle>Daily Return & Fraud Trends (Last 30 Days)</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={400}>
                  <LineChart data={trends.daily_trends}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="_id" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="return_count" stroke="#8884d8" name="Returns" />
                    <Line type="monotone" dataKey="fraud_count" stroke="#ff7c7c" name="Fraud Cases" />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="fraud" className="space-y-6">
          {/* Fraud Alerts */}
          {fraudPatterns && fraudPatterns.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                  Active Fraud Patterns
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {fraudPatterns.slice(0, 5).map((pattern, index) => (
                    <Alert key={index} className="border-red-200">
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription>
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium">{pattern.pattern_type.replace('_', ' ').toUpperCase()}</p>
                            <p className="text-sm text-gray-600">{pattern.description}</p>
                          </div>
                          <Badge className={getRiskColor(pattern.severity)}>
                            {pattern.severity}
                          </Badge>
                        </div>
                      </AlertDescription>
                    </Alert>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* High-Risk Customers */}
          {riskProfiles && (
            <Card>
              <CardHeader>
                <CardTitle>High-Risk Customer Profiles</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {riskProfiles
                    .filter(profile => profile.risk_level !== 'low')
                    .slice(0, 10)
                    .map((profile, index) => (
                      <div key={index} className="flex justify-between items-center p-4 border rounded-lg">
                        <div className="flex-1">
                          <p className="font-medium">{profile.email}</p>
                          <p className="text-sm text-gray-600">
                            Risk Score: {profile.risk_score.toFixed(1)} | 
                            Returns: {profile.return_frequency} | 
                            Avg Order: {formatCurrency(profile.avg_order_value)}
                          </p>
                          <p className="text-xs text-gray-500">{profile.recommendation}</p>
                        </div>
                        <Badge className={getRiskColor(profile.risk_level)}>
                          {profile.risk_level}
                        </Badge>
                      </div>
                    ))
                  }
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="trends" className="space-y-6">
          {trends && (
            <div className="grid gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Trend Analysis Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="text-center p-4 border rounded-lg">
                      <p className="text-sm text-gray-600">Return Trend</p>
                      <p className="text-xl font-bold flex items-center justify-center gap-2">
                        {trends.return_trend}
                        {trends.return_trend === 'increasing' ? (
                          <TrendingUp className="h-5 w-5 text-red-500" />
                        ) : (
                          <TrendingDown className="h-5 w-5 text-green-500" />
                        )}
                      </p>
                    </div>
                    <div className="text-center p-4 border rounded-lg">
                      <p className="text-sm text-gray-600">Avg Daily Returns</p>
                      <p className="text-xl font-bold">{trends.avg_daily_returns.toFixed(1)}</p>
                    </div>
                    <div className="text-center p-4 border rounded-lg">
                      <p className="text-sm text-gray-600">Avg Daily Fraud</p>
                      <p className="text-xl font-bold">{trends.avg_daily_fraud.toFixed(1)}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        <TabsContent value="export" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Export Cards */}
            {['customers', 'orders', 'returns', 'analytics'].map((dataType) => (
              <Card key={dataType}>
                <CardHeader>
                  <CardTitle className="capitalize">{dataType} Data</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-600 mb-4">
                    Export {dataType} data for external analysis in Power BI, Tableau, or Excel.
                  </p>
                  <Button 
                    onClick={() => exportData(dataType)}
                    className="w-full"
                    variant="outline"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Export as {exportType.toUpperCase()}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Power BI & Tableau Integration</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <p className="text-sm text-gray-600">
                  Use the exported data files to create advanced visualizations in Power BI or Tableau:
                </p>
                <ul className="list-disc list-inside space-y-2 text-sm">
                  <li><strong>CSV format:</strong> Direct import into Power BI, Tableau, or Excel</li>
                  <li><strong>JSON format:</strong> Structured data for advanced analytics tools</li>
                  <li><strong>Fraud scores included:</strong> Ready for risk assessment dashboards</li>
                  <li><strong>Time-series data:</strong> Perfect for trend analysis and forecasting</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Dashboard;