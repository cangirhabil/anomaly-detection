"use client"

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Activity, AlertTriangle, Settings, RefreshCw, Database } from 'lucide-react';

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
}

interface ChartDataPoint {
  time: string;
  value: number;
  mean: number;
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
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    connectWebSocket();
    return () => {
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
            
            // Anomali sayacı
            if (reading.is_anomaly) {
              setAnomalyCount(prev => prev + 1);
              setLastAnomaly(reading);
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
              anomaly: reading.is_anomaly ? reading.current_value : undefined
            };
            
            setChartData(prev => {
              const updated = [...prev, newPoint];
              return updated.slice(-100); // Son 100 veri
            });
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
        alert('Sistem sıfırlandı!');
      }
    } catch (error) {
      console.error('Sistem sıfırlama hatası:', error);
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

        {/* İstatistikler */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Toplam Okuma</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{totalReadings}</div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Anomali Sayısı</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{anomalyCount}</div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Aktif Sensör</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{Object.keys(sensorStats).length}</div>
            </CardContent>
          </Card>
        </div>

        {/* Main Grid */}
        <div className="grid gap-8 md:grid-cols-3">
          
          {/* Chart Section */}
          <Card className="col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                Gerçek Zamanlı Sensör Verileri
              </CardTitle>
              <CardDescription>
                {chartData.length > 0 ? `Son ${chartData.length} veri noktası` : 'Veri bekleniyor...'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {chartData.length === 0 ? (
                <div className="h-[400px] w-full flex items-center justify-center text-slate-400">
                  <div className="text-center">
                    <Database className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p>Veri akışı bekleniyor...</p>
                    <p className="text-sm mt-2">Terminal'den veri göndermeye başlayın</p>
                  </div>
                </div>
              ) : (
                <div className="h-[400px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                      <XAxis 
                        dataKey="time" 
                        tick={{ fontSize: 10 }}
                        interval="preserveStartEnd"
                      />
                      <YAxis />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: 'rgba(255, 255, 255, 0.95)', 
                          borderRadius: '8px', 
                          border: '1px solid #e2e8f0',
                          boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' 
                        }}
                      />
                      <Legend />
                      <Line 
                        type="monotone" 
                        dataKey="value" 
                        stroke="#2563eb" 
                        strokeWidth={2} 
                        dot={false}
                        name="Değer"
                        isAnimationActive={false}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="mean" 
                        stroke="#10b981" 
                        strokeWidth={1}
                        strokeDasharray="5 5" 
                        dot={false}
                        name="Ortalama"
                        isAnimationActive={false}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="anomaly" 
                        stroke="#ef4444" 
                        strokeWidth={0}
                        dot={{ r: 5, fill: '#ef4444' }}
                        name="Anomali"
                        isAnimationActive={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Controls & Status */}
          <div className="space-y-6">
            
            {/* Status Card */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5" />
                  Sistem Durumu
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {lastAnomaly && (
                  <Alert variant="destructive">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertTitle>Anomali Tespit Edildi!</AlertTitle>
                    <AlertDescription>
                      <div className="text-xs space-y-1 mt-2">
                        <div><strong>Sensör:</strong> {lastAnomaly.sensor_type}</div>
                        <div><strong>Değer:</strong> {lastAnomaly.current_value.toFixed(2)}</div>
                        <div><strong>Z-Score:</strong> {lastAnomaly.z_score.toFixed(2)}</div>
                        <div><strong>Zaman:</strong> {new Date(lastAnomaly.timestamp).toLocaleTimeString('tr-TR')}</div>
                      </div>
                    </AlertDescription>
                  </Alert>
                )}
                
                {!lastAnomaly && totalReadings === 0 && (
                  <div className="text-sm text-slate-500 text-center py-4">
                    Henüz veri alınmadı
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Sensör İstatistikleri */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Sensör İstatistikleri
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 max-h-[300px] overflow-y-auto">
                  {Object.entries(sensorStats).map(([sensor, stats]) => (
                    <div key={sensor} className="border-b pb-2 last:border-b-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium">{sensor}</span>
                        <Badge variant={stats.is_anomaly ? "destructive" : "secondary"} className="text-xs">
                          {stats.is_anomaly ? "⚠️" : "✓"}
                        </Badge>
                      </div>
                      <div className="text-xs text-slate-500 space-y-0.5">
                        <div>Değer: {stats.current.toFixed(2)}</div>
                        <div>Z-Score: {stats.z_score.toFixed(2)}</div>
                        <div>Okuma: {stats.count}</div>
                      </div>
                    </div>
                  ))}
                  
                  {Object.keys(sensorStats).length === 0 && (
                    <div className="text-sm text-slate-400 text-center py-4">
                      Sensör verisi bekleniyor...
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Sistem Kontrolleri */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  Sistem Kontrolleri
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button 
                  className="w-full" 
                  variant="destructive"
                  onClick={resetSystem}
                  size="sm"
                >
                  <RefreshCw className="mr-2 h-4 w-4" /> Sistemi Sıfırla
                </Button>
                
                <div className="text-xs text-slate-400 text-center pt-2">
                  Terminal'den veri gönderin:<br/>
                  <code className="bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded mt-1 inline-block">
                    python send_sensor_data.py
                  </code>
                </div>
              </CardContent>
            </Card>

          </div>
        </div>
      </div>
    </div>
  );
}
