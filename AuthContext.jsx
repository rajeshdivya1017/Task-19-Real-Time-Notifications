import { createContext, useContext, useEffect, useState } from "react";
import api from "../api";

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);


  const refreshUser = async () => {
    try {
      const res = await api.get("/api/me");
      setUser(res.data);
    } catch (err) {
      console.error("User refresh failed", err);

      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");

      setUser(null);
    }
  };


  useEffect(() => {

    const token = localStorage.getItem("access_token");

    if (token) {
      refreshUser();
    }

  }, []);



  return (
    <AuthContext.Provider
      value={{
        user,
        setUser,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}


export const useAuth = () => useContext(AuthContext);