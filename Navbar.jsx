import { Link, useNavigate } from "react-router-dom";
import { useCart } from "../context/CartContext";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import TokenCountdown from "./TokenCountdown";
import api from "../api";
import NotificationBell from "./NotificationBell";

export default function Navbar() {
  const { cartItems = [] } = useCart();
  const { user, setUser } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const navigate = useNavigate();

  const totalItems = cartItems.reduce(
    (sum, item) => sum + (item.qty || 1),
    0
  );

  const logout = async () => {
    try {
      await api.get("/api/logout");
    } catch (err) {
      console.log(err);
    }

    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");

    setUser(null);

    navigate("/login");
  };

  return (
    <div className="navbar">
      <h3>🛒 E-Commerce</h3>

      <div className="nav-links">
        <Link to="/">Home</Link>

        {user?.role !== "admin" && (
          <>
            <Link to="/cart">Cart ({totalItems})</Link>
            <Link to="/orders">My Orders</Link>
          </>
        )}

        {user?.role === "admin" && (
          <>
            <Link to="/admin/products">Products</Link>
            <Link to="/admin/orders">Orders</Link>
          </>
        )}

        {user && <Link to="/profile">Profile</Link>}

        {user?.role === "admin" && (
        <NotificationBell />
        )}

        <button className="btn-nav" onClick={toggleTheme}>
          {theme === "light" ? "🌙 Dark" : "☀️ Light"}
        </button>

        {!user ? (
          <Link
            to="/login"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              textDecoration: "none",
            }}
          >
            <img
              src="/default-avatar.png"
              alt="Default Avatar"
              style={{
                width: "38px",
                height: "38px",
                borderRadius: "50%",
                objectFit: "cover",
                border: "2px solid #ccc",
              }}
            />
            <span>Login</span>
          </Link>
        ) : (
          <>
            <Link
              to="/profile"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                textDecoration: "none",
                color: "inherit",
                marginRight: "10px",
              }}
            >
              <img
                src={
                  user.avatar_url
                    ? `http://127.0.0.1:5000${user.avatar_url}`
                    : "/default-avatar.png"
                }
                alt="Avatar"
                style={{
                  width: "40px",
                  height: "40px",
                  borderRadius: "50%",
                  objectFit: "cover",
                  border: "2px solid #ccc",
                }}
              />

              <span
                style={{
                  fontWeight: "bold",
                }}
              >
                {user.name}
              </span>
            </Link>

            <TokenCountdown />

            <button className="logout-btn" onClick={logout}>
              Logout
            </button>
          </>
        )}
      </div>
    </div>
  );
}