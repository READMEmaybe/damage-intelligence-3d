export type Action = "repair" | "replace" | "assess";
export type ActionSource = "explicit" | "inferred" | "insufficient_information";
export type Severity = "leicht" | "mittel" | "schwer" | null;
export type Archetype = "hatchback" | "wagon" | "suv" | "mpv" | "transporter";

export interface Damage {
  zone: string;
  action: Action;
  action_source: ActionSource;
  confidence: number;
  reason: string;
  evidence: string;
}

export interface ViewerCase {
  id: string;
  case_id: number;
  vehicle_make: string;
  vehicle_model: string;
  vehicle_archetype: Archetype;
  case_type: "damage" | "service";
  case_kind: string;
  severity: Severity;
  reasoning_status: string;
  created_at: string;
  freitext: string;
  damages: Damage[];
}
