"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { LanguageSelector } from "@/components/common/LanguageSelector";
import {
  Sprout,
  LayoutDashboard,
  PlusCircle,
  MapPin,
  History,
  CloudSun,
} from "lucide-react";

export function SidebarLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { t, isRtl } = useLanguage();

  const navItems = [
    {
      label: t.nav.farms,
      href: "/farms",
      icon: LayoutDashboard,
      active: pathname === "/farms",
    },
    {
      label: t.nav.registerFarm,
      href: "/farms/new",
      icon: PlusCircle,
      active: pathname === "/farms/new",
    },
    {
      label: "Peshawar Demo Farm",
      href: "/farms/farm-peshawar-001",
      icon: MapPin,
      active: pathname?.startsWith("/farms/farm-peshawar-001"),
    },
    {
      label: "Crop History",
      href: "/farms/farm-peshawar-001/crop-history",
      icon: History,
      active: pathname?.includes("/crop-history"),
    },
  ];

  return (
    <div className={`min-h-screen flex bg-slate-50 ${isRtl ? "rtl" : "ltr"}`}>
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-forest-950 text-white flex flex-col shrink-0 border-r border-forest-900 hidden md:flex">
        {/* Brand */}
        <div className="p-5 border-b border-forest-900/60 flex items-center space-x-3 rtl:space-x-reverse">
          <div className="p-2 bg-agrigreen-500 rounded-lg text-white shadow-md">
            <Sprout className="w-6 h-6" />
          </div>
          <div>
            <h1 className="font-bold text-lg tracking-wide text-white">AgroShift</h1>
            <p className="text-xs text-agrigreen-300 font-medium">Farm Management</p>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 p-4 space-y-1.5 overflow-y-auto">
          <div className="text-[10px] uppercase font-bold text-forest-400 tracking-wider px-3 mb-2">
            Module 01 Navigation
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center space-x-3 rtl:space-x-reverse px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                  item.active
                    ? "bg-forest-800 text-white shadow-sm border border-forest-700 font-semibold"
                    : "text-forest-200 hover:bg-forest-900 hover:text-white"
                }`}
              >
                <Icon className={`w-4 h-4 ${item.active ? "text-agrigreen-400" : "text-forest-400"}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}

          <div className="pt-6">
            <div className="text-[10px] uppercase font-bold text-forest-400 tracking-wider px-3 mb-2">
              Cross-Module Links
            </div>
            <div className="flex items-center space-x-3 rtl:space-x-reverse px-3 py-2 rounded-lg text-xs text-forest-400 bg-forest-900/50">
              <CloudSun className="w-4 h-4 text-forest-400 shrink-0" />
              <span>Module 02 Climate API Active</span>
            </div>
          </div>
        </nav>

        {/* Footer Info */}
        <div className="p-4 border-t border-forest-900/60 text-xs text-forest-400">
          <p className="font-semibold text-forest-200">AgroShift v0.1.0</p>
          <p className="text-[11px] text-forest-400">NASA Space Apps 2026</p>
        </div>
      </aside>

      {/* Main Container */}
      <div className="flex-1 flex flex-col min-w-0 overflow-x-hidden">
        {/* Top Header */}
        <header className="sticky top-0 z-30 bg-white border-b border-slate-200 px-6 py-3.5 shadow-sm flex items-center justify-between">
          <div className="flex items-center space-x-3 rtl:space-x-reverse md:hidden">
            <div className="p-1.5 bg-agrigreen-600 text-white rounded-md">
              <Sprout className="w-5 h-5" />
            </div>
            <span className="font-bold text-slate-900">AgroShift</span>
          </div>

          <div className="hidden md:flex items-center space-x-2 rtl:space-x-reverse text-xs text-slate-500">
            <Link href="/farms" className="hover:text-forest-700">Farms</Link>
            <span>/</span>
            <span className="text-slate-800 font-medium">Management & Location</span>
          </div>

          <div className="flex items-center space-x-3 rtl:space-x-reverse ml-auto">
            <LanguageSelector />
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-6 md:p-8 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
