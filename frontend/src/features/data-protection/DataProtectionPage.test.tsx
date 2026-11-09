import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

import { Gate1ApprovalModal } from "./components/Gate1ApprovalModal";
import type { MaskingRun } from "./types";

describe("Gate1ApprovalModal", () => {
  const mockRun: MaskingRun = {
    id: "run-test-1234",
    workspace_id: "ws-1",
    dataset_id: "ds-1",
    dataset_version_id: "ver-1",
    source_dataset_digest: "a1b2c3d4e5f678901234567890abcdefa1b2c3d4e5f678901234567890abcdef",
    masking_profile_id: null,
    status: "COMPLETED",
    extraction_coverage: "EXTRACTION_COMPLETE",
    documents_processed: 5,
    documents_failed: 0,
    findings_count: 12,
    unresolved_findings_count: 0,
    masked_output_digest: "f6e5d4c3b2a109876543210987fedcbaf6e5d4c3b2a109876543210987fedcba",
    error_message: null,
    created_by: "user-1",
    started_at: new Date().toISOString(),
    completed_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  it("renders modal with cryptographic attestation details and digests", () => {
    render(
      <Gate1ApprovalModal
        run={mockRun}
        isOpen={true}
        onClose={vi.fn()}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        isSubmitting={false}
      />
    );

    expect(screen.getByText(/Gate 1 — Human Data Protection Approval/i)).toBeInTheDocument();
    expect(screen.getByText(/Immutable Ed25519 Platform Attestation/i)).toBeInTheDocument();
    expect(screen.getByText("Source Dataset Digest")).toBeInTheDocument();
    expect(screen.getByText("Masked Output Digest")).toBeInTheDocument();
  });

  it("disables approve button until certification checkbox is checked", () => {
    render(
      <Gate1ApprovalModal
        run={mockRun}
        isOpen={true}
        onClose={vi.fn()}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        isSubmitting={false}
      />
    );

    const approveButton = screen.getByRole("button", { name: /Sign & Approve Gate 1/i });
    expect(approveButton).toBeDisabled();

    // Check certification checkbox
    const checkbox = screen.getByRole("checkbox");
    fireEvent.click(checkbox);

    expect(approveButton).toBeEnabled();
  });

  it("requires override justification when coverage is OCR_REQUIRED", async () => {
    const ocrRun: MaskingRun = {
      ...mockRun,
      extraction_coverage: "OCR_REQUIRED",
    };

    const handleApprove = vi.fn();

    render(
      <Gate1ApprovalModal
        run={ocrRun}
        isOpen={true}
        onClose={vi.fn()}
        onApprove={handleApprove}
        onReject={vi.fn()}
        isSubmitting={false}
      />
    );

    expect(screen.getByText(/Coverage Warning: OCR_REQUIRED/i)).toBeInTheDocument();

    // Check certification checkbox
    fireEvent.click(screen.getByRole("checkbox"));

    // Click approve without filling override reason
    const approveButton = screen.getByRole("button", { name: /Sign & Approve Gate 1/i });
    fireEvent.click(approveButton);

    await waitFor(() => {
      expect(
        screen.getByText(/Extraction coverage requires OCR or manual verification/i)
      ).toBeInTheDocument();
    });
    expect(handleApprove).not.toHaveBeenCalled();
  });

  it("submits approval with decision reason when form is valid", async () => {
    const handleApprove = vi.fn().mockResolvedValue(undefined);

    render(
      <Gate1ApprovalModal
        run={mockRun}
        isOpen={true}
        onClose={vi.fn()}
        onApprove={handleApprove}
        onReject={vi.fn()}
        isSubmitting={false}
      />
    );

    // Enter reason
    const reasonInput = screen.getByPlaceholderText(/All UAE Emirates IDs/i);
    fireEvent.change(reasonInput, {
      target: { value: "All UAE IDs and contact numbers verified and masked." },
    });

    // Check checkbox
    fireEvent.click(screen.getByRole("checkbox"));

    // Click approve
    const approveButton = screen.getByRole("button", { name: /Sign & Approve Gate 1/i });
    fireEvent.click(approveButton);

    await waitFor(() => {
      expect(handleApprove).toHaveBeenCalledWith({
        decision_reason: "All UAE IDs and contact numbers verified and masked.",
        override_coverage_reason: undefined,
      });
    });
  });
});
