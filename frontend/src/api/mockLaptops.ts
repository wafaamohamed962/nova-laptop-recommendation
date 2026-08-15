import type { Recommendation } from "../types/laptop";

/**
 * Fixture data standing in for a future backend scoring pipeline.
 * Isolated from the mock chat script so it's obvious what to delete
 * once real recommendations arrive from the backend.
 */
export const mockRecommendations: Recommendation[] = [
  {
    id: "rec-best-overall",
    category: "best_overall",
    score: 94,
    reasoning:
      "Balances a fast CPU, dedicated GPU, and a high-quality display within your stated budget and use case.",
    laptop: {
      id: "laptop-asus-zephyrus-g14",
      brand: "ASUS",
      model: "ROG Zephyrus G14",
      cpu: "AMD Ryzen 9 8945HS",
      gpu: "NVIDIA RTX 4070 8GB",
      ram: "32GB DDR5",
      storage: "1TB NVMe SSD",
      display: "14\" 2.8K 120Hz OLED",
      price: 1899,
      currency: "USD",
      productUrl: "https://www.asus.com/laptops/for-gaming/rog-zephyrus/",
    },
  },
  {
    id: "rec-budget-saver",
    category: "budget_saver",
    score: 82,
    reasoning:
      "Covers everyday productivity and light multitasking comfortably while keeping cost well under your ceiling.",
    laptop: {
      id: "laptop-lenovo-ideapad-slim5",
      brand: "Lenovo",
      model: "IdeaPad Slim 5",
      cpu: "AMD Ryzen 5 7530U",
      gpu: "AMD Radeon Graphics (integrated)",
      ram: "16GB DDR4",
      storage: "512GB NVMe SSD",
      display: "15.6\" FHD IPS 120Hz",
      price: 649,
      currency: "USD",
      productUrl: "https://www.lenovo.com/ideapad-slim-5",
    },
  },
  {
    id: "rec-power-future-proof",
    category: "power_future_proof",
    score: 97,
    reasoning:
      "Top-tier CPU/GPU and RAM headroom mean this stays capable for demanding workloads for years to come.",
    laptop: {
      id: "laptop-msi-raider-ge78hx",
      brand: "MSI",
      model: "Raider GE78HX",
      cpu: "Intel Core i9-14900HX",
      gpu: "NVIDIA RTX 4090 16GB",
      ram: "64GB DDR5",
      storage: "2TB NVMe SSD",
      display: "17\" QHD+ 240Hz Mini LED",
      price: 3499,
      currency: "USD",
      productUrl: "https://www.msi.com/Laptop/Raider-GE78HX-14V",
    },
  },
];
