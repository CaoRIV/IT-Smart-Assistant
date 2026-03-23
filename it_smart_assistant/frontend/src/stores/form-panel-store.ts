import { create } from "zustand";

interface FormField {
  id: string;
  label: string;
  type: string;
}

interface ProcedureWorkflow {
  procedureId?: string;
  title: string;
  summary?: string;
  eligibility?: string[];
  requiredDocuments?: string[];
  steps?: string[];
  contactOffice?: string;
}

interface FormTemplate {
  templateId?: string | null;
  title?: string;
  description?: string;
  template: string;
  fields: FormField[];
  workflow?: ProcedureWorkflow | null;
}

interface FormPanelState {
  isOpen: boolean;
  formData: FormTemplate | null;
  openPanel: (data: FormTemplate) => void;
  closePanel: () => void;
}

export const useFormPanelStore = create<FormPanelState>((set) => ({
  isOpen: false,
  formData: null,
  openPanel: (data) => set({ isOpen: true, formData: data }),
  closePanel: () => set({ isOpen: false, formData: null }),
}));
