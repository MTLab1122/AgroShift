"use client";

import React, { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { FarmProfile } from "@/types/farm";
import {
  BackendUnavailableError,
  farmApiService,
  getApiErrorMessage,
} from "@/lib/api/farmApi";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import {
  Mic,
  MicOff,
  Send,
  Bot,
  User,
  Sparkles,
  AlertTriangle,
  FileCheck,
} from "lucide-react";

// Dynamically load Map component with SSR disabled
const FarmMap = dynamic(
  () => import("@/components/map/FarmMap").then((mod) => mod.FarmMap),
  {
    ssr: false,
    loading: () => (
      <div className="h-[360px] bg-slate-100 animate-pulse flex items-center justify-center text-slate-400 text-sm rounded-xl">
        Loading Satellite Map Engine...
      </div>
    ),
  }
);

interface Message {
  id: string;
  sender: "assistant" | "user";
  text: string;
  timestamp: string;
}

interface SpeechRecognitionAlternativeLike {
  transcript: string;
}

interface SpeechRecognitionResultLike extends ArrayLike<SpeechRecognitionAlternativeLike> {
  isFinal: boolean;
}

interface SpeechRecognitionEventLike extends Event {
  results: ArrayLike<SpeechRecognitionResultLike>;
}

interface SpeechRecognitionLike {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: Event) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}

interface SpeechRecognitionWindow extends Window {
  SpeechRecognition?: new () => SpeechRecognitionLike;
  webkitSpeechRecognition?: new () => SpeechRecognitionLike;
}

interface AssistantProps {
  onSaveFarm: (farm: FarmProfile) => Promise<boolean>;
  isSaving: boolean;
}

export function ConversationalAssistant({ onSaveFarm, isSaving }: AssistantProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "msg-1",
      sender: "assistant",
      text: "Salam and Welcome to AgroShift Farm Registration. I can help you register your farm profile step-by-step. What is the name of your farm and who is the owner?",
      timestamp: "Just now",
    },
  ]);

  const [inputMessage, setInputMessage] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [voiceSupportedNotice, setVoiceSupportedNotice] = useState<string | null>(null);
  const [isChatting, setIsChatting] = useState(false);
  const [sessionId] = useState(() => `farm-registration-${Date.now()}`);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  // Extracted structured draft from conversation
  const [draftFarm, setDraftFarm] = useState<Partial<FarmProfile>>({
    farm_id: `farm-${Date.now().toString().slice(-4)}`,
    name: "Peshawar South Research Farm",
    owner_name: "Azizullah Khan",
    contact_phone: "+92 301 5556677",
    preferred_language: "en",
    location: {
      latitude: 34.0151,
      longitude: 71.5249,
      district: "Peshawar",
      province_or_region: "Khyber Pakhtunkhwa",
      country: "Pakistan",
      village_or_town: "Palosi",
    },
    total_area_hectares: 10.5,
    soil_type: "alluvial_clay",
    irrigation_source: "canal",
    current_crops: ["Wheat"],
  });

  const [missingFields, setMissingFields] = useState<string[]>([]);
  const [isConfirmed, setIsConfirmed] = useState(false);

  useEffect(() => () => recognitionRef.current?.stop(), []);

  const handleSendMessage = async () => {
    const message = inputMessage.trim();
    if (!message || isChatting) return;

    const userMsg: Message = {
      id: `usr-${Date.now()}`,
      sender: "user",
      text: message,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage("");
    setIsChatting(true);
    try {
      const response = await farmApiService.chatWithAssistant(
        sessionId,
        message,
        draftFarm.preferred_language || "en",
        draftFarm
      );
      const extracted = response.data.extracted_farm;
      setDraftFarm((previous) => ({
        ...previous,
        ...extracted,
        farm_id: previous.farm_id,
        location: extracted.location
          ? { ...previous.location, ...extracted.location }
          : previous.location,
        boundary: previous.boundary,
      }));
      setMissingFields(response.data.missing_fields);
      setMessages((prev) => [
        ...prev,
        {
          id: `ast-${Date.now()}`,
          sender: "assistant",
          text: response.data.reply_message,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } catch (error) {
      const reply = error instanceof BackendUnavailableError
        ? "The registration assistant is unavailable. You can still update the profile fields and map manually."
        : `The registration assistant request failed: ${getApiErrorMessage(error)}`;
      setMessages((prev) => [
        ...prev,
        {
          id: `ast-${Date.now()}`,
          sender: "assistant",
          text: reply,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setIsChatting(false);
    }
  };

  const handleMicToggle = () => {
    if (isRecording) {
      recognitionRef.current?.stop();
      return;
    }

    const speechWindow = window as SpeechRecognitionWindow;
    const SpeechRecognition =
      speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setVoiceSupportedNotice("Browser speech recognition is unavailable. Please use the text input.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang =
      draftFarm.preferred_language === "ur"
        ? "ur-PK"
        : draftFarm.preferred_language === "ps"
          ? "ps-AF"
          : "en-US";
    recognition.interimResults = true;
    recognition.continuous = false;
    let recognitionFailed = false;
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0]?.transcript || "")
        .join("");
      setInputMessage(transcript);
    };
    recognition.onerror = () => {
      recognitionFailed = true;
      setVoiceSupportedNotice("Speech recognition stopped. You can continue with the text input.");
      setIsRecording(false);
    };
    recognition.onend = () => {
      setIsRecording(false);
      if (!recognitionFailed) setVoiceSupportedNotice(null);
    };

    recognitionRef.current = recognition;
    setVoiceSupportedNotice(`Listening in ${recognition.lang}...`);
    setIsRecording(true);
    try {
      recognition.start();
    } catch (error) {
      setIsRecording(false);
      setVoiceSupportedNotice(getApiErrorMessage(error));
    }
  };

  const handleConfirmAndSave = async () => {
    const missing: string[] = [];
    if (!draftFarm.name) missing.push("Farm Name");
    if (!draftFarm.owner_name) missing.push("Owner Name");
    if (!draftFarm.total_area_hectares) missing.push("Total Area");
    if (!draftFarm.location?.latitude || !draftFarm.location?.longitude) missing.push("Coordinates");

    if (missing.length > 0) {
      setMissingFields(missing);
      return;
    }

    const completeFarm: FarmProfile = {
      farm_id: draftFarm.farm_id || `farm-${Date.now()}`,
      name: draftFarm.name!,
      owner_name: draftFarm.owner_name!,
      contact_phone: draftFarm.contact_phone || "+92 300 0000000",
      preferred_language: draftFarm.preferred_language || "en",
      location: draftFarm.location!,
      boundary: draftFarm.boundary,
      total_area_hectares: draftFarm.total_area_hectares!,
      soil_type: draftFarm.soil_type || "alluvial_clay",
      irrigation_source: draftFarm.irrigation_source || "canal",
      current_crops: draftFarm.current_crops || [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    const saved = await onSaveFarm(completeFarm);
    if (saved) setIsConfirmed(true);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
      {/* Left Column: Conversational Assistant */}
      <div className="lg:col-span-6 flex flex-col space-y-4">
        <Card className="border-forest-200 shadow-sm flex flex-col h-[580px]">
          <CardHeader className="bg-forest-950 text-white rounded-t-xl py-4 px-6 border-b border-forest-900">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3 rtl:space-x-reverse">
                <div className="p-2 bg-agrigreen-500 rounded-lg text-white">
                  <Bot className="w-5 h-5" />
                </div>
                <div>
                  <CardTitle className="text-white text-base">AgroShift Voice & Chat Assistant</CardTitle>
                  <CardDescription className="text-forest-200 text-xs">
                    Conversational Farm Intake & Context Gathering
                  </CardDescription>
                </div>
              </div>
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-forest-900 text-agrigreen-300 text-xs font-medium border border-forest-800">
                <Sparkles className="w-3.5 h-3.5" />
                Context Active
              </div>
            </div>
          </CardHeader>

          {/* Transcript Scroll Area */}
          <CardContent className="flex-1 overflow-y-auto p-4 space-y-3.5 bg-slate-50/70">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex items-start gap-2.5 ${
                  m.sender === "user" ? "flex-row-reverse" : "flex-row"
                }`}
              >
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-xs ${
                    m.sender === "user"
                      ? "bg-forest-700 text-white"
                      : "bg-emerald-100 text-emerald-800"
                  }`}
                >
                  {m.sender === "user" ? <User className="w-3.5 h-3.5" /> : <Bot className="w-4 h-4" />}
                </div>
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm ${
                    m.sender === "user"
                      ? "bg-forest-800 text-white rounded-tr-none"
                      : "bg-white text-slate-800 border border-slate-200 rounded-tl-none"
                  }`}
                >
                  <p>{m.text}</p>
                  <span
                    className={`block text-[10px] mt-1 ${
                      m.sender === "user" ? "text-forest-200" : "text-slate-400"
                    }`}
                  >
                    {m.timestamp}
                  </span>
                </div>
              </div>
            ))}
          </CardContent>

          {/* Voice status banner */}
          {voiceSupportedNotice && (
            <div className="px-4 py-2 bg-amber-50 border-t border-amber-200 text-amber-800 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 text-amber-600" />
              <span>{voiceSupportedNotice}</span>
            </div>
          )}

          {/* Message Input & Mic Controls */}
          <div className="p-3 bg-white border-t border-slate-200 rounded-b-xl">
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant={isRecording ? "destructive" : "outline"}
                size="icon"
                onClick={handleMicToggle}
                title={isRecording ? "Stop Recording" : "Start Voice Intake"}
              >
                {isRecording ? <MicOff className="w-4 h-4 animate-pulse" /> : <Mic className="w-4 h-4" />}
              </Button>

              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !isChatting && handleSendMessage()}
                placeholder="Type farm details or reply to assistant..."
                disabled={isChatting}
                className="flex-1 text-sm bg-slate-50 border border-slate-300 rounded-lg px-3.5 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />

              <Button
                type="button"
                onClick={handleSendMessage}
                disabled={!inputMessage.trim() || isChatting}
                className="bg-forest-700 hover:bg-forest-800"
                size="icon"
              >
                <Send className={`w-4 h-4 ${isChatting ? "animate-pulse" : ""}`} />
              </Button>
            </div>
          </div>
        </Card>

        {/* Backend Note */}
        <div className="text-xs text-slate-500 bg-white p-3 rounded-lg border border-slate-200">
          <strong className="text-slate-700">Conversational AI Architecture:</strong> Collects missing fields,
          clarifies coordinates, and presents an extracted structured confirmation card before saving. Text
          fallback is always available.
        </div>
      </div>

      {/* Right Column: Location Map & Confirmation Card */}
      <div className="lg:col-span-6 flex flex-col space-y-6">
        {/* Interactive Map */}
        <Card>
          <CardHeader className="py-4">
            <CardTitle className="text-base text-forest-950">Farm Location & Boundary</CardTitle>
            <CardDescription className="text-xs">
              Click pin to designate farm centroid; draw polygon to estimate boundaries
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-0">
            <FarmMap
              initialLat={draftFarm.location?.latitude || 34.0151}
              initialLng={draftFarm.location?.longitude || 71.5249}
              onLocationChange={(lat, lng) => {
                setDraftFarm((prev) => ({
                  ...prev,
                  location: {
                    latitude: lat,
                    longitude: lng,
                    district: prev.location?.district || "Peshawar",
                    province_or_region: prev.location?.province_or_region || "Khyber Pakhtunkhwa",
                    country: "Pakistan",
                    village_or_town: prev.location?.village_or_town || "Palosi",
                  },
                }));
              }}
              onBoundaryChange={(coords, estimatedHectares) => {
                if (coords.length >= 3) {
                  setDraftFarm((prev) => ({
                    ...prev,
                    boundary: {
                      type: "Polygon",
                      coordinates: [coords],
                    },
                    total_area_hectares: estimatedHectares || prev.total_area_hectares,
                  }));
                }
              }}
            />
          </CardContent>
        </Card>

        {/* Confirmation & Extraction Summary Card */}
        <Card className="border-forest-300">
          <CardHeader className="py-4 bg-forest-50/60 border-b border-forest-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileCheck className="w-5 h-5 text-forest-700" />
                <CardTitle className="text-base text-forest-900">Extracted Farm Profile Summary</CardTitle>
              </div>
              <span className="text-[11px] font-semibold text-forest-700 bg-forest-100 px-2 py-0.5 rounded">
                Verification Required
              </span>
            </div>
            <CardDescription className="text-xs">
              Verify all extracted parameters before submitting farm registration
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-4 space-y-4">
            {missingFields.length > 0 && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800">
                <strong>Missing required fields:</strong> {missingFields.join(", ")}
              </div>
            )}

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-400 block mb-0.5">Farm Name</span>
                <input
                  type="text"
                  value={draftFarm.name || ""}
                  onChange={(e) => setDraftFarm({ ...draftFarm, name: e.target.value })}
                  className="font-medium text-slate-800 bg-white border border-slate-300 rounded px-2 py-1 w-full"
                />
              </div>

              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-400 block mb-0.5">Owner / Farmer</span>
                <input
                  type="text"
                  value={draftFarm.owner_name || ""}
                  onChange={(e) => setDraftFarm({ ...draftFarm, owner_name: e.target.value })}
                  className="font-medium text-slate-800 bg-white border border-slate-300 rounded px-2 py-1 w-full"
                />
              </div>

              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-400 block mb-0.5">Total Area (Hectares)</span>
                <input
                  type="number"
                  step="0.1"
                  value={draftFarm.total_area_hectares || ""}
                  onChange={(e) =>
                    setDraftFarm({ ...draftFarm, total_area_hectares: parseFloat(e.target.value) || 0 })
                  }
                  className="font-medium text-slate-800 bg-white border border-slate-300 rounded px-2 py-1 w-full"
                />
              </div>

              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-400 block mb-0.5">Coordinates</span>
                <span className="font-semibold text-forest-800 block py-1">
                  {draftFarm.location?.latitude}° N, {draftFarm.location?.longitude}° E
                </span>
              </div>

              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-400 block mb-0.5">Soil Type</span>
                <select
                  value={draftFarm.soil_type || "alluvial_clay"}
                  onChange={(e) =>
                    setDraftFarm({ ...draftFarm, soil_type: e.target.value as FarmProfile["soil_type"] })
                  }
                  className="text-xs bg-white border border-slate-300 rounded px-2 py-1 w-full"
                >
                  <option value="alluvial_clay">Alluvial Clay</option>
                  <option value="sandy_loam">Sandy Loam</option>
                  <option value="clay_loam">Clay Loam</option>
                  <option value="silt_loam">Silt Loam</option>
                  <option value="sandy">Sandy</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-400 block mb-0.5">Irrigation Source</span>
                <select
                  value={draftFarm.irrigation_source || "canal"}
                  onChange={(e) =>
                    setDraftFarm({
                      ...draftFarm,
                      irrigation_source: e.target.value as FarmProfile["irrigation_source"],
                    })
                  }
                  className="text-xs bg-white border border-slate-300 rounded px-2 py-1 w-full"
                >
                  <option value="canal">Canal System</option>
                  <option value="tube_well">Tube Well</option>
                  <option value="river_lift">River Lift</option>
                  <option value="drip">Drip Irrigation</option>
                  <option value="rainfed">Rainfed</option>
                </select>
              </div>
            </div>

            <div className="pt-2">
              <Button
                type="button"
                onClick={handleConfirmAndSave}
                disabled={isSaving || isConfirmed}
                className="w-full bg-forest-700 hover:bg-forest-800 text-white font-medium py-2.5 rounded-lg shadow"
              >
                {isSaving ? "Registering Farm..." : isConfirmed ? "Farm Registered Successfully!" : "Confirm & Save Farm Profile"}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
