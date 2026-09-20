import { describe, expect, it } from "vitest";

import { createGeneratedClient } from "@/lib/api/generated/client";
import type { components, operations, paths } from "@/lib/api/generated/schema";

type ProjectsList = operations["projects_list"];
type SubmitReport = operations["reports_submit"];
type ProblemDetails = components["schemas"]["ProblemDetails"];
type ProjectListPath = paths["/v1/projects"];
type Assert<Condition extends true> = Condition;
type ProjectsListHasResponses = Assert<"responses" extends keyof ProjectsList ? true : false>;
type SubmitReportHasBody = Assert<"requestBody" extends keyof SubmitReport ? true : false>;
type ProjectListHasGet = Assert<"get" extends keyof ProjectListPath ? true : false>;

describe("generated OpenAPI contract", () => {
  it("exposes the critical operations and problem shape without runtime network access", () => {
    const client = createGeneratedClient("http://api.internal-test.invalid");
    const structuralAssertions: [ProjectsListHasResponses, SubmitReportHasBody, ProjectListHasGet] =
      [true, true, true];
    const problemCode: ProblemDetails["code"] = "validation_failed";

    expect(client).toHaveProperty("GET");
    expect(structuralAssertions).toEqual([true, true, true]);
    expect(problemCode).toBe("validation_failed");
  });
});
