/**
 * Domain types describing laptops and the recommendations built from them.
 * These mirror the shape the future backend/scoring pipeline will return —
 * the frontend never computes or hardcodes recommendation logic itself.
 */

export type RecommendationCategory =
  | "best_overall"
  | "budget_saver"
  | "power_future_proof";

export interface Laptop {
  id: string;
  brand: string;
  model: string;
  cpu: string;
  gpu?: string;
  ram: string;
  storage: string;
  display: string;
  price: number;
  /** ISO 4217 currency code, e.g. "USD". Defaults to "USD" when omitted. */
  currency?: string;
  productUrl?: string;
  imageUrl?: string;
}

export interface Recommendation {
  id: string;
  category: RecommendationCategory;
  laptop: Laptop;
  /** Backend-supplied explanation for why this laptop was picked. */
  reasoning?: string;
  /** Optional backend-computed match score, e.g. 0-100. */
  score?: number;
}
