import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import "../lib/i18n";
afterEach(() => { cleanup(); sessionStorage.clear(); });
