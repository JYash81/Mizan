export interface PilotRequest {
  fullName: string;
  workEmail: string;
  organization: string;
  teamSize: string;
  useCase: string;
  notes?: string;
}

export interface FaqItem {
  id: string;
  question: string;
  answer: string;
}

export interface PlatformCapability {
  id: string;
  number: string;
  title: string;
  summary: string;
  details: string[];
  badge: string;
}

export interface ProblemStatement {
  id: string;
  title: string;
  symptom: string;
  impact: string;
}

export interface LifecycleStage {
  number: string;
  name: string;
  summary: string;
  deliverable: string;
}

export interface Differentiator {
  id: string;
  title: string;
  summary: string;
  detail: string;
}
