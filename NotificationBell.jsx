import { useEffect, useState } from "react";
import { useSocket } from "../context/SocketContext";
import api from "../api";

function timeAgo(date) {

    console.log("NOTIFICATION DATE:", date);
    console.log("PARSED DATE:", new Date(date));
    console.log("CURRENT DATE:", new Date());
    

  const created = new Date(date);

  const now = new Date();

  const diff = now.getTime() - created.getTime();

  const seconds = Math.floor(diff / 1000);

  if (isNaN(seconds)) {
    return "Invalid date";
  }

  if (seconds < 60) {
    return "Just now";
  }

  const minutes = Math.floor(seconds / 60);

  if (minutes < 60) {
    return `${minutes} mins ago`;
  }

  const hours = Math.floor(minutes / 60);

  return `${hours} hours ago`;
}
export default function NotificationBell() {
  const { notifications } = useSocket();

  const [show, setShow] = useState(false);
  const [savedNotifications, setSavedNotifications] = useState([]);
  const [unread, setUnread] = useState(0);

  const loadNotifications = async () => {
    try {
      const res = await api.get("/api/notifications");

      setSavedNotifications(res.data);

      const unreadCount = res.data.filter(
        (n) => !n.is_read
      ).length;

      setUnread(unreadCount);

    } catch (err) {
      console.log(err);
    }
  };

  useEffect(() => {
    loadNotifications();
  }, []);

  useEffect(() => {
    if (notifications.length > 0) {
      loadNotifications();
    }
  }, [notifications]);

  const openNotifications = () => {
    setShow(!show);
  };

  const getIcon = (type) => {
    switch (type) {
      case "order":
        return "🛒";
      case "alert":
        return "⚠️";
      default:
        return "ℹ️";
    }
  };

  const markOneAsRead = async (id) => {
    try {
      await api.put(`/api/notifications/${id}/read`);

      setSavedNotifications((prev) =>
        prev.map((n) =>
          n.id === id
            ? { ...n, is_read: 1 }
            : n
        )
      );

      setUnread((c) => Math.max(0, c - 1));

    } catch (err) {
      console.log(err);
    }
  };

  const markAllAsRead = async () => {
    try {
      await api.put("/api/notifications/read-all");

      setSavedNotifications((prev) =>
        prev.map((n) => ({
          ...n,
          is_read: 1,
        }))
      );

      setUnread(0);

    } catch (err) {
      console.log(err);
    }
  };

  const deleteNotification = async (id) => {
    try {
      await api.delete(`/api/notifications/${id}`);

      setSavedNotifications((prev) =>
        prev.filter((n) => n.id !== id)
      );

    } catch (err) {
      console.log(err);
    }
  };

    return (
    <div className="notification-container">
      <button
        className="notification-btn"
        onClick={openNotifications}
      >
        🔔

        {unread > 0 && (
          <span className="notification-count">
            {unread}
          </span>
        )}
      </button>

      {show && (
        <div className="notification-dropdown">

          <div className="notification-header">
            <h4>Notifications</h4>

            {savedNotifications.length > 0 && (
              <button
                className="mark-all-btn"
                onClick={markAllAsRead}
              >
                ✓ Mark All
              </button>
            )}
          </div>

          {savedNotifications.length === 0 ? (
            <p>No Notifications</p>
          ) : (
            savedNotifications.map((n) => (
              <div
                key={n.id}
                className={`notification-item ${n.is_read ? "read" : "unread"}`}
                >
                <div
                  className="notification-message"
                  onClick={() => markOneAsRead(n.id)}
                >
                  <p>
                    <span style={{ marginRight: "8px" }}>
                      {getIcon(n.type)}
                    </span>

                    {n.message}
                  </p>

                 <small>
                    {timeAgo(n.created_at)}
                    </small>
                </div>

                <button
                  className="delete-btn"
                  onClick={() => deleteNotification(n.id)}
                >
                  🗑️
                </button>

              </div>
            ))
          )}

        </div>
      )}
    </div>
  );
}