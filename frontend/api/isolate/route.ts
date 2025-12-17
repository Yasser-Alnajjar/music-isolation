import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const formData = await req.formData();
  const file = formData.get("file") as File;
  const removeVocals = formData.get("removeVocals") === "true";

  const backendUrl = process.env.BACKEND_URL || "http://backend:8000/isolate";

  const res = await fetch(backendUrl, {
    method: "POST",
    body: (() => {
      const data = new FormData();
      data.append("file", file);
      data.append("remove_vocals", String(removeVocals));
      return data;
    })(),
  });

  const data = await res.json();
  return NextResponse.json(data);
}
