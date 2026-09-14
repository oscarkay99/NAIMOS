"use client";

import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import type { Map as MLMap, Marker } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { MapFeature } from "@/lib/types";

const STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";

const LAYER_COLORS: Record<string, string> = {
  incident: "#c33f2e",
  water_body: "#1d6fa5",
  protected_area: "#1a7f4f",
  forest_reserve: "#3f7d3f",
  ai_detection: "#7a3fc9",
};

const RISK_COLORS: Record<string, string> = {
  LOW: "#1a7f4f",
  MODERATE: "#c98a12",
  ELEVATED: "#d9701e",
  HIGH: "#c33f2e",
  CRITICAL: "#821f2e",
};

function markerColor(feature: MapFeature): string {
  if (feature.layer === "incident" && feature.risk_category) {
    return RISK_COLORS[feature.risk_category] || LAYER_COLORS.incident;
  }
  return LAYER_COLORS[feature.layer] || "#334155";
}

export function MapPanel({
  features,
  onFeatureClick,
  onMapClick,
  center = [-1.3, 6.5],
  zoom = 6.3,
  heightClass = "h-full",
  activeLayers,
}: {
  features: MapFeature[];
  onFeatureClick?: (feature: MapFeature) => void;
  onMapClick?: (lat: number, lon: number) => void;
  center?: [number, number];
  zoom?: number;
  heightClass?: string;
  activeLayers?: Set<string>;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const markersRef = useRef<Marker[]>([]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLE_URL,
      center,
      zoom,
    });
    map.addControl(new maplibregl.NavigationControl(), "top-right");
    mapRef.current = map;

    if (onMapClick) {
      map.on("click", (e) => {
        onMapClick(e.lngLat.lat, e.lngLat.lng);
      });
    }

    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    const visible = activeLayers ? features.filter((f) => activeLayers.has(f.layer)) : features;

    visible.forEach((feature) => {
      const el = document.createElement("div");
      const size = feature.layer === "incident" ? 14 : 10;
      el.style.width = `${size}px`;
      el.style.height = `${size}px`;
      el.style.borderRadius = feature.layer === "water_body" ? "2px" : "50%";
      el.style.background = markerColor(feature);
      el.style.border = "2px solid white";
      el.style.boxShadow = "0 1px 4px rgba(0,0,0,0.4)";
      el.style.cursor = "pointer";

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([feature.longitude, feature.latitude])
        .setPopup(
          new maplibregl.Popup({ offset: 12, closeButton: false }).setHTML(
            `<div style="font-size:12px;font-weight:600;color:#131c2b">${feature.name}</div>` +
              (feature.risk_category
                ? `<div style="font-size:11px;color:#64748b;margin-top:2px">Risk: ${feature.risk_score} (${feature.risk_category})</div>`
                : "")
          )
        )
        .addTo(map);

      if (onFeatureClick) {
        el.addEventListener("click", () => onFeatureClick(feature));
      }

      markersRef.current.push(marker);
    });
  }, [features, activeLayers, onFeatureClick]);

  return <div ref={containerRef} className={`${heightClass} w-full rounded-lg overflow-hidden`} />;
}
