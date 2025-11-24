"use client"

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, AlertTriangle, Settings, Play, Zap, RefreshCw } from 'lucide-react';

interface SensorData {
  timestamp: number;
  value: number;
  is_anomaly: boolean;
  anomaly_score: number;
  threshold: number;
}

interface Config {
  threshold: number;
  window_size: number;
}

export default function Dashboard() {
  const [data, setData] = useState<SensorData[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [config, setConfig] = useState<Config>({ threshold: 3.0, window_size: 20 });
  const [lastAnomaly, setLastAnomaly] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [simulating, setSimulating] = useState(false);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const connectWebSocket = () => {
    const ws = new WebSocket('ws://localhost:8000/ws');
    
    ws.onopen = () => {
      setIsConnected(true);
      console.log('Connected to WebSocket');
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      
      if (message.type === 'data') {
        const newData = message.data;
        setData(prev => {
          const updated = [...prev, newData].slice(-50); // Keep last 50 points
          return updated;
        });
        
        if (newData.is_anomaly) {
          setLastAnomaly(new Date().toLocaleTimeString());
        }
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      setTimeout(connectWebSocket, 3000); // Reconnect
    };

    wsRef.current = ws;
  };

  const updateConfig = async () => {
    try {
      await fetch('http://localhost:8000/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      alert('Config updated!');
    } catch (error) {
      console.error('Failed to update config', error);
    }
  };

  const runSimulation = async (scenario: string) => {
    setSimulating(true);
    try {
      await fetch(`http://localhost:8000/simulate/${scenario}`, { method: 'POST' });
    } catch (error) {
      console.error('Simulation failed', error);
    } finally {
      setTimeout(() => setSimulating(false), 2000);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-8 dark:bg-slate-950">
      <div className="mx-auto max-w-7xl space-y-8">
        
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">
              Anomaly Detection System
            </h1>
            <p className="text-slate-500 dark:text-slate-400">
              Real-time monitoring and control dashboard
            </p>
          </div>
          <div className="flex items-center gap-4">
            <Badge variant={isConnected ? "default" : "destructive"} className="h-8 px-4 text-sm">
              {isConnected ? "System Online" : "Disconnected"}
            </Badge>
          </div>
        </div>

        {/* Main Grid */}
        <div className="grid gap-8 md:grid-cols-3">
          
          {/* Chart Section */}
          <Card className="col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                Real-time Sensor Data
              </CardTitle>
              <CardDescription>
                Live stream from production line sensors
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[400px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                    <XAxis dataKey="timestamp" tick={false} />
                    <YAxis domain={['auto', 'auto']} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.9)', borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="value" 
                      stroke="#2563eb" 
                      strokeWidth={2} 
                      dot={false}
                      isAnimationActive={false}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="threshold" 
                      stroke="#ef4444" 
                      strokeDasharray="5 5" 
                      dot={false} 
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Controls & Status */}
          <div className="space-y-8">
            
            {/* Status Card */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5" />
                  System Status
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {lastAnomaly && (
                  <Alert variant="destructive">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertTitle>Anomaly Detected</AlertTitle>
                    <AlertDescription>
                      Last event at {lastAnomaly}
                    </AlertDescription>
                  </Alert>
                )}
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Current Value</span>
                    <span className="font-mono font-bold">
                      {data.length > 0 ? data[data.length - 1].value.toFixed(2) : '--'}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Anomaly Score</span>
                    <span className="font-mono font-bold">
                      {data.length > 0 ? data[data.length - 1].anomaly_score.toFixed(2) : '--'}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Simulation Controls */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5" />
                  Simulation
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Button 
                  className="w-full" 
                  variant="outline"
                  onClick={() => runSimulation('normal')}
                  disabled={simulating}
                >
                  <Play className="mr-2 h-4 w-4" /> Normal Operation
                </Button>
                <Button 
                  className="w-full" 
                  variant="destructive"
                  onClick={() => runSimulation('bottle_jam')}
                  disabled={simulating}
                >
                  <AlertTriangle className="mr-2 h-4 w-4" /> Trigger Bottle Jam
                </Button>
                <Button 
                  className="w-full" 
                  variant="secondary"
                  onClick={() => runSimulation('power_fluctuation')}
                  disabled={simulating}
                >
                  <Activity className="mr-2 h-4 w-4" /> Power Fluctuation
                </Button>
              </CardContent>
            </Card>

            {/* Configuration */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  Configuration
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Sensitivity Threshold</Label>
                  <Input 
                    type="number" 
                    value={config.threshold}
                    onChange={(e) => setConfig({...config, threshold: parseFloat(e.target.value)})}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Window Size</Label>
                  <Input 
                    type="number" 
                    value={config.window_size}
                    onChange={(e) => setConfig({...config, window_size: parseInt(e.target.value)})}
                  />
                </div>
                <Button className="w-full" onClick={updateConfig}>
                  <RefreshCw className="mr-2 h-4 w-4" /> Update Config
                </Button>
              </CardContent>
            </Card>

          </div>
        </div>
      </div>
    </div>
  );
}
