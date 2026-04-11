export function isTestProvider(provider: string): boolean {
  return provider.endsWith("_test") || provider === "mock_flights";
}

export function formatProviderLabel(provider: string): string {
  if (provider === "mock_flights") {
    return "Mock Data";
  }

  if (provider === "duffel_test") {
    return "Duffel Test";
  }

  if (provider === "amadeus_test") {
    return "Amadeus Test";
  }

  if (provider === "amadeus_live") {
    return "Amadeus Live";
  }

  return provider;
}
