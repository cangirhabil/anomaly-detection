"use client"

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  Area, ComposedChart, Pie, PieChart, Cell, BarChart, Bar, ReferenceLine, ScatterChart, Scatter, ZAxis
} from 'recharts';
import { Activity, AlertTriangle, Settings, RefreshCw, Database, Gauge, PieChart as PieIcon, Wifi, WifiOff, TrendingUp, Clock, Zap, BarChart3, Table2, TrendingDown, Target } from 'lucide-react';

interface ReadingData {
  is_anomaly: boolean;
  sensor_type: string;
  current_value: number;
  mean: number;
  std_dev: number;
  z_score: number;
  threshold: number;
  timestamp: string;
  severity: string;
  message: string;
  sensor_id?: string;
  unit?: string;
}

interface AnomalyLog {
  timestamp: string;
  sensor_type: string;
  current_value: number;
  z_score: number;
  severity: string;
  message: string;
  sensor_id?: string;
  unit?: string;
}

interface DataLog {
  timestamp: string;
  sensor_type: string;
  current_value: number;
  mean: number;
  std_dev: number;
  z_score: number;
  is_anomaly: boolean;
  unit?: string;
}

interface ChartDataPoint {
  time: string;
  value: number;
  mean: number;
  threshold: number;
  anomaly?: number;
}

interface SensorStats {
  [key: string]: {
    current: number;
    z_score: number;
    is_anomaly: boolean;
    count: number;
    unit?: string;
    min?: number;
    max?: number;
    sum?: number;
    anomaly_count?: number;
    values?: number[];
  };
}

interface ZScoreTableData {
  sensor: string;
  current_value: number;
  z_score: number;
  mean: number;
  std_dev: number;
  status: 'normal' | 'warning' | 'critical';
  unit?: string;
}

interface ZScoreDistribution {
  range: string;
  count: number;
  color: string;
}

interface Config {
  window_size: number;
  z_score_threshold: number;
  min_data_points: number;
  min_training_size: number;
  alert_message: string;
}

export default function Dashboard() {
  const [isConnected, setIsConnected] = useState(false);
  const [lastAnomaly, setLastAnomaly] = useState<ReadingData | null>(null);
  const [totalReadings, setTotalReadings] = useState(0);
  const [anomalyCount, setAnomalyCount] = useState(0);
  const [sensorStats, setSensorStats] = useState<SensorStats>({});
  const [sensorHistory, setSensorHistory] = useState<Record<string, ChartDataPoint[]>>({});
  const [selectedSensor, setSelectedSensor] = useState<string | null>(null);
  const [anomalyHistory, setAnomalyHistory] = useState<AnomalyLog[]>([]);
  const [allDataLogs, setAllDataLogs] = useState<DataLog[]>([]);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'anomaly-logs' | 'data-logs' | 'settings'>('dashboard');
  const [config, setConfig] = useState<Config>({
    window_size: 100,
    z_score_threshold: 3.0,
    min_data_points: 10,
    min_training_size: 20,
    alert_message: "⚠️ ANOMALİ TESPİT EDİLDİ!"
  });
  const [configSaved, setConfigSaved] = useState(false);
  const [configError, setConfigError] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    connectWebSocket();
    fetchAnomalyHistory();
    fetchAllDataLogs();
    fetchConfig();
    
    const interval = setInterval(() => {
      fetchAnomalyHistory();
      fetchAllDataLogs();
    }, 10000);
    
    return () => {
      clearInterval(interval);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    try {
      const ws = new WebSocket('ws://localhost:8000/ws');
      
      ws.onopen = () => {
        setIsConnected(true);
        console.log('✅ WebSocket bağlantısı kuruldu');
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          if (message.type === 'reading' && message.data) {
            const reading: ReadingData = message.data;
            
            setTotalReadings(prev => prev + 1);
            
            setAllDataLogs(prev => {
              const newLog: DataLog = {
                timestamp: reading.timestamp,
                sensor_type: reading.sensor_type,
                current_value: reading.current_value,
                mean: reading.mean,
                std_dev: reading.std_dev,
                z_score: reading.z_score,
                is_anomaly: reading.is_anomaly,
                unit: reading.unit
              };
              return [newLog, ...prev].slice(0, 200);
            });
            
            if (reading.is_anomaly) {
              setAnomalyCount(prev => prev + 1);
              setLastAnomaly(reading);
              
              setAnomalyHistory(prev => {
                const newHistory = [{
                  timestamp: reading.timestamp,
                  sensor_type: reading.sensor_type,
                  current_value: reading.current_value,
                  z_score: reading.z_score,
                  severity: reading.severity,
                  message: reading.message,
                  sensor_id: reading.sensor_id,
                  unit: reading.unit
                }, ...prev];
                return newHistory.slice(0, 50);
              });
            }
            
            setSensorStats(prev => {
              const existing = prev[reading.sensor_type];
              const newValues = [...(existing?.values || []), reading.current_value].slice(-100);
              return {
                ...prev,
                [reading.sensor_type]: {
                  current: reading.current_value,
                  z_score: reading.z_score,
                  is_anomaly: reading.is_anomaly,
                  count: (existing?.count || 0) + 1,
                  unit: reading.unit,
                  min: Math.min(existing?.min ?? reading.current_value, reading.current_value),
                  max: Math.max(existing?.max ?? reading.current_value, reading.current_value),
                  sum: (existing?.sum || 0) + reading.current_value,
                  anomaly_count: (existing?.anomaly_count || 0) + (reading.is_anomaly ? 1 : 0),
                  values: newValues
                }
              };
            });

            const time = new Date(reading.timestamp).toLocaleTimeString('tr-TR');
            const newPoint: ChartDataPoint = {
              time,
              value: reading.current_value,
              mean: reading.mean,
              threshold: reading.threshold,
              anomaly: reading.is_anomaly ? reading.current_value : undefined
            };

            setSensorHistory(prev => {
              const currentHistory = prev[reading.sensor_type] || [];
              const newHistory = [...currentHistory, newPoint].slice(-100);
              return {
                ...prev,
                [reading.sensor_type]: newHistory
              };
            });

            setSelectedSensor(prev => prev || reading.sensor_type);
          }
        } catch (error) {
          console.error('Mesaj işleme hatası:', error);
        }
      };

      ws.onerror = () => {
        console.error('❌ WebSocket hatası');
      };

      ws.onclose = () => {
        setIsConnected(false);
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('WebSocket bağlantı hatası:', error);
      reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
    }
  };

  const fetchAnomalyHistory = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/logs/anomalies?limit=100');
      if (response.ok) {
        const data = await response.json();
        if (data.anomalies && data.anomalies.length > 0) {
          setAnomalyHistory(data.anomalies);
        }
      }
    } catch (error) {
      console.error('Anomali geçmişi getirme hatası:', error);
    }
  };

  const fetchAllDataLogs = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/logs/recent?limit=200');
      if (response.ok) {
        const data = await response.json();
        if (data.logs && data.logs.length > 0) {
          setAllDataLogs(data.logs);
        }
      }
    } catch (error) {
      console.error('Veri logları getirme hatası:', error);
    }
  };

  const fetchConfig = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/config');
      if (response.ok) {
        const data = await response.json();
        setConfig(data);
      }
    } catch (error) {
      console.error('Konfigürasyon getirme hatası:', error);
    }
  };

  const updateConfig = async () => {
    try {
      setConfigError(false);
      console.log('Ayarlar kaydediliyor:', config);
      
      const response = await fetch('http://localhost:8000/api/v1/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      
      if (response.ok) {
        const updatedConfig = await response.json();
        console.log('Ayarlar başarıyla kaydedildi:', updatedConfig);
        setConfigSaved(true);
        setTimeout(() => setConfigSaved(false), 3000);
      } else {
        const errorData = await response.json();
        console.error('Ayarlar kaydedilemedi:', errorData);
        setConfigError(true);
        setTimeout(() => setConfigError(false), 3000);
      }
    } catch (error) {
      console.error('Konfigürasyon güncelleme hatası:', error);
      setConfigError(true);
      setTimeout(() => setConfigError(false), 3000);
    }
  };

  const resetSystem = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/reset', {
        method: 'POST',
      });
      if (response.ok) {
        setTotalReadings(0);
        setAnomalyCount(0);
        setSensorStats({});
        setSensorHistory({});
        setLastAnomaly(null);
        setAnomalyHistory([]);
        setAllDataLogs([]);
        setSelectedSensor(null);
      }
    } catch (error) {
      console.error('Sistem sıfırlama hatası:', error);
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('tr-TR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      day: '2-digit',
      month: '2-digit'
    });
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-500 text-white';
      case 'warning': return 'bg-amber-500 text-white';
      default: return 'bg-yellow-500 text-white';
    }
  };

  const anomalyRate = totalReadings > 0 ? ((anomalyCount / totalReadings) * 100).toFixed(2) : '0.00';

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-slate-700/50 bg-slate-900/80 backdrop-blur-xl">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 shadow-lg shadow-blue-500/25">
                <Activity className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-white">CountSort Anomali Tespiti</h1>
                <p className="text-xs text-slate-400">Gerçek Zamanlı İzleme Sistemi</p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <Badge 
                className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium ${
                  isConnected 
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' 
                    : 'bg-red-500/10 text-red-400 border-red-500/30'
                }`}
              >
              </Badge>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {/* Tab Navigation */}
        <div className="mb-6 flex flex-wrap gap-2 rounded-xl bg-slate-800/50 p-1.5">
          {[
            { id: 'dashboard', label: 'Dashboard', icon: Activity },
            { id: 'anomaly-logs', label: `Anomaliler (${anomalyHistory.length})`, icon: AlertTriangle },
            { id: 'data-logs', label: `Tüm Veriler (${allDataLogs.length})`, icon: Database },
            { id: 'settings', label: 'Ayarlar', icon: Settings },
          ].map((tab) => (
            <Button
              key={tab.id}
              variant="ghost"
              size="sm"
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/25'
                  : 'text-slate-400 hover:bg-slate-700/50 hover:text-white'
              }`}
            >
              <tab.icon className="h-4 w-4" />
              <span className="hidden sm:inline">{tab.label}</span>
            </Button>
          ))}
        </div>

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Stats Cards */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Card className="border-slate-700/50 bg-slate-800/50 backdrop-blur">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-medium text-slate-400">Toplam Okuma</p>
                      <p className="mt-1 text-2xl font-bold text-white">{totalReadings.toLocaleString()}</p>
                    </div>
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10">
                      <TrendingUp className="h-5 w-5 text-blue-400" />
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-slate-700/50 bg-slate-800/50 backdrop-blur">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-medium text-slate-400">Anomali Sayısı</p>
                      <p className="mt-1 text-2xl font-bold text-red-400">{anomalyCount}</p>
                    </div>
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-500/10">
                      <AlertTriangle className="h-5 w-5 text-red-400" />
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-slate-700/50 bg-slate-800/50 backdrop-blur">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-medium text-slate-400">Anomali Oranı</p>
                      <p className="mt-1 text-2xl font-bold text-amber-400">%{anomalyRate}</p>
                    </div>
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/10">
                      <Zap className="h-5 w-5 text-amber-400" />
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-slate-700/50 bg-slate-800/50 backdrop-blur">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-medium text-slate-400">Aktif Sensör</p>
                      <p className="mt-1 text-2xl font-bold text-emerald-400">{Object.keys(sensorStats).length}</p>
                    </div>
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10">
                      <Activity className="h-5 w-5 text-emerald-400" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Sensor Grid */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Object.entries(sensorStats).map(([sensor, stats]) => (
                <Card 
                  key={sensor}
                  onClick={() => setSelectedSensor(sensor)}
                  className={`cursor-pointer border-slate-700/50 bg-slate-800/50 backdrop-blur transition-all hover:border-slate-600 hover:bg-slate-800 ${
                    selectedSensor === sensor ? 'ring-2 ring-blue-500 ring-offset-2 ring-offset-slate-900' : ''
                  }`}
                >
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm font-medium text-slate-300">{sensor}</CardTitle>
                      <Badge 
                        className={`text-[10px] ${
                          stats.is_anomaly 
                            ? 'bg-red-500/10 text-red-400 border-red-500/30' 
                            : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                        }`}
                      >
                        {stats.is_anomaly ? "ANOMALİ" : "NORMAL"}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-end justify-between">
                      <div>
                        <p className="text-3xl font-bold text-white">{stats.current.toFixed(2)}</p>
                        <p className="text-xs text-slate-400">
                          Z-Score: <span className={stats.is_anomaly ? "text-red-400 font-semibold" : "text-slate-400"}>{stats.z_score.toFixed(2)}</span>
                        </p>
                      </div>
                      <div className="h-12 w-24">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={sensorHistory[sensor] || []}>
                            <Line 
                              type="monotone" 
                              dataKey="value" 
                              stroke={stats.is_anomaly ? "#ef4444" : "#3b82f6"} 
                              strokeWidth={2} 
                              dot={false} 
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}

              {Object.keys(sensorStats).length === 0 && (
                <Card className="col-span-full border-slate-700/50 bg-slate-800/50 backdrop-blur border-dashed">
                  <CardContent className="flex flex-col items-center justify-center py-12">
                    <Clock className="h-12 w-12 text-slate-500 mb-4" />
                    <p className="text-slate-400 text-center">Sensör verisi bekleniyor...</p>
                    <p className="text-slate-500 text-sm text-center mt-1">Veri gönderimi başladığında sensörler burada görünecek</p>
                  </CardContent>
                </Card>
              )}
            </div>

            {/* Main Chart & Side Panel */}
            <div className="grid gap-6 lg:grid-cols-3">
              {/* Main Chart */}
              <Card className="lg:col-span-2 border-slate-700/50 bg-slate-800/50 backdrop-blur">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-white flex items-center gap-2">
                        <Activity className="h-5 w-5 text-blue-400" />
                        {selectedSensor ? `${selectedSensor} - Kontrol Grafiği` : 'Sensör Grafiği'}
                      </CardTitle>
                      <CardDescription className="text-slate-400">
                        {selectedSensor ? 'Gerçek zamanlı değer takibi ve anomali noktaları' : 'Detaylı görüntü için bir sensör seçin'}
                      </CardDescription>
                    </div>
                    {selectedSensor && (
                      <Badge variant="outline" className="border-slate-600 text-slate-300">
                        {sensorHistory[selectedSensor]?.length || 0} veri
                      </Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  {!selectedSensor || !sensorHistory[selectedSensor]?.length ? (
                    <div className="flex h-80 items-center justify-center rounded-lg border border-dashed border-slate-700 bg-slate-800/30">
                      <div className="text-center">
                        <Activity className="mx-auto h-12 w-12 text-slate-600" />
                        <p className="mt-2 text-slate-500">Grafik için sensör seçin</p>
                      </div>
                    </div>
                  ) : (
                    <div className="h-80">
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={sensorHistory[selectedSensor]}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                          <XAxis dataKey="time" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                          <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
                          <Tooltip 
                            contentStyle={{ 
                              backgroundColor: '#1e293b', 
                              border: '1px solid #334155',
                              borderRadius: '8px',
                              color: '#f8fafc'
                            }}
                          />
                          <Legend />
                          <Area type="monotone" dataKey="threshold" fill="#3b82f620" stroke="none" name="Eşik" />
                          <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot={false} name="Değer" />
                          <Line type="monotone" dataKey="mean" stroke="#22c55e" strokeWidth={1} strokeDasharray="5 5" dot={false} name="Ortalama" />
                          <Line type="monotone" dataKey="anomaly" stroke="#ef4444" strokeWidth={0} dot={{ r: 5, fill: '#ef4444' }} name="Anomali" />
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Side Panel */}
              <div className="space-y-6">
                {/* Z-Score Gauge */}
                <Card className="border-slate-700/50 bg-slate-800/50 backdrop-blur">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-white flex items-center gap-2 text-base">
                      <Gauge className="h-4 w-4 text-blue-400" />
                      Z-Score Göstergesi
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {selectedSensor && sensorStats[selectedSensor] ? (
                      <div className="flex flex-col items-center">
                        <div className="relative h-24 w-48">
                          <PieChart width={192} height={96}>
                            <Pie
                              data={[
                                { value: 2, fill: '#22c55e' },
                                { value: 1, fill: '#eab308' },
                                { value: 1, fill: '#ef4444' },
                              ]}
                              cx="50%"
                              cy="100%"
                              startAngle={180}
                              endAngle={0}
                              innerRadius={60}
                              outerRadius={80}
                              paddingAngle={2}
                              dataKey="value"
                              stroke="none"
                            />
                          </PieChart>
                          <div className="absolute inset-x-0 bottom-0 text-center">
                            <p className="text-3xl font-bold text-white">
                              {Math.abs(sensorStats[selectedSensor].z_score).toFixed(1)}
                            </p>
                          </div>
                        </div>
                        <Badge className={`mt-2 ${sensorStats[selectedSensor].is_anomaly ? 'bg-red-500' : 'bg-emerald-500'}`}>
                          {sensorStats[selectedSensor].is_anomaly ? "KRİTİK" : "NORMAL"}
                        </Badge>
                      </div>
                    ) : (
                      <p className="py-8 text-center text-slate-500">Sensör seçilmedi</p>
                    )}
                  </CardContent>
                </Card>

                {/* Anomaly Distribution */}
                <Card className="border-slate-700/50 bg-slate-800/50 backdrop-blur">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-white flex items-center gap-2 text-base">
                      <PieIcon className="h-4 w-4 text-blue-400" />
                      Dağılım
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-40">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={[
                              { name: 'Normal', value: totalReadings - anomalyCount },
                              { name: 'Anomali', value: anomalyCount },
                            ]}
                            cx="50%"
                            cy="50%"
                            innerRadius={40}
                            outerRadius={60}
                            paddingAngle={5}
                            dataKey="value"
                          >
                            <Cell fill="#22c55e" />
                            <Cell fill="#ef4444" />
                          </Pie>
                          <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
                          <Legend />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>

                {/* Quick Actions */}
                <Card className="border-slate-700/50 bg-slate-800/50 backdrop-blur">
                  <CardContent className="p-4">
                    <Button 
                      onClick={resetSystem}
                      variant="outline"
                      className="w-full border-slate-600 text-slate-300 hover:bg-slate-700"
                    >
                      <RefreshCw className="mr-2 h-4 w-4" />
                      Sistemi Sıfırla
                    </Button>
                  </CardContent>
                </Card>
              </div>
            </div>

            {/* Z-Score Analysis Section */}
            <div className="grid gap-6 lg:grid-cols-2">
              {/* Z-Score Summary Table */}
              <Card className="border-slate-700/50 bg-slate-800/50 backdrop-blur">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <Table2 className="h-5 w-5 text-blue-400" />
                    Z-Score Özet Tablosu
                  </CardTitle>
                  <CardDescription className="text-slate-400">
                    Tüm sensörlerin anlık Z-Score değerleri ve durumları
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {Object.keys(sensorStats).length === 0 ? (
                    <div className="py-8 text-center">
                      <Table2 className="mx-auto h-10 w-10 text-slate-600" />
                      <p className="mt-2 text-slate-500">Veri bekleniyor...</p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-slate-700">
                            <th className="px-3 py-2 text-left font-medium text-slate-400">Sensör</th>
                            <th className="px-3 py-2 text-right font-medium text-slate-400">Değer</th>
                            <th className="px-3 py-2 text-right font-medium text-slate-400">Z-Score</th>
                            <th className="px-3 py-2 text-center font-medium text-slate-400">Durum</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700/50">
                          {Object.entries(sensorStats).map(([sensor, stats]) => {
                            const absZScore = Math.abs(stats.z_score);
                            const status = absZScore > config.z_score_threshold ? 'critical' : absZScore > config.z_score_threshold * 0.7 ? 'warning' : 'normal';
                            return (
                              <tr key={sensor} className="hover:bg-slate-700/30">
                                <td className="px-3 py-2 text-slate-200 font-medium">{sensor}</td>
                                <td className="px-3 py-2 text-right font-mono text-slate-200">
                                  {stats.current.toFixed(2)}
                                  {stats.unit && <span className="ml-1 text-slate-500 text-xs">{stats.unit}</span>}
                                </td>
                                <td className={`px-3 py-2 text-right font-mono font-bold ${
                                  status === 'critical' ? 'text-red-400' : status === 'warning' ? 'text-amber-400' : 'text-emerald-400'
                                }`}>
                                  {stats.z_score.toFixed(3)}
                                </td>
                                <td className="px-3 py-2 text-center">
                                  <Badge className={`text-[10px] ${
                                    status === 'critical' ? 'bg-red-500/20 text-red-300 border-red-500/30' :
                                    status === 'warning' ? 'bg-amber-500/20 text-amber-300 border-amber-500/30' :
                                    'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                                  }`}>
                                    {status === 'critical' ? 'KRİTİK' : status === 'warning' ? 'DİKKAT' : 'NORMAL'}
                                  </Badge>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Z-Score Bar Chart Comparison */}
              <Card className="border-slate-700/50 bg-slate-800/50 backdrop-blur">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <BarChart3 className="h-5 w-5 text-blue-400" />
                    Sensör Z-Score Karşılaştırması
                  </CardTitle>
                  <CardDescription className="text-slate-400">
                    Tüm sensörlerin Z-Score değerlerinin görsel karşılaştırması
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {Object.keys(sensorStats).length === 0 ? (
                    <div className="py-8 text-center">
                      <BarChart3 className="mx-auto h-10 w-10 text-slate-600" />
                      <p className="mt-2 text-slate-500">Veri bekleniyor...</p>
                    </div>
                  ) : (
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={Object.entries(sensorStats).map(([sensor, stats]) => ({
                            sensor: sensor.length > 10 ? sensor.substring(0, 10) + '...' : sensor,
                            z_score: stats.z_score,
                            absZScore: Math.abs(stats.z_score),
                            fill: Math.abs(stats.z_score) > config.z_score_threshold ? '#ef4444' : 
                                  Math.abs(stats.z_score) > config.z_score_threshold * 0.7 ? '#f59e0b' : '#22c55e'
                          }))}
                          layout="vertical"
                          margin={{ top: 5, right: 30, left: 80, bottom: 5 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                          <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                          <YAxis type="category" dataKey="sensor" tick={{ fill: '#94a3b8', fontSize: 10 }} width={75} />
                          <Tooltip
                            contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                            formatter={(value: number) => [value.toFixed(3), 'Z-Score']}
                          />
                          <ReferenceLine x={config.z_score_threshold} stroke="#ef4444" strokeDasharray="5 5" label={{ value: 'Eşik', fill: '#ef4444', fontSize: 10 }} />
                          <ReferenceLine x={-config.z_score_threshold} stroke="#ef4444" strokeDasharray="5 5" />
                          <Bar dataKey="z_score" radius={[0, 4, 4, 0]}>
                            {Object.entries(sensorStats).map(([sensor, stats], index) => (
                              <Cell 
                                key={`cell-${index}`} 
                                fill={Math.abs(stats.z_score) > config.z_score_threshold ? '#ef4444' : 
                                      Math.abs(stats.z_score) > config.z_score_threshold * 0.7 ? '#f59e0b' : '#22c55e'}
                              />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Additional Analysis Charts */}
            <div className="grid gap-6 lg:grid-cols-3">
              {/* Sensor Statistics Cards */}
              <Card className="border-slate-700/50 bg-slate-800/50 backdrop-blur">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2 text-base">
                    <Target className="h-4 w-4 text-blue-400" />
                    Sensör İstatistikleri
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {selectedSensor && sensorStats[selectedSensor] ? (
                    <div className="space-y-3">
                      <div className="flex justify-between items-center p-2 rounded bg-slate-700/30">
                        <span className="text-slate-400 text-sm">Minimum</span>
                        <span className="text-white font-mono font-bold">
                          {(sensorStats[selectedSensor].min ?? 0).toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center p-2 rounded bg-slate-700/30">
                        <span className="text-slate-400 text-sm">Maksimum</span>
                        <span className="text-white font-mono font-bold">
                          {(sensorStats[selectedSensor].max ?? 0).toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center p-2 rounded bg-slate-700/30">
                        <span className="text-slate-400 text-sm">Ortalama</span>
                        <span className="text-white font-mono font-bold">
                          {sensorStats[selectedSensor].count > 0 
                            ? ((sensorStats[selectedSensor].sum ?? 0) / sensorStats[selectedSensor].count).toFixed(2)
                            : '0.00'}
                        </span>
                      </div>
                      <div className="flex justify-between items-center p-2 rounded bg-slate-700/30">
                        <span className="text-slate-400 text-sm">Toplam Okuma</span>
                        <span className="text-white font-mono font-bold">
                          {sensorStats[selectedSensor].count}
                        </span>
                      </div>
                      <div className="flex justify-between items-center p-2 rounded bg-red-500/10">
                        <span className="text-red-400 text-sm">Anomali Sayısı</span>
                        <span className="text-red-400 font-mono font-bold">
                          {sensorStats[selectedSensor].anomaly_count ?? 0}
                        </span>
                      </div>
                      <div className="flex justify-between items-center p-2 rounded bg-amber-500/10">
                        <span className="text-amber-400 text-sm">Anomali Oranı</span>
                        <span className="text-amber-400 font-mono font-bold">
                          %{sensorStats[selectedSensor].count > 0 
                            ? (((sensorStats[selectedSensor].anomaly_count ?? 0) / sensorStats[selectedSensor].count) * 100).toFixed(1)
                            : '0.0'}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <p className="py-8 text-center text-slate-500">Sensör seçilmedi</p>
                  )}
                </CardContent>
              </Card>

              {/* Z-Score Distribution Histogram */}
              <Card className="border-slate-700/50 bg-slate-800/50 backdrop-blur">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2 text-base">
                    <TrendingDown className="h-4 w-4 text-blue-400" />
                    Z-Score Dağılımı
                  </CardTitle>
                  <CardDescription className="text-slate-400 text-xs">
                    Son verilerin Z-Score aralıklarına göre dağılımı
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {allDataLogs.length === 0 ? (
                    <div className="py-8 text-center">
                      <TrendingDown className="mx-auto h-10 w-10 text-slate-600" />
                      <p className="mt-2 text-slate-500">Veri bekleniyor...</p>
                    </div>
                  ) : (
                    <div className="h-48">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={(() => {
                            const ranges = [
                              { range: '0-1', min: 0, max: 1, count: 0, color: '#22c55e' },
                              { range: '1-2', min: 1, max: 2, count: 0, color: '#84cc16' },
                              { range: '2-3', min: 2, max: 3, count: 0, color: '#f59e0b' },
                              { range: '3-4', min: 3, max: 4, count: 0, color: '#f97316' },
                              { range: '4+', min: 4, max: Infinity, count: 0, color: '#ef4444' },
                            ];
                            allDataLogs.slice(0, 100).forEach(log => {
                              const absZ = Math.abs(log.z_score);
                              const range = ranges.find(r => absZ >= r.min && absZ < r.max);
                              if (range) range.count++;
                            });
                            return ranges;
                          })()}
                          margin={{ top: 10, right: 10, left: 10, bottom: 20 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                          <XAxis dataKey="range" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                          <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
                          <Tooltip
                            contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                            formatter={(value: number) => [value, 'Adet']}
                          />
                          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                            {[0, 1, 2, 3, 4].map((index) => (
                              <Cell key={`cell-${index}`} fill={['#22c55e', '#84cc16', '#f59e0b', '#f97316', '#ef4444'][index]} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Value vs Z-Score Scatter Plot */}
              <Card className="border-slate-700/50 bg-slate-800/50 backdrop-blur">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2 text-base">
                    <Activity className="h-4 w-4 text-blue-400" />
                    Değer - Z-Score İlişkisi
                  </CardTitle>
                  <CardDescription className="text-slate-400 text-xs">
                    {selectedSensor ? `${selectedSensor} sensörü için` : 'Sensör seçin'}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {!selectedSensor || !sensorHistory[selectedSensor]?.length ? (
                    <div className="py-8 text-center">
                      <Activity className="mx-auto h-10 w-10 text-slate-600" />
                      <p className="mt-2 text-slate-500">Sensör seçilmedi</p>
                    </div>
                  ) : (
                    <div className="h-48">
                      <ResponsiveContainer width="100%" height="100%">
                        <ScatterChart margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                          <XAxis 
                            type="number" 
                            dataKey="value" 
                            name="Değer" 
                            tick={{ fill: '#94a3b8', fontSize: 10 }}
                            label={{ value: 'Değer', position: 'bottom', fill: '#94a3b8', fontSize: 10 }}
                          />
                          <YAxis 
                            type="number" 
                            dataKey="z" 
                            name="Z-Score" 
                            tick={{ fill: '#94a3b8', fontSize: 10 }}
                            label={{ value: 'Z-Score', angle: -90, position: 'left', fill: '#94a3b8', fontSize: 10 }}
                          />
                          <ZAxis type="number" range={[30, 100]} />
                          <Tooltip
                            contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                            formatter={(value: number, name: string) => [value.toFixed(3), name]}
                          />
                          <ReferenceLine y={config.z_score_threshold} stroke="#ef4444" strokeDasharray="5 5" />
                          <ReferenceLine y={-config.z_score_threshold} stroke="#ef4444" strokeDasharray="5 5" />
                          <Scatter
                            name={selectedSensor}
                            data={allDataLogs
                              .filter(log => log.sensor_type === selectedSensor)
                              .slice(0, 50)
                              .map(log => ({
                                value: log.current_value,
                                z: log.z_score,
                                isAnomaly: log.is_anomaly
                              }))}
                            fill="#3b82f6"
                          >
                            {allDataLogs
                              .filter(log => log.sensor_type === selectedSensor)
                              .slice(0, 50)
                              .map((log, index) => (
                                <Cell key={`cell-${index}`} fill={log.is_anomaly ? '#ef4444' : '#3b82f6'} />
                              ))}
                          </Scatter>
                        </ScatterChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        )}

        {/* Anomaly Logs Tab */}
        {activeTab === 'anomaly-logs' && (
          <Card className="border-slate-700/50 bg-slate-800/50 backdrop-blur">
            <CardHeader>
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <CardTitle className="text-white flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-red-400" />
                    Anomali Logları
                  </CardTitle>
                  <CardDescription className="text-slate-400">
                    Tespit edilen tüm anomalilerin detaylı kayıtları
                  </CardDescription>
                </div>
                <Button onClick={fetchAnomalyHistory} variant="outline" size="sm" className="border-slate-600 text-slate-300">
                  <RefreshCw className="mr-2 h-4 w-4" /> Yenile
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {anomalyHistory.length === 0 ? (
                <div className="py-12 text-center">
                  <AlertTriangle className="mx-auto h-12 w-12 text-slate-600" />
                  <p className="mt-4 text-slate-400">Henüz anomali kaydı bulunmuyor</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-700">
                        <th className="px-4 py-3 text-left font-medium text-slate-400">Zaman</th>
                        <th className="px-4 py-3 text-left font-medium text-slate-400">Sensör</th>
                        <th className="px-4 py-3 text-right font-medium text-slate-400">Değer</th>
                        <th className="px-4 py-3 text-right font-medium text-slate-400">Z-Score</th>
                        <th className="px-4 py-3 text-center font-medium text-slate-400">Seviye</th>
                        <th className="px-4 py-3 text-left font-medium text-slate-400 hidden lg:table-cell">Açıklama</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-700/50">
                      {anomalyHistory.map((anomaly, index) => (
                        <tr key={index} className="hover:bg-slate-700/30">
                          <td className="px-4 py-3 font-mono text-xs text-slate-300">
                            {formatTimestamp(anomaly.timestamp)}
                          </td>
                          <td className="px-4 py-3 text-slate-200">{anomaly.sensor_type}</td>
                          <td className="px-4 py-3 text-right font-mono text-slate-200">
                            {anomaly.current_value.toFixed(2)}
                            {anomaly.unit && <span className="ml-1 text-slate-500">{anomaly.unit}</span>}
                          </td>
                          <td className="px-4 py-3 text-right font-mono font-bold text-red-400">
                            {anomaly.z_score.toFixed(2)}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <Badge className={getSeverityColor(anomaly.severity)}>
                              {anomaly.severity}
                            </Badge>
                          </td>
                          <td className="px-4 py-3 text-xs text-slate-400 hidden lg:table-cell">
                            {anomaly.message}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Data Logs Tab */}
        {activeTab === 'data-logs' && (
          <Card className="border-slate-700/50 bg-slate-800/50 backdrop-blur">
            <CardHeader>
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <CardTitle className="text-white flex items-center gap-2">
                    <Database className="h-5 w-5 text-blue-400" />
                    Tüm Veri Logları
                  </CardTitle>
                  <CardDescription className="text-slate-400">
                    Sisteme gelen tüm sensör verilerinin kayıtları
                  </CardDescription>
                </div>
                <Button onClick={fetchAllDataLogs} variant="outline" size="sm" className="border-slate-600 text-slate-300">
                  <RefreshCw className="mr-2 h-4 w-4" /> Yenile
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {allDataLogs.length === 0 ? (
                <div className="py-12 text-center">
                  <Database className="mx-auto h-12 w-12 text-slate-600" />
                  <p className="mt-4 text-slate-400">Henüz veri kaydı bulunmuyor</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-700">
                        <th className="px-4 py-3 text-left font-medium text-slate-400">Zaman</th>
                        <th className="px-4 py-3 text-left font-medium text-slate-400">Sensör</th>
                        <th className="px-4 py-3 text-right font-medium text-slate-400">Değer</th>
                        <th className="px-4 py-3 text-right font-medium text-slate-400 hidden sm:table-cell">Ortalama</th>
                        <th className="px-4 py-3 text-right font-medium text-slate-400 hidden md:table-cell">Std Dev</th>
                        <th className="px-4 py-3 text-right font-medium text-slate-400">Z-Score</th>
                        <th className="px-4 py-3 text-center font-medium text-slate-400">Durum</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-700/50">
                      {allDataLogs.map((log, index) => (
                        <tr 
                          key={index} 
                          className={`hover:bg-slate-700/30 ${log.is_anomaly ? 'bg-red-900/10' : ''}`}
                        >
                          <td className="px-4 py-3 font-mono text-xs text-slate-300">
                            {formatTimestamp(log.timestamp)}
                          </td>
                          <td className="px-4 py-3 text-slate-200">{log.sensor_type}</td>
                          <td className="px-4 py-3 text-right font-mono font-bold text-slate-200">
                            {log.current_value.toFixed(2)}
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-slate-400 hidden sm:table-cell">
                            {log.mean.toFixed(2)}
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-slate-400 hidden md:table-cell">
                            {log.std_dev.toFixed(2)}
                          </td>
                          <td className={`px-4 py-3 text-right font-mono font-bold ${log.is_anomaly ? 'text-red-400' : 'text-slate-400'}`}>
                            {log.z_score.toFixed(2)}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <Badge className={log.is_anomaly ? 'bg-red-500' : 'bg-emerald-500'}>
                              {log.is_anomaly ? "Anomali" : "Normal"}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <div className="grid gap-6 lg:grid-cols-2">
            <Card className="border-slate-700/50 bg-slate-800/50 backdrop-blur">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Settings className="h-5 w-5 text-blue-400" />
                  Sistem Ayarları
                </CardTitle>
                <CardDescription className="text-slate-400">
                  Anomali tespit parametrelerini buradan ayarlayabilirsiniz
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {configSaved && (
                  <Alert className="border-emerald-500/30 bg-emerald-500/10">
                    <AlertTitle className="text-emerald-400">Başarılı!</AlertTitle>
                    <AlertDescription className="text-emerald-300">Ayarlar kaydedildi ve uygulandı.</AlertDescription>
                  </Alert>
                )}

                <div className="space-y-2">
                  <Label htmlFor="z_score" className="text-slate-300 font-medium">Hassasiyet Seviyesi (Z-Score Eşiği)</Label>
                  <div className="flex items-center gap-3">
                    <Input 
                      id="z_score"
                      type="number" 
                      step="0.1"
                      className="w-28 bg-slate-700 border-slate-600 text-white"
                      value={config.z_score_threshold} 
                      onChange={(e) => setConfig({...config, z_score_threshold: parseFloat(e.target.value) || 0})}
                    />
                    <span className="text-sm text-slate-400">Önerilen: 2.0 - 3.5</span>
                  </div>
                  <p className="text-xs text-slate-500">
                    Düşük değer = Hassas (çok alarm), Yüksek değer = Toleranslı (az alarm)
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="window" className="text-slate-300 font-medium">Analiz Penceresi</Label>
                  <Input 
                    id="window"
                    type="number" 
                    className="bg-slate-700 border-slate-600 text-white"
                    value={config.window_size} 
                    onChange={(e) => setConfig({...config, window_size: parseInt(e.target.value) || 0})}
                  />
                  <p className="text-xs text-slate-500">
                    Sistem kaç veri noktasını referans alarak normal durumu belirlesin
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="training" className="text-slate-300">Öğrenme Süresi</Label>
                    <Input 
                      id="training"
                      type="number" 
                      className="bg-slate-700 border-slate-600 text-white"
                      value={config.min_training_size} 
                      onChange={(e) => setConfig({...config, min_training_size: parseInt(e.target.value) || 0})}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="mindata" className="text-slate-300">Min. Veri</Label>
                    <Input 
                      id="mindata"
                      type="number" 
                      className="bg-slate-700 border-slate-600 text-white"
                      value={config.min_data_points} 
                      onChange={(e) => setConfig({...config, min_data_points: parseInt(e.target.value) || 0})}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="alert" className="text-slate-300 font-medium">Alarm Mesajı</Label>
                  <Input 
                    id="alert"
                    type="text" 
                    className="bg-slate-700 border-slate-600 text-white"
                    placeholder="⚠️ ANOMALİ TESPİT EDİLDİ!"
                    value={config.alert_message} 
                    onChange={(e) => setConfig({...config, alert_message: e.target.value})}
                  />
                  <p className="text-xs text-slate-500">
                    Anomali tespit edildiğinde gösterilecek uyarı mesajı
                  </p>
                </div>

                {configSaved && (
                  <Alert className="bg-emerald-500/10 border-emerald-500/50">
                    <AlertTitle className="text-emerald-400 flex items-center gap-2">
                      ✅ Ayarlar Kaydedildi!
                    </AlertTitle>
                    <AlertDescription className="text-emerald-300">
                      Tüm parametreler başarıyla güncellendi.
                    </AlertDescription>
                  </Alert>
                )}

                {configError && (
                  <Alert className="bg-red-500/10 border-red-500/50">
                    <AlertTriangle className="h-4 w-4 text-red-400" />
                    <AlertTitle className="text-red-400">
                      Ayarlar Kaydedilemedi!
                    </AlertTitle>
                    <AlertDescription className="text-red-300">
                      Backend sunucusuna bağlanılamadı. Lütfen sunucunun çalıştığından emin olun.
                    </AlertDescription>
                  </Alert>
                )}

                <Button onClick={updateConfig} className="w-full bg-blue-600 hover:bg-blue-700">
                  <Settings className="mr-2 h-4 w-4" />
                  Ayarları Kaydet
                </Button>
              </CardContent>
            </Card>

            <Card className="border-slate-700/50 bg-slate-800/50 backdrop-blur">
              <CardHeader>
                <CardTitle className="text-white">Hazır Profiller</CardTitle>
                <CardDescription className="text-slate-400">
                  Tek tıkla optimize edilmiş ayarları yükleyin
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button 
                  variant="outline"
                  className={`w-full h-auto py-4 justify-start border-2 transition-all ${
                    config.z_score_threshold < 2.0 
                      ? 'border-blue-500 bg-blue-500/10' 
                      : 'border-slate-600 hover:border-slate-500'
                  }`}
                  onClick={() => setConfig({
                    ...config,
                    z_score_threshold: 1.8,
                    window_size: 50,
                    min_data_points: 10,
                    min_training_size: 20
                  })}
                >
                  <div className="text-left">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white">🎯 Hassas Mod</span>
                      <Badge className="bg-blue-500/20 text-blue-300 border-blue-500/30">Yüksek Dikkat</Badge>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">En ufak değişimi yakalar. Kalite kontrol için ideal.</p>
                  </div>
                </Button>

                <Button 
                  variant="outline"
                  className={`w-full h-auto py-4 justify-start border-2 transition-all ${
                    config.z_score_threshold >= 2.0 && config.z_score_threshold <= 3.0 
                      ? 'border-emerald-500 bg-emerald-500/10' 
                      : 'border-slate-600 hover:border-slate-500'
                  }`}
                  onClick={() => setConfig({
                    ...config,
                    z_score_threshold: 2.5,
                    window_size: 100,
                    min_data_points: 20,
                    min_training_size: 50
                  })}
                >
                  <div className="text-left">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white">⚖️ Dengeli Mod</span>
                      <Badge className="bg-emerald-500/20 text-emerald-300 border-emerald-500/30">Önerilen</Badge>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">Standart üretim hattı için optimize edildi.</p>
                  </div>
                </Button>

                <Button 
                  variant="outline"
                  className={`w-full h-auto py-4 justify-start border-2 transition-all ${
                    config.z_score_threshold > 3.0 
                      ? 'border-amber-500 bg-amber-500/10' 
                      : 'border-slate-600 hover:border-slate-500'
                  }`}
                  onClick={() => setConfig({
                    ...config,
                    z_score_threshold: 3.5,
                    window_size: 200,
                    min_data_points: 50,
                    min_training_size: 100
                  })}
                >
                  <div className="text-left">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white">🛡️ Esnek Mod</span>
                      <Badge className="bg-amber-500/20 text-amber-300 border-amber-500/30">Az Alarm</Badge>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">Sadece büyük arızalarda alarm verir.</p>
                  </div>
                </Button>

                <Alert className="mt-4 border-slate-600 bg-slate-700/50">
                  <AlertTitle className="text-slate-300 text-xs uppercase">Not</AlertTitle>
                  <AlertDescription className="text-slate-400 text-xs">
                    Profil seçtikten sonra &quot;Ayarları Kaydet&quot; butonuna basarak değişiklikleri uygulayın.
                  </AlertDescription>
                </Alert>
              </CardContent>
            </Card>
          </div>
        )}
      </main>
    </div>
  );
}
