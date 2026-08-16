import type { Recommendation } from "../../types/laptop";
import { formatPrice } from "../../utils/format";
import { CategoryBadge } from "./CategoryBadge";

interface RecommendationCardProps {
  recommendation: Recommendation;
}

const SPEC_ROWS: { key: keyof Recommendation["laptop"]; label: string }[] = [
  { key: "cpu", label: "CPU" },
  { key: "gpu", label: "GPU" },
  { key: "ram", label: "RAM" },
  { key: "storage", label: "Storage" },
  { key: "display", label: "Display" },
];

export function RecommendationCard({ recommendation }: RecommendationCardProps) {
  const { laptop, reasoning } = recommendation;

  return (
    <div className="flex w-full flex-col gap-4 rounded-2xl border border-border bg-surface-elevated p-5 transition-colors hover:border-border-strong">
      <div className="flex flex-col gap-2">
        <CategoryBadge category={recommendation.category} />
        <div>
          <p className="text-sm text-text-muted">{laptop.brand}</p>
          <h3 className="text-lg font-semibold text-text-primary">{laptop.model}</h3>
        </div>
      </div>

      <dl className="grid grid-cols-1 gap-x-4 gap-y-1.5 text-sm sm:grid-cols-2">
        {SPEC_ROWS.map(({ key, label }) => {
          const value = laptop[key];
          if (!value) return null;
          return (
            <div key={key} className="flex justify-between gap-3 border-b border-border/60 py-1 sm:justify-start">
              <dt className="text-text-muted">{label}</dt>
              <dd className="text-right text-text-secondary sm:text-left">{value}</dd>
            </div>
          );
        })}
      </dl>

      {reasoning && (
        <p className="rounded-xl bg-surface px-3 py-2.5 text-sm leading-relaxed text-text-secondary">
          {reasoning}
        </p>
      )}

      <div className="mt-auto flex items-center justify-between gap-3 pt-1">
        <span className="text-xl font-semibold text-text-primary">
          {formatPrice(laptop.price, laptop.currency)}
        </span>
        {laptop.productUrl && (
          <a
            href={laptop.productUrl}
            target="_blank"
            rel="noreferrer noopener"
            className="rounded-full border border-accent-500/40 px-4 py-2 text-sm font-medium text-accent-400 transition-colors hover:bg-accent-500/10"
          >
            View product
          </a>
        )}
      </div>
    </div>
  );
}
