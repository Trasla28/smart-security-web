"use client"; // This comment indicates this is used only in client-side code

import axios from "axios";
import { getSession, signOut } from "next-auth/react";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL + "/api/v1",
  headers: { "Content-Type": "application/json" },
  withCredentials: true, // to send refresh cookie
});

api.interceptors.request.use(async (config) => {
  const session = await getSession();
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    // _retry flag prevents infinite loops if the retry itself gets a 401
    if (error.response?.status === 401 && !error.config._retry) {
      error.config._retry = true;
      try {
        const refreshRes = await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/refresh`,
          {},
          { withCredentials: true }
        );
        const newToken: string = refreshRes.data.access_token;

        // Persist the new token into the NextAuth session so future requests
        // from getSession() receive the updated token
        await fetch("/api/auth/session", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ access_token: newToken }),
          credentials: "include",
        });

        // Use the new token directly in the retry without waiting for the
        // session cookie to propagate
        error.config.headers.Authorization = `Bearer ${newToken}`;
        return api(error.config);
      } catch {
        await signOut({ callbackUrl: "/login" });
      }
    }
    return Promise.reject(error);
  }
);

export default api;
