"use client";

import React, { use } from "react";
import { useParams } from "next/navigation";
import { FspCreateCourse } from "../_components";

interface PageProps {
  params: Promise<{ format: string }> | { format: string };
}

export default function BuildFormatPage({ params }: PageProps) {
  // Support both Promise params in Next 15 and useParams fallback
  const resolvedParams =
    params && "then" in params && typeof (params as Promise<{ format: string }>).then === "function"
      ? use(params as Promise<{ format: string }>)
      : (params as { format?: string });
  const clientParams = useParams();
  const format = resolvedParams?.format || (clientParams?.format as string) || "course";

  return <FspCreateCourse formatParam={format} />;
}
