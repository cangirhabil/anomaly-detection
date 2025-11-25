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
  Area, AreaChart, Bar, BarChart, Cell, ComposedChart, Pie, PieChart, ReferenceLine
} from 'recharts';
import { Activity, AlertTriangle, Settings, RefreshCw, Database, Gauge, PieChart as PieIcon } from 'lucide-react';

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
  };
}

export default function Dashboard() {
  const [chartData, setChartData] = useState<ChartDataPoint[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [lastAnomaly, setLastAnomaly] = useState<ReadingData | null>(null);
  const [totalReadings, setTotalReadings] = useState(0);
  const [anomalyCount, setAnomalyCount] = useState(0);
  const [sensorStats, setSensorStats] = useState<SensorStats>({});
  const [sensorHistory, setSensorHistory] = useState<Record<string, ChartDataPoint[]>>({});
  const [selectedSensor, setSelectedSensor] = useState<string | null>(null);
  const [anomalyHistory, setAnomalyHistory] = useState<AnomalyLog[]>([]);
  const [allDataLogs, setAllDataLogs] = useState<DataLog[]>([]);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'anomaly-logs' | 'data-logs'>('dashboard');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    connectWebSocket();
    fetchAnomalyHistory();
    fetchAllDataLogs();
    
    // Her 10 saniyede bir logları güncelle
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
          console.log('📨 Gelen mesaj:', message);
          
          if (message.type === 'reading' && message.data) {
            const reading: ReadingData = message.data;
            
            // Toplam okuma sayısını artır
            setTotalReadings(prev => prev + 1);
            
            // Tüm veri loglarına ekle
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
              return [newLog, ...prev].slice(0, 200); // Son 200 veri
            });
            
            // Anomali sayacı
            if (reading.is_anomaly) {
              setAnomalyCount(prev => prev + 1);
              setLastAnomaly(reading);
              
              // Anomali geçmişine ekle
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
                return newHistory.slice(0, 50); // Son 50 anomali
              });
            }
            
            // Sensör istatistiklerini güncelle
            setSensorStats(prev => ({
              ...prev,
              [reading.sensor_type]: {
                current: reading.current_value,
                z_score: reading.z_score,
                is_anomaly: reading.is_anomaly,
                count: (prev[reading.sensor_type]?.count || 0) + 1
              }
            }));

            // Grafik verisini güncelle
            const time = new Date(reading.timestamp).toLocaleTimeString('tr-TR');
            const newPoint: ChartDataPoint = {
              time,
              value: reading.current_value,
              mean: reading.mean,
              threshold: reading.threshold,
              anomaly: reading.is_anomaly ? reading.current_value : undefined
            };
            
            setChartData(prev => {
              const updated = [...prev, newPoint];
              return updated.slice(-100); // Son 100 veri
            });

            // Sensör geçmişini güncelle
            setSensorHistory(prev => {
              const currentHistory = prev[reading.sensor_type] || [];
              const newHistory = [...currentHistory, newPoint].slice(-100);
              return {
                ...prev,
                [reading.sensor_type]: newHistory
              };
            });

            // İlk sensörü seç
            setSelectedSensor(prev => prev || reading.sensor_type);
          }
        } catch (error) {
          console.error('Mesaj işleme hatası:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('❌ WebSocket hatası:', error);
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log('⚠️ WebSocket bağlantısı kapandı, 3 saniye sonra yeniden bağlanılacak...');
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

  const updateConfig = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          z_score_threshold: 3.0,
          window_size: 100
        }),
      });
      if (response.ok) {
        alert('Konfigürasyon güncellendi!');
      }
    } catch (error) {
      console.error('Konfigürasyon güncelleme hatası:', error);
    }
  };

  const resetSystem = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/reset', {
        method: 'POST',
      });
      if (response.ok) {
        setChartData([]);
        setTotalReadings(0);
        setAnomalyCount(0);
        setSensorStats({});
        setLastAnomaly(null);
        setAnomalyHistory([]);
        alert('Sistem sıfırlandı!');
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
      case 'critical': return 'text-red-700 bg-red-100 dark:bg-red-900 dark:text-red-200';
      case 'warning': return 'text-orange-700 bg-orange-100 dark:bg-orange-900 dark:text-orange-200';
      default: return 'text-yellow-700 bg-yellow-100 dark:bg-yellow-900 dark:text-yellow-200';
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-8 dark:bg-slate-950">
      <div className="mx-auto max-w-7xl space-y-8">
        
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">
              Endüstriyel Anomali Tespit Sistemi
            </h1>
            <p className="text-slate-500 dark:text-slate-400">
              Gerçek zamanlı sensör verisi izleme ve anomali tespiti
            </p>
          </div>
          <div className="flex items-center gap-4">
            <Badge variant={isConnected ? "default" : "destructive"} className="h-8 px-4 text-sm">
              {isConnected ? "🟢 Bağlı" : "🔴 Bağlantı Kesildi"}
            </Badge>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-2 border-b border-slate-200 dark:border-slate-800">
          <Button
            variant={activeTab === 'dashboard' ? 'default' : 'ghost'}
            onClick={() => setActiveTab('dashboard')}
            className="rounded-b-none"
          >
            <Activity className="mr-2 h-4 w-4" />
            Dashboard
          </Button>
          <Button
            variant={activeTab === 'anomaly-logs' ? 'default' : 'ghost'}
            onClick={() => setActiveTab('anomaly-logs')}
            className="rounded-b-none"
          >
            <AlertTriangle className="mr-2 h-4 w-4" />
            Anomali Logları ({anomalyHistory.length})
          </Button>
          <Button
            variant={activeTab === 'data-logs' ? 'default' : 'ghost'}
            onClick={() => setActiveTab('data-logs')}
            className="rounded-b-none"
          >
            <Database className="mr-2 h-4 w-4" />
            Tüm Veri Logları ({allDataLogs.length})
          </Button>
        </div>

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="space-y-8">
            {/* Fleet View - Sensor Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {Object.entries(sensorStats).map(([sensor, stats]) => (
                <Card 
                  key={sensor}
                  className={`cursor-pointer transition-all hover:shadow-md ${selectedSensor === sensor ? 'ring-2 ring-blue-500' : ''}`}
                  onClick={() => setSelectedSensor(sensor)}
                >
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">
                      {sensor}
                    </CardTitle>
                    {stats.is_anomaly ? (
                      <AlertTriangle className="h-4 w-4 text-red-500" />
                    ) : (
                      <Activity className="h-4 w-4 text-slate-500" />
                    )}
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{stats.current.toFixed(2)}</div>
                    <div className="flex items-center justify-between mt-1">
                      <p className="text-xs text-slate-500">
                        Z-Score: <span className={Math.abs(stats.z_score) > 3 ? "text-red-500 font-bold" : ""}>{stats.z_score.toFixed(2)}</span>
                      </p>
                      <Badge variant={stats.is_anomaly ? "destructive" : "secondary"} className="text-[10px] h-5">
                        {stats.is_anomaly ? "ANOMALİ" : "NORMAL"}
                      </Badge>
                    </div>
                    {/* Sparkline */}
                    <div className="h-[40px] mt-3">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={sensorHistory[sensor] || []}>
                          <Line 
                            type="monotone" 
                            dataKey="value" 
                            stroke={stats.is_anomaly ? "#ef4444" : "#2563eb"} 
                            strokeWidth={2} 
                            dot={false} 
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              ))}
              
              {/* Summary Cards */}
              <Card className="bg-slate-50 dark:bg-slate-900 border-dashed">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-slate-500">Sistem Özeti</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Toplam Okuma:</span>
                      <span className="font-bold">{totalReadings}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Anomali:</span>
                      <span className="font-bold text-red-600">{anomalyCount}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Aktif Sensör:</span>
                      <span className="font-bold">{Object.keys(sensorStats).length}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Detailed Analysis */}
            <div className="grid gap-8 md:grid-cols-3">
              
              {/* Main Control Chart */}
              <Card className="col-span-2">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        <Activity className="h-5 w-5" />
                        {selectedSensor ? `${selectedSensor} - Kontrol Grafiği` : 'Sensör Analizi'}
                      </CardTitle>
                      <CardDescription>
                        {selectedSensor 
                          ? '3-Sigma kontrol limitleri ve anomali noktaları' 
                          : 'Detaylı analiz için yukarıdan bir sensör seçin'}
                      </CardDescription>
                    </div>
                    {selectedSensor && (
                      <Badge variant="outline" className="font-mono">
                        {sensorHistory[selectedSensor]?.length || 0} Veri Noktası
                      </Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  {!selectedSensor ? (
                    <div className="h-[400px] w-full flex items-center justify-center text-slate-400 bg-slate-50/50 dark:bg-slate-900/50 rounded-lg border border-dashed">
                      <div className="text-center">
                        <Activity className="h-12 w-12 mx-auto mb-2 opacity-50" />
                        <p>Analiz etmek için bir sensör seçin</p>
                      </div>
                    </div>
                  ) : (
                    <div className="h-[400px] w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={sensorHistory[selectedSensor] || []}>
                          <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                          <XAxis 
                            dataKey="time" 
                            tick={{ fontSize: 10 }}
                            interval="preserveStartEnd"
                          />
                          <YAxis domain={['auto', 'auto']} />
                          <Tooltip 
                            contentStyle={{ 
                              backgroundColor: 'rgba(255, 255, 255, 0.95)', 
                              borderRadius: '8px', 
                              border: '1px solid #e2e8f0',
                              boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' 
                            }}
                          />
                          <Legend />
                          
                          {/* 3-Sigma Area (Mean +/- 3 StdDev approx) */}
                          <Area 
                            type="monotone" 
                            dataKey="threshold" 
                            fill="#f1f5f9" 
                            stroke="none" 
                            name="Normal Aralık"
                          />
                          
                          <Line 
                            type="monotone" 
                            dataKey="value" 
                            stroke="#2563eb" 
                            strokeWidth={2} 
                            dot={false}
                            name="Değer"
                          />
                          
                          <Line 
                            type="monotone" 
                            dataKey="mean" 
                            stroke="#10b981" 
                            strokeWidth={1}
                            strokeDasharray="5 5" 
                            dot={false}
                            name="Ortalama"
                          />
                          
                          <Line 
                            type="monotone" 
                            dataKey="anomaly" 
                            stroke="#ef4444" 
                            strokeWidth={0}
                            dot={{ r: 6, fill: '#ef4444', strokeWidth: 2, stroke: '#fff' }}
                            name="Anomali"
                          />
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Side Panel - Gauge & Stats */}
              <div className="space-y-6">
                
                {/* Z-Score Gauge */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Gauge className="h-5 w-5" />
                      Anomali Skoru (Z-Score)
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-col items-center justify-center py-6">
                    {selectedSensor && sensorStats[selectedSensor] ? (
                      <>
                        <div className="relative flex items-center justify-center">
                          <PieChart width={200} height={100}>
                            <Pie
                              data={[
                                { value: 3, fill: '#22c55e' },  // Normal
                                { value: 2, fill: '#eab308' },  // Warning
                                { value: 1, fill: '#ef4444' },  // Critical
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
                          <div className="absolute bottom-0 text-center">
                            <div className="text-3xl font-bold">
                              {Math.abs(sensorStats[selectedSensor].z_score).toFixed(1)}
                            </div>
                            <div className="text-xs text-slate-500">Z-Score</div>
                          </div>
                        </div>
                        <div className="mt-4 text-center">
                          <Badge variant={sensorStats[selectedSensor].is_anomaly ? "destructive" : "outline"} className="text-sm px-4 py-1">
                            {sensorStats[selectedSensor].is_anomaly ? "KRİTİK SEVİYE" : "NORMAL SEVİYE"}
                          </Badge>
                        </div>
                      </>
                    ) : (
                      <div className="text-slate-400 text-center py-8">
                        <p>Sensör seçilmedi</p>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Anomaly Distribution */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <PieIcon className="h-5 w-5" />
                      Anomali Dağılımı
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[200px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={[
                              { name: 'Normal', value: totalReadings - anomalyCount, fill: '#22c55e' },
                              { name: 'Anomali', value: anomalyCount, fill: '#ef4444' },
                            ]}
                            cx="50%"
                            cy="50%"
                            innerRadius={60}
                            outerRadius={80}
                            paddingAngle={5}
                            dataKey="value"
                          >
                            <Cell key="normal" fill="#22c55e" />
                            <Cell key="anomaly" fill="#ef4444" />
                          </Pie>
                          <Tooltip />
                          <Legend verticalAlign="bottom" height={36}/>
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>

                {/* System Controls */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium">Hızlı İşlemler</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <Button 
                      className="w-full" 
                      variant="outline"
                      onClick={resetSystem}
                      size="sm"
                    >
                      <RefreshCw className="mr-2 h-4 w-4" /> Sistemi Sıfırla
                    </Button>
                  </CardContent>
                </Card>

              </div>
            </div>
          </div>
        )}

        {/* Anomaly Logs Tab */}
        {activeTab === 'anomaly-logs' && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-red-500" />
                    Anomali Logları
                  </CardTitle>
                  <CardDescription>
                    Tespit edilen tüm anomalilerin detaylı kayıtları
                  </CardDescription>
                </div>
                <Button onClick={fetchAnomalyHistory} variant="outline" size="sm">
                  <RefreshCw className="mr-2 h-4 w-4" /> Yenile
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {anomalyHistory.length === 0 ? (
                <div className="text-center py-12 text-slate-400">
                  <AlertTriangle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Henüz anomali kaydı bulunmuyor</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="border-b bg-slate-50 dark:bg-slate-900">
                      <tr>
                        <th className="px-4 py-3 text-left font-medium">Zaman</th>
                        <th className="px-4 py-3 text-left font-medium">Sensör Tipi</th>
                        <th className="px-4 py-3 text-right font-medium">Değer</th>
                        <th className="px-4 py-3 text-right font-medium">Z-Score</th>
                        <th className="px-4 py-3 text-center font-medium">Seviye</th>
                        <th className="px-4 py-3 text-left font-medium">Açıklama</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {anomalyHistory.map((anomaly, index) => (
                        <tr key={index} className="hover:bg-slate-50 dark:hover:bg-slate-900">
                          <td className="px-4 py-3 text-slate-600 dark:text-slate-300 font-mono text-xs">
                            {formatTimestamp(anomaly.timestamp)}
                          </td>
                          <td className="px-4 py-3 font-medium">
                            {anomaly.sensor_type}
                          </td>
                          <td className="px-4 py-3 text-right font-mono">
                            {anomaly.current_value.toFixed(2)}
                            {anomaly.unit && <span className="text-xs text-slate-500 ml-1">{anomaly.unit}</span>}
                          </td>
                          <td className="px-4 py-3 text-right font-mono font-bold text-red-600">
                            {anomaly.z_score.toFixed(2)}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <Badge className={getSeverityColor(anomaly.severity)}>
                              {anomaly.severity}
                            </Badge>
                          </td>
                          <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">
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

        {/* All Data Logs Tab */}
        {activeTab === 'data-logs' && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Database className="h-5 w-5 text-blue-500" />
                    Tüm Veri Logları
                  </CardTitle>
                  <CardDescription>
                    Sisteme gelen tüm sensör verilerinin kayıtları (normal + anomali)
                  </CardDescription>
                </div>
                <Button onClick={fetchAllDataLogs} variant="outline" size="sm">
                  <RefreshCw className="mr-2 h-4 w-4" /> Yenile
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {allDataLogs.length === 0 ? (
                <div className="text-center py-12 text-slate-400">
                  <Database className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Henüz veri kaydı bulunmuyor</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="border-b bg-slate-50 dark:bg-slate-900">
                      <tr>
                        <th className="px-4 py-3 text-left font-medium">Zaman</th>
                        <th className="px-4 py-3 text-left font-medium">Sensör Tipi</th>
                        <th className="px-4 py-3 text-right font-medium">Değer</th>
                        <th className="px-4 py-3 text-right font-medium">Ortalama</th>
                        <th className="px-4 py-3 text-right font-medium">Std Dev</th>
                        <th className="px-4 py-3 text-right font-medium">Z-Score</th>
                        <th className="px-4 py-3 text-center font-medium">Durum</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {allDataLogs.map((log, index) => (
                        <tr 
                          key={index} 
                          className={`hover:bg-slate-50 dark:hover:bg-slate-900 ${
                            log.is_anomaly ? 'bg-red-50 dark:bg-red-900/10' : ''
                          }`}
                        >
                          <td className="px-4 py-3 text-slate-600 dark:text-slate-300 font-mono text-xs">
                            {formatTimestamp(log.timestamp)}
                          </td>
                          <td className="px-4 py-3 font-medium">
                            {log.sensor_type}
                          </td>
                          <td className="px-4 py-3 text-right font-mono font-bold">
                            {log.current_value.toFixed(2)}
                            {log.unit && <span className="text-xs text-slate-500 ml-1">{log.unit}</span>}
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-slate-600">
                            {log.mean.toFixed(2)}
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-slate-600">
                            {log.std_dev.toFixed(2)}
                          </td>
                          <td className={`px-4 py-3 text-right font-mono font-bold ${
                            log.is_anomaly ? 'text-red-600' : 'text-slate-600'
                          }`}>
                            {log.z_score.toFixed(2)}
                          </td>
                          <td className="px-4 py-3 text-center">
                            {log.is_anomaly ? (
                              <Badge variant="destructive" className="text-xs">
                                ⚠️ Anomali
                              </Badge>
                            ) : (
                              <Badge variant="secondary" className="text-xs">
                                ✓ Normal
                              </Badge>
                            )}
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
        
      </div>
    </div>
  );
}
