/**
 * Thin fetch wrapper shared by all real API service implementations.
 * The base URL comes from an environment variable so no part of the app
 * ever hardcodes a host — see .env.example for VITE_API_BASE_URL.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiFetch<TResponse>(
  path: string,
  options?: RequestInit,
): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new ApiError(
      body || `Request to ${path} failed with status ${response.status}`,
      response.status,
    );
  }

  return (await response.json()) as TResponse;
}
