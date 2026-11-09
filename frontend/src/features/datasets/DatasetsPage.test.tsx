import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { DocumentPreviewModal } from "./components/DocumentPreviewModal";
import { UploadDropzone } from "./components/UploadDropzone";
import type { Document } from "./types";

describe("DocumentPreviewModal", () => {
  const mockDoc: Document = {
    id: "doc-123",
    dataset_version_id: "ver-1",
    workspace_id: "ws-1",
    name: "employee_handbook.pdf",
    file_type: "PDF",
    mime_type: "application/pdf",
    raw_file_size_bytes: 2048576,
    raw_sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    extracted_text_sample: "Welcome to Mizan! This is the primary company code of conduct.",
    char_count: 62,
    word_count: 10,
    page_count: 5,
    extraction_status: "COMPLETED",
    extraction_error: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  it("renders document metadata, extracted sample, and word count", () => {
    render(<DocumentPreviewModal document={mockDoc} onClose={vi.fn()} />);

    expect(screen.getByText("employee_handbook.pdf")).toBeInTheDocument();
    expect(screen.getByText("PDF")).toBeInTheDocument();
    expect(screen.getByText("10 words")).toBeInTheDocument();
    expect(screen.getByText("5 pages")).toBeInTheDocument();
    expect(screen.getByText(/Welcome to Mizan/)).toBeInTheDocument();
    expect(screen.getByText("Copy Text")).toBeInTheDocument();
  });

  it("calls onClose when done button is clicked", () => {
    const handleClose = vi.fn();
    render(<DocumentPreviewModal document={mockDoc} onClose={handleClose} />);

    fireEvent.click(screen.getByRole("button", { name: "Done" }));
    expect(handleClose).toHaveBeenCalledOnce();
  });
});

describe("UploadDropzone", () => {
  it("renders file upload instructions and 25 MB limit", () => {
    render(
      <UploadDropzone
        workspaceId="ws-1"
        datasetId="ds-1"
        versionId="ver-1"
        onUploadSuccess={vi.fn()}
      />
    );

    expect(screen.getByText(/Click to upload/i)).toBeInTheDocument();
    expect(screen.getByText(/Max 25 MB per file/i)).toBeInTheDocument();
  });

  it("shows disabled state when disabled prop is true", () => {
    render(
      <UploadDropzone
        workspaceId="ws-1"
        datasetId="ds-1"
        versionId="ver-1"
        disabled={true}
        onUploadSuccess={vi.fn()}
      />
    );

    const input = screen.getByTestId("file-upload-input");
    expect(input).toBeDisabled();
  });
});
