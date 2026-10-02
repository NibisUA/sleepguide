import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { Home } from "../features/dashboard/Home";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: true } },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Home />
    </QueryClientProvider>
  );
}
