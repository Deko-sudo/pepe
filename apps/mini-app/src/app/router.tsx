import { createBrowserRouter, RouteObject } from "react-router-dom";
import { AppLayout } from "./layout";
import { Dashboard } from "@/pages/dashboard";
import { Markets } from "@/pages/markets";
import { Reports } from "@/pages/reports";
import { Settings } from "@/pages/settings";

const routes: RouteObject[] = [{
  element: <AppLayout />,
  children: [{
    path: "/",
    element: <Dashboard />,
  },
  {
    path: "/markets",
    element: <Markets />,
  },
  {
    path: "/reports",
    element: <Reports />,
  },
  {
    path: "/settings",
    element: <Settings />,
  }],
}];

export const router = createBrowserRouter(routes);
