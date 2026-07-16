import { createContext, useContext, useEffect, useState } from "react";
import { io } from "socket.io-client";
import { useAuth } from "./AuthContext";

const SocketContext = createContext();

export function SocketProvider({ children }) {
  const { user } = useAuth();

  const [socket, setSocket] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (!user) return;

    const s = io("http://localhost:5000");

    setSocket(s);

    s.on("connect", () => {
      console.log("✅ Socket Connected");

      s.emit("join", {
        user_id: user.id,
        role: user.role,
      });
    });

    s.on("joined", (data) => {
      console.log(data);
    });

    s.on("new_notification", (data) => {
      console.log("🔥 Notification Received", data);
      alert("Notification Received");
      setNotifications((prev) => [
        {
          ...data,
          id: Date.now(),
          is_read: false,
        },
        ...prev,
      ]);

      setUnreadCount((c) => c + 1);
    });

    return () => {
      s.disconnect();
    };
  }, [user]);

  return (
    <SocketContext.Provider
      value={{
        socket,
        notifications,
        unreadCount,
      }}
    >
      {children}
    </SocketContext.Provider>
  );
}

export const useSocket = () => useContext(SocketContext);