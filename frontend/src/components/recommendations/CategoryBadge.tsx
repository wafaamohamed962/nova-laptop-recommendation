import type { RecommendationCategory } from "../../types/laptop";

const CATEGORY_LABELS: Record<RecommendationCategory, string> = {
  best_overall: "Best Overall Match",
  budget_saver: "Budget Saver",
  power_future_proof: "Power / Future-Proof Pick",
};

interface CategoryBadgeProps {
  category: RecommendationCategory;
}

export function CategoryBadge({ category }: CategoryBadgeProps) {
  return (
    <span className="inline-flex w-fit items-center gap-1.5 rounded-full border border-accent-500/30 bg-accent-500/10 px-3 py-1 text-xs font-medium text-accent-400">
      <span className="h-1.5 w-1.5 rounded-full bg-accent-400" />
      {CATEGORY_LABELS[category]}
    </span>
  );
}
