import { invoke, isTauri } from "@tauri-apps/api/core";
import type { HealthData, SearchData, SearchRequest, TaxonomyTag } from "./contracts";

export type DataSource = "mock" | "local";

export const isDesktopRuntime = (): boolean => isTauri();

export async function getHealth(): Promise<HealthData> {
  return invoke<HealthData>("service_health");
}

export async function searchLocal(request: SearchRequest): Promise<SearchData> {
  return invoke<SearchData>("search", { request });
}

export async function getTaxonomy(): Promise<{ tags: TaxonomyTag[] }> {
  return invoke<{ tags: TaxonomyTag[] }>("taxonomy");
}
