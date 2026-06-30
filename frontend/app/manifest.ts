import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "FinSight — Personal Finance",
    short_name: "FinSight",
    description: "Personal finance intelligence for Canadians.",
    start_url: "/",
    display: "standalone",
    background_color: "#060b14",
    theme_color: "#0d9488",
    icons: [
      {
        src: "/icon.svg",
        sizes: "any",
        type: "image/svg+xml",
      },
      {
        src: "/apple-icon.svg",
        sizes: "180x180",
        type: "image/svg+xml",
      },
    ],
  };
}
