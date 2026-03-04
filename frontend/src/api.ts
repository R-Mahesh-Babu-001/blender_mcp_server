export type JobEvent = {
  type: string;
  job_id: string;
  timestamp: string;
  payload: Record<string, unknown>;
};

export type JobStatus = {
  job_id: string;
  status: string;
  prompt: string;
  image_path?: string | null;
  result_path?: string | null;
  error?: string | null;
  created_at: string;
  updated_at: string;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export function getFileUrl(rawPath: string | null | undefined): string | null {
  if (!rawPath) {
    return null;
  }
  const normalized = rawPath.replaceAll("\\", "/");
  const marker = normalized.indexOf("/data/");
  if (marker >= 0) {
    return `${API_BASE_URL}/files${normalized.slice(marker + "/data".length)}`;
  }
  return null;
}

export async function createJob(prompt: string, file?: File | null): Promise<{ job_id: string; status: string }> {
  const formData = new FormData();
  formData.append("request_json", JSON.stringify({ prompt }));
  if (file) {
    formData.append("image", file);
  }

  const response = await fetch(`${API_BASE_URL}/api/jobs`, {
    method: "POST",
    body: formData
  });
  if (!response.ok) {
    throw new Error(`Failed to create job: ${response.status}`);
  }
  return response.json();
}

export async function getJob(jobId: string): Promise<JobStatus> {
  const response = await fetch(`${API_BASE_URL}/api/jobs/${jobId}`);
  if (!response.ok) {
    throw new Error(`Failed to load job ${jobId}`);
  }
  return response.json();
}

export function createEventSource(jobId: string): EventSource {
  return new EventSource(`${API_BASE_URL}/api/jobs/${jobId}/events`);
}
