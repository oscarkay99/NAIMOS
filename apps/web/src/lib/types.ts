export type RoleName =
  | "SUPER_ADMIN"
  | "NATIONAL_ADMIN"
  | "OPERATIONS_MANAGER"
  | "FIELD_SUPERVISOR"
  | "FIELD_OFFICER"
  | "INTELLIGENCE_ANALYST"
  | "ENVIRONMENTAL_ANALYST"
  | "PRO"
  | "REPORT_VIEWER"
  | "AUDITOR";

export type IncidentStatus =
  | "NEW"
  | "UNDER_REVIEW"
  | "FIELD_VERIFICATION_REQUIRED"
  | "VERIFIED"
  | "UNVERIFIED"
  | "CLOSED"
  | "ARCHIVED";

export type VerificationStatus = "UNVERIFIED" | "PENDING_VERIFICATION" | "VERIFIED" | "REJECTED";

export type RiskCategory = "LOW" | "MODERATE" | "ELEVATED" | "HIGH" | "CRITICAL";

export type Priority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type IncidentType =
  | "SUSPECTED_ILLEGAL_MINING"
  | "LAND_DISTURBANCE"
  | "WATER_POLLUTION"
  | "VEGETATION_LOSS"
  | "UNAUTHORIZED_EQUIPMENT"
  | "OTHER";

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  role: { id: string; name: RoleName; description: string };
  badge_number: string | null;
  is_active: boolean;
  permissions: string[];
}

export interface Incident {
  id: string;
  reference_number: string;
  title: string;
  description: string;
  latitude: number;
  longitude: number;
  region_id: string | null;
  district_id: string | null;
  incident_type: IncidentType;
  source_type: string;
  status: IncidentStatus;
  verification_status: VerificationStatus;
  priority: Priority;
  classification: string;
  water_body_affected: boolean;
  protected_area_affected: boolean;
  equipment_observed: string | null;
  estimated_people_present: number | null;
  risk_score: number | null;
  is_demo: boolean;
  assigned_officer_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface IncidentStatusHistoryEntry {
  id: string;
  previous_status: IncidentStatus | null;
  new_status: IncidentStatus;
  changed_by: string | null;
  reason: string | null;
  changed_at: string;
}

export interface IncidentDetail extends Incident {
  status_history: IncidentStatusHistoryEntry[];
}

export interface RiskFactor {
  label: string;
  points: number;
  detail: string | null;
}

export interface RiskScoreOut {
  id: string;
  incident_id: string | null;
  score: number;
  category: RiskCategory;
  calculated_at: string;
  model_version: string;
  explanation: string | null;
  factors: RiskFactor[];
}

export interface MapFeature {
  id: string;
  layer: "incident" | "water_body" | "protected_area" | "forest_reserve" | "ai_detection";
  name: string;
  latitude: number;
  longitude: number;
  status: string | null;
  risk_score: number | null;
  risk_category: string | null;
}

export interface LocationIntelligence {
  latitude: number;
  longitude: number;
  region: string | null;
  district: string | null;
  risk_score: number | null;
  risk_category: string | null;
  risk_trend: string;
  nearest_water_body_name: string | null;
  nearest_water_body_distance_km: number | null;
  nearest_protected_area_name: string | null;
  nearest_protected_area_distance_km: number | null;
  historical_incident_count: number;
  ai_detection_count: number;
  human_verified_incident_count: number;
  last_field_verification: string | null;
  recommended_action: string;
}

export interface EvidenceOut {
  id: string;
  incident_id: string;
  uploaded_by: string;
  file_type: string;
  original_filename: string;
  file_hash: string;
  file_size_bytes: number;
  captured_at: string | null;
  description: string | null;
  ai_analysis: { detections?: { label: string; confidence: number }[] } | null;
  verification_status: VerificationStatus;
  current_version: number;
  created_at: string;
}

export interface Region {
  id: string;
  name: string;
  capital: string | null;
}

export interface District {
  id: string;
  region_id: string;
  name: string;
  capital: string | null;
}

export interface AssistantResponse {
  question: string;
  detected_intent: string;
  answer: string;
  data: Record<string, unknown>[];
  row_count: number;
  model_name: string;
  model_version: string;
  insufficient_data: boolean;
}

export interface ReportOut {
  id: string;
  report_type: string;
  title: string;
  content_markdown: string;
  model_name: string;
  model_version: string;
  source_incident_ids: string[];
  created_at: string;
}

export interface AnalyticsSummary {
  incidents_over_time: { week: string; count: number }[];
  incidents_by_region: { region: string; count: number }[];
  incidents_by_status: { status: string; count: number }[];
  verification_rate: { verified: number; total: number };
  team_workload: { team: string; active: number; high_priority: number; overdue: number; completed: number }[];
}

export interface AuditLogEntry {
  id: string;
  user_id: string | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  previous_value: string | null;
  new_value: string | null;
  reason: string | null;
  created_at: string;
}

export interface AIDetectionOut {
  id: string;
  detection_type: string;
  confidence: number;
  estimated_area_hectares: number | null;
  observation_date: string;
  requires_verification: boolean;
  review_status: string;
  model_name: string;
  model_version: string;
}

export interface VoiceExtraction {
  time_mentioned: string | null;
  equipment_mentioned: string[];
  water_body_mentioned: string | null;
  activity_summary: string | null;
  status: string;
}

export interface VoiceReportTranscribeOut {
  field_report_id: string;
  transcript: string;
  extraction: VoiceExtraction;
  model_name: string;
  model_version: string;
}

export interface ObservationOut {
  provider: string;
  acquisition_date: string;
  resolution_m: number;
  cloud_coverage_pct: number;
  is_simulated: boolean;
}

export interface NearbyFeatureOut {
  name: string;
  distance_km: number;
}

export interface SatelliteScanResult {
  change_detected: boolean;
  is_simulated: boolean;
  ai_detection_id: string | null;
  latitude: number;
  longitude: number;
  region: string | null;
  district: string | null;
  risk_score: number;
  risk_category: RiskCategory;
  detection_type: string | null;
  confidence: number | null;
  estimated_area_hectares: number | null;
  first_detected_days_ago: number | null;
  nearest_water_body: NearbyFeatureOut | null;
  nearest_protected_area: NearbyFeatureOut | null;
  recommended_action: string;
  previous_observation: ObservationOut;
  current_observation: ObservationOut;
  model_name: string;
  model_version: string;
  requires_verification: boolean;
  disclaimer: string;
}

export interface SatelliteHistoryEntry {
  id: string;
  detection_type: string;
  confidence: number | null;
  estimated_area_hectares: number | null;
  observation_date: string;
  review_status: string;
  latitude: number;
  longitude: number;
}
