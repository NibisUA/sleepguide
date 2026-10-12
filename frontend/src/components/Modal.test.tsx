import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { Modal } from "./Modal";

it("traps keyboard focus, closes on Escape and restores the opener", async () => {
  const user = userEvent.setup();
  function Example() {
    const [open, setOpen] = useState(false);
    return <><button onClick={() => setOpen(true)}>Open</button>{open && <Modal title="Test" onClose={() => setOpen(false)}>
      <button>First</button><button>Last</button>
    </Modal>}</>;
  }
  render(<Example />);
  const opener = screen.getByRole("button", { name: "Open" });
  await user.click(opener);
  expect(document.activeElement).toBe(screen.getByRole("button", { name: "First" }));
  await user.tab({ shift: true });
  expect(document.activeElement).toBe(screen.getByRole("button", { name: "Last" }));
  await user.tab();
  expect(document.activeElement).toBe(screen.getByRole("button", { name: "First" }));
  expect(screen.getByRole("dialog").getAttribute("aria-modal")).toBe("true");
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(document.activeElement).toBe(opener);
  expect(document.body.style.overflow).toBe("");
});
